#pragma once

// types.h is staged from the unchanged upstream defs.h by assemble.py.
#include "types.h"
#include "pup_stl.h"

// No new serialization type: this is exactly the original std::string.
using LeanMDLogPath = std::string;
