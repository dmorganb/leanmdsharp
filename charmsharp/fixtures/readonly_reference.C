#include <string>
#include "ReadonlyReference.decl.h"

std::string logs;
CProxy_Main mainProxy;

class Main : public CBase_Main {
public:
    Main(CkArgMsg* msg) {
        delete msg;
        logs = "checkpoints/LeanMD run";
        mainProxy = thisProxy;
        CProxy_LogReader::ckNew(2);
    }
    void done() {
        CkPrintf("READONLY_DONE\n");
        CkExit();
    }
};

class LogReader : public CBase_LogReader {
public:
    LogReader() {
        if (logs != "checkpoints/LeanMD run") CkAbort("readonly string mismatch");
        CkPrintf("READONLY_OK index=%d pe=%d\n", thisIndex, CkMyPe());
        contribute(CkCallback(CkIndex_Main::done(), mainProxy));
    }
};

#include "ReadonlyReference.def.h"
