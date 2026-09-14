# RDL Enterprise — Core v2.3 Migration Audit

*Status: ACTIVE MIGRATION AUDIT*  
*Current reviewed boundary: staged migration through P7; P8–P10 remain open*  
*Canonical semantic source: `Aporapeiron/RDL_Core` BASE / SPEC v2.3*  
*Related current sources: `RDL_Functions`, `RDL_Durability_Modules`*

## 0. Purpose

This document records the migration boundary from the Enterprise implementation built around the older `EFP` generation to the current Core v2.3 `RIB / RIB_B` model.

The goal is not to rewrite working Enterprise mechanisms merely to rename symbols. The goal is to preserve useful mechanisms while removing semantic identities that no longer match current Core.

Enterprise implementation names are not canonical RDL primitives. Backward-compatible names may remain temporarily, but current design must not infer Core ontology from those names.

---

## 1. Canonical baseline

```text
nonlinear relational network
        │
       SILN
      ↕ ↕ ↕
   RIB₁ RIB₂ RIB₃ ...
        │
        ↓ Purpose / B
   M_B + RIB_B
        ↓
F = interp(M_B, RIB_B)
        ↓
optional comparison of F / F'
        ↓
E = Δ(F, F')
        ↓ unresolved remainder
        H
        ↓
H < θ / H >= θ → M_Δ → M_B'
```

Required separations:

```text
raw input                  != RIB_B
RIB_B                      != F
Enterprise Runtime         != M_B
Function                   != M_B
noise / uncertainty        != ξ
missing observation        != ξ
coverage / input gap       != E != H
static structural conflict != E != H
Human Attention            != H
```

Core `E` standard:

```text
RIB_B(t)     = Section_B({RIB_i(t)})
F(t)         = interp(M_B, RIB_B(t))

RIB_B(t+Δ)   = Section_B({RIB_i(t+Δ)})
F'(t+Δ)      = interp(M_B, RIB_B(t+Δ))

E(t+Δ)       = Δ(F, F')
```

`ξ` is relation not recovered under a finite `B`. It is not a random variable, missing-data counter, uncertainty score, exploration target, hidden store, or injected runtime quantity.

---

## 2. Findings and current disposition

### F1 — raw `BusinessInput` was treated as the interaction primitive

**Original issue:** raw business input was passed directly through the interpretation stack without an explicit finite interaction-section role.

**Current disposition: RESOLVED ON MIGRATION SURFACE.**

`src/rdl_enterprise/interaction.py` now provides `RIBSection` and explicit request acquisition. `EnterpriseRuntimeRIBBridge` retains raw input separately and uses a finite `RIBSection` as the canonical interaction role.

Remaining debt: the bridge still projects `RIBSection` back into `BusinessInput` for the inherited Runtime/Cascade. Removing that semantic dependency is P8.

### F2 — later interaction was synthesized as `EFP'`

**Original issue:** `FeedbackResult` / `EFPPrimeAdapter` semantics collapsed later raw observation, later interaction section, and subsequent interpretation.

**Current disposition: RESOLVED ON RIB BRIDGE.**

Later feedback is acquired into a separate subsequent `RIBSection`, interpreted through the same frozen pre-update `M_B` / interpretation conditions, and recorded separately as `F'` and `Δ(F,F')`.

Legacy EFP-named fields may remain as compatibility surfaces in old Snapshot/Runtime code.

### F3 — Enterprise `e_input` was mixed into Core H

**Original issue:** input/acquisition gap contributed to the quantity used for `H >= θ` reconstruction.

**Current disposition: RESOLVED FOR OPERATIONAL H ON RIB BRIDGE.**

`EnterpriseRuntimeRIBBridge` replaces the parent metabolism inputs before H accumulation:

```text
canonical unresolved Δ(F,F') -> operational H
legacy e_input                -> diagnostic only
coverage / missing            -> Enterprise-local observation
```

The historical `HState.input_err` field remains for base-Runtime compatibility and is explicitly documented as non-Core.

### F4 — `ξ` was implemented as an observable score

**Original issue:** unclassified / missing / unknown / rejection rates were named `xi_obs` and used by an Enterprise threshold policy.

**Current disposition: RESOLVED FOR CURRENT API; LEGACY ALIAS RETAINED.**

Canonical name is `coverage_gap_score`. `xi_obs()` remains only as a deprecated compatibility alias and explicitly does not represent Core `ξ`.

Any coverage-adjusted threshold remains an Enterprise policy, not a Core consequence of `ξ`.

### F5 — timeout fabricated mismatch / uncertainty heat

**Original issue:** timeout could create fixed mismatch/input values despite no adequate later interaction state.

**Current disposition: RESOLVED ON CANONICAL RIB TIMEOUT PATH.**

`expire_pending_tickets_v23()` records later `RIB_B`, `F'`, and `E` as `NOT_EVALUATED` when unavailable and does not add fabricated H. The inherited legacy timeout API remains callable for compatibility, but its synthetic values cannot enter operational H through the bridge adapter.

### F6 — Function was identified with Compiled M_B

**Original issue:** names such as `CompiledMB`, `ConditionalCompiledMB`, and `ActiveCompiledMB` encouraged `Function = M_B`.

**Current disposition: RESOLVED FOR PUBLIC CORE API; LEGACY NAMES RETAINED.**

Canonical public names now include:

```text
CompiledFunction
ActiveFunction
ConditionalCompiledFunction
ConditionalFunctionPromotionRecord
ConditionalFunctionActivationRecord
```

Normal and conditional canonical lifecycles are tested without reverting to a `CompiledMB` artifact. Historical names remain compatibility types / aliases only.

### F7 — useful Enterprise invariants remain valid

**Current disposition: RETAINED.**

```text
Observation != Candidate != Commitment != Active
Authority != Truth
UNKNOWN != UNRESOLVED != NOT_EVALUATED
static structural conflict != E != H
Human Attention != H
F and F' use the same pre-update M_B
provenance and finite boundary are recoverable
test success != universal truth
```

### F8 — meaning-affecting observation time leaked to wall clock

**Observed during migration:** 60-day exact Simulation replay intermittently diverged at different records despite identical seed and virtual clock.

`BusinessInput.created_at` already carried Simulation time, but `FrozenInterpretationContext.constraint_evaluation_time` fell back to actual wall clock. Constraint freshness could therefore vary between otherwise identical runs.

**Current disposition: RESOLVED.**

`EnterpriseRuntime.dispatch_ticket()` now binds explicit `BusinessInput.created_at` into the frozen interpretation context. Invalid or absent explicit times retain the compatibility fallback. The full test suite, including 60-day exact lifecycle determinism, passes under this boundary.

---

## 3. Current architecture boundary

### Canonical migration path

```text
raw request
  ↓ acquire under B
RIBSection(t)
  ↓ compatibility projection
existing Cascade / frozen M_B
  ↓
F(t)

later raw observation
  ↓ acquire under B
RIBSection(t+Δ)
  ↓ same frozen pre-update M_B
F'(t+Δ)
  ↓
Δ(F,F')
  ↓ unresolved only
V23OperationalHStateAdapter
```

### Compatibility boundary still present

```text
RIBSection
  ↓ to_business_input()
BusinessInput-named Runtime / Cascade surfaces
```

This adapter is currently deliberate. It preserves working Authority, persistence, canary, promotion, ledger, snapshot and product behavior while the semantic foundation migrates.

It is also the next debt boundary: P8 should make `RIBSection` a first-class Runtime input rather than a semantic role projected back into an older type.

---

## 4. Migration phase status

| Phase | Contract | Status |
| --- | --- | --- |
| P0 | Freeze Core v2.3 semantic baseline / compatibility policy | **DONE** |
| P1 | Explicit request `RIBSection` acquisition | **DONE** |
| P2 | Explicit later interaction acquisition | **DONE** |
| P3 | Same-pre-update-M_B `F / F'` comparison | **DONE** |
| P4 | Separate unresolved mismatch H from coverage | **DONE** |
| P5 | Remove `e_input` operational force from bridge H / M_Δ | **DONE ON RIB BRIDGE** |
| P6 | Observable-ξ terminology removal | **DONE FOR CURRENT API; legacy alias retained** |
| P7 | Function identity migration | **DONE FOR PUBLIC CORE API** |
| P8 | Native Runtime cutover to RIBSection | **OPEN** |
| P9 | Persist canonical RIB / mismatch state through restart | **OPEN** |
| P10 | One complete real interaction acceptance chain | **PARTIAL / OPEN** |

`DONE` means the declared contract is implemented and covered by the current finite tests. It does not imply terminal completeness.

---

## 5. Function migration acceptance

Canonical normal lifecycle:

```text
StructureCandidate
→ FunctionCandidate
→ CompilationRecord(PASSED)
→ CompiledFunction
→ PromotionDecision
→ ActiveFunction
→ Deactivation / Recompilation / Supersession
```

Canonical conditional lifecycle:

```text
ConditionalFunctionCandidate
→ ConditionalCompiledFunction
→ ConditionalFunctionPromotionRecord
→ ConditionalFunctionActivationRecord
→ ActiveFunction
```

Compatibility remains available:

```text
CompiledMB
ConditionalCompiledMB
ActiveCompiledMB
ConditionalPromotionRecord
ConditionalActivationRecord
```

The compatibility names do not define ontology. New code should use canonical Function names.

---

## 6. Test evidence currently pinning v2.3 migration

Current regression contracts include:

- raw request acquisition keeps raw input and `RIBSection` distinct;
- later observation forms a separate subsequent section;
- `e_input > 0` does not enter bridge operational H or trigger reconstruction;
- unresolved canonical `Δ(F,F')` is the bridge operational H increment;
- resolved mismatch may be observed without being retained as H;
- coverage observations do not lower bridge operational θ;
- canonical timeout does not fabricate `F'`, `E`, or H;
- explicit observation time is frozen into interpretation context;
- 60-day fixed-condition lifecycle replay remains deterministic under that time boundary;
- `CompiledFunction` lifecycle works through promotion, activation, deactivation, recompilation and supersession;
- legacy `CompiledMB` remains accepted during migration;
- conditional Function lineage round-trips through the legacy compatibility shape;
- canonical conditional promotion / activation remains on `CompiledFunction` / `ActiveFunction` artifacts.

These tests establish bounded implementation contracts only.

---

## 7. Compatibility policy

During migration:

- Existing external behavior remains stable unless it encodes an invalid current-Core semantic claim.
- Old names survive only as compatibility aliases / properties / adapters.
- New tests target canonical v2.3 names.
- Operational invariants are migrated, not deleted, when their role remains valid.
- Invalid semantic identities are replaced with the closest valid bounded observation rather than weakening tests.

Examples:

```text
efp / BusinessInput       -> raw / compatibility input surface
RIBSection                -> canonical finite interaction section

efp_prime                 -> legacy later-input compatibility surface
subsequent RIBSection     -> canonical later interaction section

e_input                   -> acquisition/input diagnostic
xi_obs                    -> deprecated alias for coverage_gap_score
CompiledMB                -> compatibility type for canonical Function artifact
```

---

## 8. Next migration boundary

The next mandatory work is P8, not another semantic type expansion.

```text
current:
RIBSection
  ↓ compatibility projection
BusinessInput / inherited Runtime
  ↓
product lifecycle

next:
RIBSection
  ↓ native Runtime boundary
interpretation / lifecycle
```

P8 must preserve already demonstrated invariants:

```text
same pre-update M_B for F/F'
Boundary / Provenance recovery
Authority separation
staged Commitment / Promotion
Canary isolation
ActionLedger behavior
Persistence safety
observation-time determinism
UNKNOWN / UNRESOLVED / NOT_EVALUATED separation
```

P9 then makes canonical RIB/mismatch state restart-durable. P10 remains the real-world acceptance gate.

---

## 9. Non-goals

This migration does not claim to:

- prove RDL v2.3;
- model the complete set of real-world RIBs;
- infer `ξ` contents;
- replace Enterprise Authority / Ledger / Jira mechanisms merely for naming purity;
- make a localhost single-writer Runtime production-secure;
- turn test success into universal semantic validity.
