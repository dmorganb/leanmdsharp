# LeanMD compatibility assessment after Phase 6

Assessment date: 2026-10-28 (Costa Rica).

- Compiler: [`b45b2a0c50cb82653b0f3ee303f4dadc7324777f`](https://github.com/dmorganb/charmsharp/tree/b45b2a0c50cb82653b0f3ee303f4dadc7324777f).
- Previous migration: [merged PR #1](https://github.com/dmorganb/leanmdsharp/pull/1),
  merge `180ed2cfa9b0c7f1df03bf69872fc9a4a6542ed9`.
- Original LeanMD: `UIUC-PPL/leanmd` at `dfb51ac438be30370fa2f71869d6d9f4ef0e7b31`.
- Native validation target: Charm++ v8.0.0, multicore Linux x86-64.

## Finding

**None of the seven formerly rejected source forms is directly unblocked by
Phase 6.** All seven still produce the same diagnostics. The original hybrid
translates successfully with the new compiler. The prior compiler pin was
`0e2e0280f252598f9de48159320be55c3d20d703`; its successful native run remains
[available here](https://github.com/dmorganb/leanmdsharp/actions/runs/40625755396).

Phase 6 adds entry attributes and scalar chare templates, registrations, shared
template headers and a tested separate C++ consumer. LeanMD has no templated
chares. Its explicit entry attribute is `reductiontarget`, already supported;
`[migratable]` applies to the mainchare itself. Do not add templates or change
message ownership/scheduling just to exercise the new syntax.

The additional port moves `logs` to `readonly LeanMDLogPath logs;`, with a
standard C++ alias to `std::string` in an explicitly included compatibility
header. This also translates with the old compiler. It is a useful migration
of an existing supported form, not evidence that Phase 6 added qualified
readonly support. All thirteen readonly globals now have generated metadata.
The three SDAG routines remain legacy.

## Prioritized blockers and classifications

Priorities indicate value for this application, not a commitment to extend the
compiler. Every change to Charm# requires separate discussion first.

| Priority | Concrete requirement | Classification and observed result | Suggested scope |
| --- | --- | --- | --- |
| P1 | `when energySum(...) when energySum(...)` and paired `calculateForces` receives | Missing supported language form: chained body rejected; braced nested form explicitly rejected | Nested receive scopes and ownership/lifetime validation unblock Main and Compute SDAG. |
| P1 | `reduceForces(vec3 forces[n], int n)` | Missing supported entry form: custom array type and trailing length each rejected | Serializable named element types and forward length references; retain original ABI/order. |
| P1 | Explicit versus inferred `reduceForces` array validation | Transpiler validation bug/inconsistency: inferred receive accepted while explicit declaration rejected | Align validation paths. No demonstrated runtime miscompilation; do not rely on this undocumented acceptance. |
| P1 | Complete interface split between `leanmd.csh` and legacy SDAG | Build/source model limitation: no same-class fragment composition | A narrow explicit fragment/dependency contract would remove custom assembly; general whole-program analysis is unnecessary for this case. |
| P1 | Value types before generated `.decl.h` | Build/source model limitation: emitter still prepends `.decl.h` before user includes | Explicit dependency/prelude placement could replace forced includes. Template headers do not resolve this non-template dependency. |
| P2 | `message ParticleDataMsg { vec3 part[]; }` | Missing supported language form: variable-size field rejected | Preserve allocation, multicast base and PUP behavior; validate all together before porting. |
| P2 | `mainchare [migratable] Main` | Missing chare attribute: parser expects a name | Object-level metadata; new entry attributes do not apply. |
| P2 | `group CellMap : public CkArrayMap` | Missing external-base resolution and unvalidated special runtime-base integration | Current parser rejects the external base. Do not insert a fake local definition: generated multiple inheritance would require independent validation. |
| P2 | `#if CMK_MEM_CHECKPOINT` around SDAG control flow | Preprocessing/SDAG integration boundary: source rejected with an ordinary-statement diagnostic | Define preprocessing order; test both branches. No need to add a new runtime mechanism. |
| P3 | `readonly std::string logs` | Direct qualified spelling still rejected; standard C++ alias is supported | Alias-based migration avoids a language change; broader qualified-type recognition is optional convenience here. |

## Minimal source reproductions

`test_migration.py` runs twelve probes, including all rejection examples below,
the positive dimensions/alias cases, and the inferred-array discrepancy. These
are isolated translation probes, not executable programs or serialization proofs.

### Nested/chained receives — missing language subset

LeanMD's `leanmd.ci`, Main and Compute `run()` routines, needs this shape:

```cpp
chare Compute {
entry:
    void run() {
        when calculateForces(ParticleDataMsg *msg1)
        when calculateForces(ParticleDataMsg *msg2) { interact(msg1, msg2); }
    }
};
```

Diagnostic: `expected SDAG receive body`. Adding braces around the second wait
produces `nested SDAG awaits are deferred`. Flattening the receives would require
persistent storage for `msg1`, ownership handling and migration serialization;
that is not a mechanical syntax conversion. Preserve the original SDAG.

### Force-array signature — two independent subset limits

```cpp
array [3D] chare Cell {
entry:
    void reduceForces(int n, vec3 forces[n]); // custom type rejected
};
```

Diagnostic: `unsupported marshalled array element type`.

```cpp
array [3D] chare Cell {
entry:
    void reduceForces(double forces[n], int n); // trailing length rejected
};
```

Diagnostic: `marshalled array bound must name an earlier integer parameter`.
The actual LeanMD signature combines both restrictions and has
`[reductiontarget]`. Replacing vec3 with double or reordering parameters would
change the original callback/marshalling contract, so this port does neither.

### Inferred receive — inconsistent validation, not a supported workaround

```cpp
array [3D] chare Cell {
entry:
    void run() {
        when reduceForces(vec3 forces[n], int n) { updateProperties(forces); }
    }
};
```

This translates and infers `entry void reduceForces(vec3 forces[n], int n);`.
In `src/translator.cpp`, explicit entries call `analyze_entry_arrays`, whereas
`analyze_sdag_node` records inferred signatures without the equivalent check.
The failure/acceptance asymmetry exists with both old and new compiler pins.
This fixture does not provide the reduction-target metadata LeanMD requires.
It does not establish custom-array support or justify bypassing the explicit
signature diagnostic. Aligning validation is a correctness/diagnostic follow-up,
separate from deciding to expand the supported array subset.

### Variable-size message — missing language subset

```cpp
message ParticleDataMsg { public: vec3 part[]; };
```

Diagnostic: `variable-size message arrays are deferred`. In the application,
`Cell.h` also gives this message a `CkMcastBaseMsg` base, coordinates, length,
and a PUP routine; `Cell.cc` uses variable-size message allocation. Its legacy
interface metadata and ordinary C++ implementation remain together.

### Migratable mainchare — missing object attribute

```cpp
mainchare [migratable] Main { entry: Main(CkArgMsg* msg); };
```

Diagnostic: `expected a parallel type name`. Native `[[charm::...]]` support
is for entry methods, not this object-level flag. Preserve `[migratable]` in
the assembled interface rather than silently dropping it.

### External map base — missing resolution and integration validation

```cpp
#include "charm++.h"
group CellMap : public CkArrayMap {
entry:
    CellMap(int x, int y, int z);
};
```

Diagnostic: `unresolved or later-defined C++ base type`. The real `CellMap` in
`Cell.h` remains ordinary C++, deriving only from `CkArrayMap`; it is not a
native Charm# group declaration. Treating the runtime base as an ordinary local
base would additionally introduce `CBase_CellMap`, which needs validation.

### Conditional SDAG — preprocessing integration boundary

```cpp
chare Worker {
entry:
    void run() {
        when ready() {}
#if CMK_MEM_CHECKPOINT
        if (stepCount == 60) serial { CkDieNow(); }
#endif
    }
};
```

Diagnostic: `expected ';' in ordinary statement`. The reduced example isolates
the same directive placement as Cell's fault-injection block. The port preserves
the actual directives in legacy `.ci` for Charmxi preprocessing. The diagnostic
could be improved, but rejection of this unsupported form is not evidence of
runtime failure.

### Readonly string — migrated with existing alias syntax

Rejected directly:

```cpp
readonly std::string logs;
```

Accepted alternative:

```cpp
// compat_types.h, visible before generated .decl.h
using LeanMDLogPath = std::string;
// leanmd.csh
readonly LeanMDLogPath logs;
```

The C++ type is unchanged; no wrapper, custom PUP method or manual conversion is
introduced. The alias fixture uses `static_assert` on type identity and compares
a non-empty string broadcast on 1/2 PEs with an independent handwritten Charm++
reference. This does not test filesystem checkpoint/restart.

### Interface composition and include ordering — build model limitations

Source shape still requiring the adapter:

```cpp
// leanmd.csh owns this entry and class:
array [3D] chare Cell { entry: Cell(); /* ordinary members omitted */ };
// legacy .ci also owns Cell's SDAG run and receive metadata:
// array [3D] Cell { entry void run() { ... }; ... };
```

Compiling both complete class interfaces would duplicate declarations and
registrations. `assemble.py` explicitly composes one interface. Similarly,
ordinary `#include "defs.h"` in a `.csh` cannot establish `vec3` before the
emitter's prepended `#include "leanmd.decl.h"`; `compat_types.h` is force-included
instead. The Phase 6 `_templates.h` feature applies to actual chare templates,
not to these arbitrary non-template dependencies.

## Runtime constraints versus frontend limits

No new Charm++ v8.0.0 runtime incompatibility is established by these rejection
probes: the original program already compiles/runs with the target toolchain.
Its existing SDAG/PUP behavior is retained, including message deletion in
`Compute::selfInteract`/`interact`. Adding `nokeep` would change that ownership
contract and is not an appropriate migration convenience.

The compiler documents a Charmxi-generated continuation scope limitation for
loop-local indices across waits. LeanMD already uses persistent members
`stepCount` and `updateCount`, so that known constraint does not currently block
this port. General overlapping-invocation/lifetime proof is outside this test.

Checkpoint/restart, memory-fault injection, different network builds, and
particle-by-particle trajectory equivalence remain untested. They are validation
gaps, not observed runtime defects. Do not classify the unsupported Charm#
`[migratable]` spelling as a lack of checkpoint support in Charm++ itself.

## Evidence and recommendations

Local evidence: the new compiler passes 546 checks plus CLI tests; the old and
new pins both pass the twelve migration probes with the documented outcomes.
All twelve original repository files retain their upstream Git blob hashes.
CI pins both toolchains and checks native compilation, eight application runs,
and four readonly-reference/alias runs. See the PR's current CI results for
runtime status; no runtime success is assumed merely from translation.

Recommended next discussion: nested receive semantics and the explicit-array
subset would unlock much larger portions than further template work. Decide
whether those additions serve the small source-to-source design, then implement
independent Charm++ comparisons before migrating the affected SDAG routines.
The validation-path discrepancy can be fixed independently without adding a
language feature. A narrow explicit dependency/interface composition mechanism
would improve incremental migration beyond LeanMD. No compiler changes are made
by this assessment or port update.

Source review: current compiler `docs/language-coverage.md`,
`docs/charmsharp-grammar-v0.1.md` (including Phase 6 appendices),
`docs/roadmap.md`, `docs/chare-template-coverage-audit.md`,
`src/translator.cpp`, `src/sdag.cpp`, `src/ci_emitter.cpp`, and
`src/cpp_emitter.cpp`. Historical grammar sections are not treated as evidence
that every proposed form is implemented.
