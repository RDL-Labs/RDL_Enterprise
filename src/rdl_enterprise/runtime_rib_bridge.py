"""Staged Runtime bridge from raw Enterprise events to Core v2.3 RIB_B roles.

This is a migration surface, not a claim that the legacy Enterprise Runtime is
already fully Core v2.3 compliant. It moves the request/subsequent-observation
boundary first while the legacy Cascade and metabolism implementation remain
available behind compatibility projections.

Current staged path:

    raw BusinessInput
      -> acquire_request_rib_section(...)
      -> RIBSection
      -> compatibility BusinessInput
      -> legacy EnterpriseRuntime / InterpCascade

Later feedback is acquired as a canonical subsequent RIBSection. The bridge
also forms a shadow ``F'`` from that section with the same frozen pre-update
interpretation context and records a v2.3-style ``Delta(F, F')`` separately
from the legacy metabolism.

Important: the inherited legacy metabolism still contains pre-v2.3 semantics
(`e_input` heat and observable-xi compatibility policy). The new mismatch / H /
coverage states are migration evidence until the legacy path is cut over.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .authority import AuthorityContext
from .interaction import RIBSection, acquire_feedback_rib_section, acquire_request_rib_section
from .mismatch_state import (
    ObservationCoverageState,
    UnresolvedMismatchState,
    compare_interpretation_states,
)
from .runtime import EnterpriseRuntime, TicketDispatchResult, TicketResolutionResult
from .snapshot import BusinessInput, FeedbackResult, CaseStatus, OutcomeObservation


@dataclass(frozen=True)
class V23TimeoutResolution:
    """Timeout observation where no later Core comparison state was established."""

    ticket_id: str
    status: CaseStatus
    f_prime_status: str
    e_status: str
    e_prediction: Optional[float]
    current_h: float
    current_theta: float
    coverage_gap_score: float


class EnterpriseRuntimeRIBBridge(EnterpriseRuntime):
    """Compatibility Runtime that makes the RIB_B acquisition boundary real.

    The public request API continues to accept ``BusinessInput`` for product
    compatibility. A pre-built ``RIBSection`` may also be supplied for tests
    and explicit acquisition pipelines.
    """

    migration_stage = "P1_P4_RIB_MISMATCH_TIMEOUT_SHADOW"

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

            pred = resolved.f_pred
            mb_version = getattr(
                getattr(getattr(resolved, "frozen_context", None), "frozen_mb", None),
                "version",
                "prod",
            )
            self.v23_coverage.record(
                unclassified=(pred.matched_node_id is None),
                missing_info=False,
                unknown_route=(pred.matched_node_id is None and pred.cost_tier == 3),
                rejected=bool(feedback.human_rejected),
                mb_version=mb_version,
                is_canary=bool(getattr(resolved, "is_canary", False)),
            )

            # Enterprise shadow retention policy: only a mismatch that remains
            # unresolved by the later observation contributes to the v2.3 H
            # candidate. Resolution status is separate from F' construction.
            if (
                v23_mismatch is not None
                and v23_mismatch.value > 0.0
                and (not feedback.user_resolved or feedback.human_rejected)
            ):
                self.v23_h_state.add_unresolved_mismatch(
                    pred.matched_node_id,
                    v23_mismatch.value,
                    mb_version=mb_version,
                    is_canary=bool(getattr(resolved, "is_canary", False)),
                )

            resolved.v23_h_total = self.v23_h_state.global_mismatch.total()
            resolved.v23_coverage_gap_score = self.v23_coverage.coverage_gap_score()

        return result

    def expire_pending_tickets_v23(
        self,
        ticket_ids: Optional[List[str]] = None,
        at: Optional[Any] = None,
    ) -> List[V23TimeoutResolution]:
        """Resolve timeouts without fabricating ``F'``, Core ``E`` or ``H``.

        This method is the canonical migration path. The inherited
        ``expire_pending_tickets`` remains available only for legacy product
        compatibility until Runtime cutover.
        """

        target_ids = ticket_ids if ticket_ids is not None else list(self.pending_snapshots.keys())
        results: List[V23TimeoutResolution] = []

        for ticket_id in target_ids:
            if ticket_id not in self.pending_snapshots:
                continue

            snapshot = self.pending_snapshots.pop(ticket_id)
            resolved_at = at.isoformat() if isinstance(at, datetime) else (str(at) if at is not None else datetime.utcnow().isoformat())
            snapshot.status = CaseStatus.UNKNOWN
            snapshot.resolved_at = resolved_at
            snapshot.outcome_observation = OutcomeObservation(
                status=CaseStatus.UNKNOWN,
                outcome="not_evaluated",
                user_resolved=False,
                feedback_comment="timeout: later interaction section unavailable",
                observed_at=resolved_at,
            )
            # Crucial semantic difference from legacy mark_unknown(): absence of
            # a later section is not interpreted as a zero or synthetic delta.
            snapshot.rib_section_next = None
            snapshot.v23_f_prime = None
            snapshot.v23_mismatch = None
            snapshot.v23_core_e_status = "NOT_EVALUATED"
            snapshot.interaction_semantic_version = "core-v2.3-rib-shadow"

            pred = snapshot.f_pred
            self.v23_coverage.record(
                unclassified=(pred.matched_node_id is None),
                missing_info=True,
                unknown_route=(pred.matched_node_id is None and pred.cost_tier == 3),
                rejected=False,
                mb_version=getattr(
                    getattr(getattr(snapshot, "frozen_context", None), "frozen_mb", None),
                    "version",
                    "prod",
                ),
                is_canary=bool(getattr(snapshot, "is_canary", False)),
            )
            snapshot.v23_h_total = self.v23_h_state.global_mismatch.total()
            snapshot.v23_coverage_gap_score = self.v23_coverage.coverage_gap_score()

            self.resolved_snapshots.append(snapshot)
            self.timeout_count += 1
            if self.case_store:
                self.case_store.save_case(ticket_id, snapshot, snapshot.status.value)
                self._persist_runtime_state()

            results.append(V23TimeoutResolution(
                ticket_id=ticket_id,
                status=CaseStatus.UNKNOWN,
                f_prime_status="NOT_EVALUATED",
                e_status="NOT_EVALUATED",
                e_prediction=None,
                current_h=self.v23_h_state.global_mismatch.total(),
                current_theta=self.v23_h_state.theta,
                coverage_gap_score=self.v23_coverage.coverage_gap_score(),
            ))

        return results
