# RDL Enterprise — Core v2.3 Migration Audit

*Status: ACTIVE MIGRATION AUDIT*  
*Baseline reviewed: `main` at `06420a78752ed43a9d8a3d62e939c3ebd08be067`*  
*Canonical semantic source: `Aporapeiron/RDL_Core` BASE / SPEC v2.3*  
*Related current sources: `RDL_Functions`, `RDL_Durability_Modules`*

## 0. Purpose

This document records the migration boundary from the Enterprise implementation built around the v2.0/v2.1 `EFP` generation to the current Core v2.3 `RIB / RIB_B` model.

The goal is **not** to rewrite working Enterprise mechanisms merely to rename symbols. The goal is to preserve mechanisms that remain useful while removing semantic identities that no longer match the current Core.

Enterprise implementation names are not canonical RDL primitives. During migration, backward-compatible names may remain temporarily, but they must be marked as compatibility surfaces rather than current semantic definitions.

---

## 1. Current canonical baseline

Enterprise now treats the following as the canonical semantic skeleton:

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
E → unresolved remainder → H
        ↓
H < θ / H ≥ θ → M_Δ → M_B'
```

Required separations:

```text
raw input                  != RIB_B
RIB_B                      != F
Enterprise Runtime         != M_B
Function                   != M_B
noise / uncertainty        != ξ
missing observation        != ξ
queue / load / input gap   != H
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

`ξ` is the relation not recovered under a finite `B`. It is not a random variable, a missing-data counter, an uncertainty score, an exploration target, a hidden store, or a quantity injected into the runtime.

---

## 2. Findings

### F1 — raw `BusinessInput` is currently treated as EFP

Current code passes `BusinessInput` directly into `InterpCascade.interpret()` and names that input `efp` throughout Runtime, Snapshot, Constraint, and tests.

This collapses two roles:

```text
raw business event / request
        ↓ acquisition / selection under B
RIB_B
```

The acquisition / finite-section step is currently implicit.

**Migration requirement:** introduce an explicit Enterprise finite interaction section (`RIBSection`) and make raw `BusinessInput` a source used to construct it.

---

### F2 — subsequent interaction is currently synthesized as `EFP'`

`EFPPrimeAdapter` merges `FeedbackResult` and the original request into another `BusinessInput`, then reinterprets it as `F'`.

The useful property should be retained: `F` and `F'` are formed using the same pre-update interpretation structure and frozen interpretation conditions.

The obsolete semantic identity is:

```text
FeedbackResult = EFP'
```

**Migration requirement:** construct a subsequent `RIB_B(t+Δ)` from later observations / responses / provider records / interaction history. Preserve the frozen pre-update `M_B` comparison discipline.

---

### F3 — Enterprise `e_input` is mixed into Core H

`CaseSnapshot.record_feedback()` currently computes both:

```text
e_prediction = Δ(F, F')
e_input      = an Enterprise-specific input-gap score
```

`HState.add_heat()` then accepts both `pred_err` and `input_err`, and both contribute to the quantity used for the `H ≥ θ` transition.

Under current Core, the standard `E` is the `F / F'` mismatch. Input completeness, acquisition gaps, missing fields, queue load, confidence, and similar metrics may exist as Enterprise-local observations, but they do not automatically become Core `E` or `H`.

**Migration requirement:** rename / reclassify `e_input` as an Enterprise acquisition or coverage metric and remove its automatic contribution to Core `H`.

---

### F4 — `ξ` is implemented as an observable score

`HState` currently records unclassified, missing, unknown, and rejected events as `ξ_obs`, then lowers `θ_eff` using this score.

This is incompatible with Core v2.3.

Useful observations may remain, but their role must be explicit:

```text
unclassified rate
missing information rate
unknown-route rate
rejection rate
coverage gap
```

These are modeled Enterprise observations, **not `ξ`**.

**Migration requirement:** rename the score and remove the claim that it measures `ξ`. Any threshold adaptation must be declared as an Enterprise policy, not a Core consequence of `ξ`.

---

### F5 — timeout currently fabricates Core mismatch / ξ heat

`CaseSnapshot.mark_unknown()` currently creates fixed `e_prediction` / `e_input` values and describes the result as uncertainty heat left as `ξ`.

If no later `RIB_B` can be formed, then `F'` and Core `E` are not established merely by timeout.

**Migration requirement:** timeout should record `NOT_EVALUATED` / unresolved acquisition state. It may affect Enterprise risk, attention, retry, or coverage metrics, but must not fabricate Core `E`, `H`, or `ξ`.

---

### F6 — Function is identified with Compiled M_B

`docs/RDL_Compiled_MB.md` explicitly states `Function = Compiled M_B`. Core-local types also expose names such as:

```text
CompiledMB
ConditionalCompiledMB
ActiveCompiledMB
```

Current `RDL_Functions` separates these roles:

```text
Function != M_B
Function != SILN
Function != RIB_B
```

A Function is a reusable operatorized constraint / transform / evaluation module with a finite contract, inputs, outputs, provenance, and unresolved / failure conditions. Its internal constraints may be integrated into an `M_B` implementation section in a particular system, but identity is not equivalence.

**Migration requirement:** introduce canonical Function artifact names and keep `*CompiledMB` only as compatibility aliases during transition.

---

### F7 — useful Enterprise invariants remain valid

The following existing design disciplines are retained:

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

The migration should preserve these rather than rebuild Enterprise from zero.

---

## 3. Affected surfaces

### Semantic / documentation

High-priority current documents:

- `README.md`
- `docs/INTERACTION_REFLECTION_PLAN_v0.2.md`
- `docs/RDL_Coding_Principles.md`
- `docs/RDL_Compiled_MB.md`
- `docs/RDL_Core_Extraction_Gate.md`
- `docs/RDL_Core_Route_v0.1.md`
- `docs/RDL_Product_Status_v0.1.md`
- `docs/RDL_Reference_Sources.md`
- current detailed design and parameter documents

Historical phase documents may retain old terminology when clearly marked as historical / pre-v2.3 material.

### Runtime semantic hot spots

- `src/rdl_enterprise/snapshot.py`
  - `BusinessInput`
  - `CounterfactualInput.efp`
  - `FrozenInterpretationContext.interpret_efp()`
  - `EFPPrimeAdapter`
  - `FeedbackResult` description
  - `CaseSnapshot.efp / efp_prime`
  - timeout handling
- `src/rdl_enterprise/cascade.py`
  - `interpret(efp)`
  - selection / constraint functions parameterized directly by `BusinessInput`
- `src/rdl_enterprise/runtime.py`
  - `dispatch_ticket(efp)`
  - `resolve_ticket_feedback()`
  - `e_input` → H path
  - `compute_efp_prime_constraint`
- `src/rdl_enterprise/constraint.py`
  - `ConstraintContext.efp`
  - `BundleAuxiliary` described as `ξ evidence`
  - EFP-prime constraint naming
- `src/rdl_enterprise/h_state.py`
  - `input_err` as H component
  - `ξ_obs`
  - `theta_eff = theta0 - g(ξ_obs)`

### Core-local Function hot spots

- `src/rdl_core/evolution_types.py`
- `src/rdl_core/activation_types.py`
- `src/rdl_core/registry_types.py`
- `src/rdl_core/recompilation_types.py`
- exported names in `src/rdl_core/__init__.py`

### Tests that currently pin old semantics

At minimum:

- `tests/test_core.py`
- `tests/test_interaction_trace.py`
- `tests/test_p10_live_interaction.py`
- `tests/test_core_contracts.py`
- `tests/test_constraint_model.py`
- `tests/test_product_acceptance.py`

Examples already identified:

- `test_h_state_dissipation_and_theta_eff` expects an unknown-input score to reduce θ.
- timeout tests currently treat missing subsequent observation as uncertainty heat.
- P10 explicitly names the later observation as `subsequent_efp`.
- interaction trace tests assert `efp_prime` state.

---

## 4. Migration order

### P0 — Semantic freeze and compatibility policy

1. Declare BASE / SPEC v2.3 as the only current semantic baseline.
2. Record old `EFP` and `Function = Compiled M_B` names as compatibility debt, not canonical definitions.
3. Preserve current working behavior while adding v2.3 roles in parallel.

Acceptance:

```text
No new code is allowed to introduce EFP as a canonical primitive.
No new code may equate Function with M_B.
No new code may model ξ as a measurable runtime quantity.
```

### P1 — Explicit RIB_B acquisition layer

Add a finite interaction-section contract:

```text
raw business / provider / feedback observations
        ↓ acquisition under Purpose / B
RIBSection  (Enterprise representation of RIB_B)
        ↓
interp(M_B, RIBSection)
        ↓
F
```

Initially keep adapters back to the current `BusinessInput`-based Cascade so behavior remains testable.

### P2 — Subsequent interaction and F/F'

Replace semantic `EFPPrimeAdapter` with a subsequent-section builder:

```text
later observations / responses / changed provider state
        ↓ acquisition under the same comparison B where required
RIB_B(t+Δ)
        ↓ same pre-update M_B
F'(t+Δ)
        ↓
E = Δ(F, F')
```

Retain frozen interpretation context and replay evidence where they remain useful.

### P3 — Separate Core H from Enterprise metrics

- Core mismatch candidate: `E = Δ(F, F')`.
- Enterprise-local metrics: acquisition gap, missing data, unresolved route, confidence, queue load, human attention, risk, security, provider availability.
- Only an explicitly declared unresolved-E policy may feed Core H.
- timeout without `F'` becomes `NOT_EVALUATED`, not fabricated E/H.

### P4 — Remove ξ quantification

Rename `ξ_obs` and all derived policy use to Enterprise-local coverage / unresolved-observation metrics.

```text
coverage_gap_score != ξ
missing_info_count  != ξ
unknown_route_rate  != ξ
```

If an Enterprise policy uses these values to change a review threshold, that policy must be named and tested as an Enterprise policy.

### P5 — Function identity migration

Introduce canonical names such as `CompiledFunction` / `ActiveFunction` while retaining old `CompiledMB` names as deprecated compatibility aliases until all callers migrate.

Do not change runtime behavior solely to satisfy naming.

### P6 — Documentation and acceptance rewrite

Update current README / plans / acceptance tests to:

```text
RIB / RIB_B
Core v2.3
Function != M_B
ξ != modeled unknown
```

Historical documents can remain unchanged if clearly marked pre-v2.3.

---

## 5. Compatibility policy

During migration:

- Existing external behavior should remain stable unless the behavior itself encodes an invalid Core semantic claim.
- Old names may survive temporarily only as compatibility aliases / properties / adapters.
- New tests should target canonical v2.3 names.
- Old tests should be migrated rather than deleted when the operational invariant remains valid.
- When a previous test asserted an invalid semantic identity, replace it with the closest valid bounded observation rather than weakening the test.

Examples:

```text
efp            -> legacy alias / raw input compatibility surface
rib_section    -> canonical finite interaction section

efp_prime      -> legacy alias
rib_section_next -> canonical subsequent finite section

e_input        -> acquisition_gap / coverage metric
ξ_obs          -> coverage_gap_score
CompiledMB     -> compatibility alias for canonical Function artifact
```

---

## 6. Non-goals

This migration does not claim to:

- prove RDL v2.3;
- model the complete set of real-world RIBs;
- infer ξ contents;
- replace Enterprise Authority / Ledger / Jira / Persistence mechanisms;
- make a localhost single-writer runtime production-secure;
- turn test success into universal semantic validity.

---

## 7. First implementation step

The first code change should be non-destructive:

1. add an explicit `RIBSection` type;
2. add request and subsequent-observation acquisition functions;
3. add a compatibility projection into the existing `BusinessInput` Cascade;
4. test that `raw input != RIBSection` and that the finite Boundary / provenance are retained;
5. only after that, route `EnterpriseRuntime.dispatch_ticket()` through the new section layer.

This keeps the current working system inspectable while changing the semantic foundation underneath it.
