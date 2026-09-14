"""Staged Runtime bridge from raw Enterprise events to Core v2.3 RIB_B roles.

This is a migration surface, not a claim that the legacy Enterprise Runtime is
already fully Core v2.3 compliant.  It moves the request/subsequent-observation
boundary first while the legacy Cascade and metabolism implementation remain
available behind compatibility projections.

Current staged path:

    raw BusinessInput
      -> acquire_request_rib_section(...)
      -> RIBSection
      -> compatibility BusinessInput
      -> legacy EnterpriseRuntime / InterpCascade

Later feedback is acquired as a canonical subsequent RIBSection.  The bridge
also forms a shadow ``F'`` from that section with the same frozen pre-update
interpretation context and records a v2.3-style ``Delta(F, F')`` separately
from the legacy metabolism.

Important: the inherited legacy metabolism still contains pre-v2.3 semantics
(`e_input` heat and observable-xi threshold policy).  The new mismatch / H /
coverage states are shadow migration evidence until the legacy path is cut
over.  Consumers must not treat this bridge as completion of the migration.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from .authority import AuthorityContext
from .interaction import RIBSection, acquire_feedback_rib_section, acquire_request_rib_section
from .mismatch_state import (
    ObservationCoverageState,
    UnresolvedMismatchState,
    compare_interpretation_states,
)
from .runtime import EnterpriseRuntime, TicketDispatchResult, TicketResolutionResult
from .snapshot import BusinessInput, FeedbackResult


class EnterpriseRuntimeRIBBridge(EnterpriseRuntime):
    """Compatibility Runtime that makes the RIB_B acquisition boundary real.

    The public request API continues to accept ``BusinessInput`` for product
    compatibility.  A pre-built ``RIBSection`` may also be supplied for tests
    and explicit acquisition pipelines.
    """

    migration_stage = "P1_P3_RIB_AND_MISMATCH_SHADOW"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Shadow state: this does not replace legacy self.h_state yet.
        theta = float(getattr(self.h_state, "theta_0", 2.0))
        gamma = float(getattr(self.h_state, "gamma", 0.05))
        self.v23_h_state = UnresolvedMismatchState(theta=theta, gamma=gamma)
        self.v23_coverage = ObservationCoverageState()

    def dispatch_ticket(
        self,
        request: Union[BusinessInput, RIBSection],
        human_override_answer: Optional[str] = None,
        authority: Optional[AuthorityContext] = None,
    ) -> TicketDispatchResult:
        if isinstance(request, RIBSection):
            rib_section = request
            raw_request = request.to_business_input()
        elif isinstance(request, BusinessInput):
            raw_request = request
            rib_section = acquire_request_rib_section(request)
        else:
            raise TypeError("request must be BusinessInput or RIBSection")

        compatibility_input = rib_section.to_business_input()
        result = super().dispatch_ticket(
            compatibility_input,
            human_override_answer=human_override_answer,
            authority=authority,
        )

        snapshot = self.pending_snapshots[result.ticket_id]
        # These fields are deliberately additive. Existing ``efp`` remains a
        # compatibility field until Snapshot/Persistence migration is complete.
        snapshot.raw_business_input = raw_request
        snapshot.rib_section = rib_section
        snapshot.interaction_semantic_version = "core-v2.3-rib-shadow"
        return result

    def resolve_ticket_feedback(
        self,
        ticket_id: str,
        feedback: FeedbackResult,
        at: Optional[Any] = None,
        operation_id: Optional[str] = None,
        actor_provenance: Optional[Dict[str, Any]] = None,
        authority: Optional[AuthorityContext] = None,
    ) -> TicketResolutionResult:
        if ticket_id not in self.pending_snapshots:
            # Delegate the legacy error/idempotency behavior when an operation
            # id can resolve a prior result.
            return super().resolve_ticket_feedback(
                ticket_id,
                feedback,
                at=at,
                operation_id=operation_id,
                actor_provenance=actor_provenance,
                authority=authority,
            )

        snapshot = self.pending_snapshots[ticket_id]
        raw_request = getattr(snapshot, "raw_business_input", snapshot.efp)
        rib_section_next = acquire_feedback_rib_section(raw_request, feedback)
        snapshot.rib_section_next = rib_section_next

        # Canonical shadow comparison: interpret the acquired subsequent
        # section, not FeedbackResult itself, through the frozen pre-update M_B.
        v23_f_prime = None
        v23_mismatch = None
        frozen_context = getattr(snapshot, "frozen_context", None)
        if frozen_context is not None:
            v23_f_prime = frozen_context.interpret_efp(
                rib_section_next.to_business_input()
            )
            if v23_f_prime is not None:
                v23_mismatch = compare_interpretation_states(
                    snapshot.f_pred,
                    v23_f_prime,
                )
        snapshot.v23_f_prime = v23_f_prime
        snapshot.v23_mismatch = v23_mismatch

        result = super().resolve_ticket_feedback(
            ticket_id,
            feedback,
            at=at,
            operation_id=operation_id,
            actor_provenance=actor_provenance,
            authority=authority,
        )

        resolved = next(
            (item for item in reversed(self.resolved_snapshots)
             if getattr(getattr(item, "efp", None), "ticket_id", None) == ticket_id),
            None,
        )
        if resolved is not None:
            resolved.rib_section_next = rib_section_next
            resolved.v23_f_prime = v23_f_prime
            resolved.v23_mismatch = v23_mismatch
            resolved.interaction_semantic_version = "core-v2.3-rib-shadow"

            # Coverage observations remain outside Core H and outside xi.
            pred = resolved.f_pred
            self.v23_coverage.record(
                unclassified=(pred.matched_node_id is None),
                missing_info=False,
                unknown_route=(pred.matched_node_id is None and pred.cost_tier == 3),
                rejected=bool(feedback.human_rejected),
                mb_version=getattr(
                    getattr(getattr(resolved, "frozen_context", None), "frozen_mb", None),
                    "version",
                    "prod",
                ),
                is_canary=bool(getattr(resolved, "is_canary", False)),
            )

            # Enterprise shadow retention policy: only a mismatch that remains
            # unresolved by the later observation contributes to the v2.3 H
            # candidate. Resolution status is not used to rewrite F'; it is a
            # separate operational retention decision.
            if (
                v23_mismatch is not None
                and v23_mismatch.value > 0.0
                and (not feedback.user_resolved or feedback.human_rejected)
            ):
                self.v23_h_state.add_unresolved_mismatch(
                    pred.matched_node_id,
                    v23_mismatch.value,
                    mb_version=getattr(
                        getattr(getattr(resolved, "frozen_context", None), "frozen_mb", None),
                        "version",
                        "prod",
                    ),
                    is_canary=bool(getattr(resolved, "is_canary", False)),
                )

            resolved.v23_h_total = self.v23_h_state.global_mismatch.total()
            resolved.v23_coverage_gap_score = self.v23_coverage.coverage_gap_score()

        return result
