"""Staged Runtime bridge from raw Enterprise events to Core v2.3 RIB_B roles.

This migration surface keeps the product lifecycle of ``EnterpriseRuntime``
while replacing the semantic path in bounded stages.

Current canonical path:

    raw BusinessInput
      -> acquire_request_rib_section(...)
      -> RIBSection (Enterprise RIB_B representation)
      -> direct interpretation by the inherited Cascade
      -> F

    later raw feedback / observation
      -> acquire_feedback_rib_section(...)
      -> later RIBSection
      -> direct interpretation by the same frozen pre-update M_B/context
      -> F'
      -> bounded Delta(F, F')
      -> unresolved component only -> operational H

Canonical F/F' formation no longer projects ``RIBSection`` back to
``BusinessInput``. Legacy BusinessInput/EFP-shaped logic remains only inside
unmigrated lifecycle diagnostics and compatibility surfaces.

Coverage, missing information, unknown routing and rejection observations remain
separate Enterprise-local measurements. They do not quantify Core ``xi`` and
do not lower the operational reconstruction threshold on this bridge.
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
from .operational_h import V23OperationalHStateAdapter
from .runtime import EnterpriseRuntime, TicketDispatchResult, TicketResolutionResult
from .snapshot import (
    BusinessInput,
    CaseSnapshot,
    FeedbackResult,
    CaseStatus,
    OutcomeObservation,
)


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
    """Runtime whose canonical interpretation input is the acquired RIBSection.

    Public raw-request compatibility is retained, but F/F' and operational
    H/M_delta use the v2.3 roles directly. ``e_input`` remains available as a
    legacy diagnostic value returned by the parent snapshot path; it is not
    added to H.
    """

    migration_stage = "P8_RIB_DIRECT_INTERPRETATION"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        loaded_h_state = self.h_state
        theta = float(getattr(loaded_h_state, "theta_0", 2.0))
        gamma = float(getattr(loaded_h_state, "gamma", 0.05))

        # A persisted bridge may already contain the v2.3 operational adapter.
        # A legacy Runtime state is not silently reinterpreted as v2.3 H: keep
        # it as an explicit in-memory migration archive and start a new bounded
        # operational H state.
        if isinstance(loaded_h_state, V23OperationalHStateAdapter):
            self.legacy_h_state_archive = None
            self.h_state = loaded_h_state
            self.operational_h_migration_reset = False
        else:
            self.legacy_h_state_archive = loaded_h_state
            self.h_state = V23OperationalHStateAdapter(theta_0=theta, gamma=gamma)
            self.operational_h_migration_reset = True

        # Independent audit/shadow state: useful for comparing the explicit
        # unresolved-mismatch model with the legacy-compatible operational API.
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
            request_source: Union[BusinessInput, RIBSection] = request
        elif isinstance(request, BusinessInput):
            request_source = request
            rib_section = acquire_request_rib_section(request)
        else:
            raise TypeError("request must be BusinessInput or RIBSection")

        # P8 cutover: the inherited Runtime receives the acquired finite section
        # itself. EnterpriseRuntime is structurally typed here; RIBSection
        # exposes the bounded read contract used by Cascade/lifecycle code.
        # No BusinessInput projection participates in canonical F formation.
        result = super().dispatch_ticket(
            rib_section,
            human_override_answer=human_override_answer,
            authority=authority,
        )

        snapshot = self.pending_snapshots[result.ticket_id]
        snapshot.request_source = request_source
        if isinstance(request_source, BusinessInput):
            # Historical field retained only for callers that still inspect the
            # raw request. Canonical interpretation uses ``snapshot.efp`` /
            # ``snapshot.rib_section``, both of which are the RIBSection.
            snapshot.raw_business_input = request_source
        snapshot.rib_section = rib_section
        snapshot.interaction_semantic_version = "core-v2.3-rib-p8-direct"

        # Parent dispatch persists before these migration aliases are attached.
        # Re-save so restart inspection can recover the canonical section and
        # its raw-source link where one exists.
        if self.case_store:
            self.case_store.save_case(
                result.ticket_id,
                snapshot,
                snapshot.status.value,
            )
            self._persist_runtime_state()
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
        request_source = getattr(
            snapshot,
            "request_source",
            getattr(snapshot, "raw_business_input", snapshot.efp),
        )
        rib_section_next = acquire_feedback_rib_section(request_source, feedback)
        snapshot.rib_section_next = rib_section_next

        # Canonical comparison: interpret the acquired later RIB section itself,
        # not a reconstructed BusinessInput projection. The same frozen
        # pre-update M_B and interpretation conditions are reused.
        v23_f_prime = None
        v23_mismatch = None
        frozen_context = getattr(snapshot, "frozen_context", None)
        if frozen_context is not None:
            v23_f_prime = frozen_context.interpret_efp(rib_section_next)
            if v23_f_prime is not None:
                v23_mismatch = compare_interpretation_states(
                    snapshot.f_pred,
                    v23_f_prime,
                )
        snapshot.v23_f_prime = v23_f_prime
        snapshot.v23_mismatch = v23_mismatch
        snapshot.v23_core_e_status = "OBSERVED" if v23_mismatch is not None else "NOT_EVALUATED"

        # Parent resolution still performs product lifecycle work. Its call to
        # ``self._finalize_case_metabolism`` dispatches to the override below,
        # where legacy E/input/C_prime heat is replaced by canonical v2.3 roles.
        # CaseSnapshot's inherited EFP-prime interpretation remains a diagnostic
        # compatibility path and does not define the canonical F' above.
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
            resolved.interaction_semantic_version = "core-v2.3-rib-p8-direct"

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

            # Independent audit state mirrors the same unresolved-only
            # retention rule used by the operational adapter.
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
            resolved.v23_operational_h_total = self.h_state.global_heat.total(
                self.h_state.w_pred,
                self.h_state.w_input,
            )
            resolved.v23_coverage_gap_score = self.v23_coverage.coverage_gap_score()

        return result

    def _finalize_case_metabolism(
        self,
        snapshot: CaseSnapshot,
        status: CaseStatus,
        e_pred: float,
        e_input: float,
        feedback: Optional[FeedbackResult] = None,
        opposing_strength: float = 1.0,
        is_timeout: bool = False,
        at: Optional[Any] = None,
        operation_id: Optional[str] = None,
        actor_provenance: Optional[Dict[str, Any]] = None,
    ) -> TicketResolutionResult:
        """Cut operational H over to the canonical v2.3 mismatch path.

        The parent Runtime still supplies legacy ``e_pred``, ``e_input`` and a
        legacy C_prime-derived ``opposing_strength``. None of those values is
        allowed to directly drive H on this bridge.

        Operational retention rule:

            observed E = Delta(F, F') when a canonical comparison exists
            retained H increment = E only when the later observation remains
                                   unresolved/rejected
            input / coverage metrics = never H

        A neutral retention weight is used until relation-constraint weighting
        is rebuilt directly from RIB_B rather than the retired EFP' path.
        """

        observation = getattr(snapshot, "v23_mismatch", None)
        observed_e: Optional[float] = None
        retained_mismatch = 0.0

        if observation is not None:
            observed_e = float(observation.value)
            unresolved = bool(
                feedback is not None
                and (not feedback.user_resolved or feedback.human_rejected)
            )
            if unresolved:
                retained_mismatch = observed_e

        snapshot.v23_observed_e = observed_e
        snapshot.v23_retained_mismatch = retained_mismatch
        snapshot.v23_legacy_e_prediction_diagnostic = e_pred
        snapshot.v23_legacy_e_input_diagnostic = e_input

        result = super()._finalize_case_metabolism(
            snapshot=snapshot,
            status=status,
            e_pred=retained_mismatch,
            e_input=0.0,
            feedback=feedback,
            opposing_strength=1.0,
            is_timeout=is_timeout,
            at=at,
            operation_id=operation_id,
            actor_provenance=actor_provenance,
        )

        # Preserve observability without giving diagnostics operational force.
        result.e_input = e_input
        if observed_e is None:
            result.e_prediction = 0.0
            result.difference_reaction_status = "NOT_EVALUATED"
        else:
            result.e_prediction = observed_e
            if retained_mismatch > 0.0:
                result.difference_reaction_status = "RETAINED_UNRESOLVED"
            elif observed_e > 0.0:
                result.difference_reaction_status = "RESOLVED_NOT_RETAINED"
            else:
                result.difference_reaction_status = "NO_MISMATCH"

        result.v23_core_e_status = (
            "OBSERVED" if observed_e is not None else "NOT_EVALUATED"
        )
        result.v23_retained_mismatch = retained_mismatch
        result.v23_operational_h = self.h_state.global_heat.total(
            self.h_state.w_pred,
            self.h_state.w_input,
        )
        result.v23_operational_theta = self.h_state.theta_eff()
        return result

    def expire_pending_tickets_v23(
        self,
        ticket_ids: Optional[List[str]] = None,
        at: Optional[Any] = None,
    ) -> List[V23TimeoutResolution]:
        """Resolve timeouts without fabricating ``F'``, Core ``E`` or ``H``.

        This is the canonical timeout path. The inherited legacy timeout method
        is still available for product compatibility, but because operational H
        is now cut over through ``_finalize_case_metabolism`` it cannot add its
        synthetic legacy E/input values to H on this bridge.
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
            snapshot.rib_section_next = None
            snapshot.v23_f_prime = None
            snapshot.v23_mismatch = None
            snapshot.v23_core_e_status = "NOT_EVALUATED"
            snapshot.interaction_semantic_version = "core-v2.3-rib-p8-direct"

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
            snapshot.v23_operational_h_total = self.h_state.global_heat.total(
                self.h_state.w_pred,
                self.h_state.w_input,
            )
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
                current_h=self.h_state.global_heat.total(
                    self.h_state.w_pred,
                    self.h_state.w_input,
                ),
                current_theta=self.h_state.theta_eff(),
                coverage_gap_score=self.v23_coverage.coverage_gap_score(),
            ))

        return results
