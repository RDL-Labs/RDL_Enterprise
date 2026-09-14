# Interaction Reflection Plan v0.3

Status: **Core v2.3 staged migration: P1–P9 implemented; remaining mandatory boundary is real interaction acceptance (P10).**  
Semantic reference: `Aporapeiron/RDL_Core` T0 BASE / SPEC v2.3.  
Supersedes for current design: `INTERACTION_REFLECTION_PLAN_v0.2.md` (pre-v2.3 / EFP generation).

## 1. Operational model

Enterprise does not treat a raw request, provider response, feedback object, or engine event as Core `RIB_B` directly.

```text
ongoing interaction / provider / user / tool conditions
        ↓
      {RIB_i}
        ↓ Purpose / B / acquisition
      RIB_B(t)
        ↓ same current M_B
      F(t)
        ↓ response / action
interaction conditions change
        ↓
      {RIB_i(t+Δ)}
        ↓ Purpose / B / acquisition
      RIB_B(t+Δ)
        ↓ same pre-update M_B
      F'(t+Δ)
        ↓
E(t+Δ) = Δ(F, F')
        ↓ unresolved part only
        H
```

The same frozen pre-update `M_B` and meaning-affecting interpretation conditions are used for `F / F'` comparison. Learning, commitment, recompilation, or reconstruction must not rewrite the comparison boundary halfway through.

### Required separations

```text
raw BusinessInput / provider payload / FeedbackResult != RIB_B
RIB_B != F
static structural conflict != E != H
acquisition gap != E
coverage gap != H
coverage gap != ξ
Human Attention != H
Function != M_B
```

`ξ` is not a measurable runtime quantity. Missing observations, unknown routes, rejected responses, provider failures, confidence, queue pressure, and coverage may be modeled separately as Enterprise-local states.

---

## 2. Current migration implementation

The current main branch contains these v2.3 migration surfaces:

```text
src/rdl_enterprise/interaction.py
  RIBSection
  acquire_request_rib_section(...)
  acquire_feedback_rib_section(...)

src/rdl_enterprise/runtime_rib_bridge.py
  EnterpriseRuntimeRIBBridge

src/rdl_enterprise/mismatch_state.py
  InterpretationMismatchObservation
  UnresolvedMismatchState
  ObservationCoverageState

src/rdl_enterprise/operational_h.py
  V23OperationalHStateAdapter

src/rdl_core/compiled_function_types.py
  CompiledFunction

src/rdl_core/conditional_compiled_function_types.py
  ConditionalCompiledFunction
  ConditionalFunctionPromotionRecord
  ConditionalFunctionActivationRecord
```

The canonical path is now:

```text
raw BusinessInput
→ acquisition under B
→ RIBSection(request)
→ direct interpretation through the RIBSection read contract
→ F

FeedbackResult / later observation
→ acquisition under B
→ RIBSection(subsequent)
→ same frozen pre-update M_B / interpretation context
→ F'
→ Δ(F,F')
→ unresolved component only
→ operational H
```

Canonical `F / F'` formation does not depend on `RIBSection.to_business_input()`. That adapter remains only for historical / compatibility surfaces.

On `EnterpriseRuntimeRIBBridge`:

```text
legacy e_input                 -> diagnostic only
coverage / missing / rejection -> Enterprise-local observation only
canonical unresolved Δ(F,F')   -> operational H input
coverage                        -/-> operational θ reduction
```

---

## 3. Restart durability

The bridge persists the canonical v2.3 inspection boundary through the current single-writer SQLite Runtime.

```text
request RIBSection
+ frozen interpretation boundary
+ subsequent RIBSection
+ F / F'
+ mismatch observation
+ unresolved-mismatch state
+ coverage state
+ operational H adapter state
        ↓ persist
      SQLite
        ↓ restart
recover the same bounded roles
```

Timeout remains distinct:

```text
later RIBSection unavailable
→ F' NOT_EVALUATED
→ Core E NOT_ESTABLISHED
→ no fabricated H
→ coverage may still be recorded and persisted
```

This is bounded restart durability, not distributed or tamper-proof persistence.

---

## 4. Structural conflict

Structural conflict is not temporal Core mismatch.

```text
StructuralConflict
!= Core E
!= Core H
```

A structural conflict may influence selection, response, later interaction conditions, or inspection depth. It becomes relevant to Core mismatch only through a later interaction section and the resulting `F / F'` comparison.

```text
structural conflict observation
→ selected response / action
→ changed interaction conditions
→ later RIB_B
→ same pre-update M_B
→ F'
→ Δ(F,F')
```

No conflict score, priority score, coverage score, or human-attention score is added directly to Core H.

---

## 5. Delivery phases

| Phase | Required work | Current state / acceptance evidence |
| --- | --- | --- |
| **P0** | Freeze Core v2.3 semantic baseline | **DONE** |
| **P1** | Explicit request acquisition | **DONE** |
| **P2** | Explicit later interaction acquisition | **DONE** |
| **P3** | Same-M_B `F / F'` comparison | **DONE** |
| **P4** | Separate H and coverage | **DONE** |
| **P5** | Cut legacy `e_input → H` | **DONE on RIB bridge** |
| **P6** | Remove observable-ξ semantics | **DONE for current migration API** |
| **P7** | Function artifact migration | **DONE for public Core API** |
| **P8** | Runtime cutover | **DONE on RIB bridge** — canonical initial `F` and later `F'` consume `RIBSection` directly |
| **P9** | Persistence / restart durability | **DONE for current SQLite Runtime boundary** — canonical RIB/mismatch/coverage/H state survives restart |
| **P10** | Real interaction acceptance | **PARTIAL / OPEN** — canonical live Jira read path exists; one changed-condition end-to-end chain remains to be observed |

Completion here means only that the declared migration contract is implemented and covered by the current finite test boundary. It does not imply universal correctness or completeness.

---

## 6. Function artifact migration boundary

Current canonical lifecycle:

```text
StructureCandidate
→ FunctionCandidate
→ CompilationRecord(PASSED)
→ CompiledFunction
→ PromotionDecision
→ ActiveFunction
→ Deactivation / Recompilation / Supersession
```

Conditional lineage:

```text
ConditionalFunctionCandidate
→ ConditionalCompiledFunction
→ ConditionalFunctionPromotionRecord
→ ConditionalFunctionActivationRecord
→ ActiveFunction
```

Historical names remain callable during migration:

```text
CompiledMB
ConditionalCompiledMB
ActiveCompiledMB
ConditionalPromotionRecord
ConditionalActivationRecord
```

They are compatibility names, not evidence that `Function = M_B`.

---

## 7. Human Attention

Observation is not notification. Conflict is not a review request. Core H is not human cognitive load.

Human attention/review load remains a separate Enterprise-local quantity with its own Authority, deduplication, persistence, safety and aggregation rules.

A review request may be triggered by explicit safety policy, authority requirement, repeated unresolved operational cases, coverage failure, provider failure, durability break, or an actually established `H >= θ` condition. These causes are not semantically identical.

---

## 8. Observation time and deterministic replay

Meaning-affecting time is an explicit finite condition.

Explicit request observation time is bound to `FrozenInterpretationContext.constraint_evaluation_time`. Because the RIB bridge passes `RIBSection` directly, its `created_at` read contract exposes the acquired observation time without reintroducing wall clock.

```text
observation time
→ frozen interpretation condition
→ F / F' comparison boundary
```

Compatibility surfaces may still have wall-clock fallbacks when no observation time exists. Such fallback is not treated as equivalent to a fixed replay condition.

---

## 9. Acceptance evidence

The P9 acceptance run at commit `f102917c5bf1ddaaca2d58d65667bdb5ddbfa8f8` completed with:

```text
314 passed
4 skipped
6 subtests passed
```

The skipped tests include live-provider acceptance when credentials are not configured. Green tests establish only bounded contract evidence.

```text
bounded acceptance
!= terminal completeness
!= universal validity
!= world identity
```

---

## 10. P10 — remaining mandatory break

The live Jira test now targets the canonical v2.3 path:

```text
real Jira observation
→ request RIBSection
→ F
→ later real Jira observation
→ subsequent RIBSection
→ same frozen pre-update M_B
→ F'
→ canonical Δ(F,F')
→ unresolved H when applicable
```

Because the test is read-only, two immediate observations may legitimately be identical. That gives real-provider evidence but does not establish a changed-condition chain.

The remaining P10 gate is:

```text
real structural conflict / actionable condition
→ actual response or action
→ changed external interaction conditions
→ later real RIB_B
→ same frozen pre-update M_B
→ F'
→ E
→ unresolved H when applicable
```

P10 should be closed only after one such bounded chain is observed end-to-end with recoverable Boundary and Provenance. Do not manufacture the external change merely to make the test pass.
