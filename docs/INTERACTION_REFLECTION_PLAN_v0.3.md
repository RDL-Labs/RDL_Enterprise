# Interaction Reflection Plan v0.3

Status: **Core v2.3 staged migration: P1–P7 implemented; next mandatory boundary is native Runtime cutover (P8).**  
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

The current main branch contains the following v2.3 migration surfaces.

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

The canonical bridge path is now:

```text
raw BusinessInput
→ RIBSection(request)
→ compatibility projection
→ existing Cascade
→ F

FeedbackResult / later observation
→ RIBSection(subsequent)
→ same frozen pre-update M_B / interpretation context
→ F'
→ Δ(F,F')
→ unresolved component only
→ operational H
```

On `EnterpriseRuntimeRIBBridge`:

```text
legacy e_input                 -> diagnostic only
coverage / missing / rejection -> Enterprise-local observation only
canonical unresolved Δ(F,F')   -> operational H input
coverage                        -/-> operational θ reduction
```

The parent `EnterpriseRuntime` lifecycle is still reused for product behavior, persistence, canary, promotion, and other compatibility mechanisms. Its historical `HState` shape and old names therefore remain compatibility surfaces. They are not the semantic source for the bridge's Core v2.3 H decision.

This distinction is important:

```text
v2.3 bridge operational cutover = implemented
native RIBSection Runtime        = not yet implemented
```

---

## 3. Structural conflict

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

## 4. Delivery phases

| Phase | Required work | Current state / acceptance evidence |
| --- | --- | --- |
| **P0** | Freeze Core v2.3 semantic baseline | **DONE** — current migration audit and coding principles reject canonical EFP / ξ-score / Function=M_B usage |
| **P1** | Explicit request acquisition | **DONE** — raw `BusinessInput != RIBSection`; Boundary / provenance retained |
| **P2** | Explicit later interaction acquisition | **DONE** — later observation forms separate subsequent `RIBSection` |
| **P3** | Same-M_B `F / F'` comparison | **DONE** — later section interpreted through frozen pre-update context; `Δ(F,F')` recorded separately |
| **P4** | Separate H and coverage | **DONE** — unresolved mismatch and coverage state are separate |
| **P5** | Cut legacy `e_input → H` | **DONE on RIB bridge** — `e_input` remains observable but cannot drive operational H / M_Δ |
| **P6** | Remove observable-ξ semantics | **DONE for current migration API** — `coverage_gap_score` is canonical; `xi_obs` is deprecated compatibility alias only |
| **P7** | Function artifact migration | **DONE for public Core API** — `CompiledFunction / ActiveFunction / ConditionalCompiledFunction` and canonical conditional lifecycle are available; `*CompiledMB` remains compatibility-only |
| **P8** | Runtime cutover | **OPEN** — remove the compatibility projection as the semantic execution dependency and let product Runtime consume RIB sections natively |
| **P9** | Persistence / restart durability | **OPEN** — canonical RIB sections and v2.3 mismatch state must survive process restart as first-class persisted state |
| **P10** | Real interaction acceptance | **PARTIAL / OPEN** — real-provider observations exist, but one complete structural-conflict → response → changed conditions → later RIB_B → F/F' → E chain remains to be observed end-to-end |

Completion here means only that the declared migration contract is implemented and covered by the current finite test boundary. It does not imply universal correctness or completeness.

---

## 5. Function artifact migration boundary

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

Conditional lineage has a canonical path as well:

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

## 6. Human Attention

Observation is not notification. Conflict is not a review request. Core H is not human cognitive load.

Human attention/review load remains a separate Enterprise-local quantity with its own Authority, deduplication, persistence, safety and aggregation rules.

A review request may be triggered by explicit safety policy, authority requirement, repeated unresolved operational cases, coverage failure, provider failure, durability break, or an actually established `H >= θ` condition. These causes are not semantically identical.

---

## 7. Timeout and missing later observation

Timeout does **not** manufacture a later Core state.

If no adequate later interaction section can be formed:

```text
RIB_B(t+Δ) = NOT_EVALUATED / unavailable
F'(t+Δ)    = NOT_EVALUATED
Core E     = NOT_ESTABLISHED
```

The canonical bridge timeout path records coverage / operational information without fabricating `F'`, `E`, `H`, or `ξ`. The inherited legacy timeout API remains available for compatibility, but the RIB bridge's operational H adapter prevents its synthetic legacy values from entering operational H.

---

## 8. Observation time and deterministic replay

Meaning-affecting time is an explicit finite condition.

`EnterpriseRuntime.dispatch_ticket()` now binds an explicit `BusinessInput.created_at` to `FrozenInterpretationContext.constraint_evaluation_time` when available. This prevents constraint freshness from silently depending on wall clock during deterministic Simulation / replay.

```text
observation time
→ frozen interpretation condition
→ F / F' comparison boundary
```

If no explicit observation time is supplied, the compatibility fallback may still use current time. The fallback is not treated as equivalent to a fixed replay condition.

---

## 9. Evidence integrity

Synthetic cases remain synthetic. Development-authored priority labels, factor tables, expected outcomes, and benchmark fixtures are bounded hypotheses / test references, not collected operator truth.

A deterministic replay or green test establishes only that no contract violation was observed inside the declared finite test Boundary.

```text
bounded acceptance
!= terminal completeness
!= universal validity
!= world identity
```

---

## 10. Stop rule and next mandatory break

Do not add new semantic primitives merely because the v2.3 vocabulary permits more modeling.

Add or promote a new type only when it is necessary to prevent a direct BASE / SPEC v2.3 violation, recover missing Boundary or Provenance, distinguish currently collapsed roles, inspect an observed operational break, or preserve an already demonstrated invariant during migration.

The next mandatory break is now:

```text
RIBSection
   ↓
compatibility projection to BusinessInput / inherited Runtime
   ↓
product lifecycle
```

P8 should remove this projection as the semantic execution dependency while preserving the already demonstrated Authority, persistence, canary, staged commitment, frozen-`M_B`, provenance, and deterministic replay contracts.
