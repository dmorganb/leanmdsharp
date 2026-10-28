// Incremental LeanMD port. Unsupported metadata and SDAG live in legacy.ci.in.
// Build with Makefile in this directory; see README.md for the assembly adapter.
#include "types.h"
#include "ckmulticast.h"
#include <string>
#include <vector>
#include <cmath>

readonly CProxy_Main mainProxy;
readonly CProxy_Cell cellArray;
readonly CProxy_Compute computeArray;
readonly int cellArrayDimX;
readonly int cellArrayDimY;
readonly int cellArrayDimZ;
readonly int finalStepCount;
readonly int firstLdbStep;
readonly int ldbPeriod;
readonly int checkptFreq;
readonly int checkptStrategy;
readonly int bFactor;
// Complex readonly metadata remains in the legacy interface.
std::string logs;

//data message to be sent to computes
struct ParticleDataMsg : public CkMcastBaseMsg, public CMessage_ParticleDataMsg {
  vec3* part; //list of atoms
  int lengthAll;  //length of list
  int x, y, z;    // (x,y,z) coordinate of cell sending this message

  ParticleDataMsg(const int x_, const int y_, const int z_, const int numPos)
    : x(x_), y(y_), z(z_), lengthAll(numPos) { }

  void pup(PUP::er &p){
    CMessage_ParticleDataMsg::pup(p);
    p | lengthAll;
    p | x; p | y; p | z;
    if (p.isUnpacking()) part = new vec3[lengthAll];
    PUParray(p, part, lengthAll);
  } 
};

class CellMap : public CkArrayMap {
  int num_x, num_y, num_z, num_yz;
  float ratio;
  public:
  CellMap(int num_x_, int num_y_, int num_z_) : 
    num_x(num_x_), num_y(num_y_), num_z(num_z_) 
  {
    num_yz = num_y * num_z;
    ratio = ((float)CkNumPes())/(num_x * num_yz);
  }
  CellMap(CkMigrateMessage *m) {}
  int registerArray(CkArrayIndex& numElements, CkArrayID aid) {
    return 0;
  }
  int procNum(int arrayHdl, const CkArrayIndex &idx) {
    int *index =(int *)idx.data();
    int patchID = index[2] + index[1] * num_z + index[0] * num_yz;
    return (int)(patchID * ratio);
  }
};


mainchare Main {
  private:
    Main_SDAG_CODE
    double startBenchmarkTime;

  public:
entry:
    Main(CkArgMsg* msg);
public:
    Main(CkMigrateMessage* msg);
    void pup(PUP::er &p);
};

array [3D] chare Cell {
private:
  Cell_SDAG_CODE;

  // list of atoms
  std::vector<Particle> particles;
  // my compute locations
  std::vector<CkArrayIndex6D> computesList;
  // to count the number of steps, and decide when to stop
  int stepCount;
  // number of atoms in my cell
  int myNumParts;
  // number of interacting neighbors
  int inbrs;
  double stepTime;
  int updateCount;
  // store kinetic energy - initial and final
  double energy[2];
  int numReadyCheckpoint;
  void migrateToCell(Particle p, int &px, int &py, int &pz);
  // updates properties after receiving forces from computes
  void updateProperties(vec3 *forces);
  // limit velcities to an upper limit
  void limitVelocity(Particle &p);
  // particles going out of right enters from left
  Particle& wrapAround(Particle &p);
  // handle to section proxy of computes
  CProxySection_Compute mCastSecProxy;

public:
entry:
  Cell();
  void createComputes();
public:
  Cell(CkMigrateMessage *msg);
  ~Cell();
  void createSection();   //created multicast section of computes
  void migrateParticles();
  void sendPositions();
  void startCheckpoint(int);
  void pup(PUP::er &p);
};

array [6D] chare Compute {
  private:
    Compute_SDAG_CODE
    int stepCount;  //current step number
    double energy[2]; //store potential energy
    //handles to differentiate the two multicast sections I am part of
    CkSectionInfo mcast1;     
    CkSectionInfo mcast2;

  public:
entry:
    Compute();
public:
    Compute(CkMigrateMessage *msg);
    void pup(PUP::er &p);

    void selfInteract(ParticleDataMsg *msg);
    void interact(ParticleDataMsg *msg1, ParticleDataMsg *msg2);
};

// Staged verbatim implementations, with obsolete includes/readonly definitions removed.
#include "Main.inc"
#include "Cell.inc"
#include "Compute.inc"
