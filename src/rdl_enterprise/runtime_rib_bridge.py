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

Later feedback is also acquired as a canonical subsequent RIBSection and
attached to the case before/after the legacy feedback metabolism runs.

Important: the inherited legacy metabolism still contains pre-v2.3 semantics
(`e_input` heat and observable-xi threshold policy).  Consumers must not treat
this bridge as completion of the migration until those stages are replaced.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from .authority import AuthorityContext
from .interaction import RIBSection, acquire_feedback_rib_section, acquire_request_rib_section
from .runtime import EnterpriseRuntime, TicketDispatchResult, TicketResolutionResult
from .snapshot import BusinessInput, FeedbackResult


class EnterpriseRuntimeRIBBridge(EnterpriseRuntime):
    """Compatibility Runtime that makes the RIB_B acquisition boundary real.

    The public request API continues to accept ``BusinessInput`` for product
    compatibility.  A pre-built ``RIBSection`` may also be supplied for tests
    and explicit acquisition pipelines.
    """

    migration_stage = "P1_P2_RIB_ACQUISITION_BRIDGE"

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
        # These fields are deliberately additive.  Existing ``efp`` remains a
        # compatibility field until Snapshot/Persistence migration is complete.
        snapshot.raw_business_input = raw_request
        snapshot.rib_section = rib_section
        snapshot.interaction_semantic_version = "core-v2.3-rib-bridge"
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
        # Attach before the legacy call so persistence of a pending snapshot can
        # retain acquisition provenance if later code adds an intermediate save.
        snapshot.rib_section_next = rib_section_next

        result = super().resolve_ticket_feedback(
            ticket_id,
            feedback,
            at=at,
            operation_id=operation_id,
            actor_provenance=actor_provenance,
            authority=authority,
        )

        # The same snapshot object is moved to resolved_snapshots by the legacy
        # Runtime.  Keep canonical section identity recoverable there as well.
        resolved = next(
            (item for item in reversed(self.resolved_snapshots)
             if getattr(getattr(item, "efp", None), "ticket_id", None) == ticket_id),
            None,
        )
        if resolved is not None:
            resolved.rib_section_next = rib_section_next
            resolved.interaction_semantic_version = "core-v2.3-rib-bridge"
        return result
