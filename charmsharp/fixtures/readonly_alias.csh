// Isolate the newly migrated readonly from checkpoint/restart semantics.
// Compile with -include compat_types.h, as with the LeanMD application.
#include "compat_types.h"
#include <type_traits>
static_assert(std::is_same<LeanMDLogPath, std::string>::value,
              "The port must retain the original readonly type");

readonly LeanMDLogPath logs;
readonly CProxy_Main mainProxy;

mainchare Main {
entry:
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

array [1D] chare LogReader {
entry:
    LogReader() {
        if (logs != "checkpoints/LeanMD run") CkAbort("readonly string mismatch");
        CkPrintf("READONLY_OK index=%d pe=%d\n", thisIndex, CkMyPe());
        contribute(CkCallback(CkIndex_Main::done(), mainProxy));
    }
};
