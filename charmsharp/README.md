# LeanMD incremental Charm# port

This is a **partial migration**, with a LeanMD-specific build adapter. The
compiler is unchanged. Native Charm# owns the `Main`, 3D `Cell`, and 6D `Compute`
class declarations, their three entry constructors, `Cell::createComputes`,
and all thirteen readonly globals (the string uses a standard C++ alias). Ordinary C++ members, migration constructors,
PUP routines and numerical kernels retain their original implementations.

All three SDAG `run()` routines, their receive declarations and reduction
attributes, the migratable-mainchare flag, variable-size message metadata,
`CellMap` registration remain in `legacy.ci.in`. No claim is made that these have been migrated to native
Charm# syntax. `ParticleDataMsg` and `CellMap` remain ordinary C++ in the `.csh`
source; putting them in this file does not make them native Charm# declarations.

## Pinned inputs

- LeanMD: `UIUC-PPL/leanmd` at `dfb51ac438be30370fa2f71869d6d9f4ef0e7b31`.
- Charm#: `dmorganb/charmsharp` at `b45b2a0c50cb82653b0f3ee303f4dadc7324777f` (Phase 6 complete subset).
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
2. Extract the generated class kinds, four entries, and thirteen readonly
   declarations into marked slots in `legacy.ci.in`. Preserve `[migratable]`
   and every legacy SDAG body. Compile only the assembled interface.
3. Keep the compiler-produced `.cpp` byte-for-byte. Stage the original method
   bodies as `.inc` files, removing only superseded headers and readonly
   definitions. There are no hand-edited generated state machines.
4. Stage the original value types/constants as `types.h` and force-include `compat_types.h`
   before the generated `.decl.h`. This small authored header defines
   `LeanMDLogPath = std::string`, retaining the original readonly type. Compile the generated program as one C++
   translation unit with one final `.def.h` inclusion.

This adapter is evidence of a missing frontend integration feature. It is
not a general migration tool, a compiler patch, or a native separate-module
solution. It deliberately stops on unexpected generated declaration counts.

## Validation status and scope

The original migration in PR #1 passed native compile/run checks against
Charm++ v8.0.0. This follow-up pins the completed Phase 6 compiler, moves the
remaining `logs` readonly metadata into Charm#, and revalidates the hybrid.
This alias-based migration was also accepted by the old compiler: it is a
newly validated use of existing syntax, not a feature unlocked by Phase 6.

- Pinned compiler: 546 checks and CLI tests passed locally.
- Twelve coverage probes record accepted/rejected forms, including the unchanged
  blockers and an inferred-receive validation inconsistency.
- The assembled interface and SDAG tokens match the original after one exact,
  reviewed normalization of `readonly LeanMDLogPath logs` to `std::string`.
  The runtime alias fixture also checks the C++ types are identical.
- All twelve original files still match upstream Git blob hashes.
- Native compile/run results for this revision must be read from the PR's
  `Incremental CharmSharp port` workflow. They are pending at PR creation.

The runtime comparison retains eight original/hybrid executions (1/2 PEs,
5/21 steps). A second, independent pair compares non-empty readonly string
broadcast using `std::string` in handwritten Charm++ and the alias in Charm#.
This checks that the newly migrated global is actually initialized and read
on both PEs, even though the short LeanMD runs do not checkpoint. Logs and a
JSON result summary are uploaded as `leanmd-runtime-evidence`.

The workflow runs on PRs, manual dispatch, and pushes to `master`; it no longer
runs twice for each PR branch push. It preserves the pinned Charm++ cache.

See [LIMITATIONS.md](LIMITATIONS.md) for the updated compatibility assessment,
concrete reproductions, classifications, and recommended priorities.
