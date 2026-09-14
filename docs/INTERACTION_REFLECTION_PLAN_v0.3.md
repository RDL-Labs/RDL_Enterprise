# Interaction Reflection Plan v0.3

Status: **Core v2.3 migration in progress; RIB acquisition + mismatch shadow implemented, legacy metabolism not yet cut over.**  
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

The current main branch now contains:

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
  CoverageAdjustedThresholdPolicy
```

The bridge currently performs:

```text
raw BusinessInput
→ RIBSection(request)
→ compatibility projection
→ legacy Runtime / Cascade

FeedbackResult / later observation
→ RIBSection(subsequent)
→ same frozen interpretation context
→ shadow F'
→ shadow Δ(F,F')
→ unresolved mismatch shadow H candidate

coverage observations
→ separate ObservationCoverageState
```

This is **migration evidence**, not completion. The inherited Runtime still executes the pre-v2.3 `e_input` heat path and legacy threshold policy. Until cutover, product decisions must not treat the shadow state as the sole operational source.

---

## 3. Structural conflict

The earlier proposal to add structural conflict directly to temporal `E` remains rejected.

```text
StructuralConflict
!= Core E
!= Core H
```

A structural conflict may influence selection, response, later interaction conditions, or inspection depth. It becomes relevant to Core mismatch only through a real later interaction section and the resulting `F / F'` comparison.

```text
structural conflict observation
→ selected response / action
→ changed interaction conditions
→ later RIB_B
→ same pre-update M_B
→ F'
→ Δ(F,F')
```

No conflict score, shadow score, priority score, or human-attention score may be added directly to Core H.

---

## 4. Delivery phases

| Phase | Required work | Acceptance evidence |
| --- | --- | --- |
| **P0** | Freeze Core v2.3 semantic baseline | Migration audit + coding principles reject new canonical EFP/xi-score/Function=M_B usage |
| **P1** | Explicit request acquisition | raw `BusinessInput != RIBSection`; selected finite fields and Boundary/Provenance recoverable |
| **P2** | Explicit later interaction acquisition | later observation forms a separate `RIBSection`; not identified with `FeedbackResult` itself |
| **P3** | Same-M_B `F / F'` shadow comparison | subsequent section interpreted through frozen pre-update context; `Delta(F,F')` recorded separately |
| **P4** | Separate H and coverage | unresolved mismatch state has no coverage/input term; coverage state has no `xi` API |
| **P5** | Cut legacy `e_input → H` | operational reconstruction decisions no longer depend on acquisition gap as Core H |
| **P6** | Remove observable-ξ semantics | legacy `xi_obs` becomes compatibility alias only; all current docs/code use coverage terminology |
| **P7** | Function artifact migration | canonical `CompiledFunction / ActiveFunction` roles available; `CompiledMB` names compatibility-only |
| **P8** | Runtime cutover | product Runtime uses RIBSection path natively rather than through compatibility projection |
| **P9** | Persistence / restart durability | canonical RIB sections and v2.3 mismatch state survive process restart with provenance |
| **P10** | Real interaction acceptance | one real structural-conflict → response → changed conditions → later RIB_B → F/F' → E chain observed end-to-end |

P1–P4 may run in shadow beside legacy behavior before cutover. P5–P9 require regression tests proving that previously valid operational contracts remain intact or are explicitly replaced.

---

## 5. Human Attention

Observation is not notification. Conflict is not a review request. Core H is not human cognitive load.

Human attention/review load remains a separate Enterprise-local quantity with its own Authority, deduplication, persistence, safety and aggregation rules.

A review request may be triggered by:

- explicit safety policy;
- authority requirement;
- repeated unresolved operational cases;
- coverage failure;
- provider failure;
- durability break;
- a Core `H >= θ` condition, if that condition is actually established.

None of these causes are semantically identical.

---

## 6. Timeout and missing later observation

Timeout does **not** manufacture a later Core state.

If no adequate later interaction section can be formed:

```text
RIB_B(t+Δ) = NOT_EVALUATED / unavailable
F'(t+Δ)    = NOT_EVALUATED
Core E     = NOT_ESTABLISHED
```

Enterprise may still record:

```text
timeout
provider availability
retry count
coverage gap
human review eligibility
operational risk
```

but these are not fabricated `E`, `H`, or `ξ`.

The current legacy `CaseSnapshot.mark_unknown()` behavior is therefore migration debt and must be replaced before Runtime cutover.

---

## 7. Evidence integrity

Existing synthetic cases remain synthetic. Development-authored priority labels, factor tables, expected outcomes, and benchmark fixtures are bounded hypotheses / test references, not collected operator truth.

A deterministic replay or green test establishes only that no contract violation was observed inside the declared finite test Boundary.

```text
bounded acceptance
!= terminal completeness
!= universal validity
!= world identity
```

---

## 8. Stop rule

Do not add new semantic primitives merely because the v2.3 vocabulary permits more modeling.

Add or promote a new type only when it is necessary to:

- prevent a direct BASE / SPEC v2.3 violation;
- recover missing Boundary or Provenance;
- distinguish roles currently collapsed by implementation;
- inspect an observed operational break;
- preserve an already demonstrated operational invariant during migration.

The next mandatory break to remove is:

```text
legacy e_input / coverage
        ↓
legacy H / theta decision
```

while preserving the existing frozen-`M_B`, provenance, Authority, persistence, and staged-commitment behavior.
