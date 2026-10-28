# Limitations exposed by LeanMD

Observed against Charm# `0e2e0280f252598f9de48159320be55c3d20d703`.
Run `test_migration.py` for the minimal executable reproductions and actual
diagnostics. These are implementation limits, not claims about the full
Charm++ runtime or the proposed language grammar.

| LeanMD requirement | Observation | Treatment / next step |
| --- | --- | --- |
| `array [3D] Cell`, `array [6D] Compute` | Both translate successfully | Migrated; dimensionality itself is not a frontend blocker. Native runtime remains a separate check. |
| `vec3 forces[n]` | Explicit entry rejects custom element type | Preserve `reduceForces` in legacy interface; support serializable named types. |
| `forces[n], int n` | Even with `double`, length must precede array | Preserve parameter order; support forward length references. Reordering would change the reduction-target ABI. |
| `when A(...) when A(...)` | Parser requires a body after first receive | Preserve Main and Compute SDAG. Add nested receive scopes and retained message lifetime support. |
| `when A(...) { when A(...) {...} }` | Explicitly rejects nested waits | Braces alone do not solve the preceding limitation. Avoid pointer-stashing rewrites that would alter ownership/PUP requirements. |
| `message ParticleDataMsg { vec3 part[]; }` | Variable-size fields rejected | Keep legacy variable-message metadata, original allocation, multicast base and PUP routine together. |
| `mainchare [migratable] Main` | Object attribute rejected | Main class/constructor use Charm#; adapter retains legacy `[migratable]` metadata. Do not silently drop checkpoint semantics. |
| `readonly std::string logs` | Requires a single-token type | Keep only this readonly declaration in legacy metadata; twelve simple declarations migrate. A typedef workaround would need serialization validation. |
| `CellMap : CkArrayMap` | Generated ordinary-base handling adds `CBase_CellMap` | Not migrated: preserving special runtime base identity needs native compile/runtime evidence; parser acceptance alone would not establish correctness. |
| `CMK_MEM_CHECKPOINT` conditional in Cell SDAG | Structural preprocessing is restricted; this exact configuration is not validated here | Preserve original conditional text and preprocessing through Charmxi. Add enabled/disabled compiler and runtime fixtures before native migration. |
| Legacy and generated entries in the same class | No native fragment merge/include-order control | Project-specific adapter composes a single interface and force-includes value types. Add native metadata-fragment composition or a header/dependency model. |

## Why Cell's run routine remains legacy

Most of its sequencing, loops, waits and ordinary operations are within the
implemented SDAG family. The force receive declaration crosses the unsupported
custom-type and forward-length boundaries, and the fault-injection conditional
adds a preprocessing concern. Splitting one SDAG state machine across generated
and handwritten ownership would make an ostensibly mechanical port harder to
validate. The complete routine stays intact until those boundaries are supported.

## Suggested implementation order

1. Custom marshalled element types and forward length references: directly
   unblock Cell's force receive without changing its reduction callback contract.
2. Nested receive scopes and lifetimes: unblock the two-message interactions
   in Compute and two-energy aggregation in Main.
3. Migratable mainchare metadata and variable-size multicast messages.
4. Native legacy-fragment composition, user-type include ordering, qualified
   readonly types, and special runtime-base integration.
5. Validate conditional SDAG and checkpoint/restart configurations end-to-end.

Keep this partial port as a regression fixture. As each blocker is removed,
replace the relevant legacy template section with native `.csh`, retain the
upstream comparison, and extend runtime checks before claiming broader coverage.
