# LeanMD incremental Charm# port

This is a **partial migration**, with a LeanMD-specific build adapter. The
compiler is unchanged. Native Charm# owns the `Main`, 3D `Cell`, and 6D `Compute`
class declarations, their three entry constructors, `Cell::createComputes`,
and twelve readonly globals. Ordinary C++ members, migration constructors,
PUP routines and numerical kernels retain their original implementations.

All three SDAG `run()` routines, their receive declarations and reduction
attributes, the migratable-mainchare flag, variable-size message metadata,
`CellMap` registration and `std::string` readonly metadata remain in
`legacy.ci.in`. No claim is made that these have been migrated to native
Charm# syntax. `ParticleDataMsg` and `CellMap` remain ordinary C++ in the `.csh`
source; putting them in this file does not make them native Charm# declarations.

## Pinned inputs

- LeanMD: `UIUC-PPL/leanmd` at `dfb51ac438be30370fa2f71869d6d9f4ef0e7b31`.
- Charm#: `dmorganb/charmsharp` at `0e2e0280f252598f9de48159320be55c3d20d703`.
- Runtime validation target: Charm++ `v8.0.0`, multicore Linux x86-64.

The twelve original repository files are unchanged. `upstream-files.json`
records their Git blob hashes and the translation tests verify all of them.
Root `make` still builds the original program.

## Build and test

Build the pinned Charm# compiler in a separate checkout. Then, from this
repository root:

```sh
python3 charmsharp/test_migration.py --compiler /absolute/path/to/charmsharp/build/charmsharp
make -C charmsharp CHARMSHARP=/absolute/path/to/charmsharp/build/charmsharp CHARMC=/absolute/path/to/charmc
./charmsharp/build/leanmd +p2 4 4 4 21 3 3 +balancer GreedyLB
```

`make -C charmsharp generate CHARMSHARP=...` only requires the transpiler and
Python 3. The complete comparison, requiring a multicore Charm++ toolchain:

```sh
python3 charmsharp/runtime_check.py --compiler /absolute/path/to/charmsharp/build/charmsharp --charmc /absolute/path/to/charmc
```

The runtime script builds an untouched reference in a temporary directory,
builds the hybrid, and checks both for the expected step count and successful
energy conservation. It tests 1 and 2 PEs, normal force exchange, particle
migration at step 20, and repeated load-balancing synchronization. It is a
completion/invariant comparison, **not** a particle-by-particle trajectory or
performance comparison. Checkpoint/restart and injected process failure still
need separate runtime tests. Use `CI_FLAGS=-DCMK_MEM_CHECKPOINT=1` only with a
compatible fault-tolerant runtime configuration; that configuration is untested.

## Why an adapter is required

Charm# currently emits one complete `.ci` module and one `.cpp` per input.
It cannot natively merge legacy and generated entries belonging to the same
parallel class, or place required user types before the generated `.decl.h`.
Simply compiling both complete interfaces would duplicate registrations.

`assemble.py` performs an explicit, project-specific composition:

1. Translate `leanmd.csh` unchanged with the pinned compiler.
2. Extract the generated class kinds, four entries, and twelve readonly
   declarations into marked slots in `legacy.ci.in`. Preserve `[migratable]`
   and every legacy SDAG body. Compile only the assembled interface.
3. Keep the compiler-produced `.cpp` byte-for-byte. Stage the original method
   bodies as `.inc` files, removing only superseded headers and readonly
   definitions. There are no hand-edited generated state machines.
4. Stage the original value types/constants as `types.h` and force-include it
   before the generated `.decl.h`. Compile the generated program as one C++
   translation unit with one final `.def.h` inclusion.

This adapter is evidence of a missing frontend integration feature. It is
not a general migration tool, a compiler patch, or a native separate-module
solution. It deliberately stops on unexpected generated declaration counts.

## Validation status when authored

- Pinned compiler: 419 checks and CLI tests passed locally.
- Port translates; eight isolated coverage probes pass their expected outcomes.
- Assembled interface and all SDAG tokens match upstream, allowing only
  readonly-declaration ordering, whitespace and comments to differ.
- All twelve original files match their upstream Git blob hashes.
- Python scripts compile successfully.
- No local Charm++ toolchain was available. Native compile/run results must
  be read from the `Incremental CharmSharp port` workflow; do not treat
  successful source translation as runtime validation.

See [LIMITATIONS.md](LIMITATIONS.md) for observed blockers and next steps.
