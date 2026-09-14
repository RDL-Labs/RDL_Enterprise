"""Enterprise interaction acquisition for the Core v2.3 RIB / RIB_B model.

This module deliberately separates raw Enterprise events from the finite
interaction section interpreted by the current runtime.

Canonical role:

    raw observation / request / later feedback
        -> acquisition under Purpose / B
        -> RIBSection   (Enterprise representation of RIB_B)
        -> interp(M_B, RIBSection)
        -> F

The existing Cascade still consumes ``BusinessInput``.  ``to_business_input``
is therefore a compatibility projection, not a claim that raw BusinessInput
and RIB_B are identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

from rdl_core import BoundaryContext, Provenance

from .snapshot import BusinessInput, FeedbackResult


@dataclass(frozen=True)
class RIBSection:
    """One finite, uninterpreted interaction section under a declared Boundary.

    ``RIBSection`` is an Enterprise implementation representation of Core
    ``RIB_B``.  It is *not* the relation network, not the complete set of RIBs,
    and not an interpreted state ``F``.

    ``payload`` contains only fields selected for this finite section.  Raw
    provider/world state may be broader and must not be silently promoted into
    the section.
    """

    section_id: str
    context: BoundaryContext
    section_role: str
    payload: Mapping[str, Any]
    projection_text: str
    source_refs: Tuple[str, ...] = ()
    provenance: Optional[Provenance] = None

    def __post_init__(self) -> None:
        if not isinstance(self.section_id, str) or not self.section_id.strip():
            raise ValueError("section_id must be a non-empty string")
        if not isinstance(self.context, BoundaryContext):
            raise TypeError("context must be BoundaryContext")
        if not isinstance(self.section_role, str) or not self.section_role.strip():
            raise ValueError("section_role must be a non-empty string")
        if not isinstance(self.projection_text, str):
            raise TypeError("projection_text must be a string")
        refs = tuple(dict.fromkeys(self.source_refs))
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ValueError("source_refs must contain non-empty strings")
        object.__setattr__(self, "source_refs", refs)
        # Shallow freeze is intentional: the acquisition contract selects the
        # top-level finite fields, while provider-specific nested values remain
        # opaque implementation data until a later adapter explicitly selects
        # them.
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    @property
    def boundary_id(self) -> str:
        return self.context.boundary_id

    @property
    def category(self) -> Optional[str]:
        value = self.payload.get("category")
        return value if isinstance(value, str) and value else None

    @property
    def ticket_id(self) -> Optional[str]:
        value = self.payload.get("ticket_id")
        return value if isinstance(value, str) and value else None

    def to_business_input(self) -> BusinessInput:
        """Project this finite section into the legacy Cascade input contract.

        This method is a migration adapter only.  Callers must not infer
        ``BusinessInput == RIB_B`` from its existence.
        """

        ticket_id = self.ticket_id or self.section_id
        user_id = self.payload.get("user_id")
        if not isinstance(user_id, str) or not user_id:
            user_id = "interaction-section"
        metadata = {
            "rib_section_id": self.section_id,
            "rib_section_role": self.section_role,
            "rib_boundary_id": self.context.boundary_id,
            "rib_source_refs": list(self.source_refs),
        }
        interaction_series_id = self.payload.get("interaction_series_id")
        if isinstance(interaction_series_id, str) and interaction_series_id:
            metadata["interaction_series_id"] = interaction_series_id
        return BusinessInput(
            ticket_id=ticket_id,
            user_id=user_id,
            category=self.category,
            query_text=self.projection_text,
            metadata=metadata,
            created_at=(
                self.context.observation_time
                or self.payload.get("created_at")
                or datetime.utcnow().isoformat()
            ),
        )


def acquire_request_rib_section(
    request: BusinessInput,
    *,
    context: Optional[BoundaryContext] = None,
    provenance: Optional[Provenance] = None,
) -> RIBSection:
    """Acquire the finite request-side interaction section used for interpretation."""

    if not isinstance(request, BusinessInput):
        raise TypeError("request must be BusinessInput")
    if context is None:
        conditions = {"category": request.category or "general"}
        series = request.metadata.get("interaction_series_id")
        if isinstance(series, str) and series:
            conditions["interaction_series_id"] = series
        context = BoundaryContext(
            boundary_id=f"enterprise.request:{request.ticket_id}",
            question=request.query_text,
            observation_time=request.created_at,
            purpose="business_request_interpretation",
            conditions=conditions,
        )
    if provenance is None:
        provenance = Provenance(
            source="business_input",
            actor=request.user_id,
            observed_at=request.created_at,
            lineage=request.ticket_id,
        )
    payload = {
        "ticket_id": request.ticket_id,
        "user_id": request.user_id,
        "category": request.category,
        "query_text": request.query_text,
        "created_at": request.created_at,
    }
    series = request.metadata.get("interaction_series_id")
    if isinstance(series, str) and series:
        payload["interaction_series_id"] = series
    return RIBSection(
        section_id=f"rib:{request.ticket_id}:request",
        context=context,
        section_role="request_observation",
        payload=payload,
        projection_text=request.query_text,
        source_refs=(f"business_input:{request.ticket_id}",),
        provenance=provenance,
    )


def acquire_feedback_rib_section(
    request: BusinessInput,
    feedback: FeedbackResult,
    *,
    context: Optional[BoundaryContext] = None,
    provenance: Optional[Provenance] = None,
) -> RIBSection:
    """Acquire a later finite section from feedback / subsequent observation.

    The returned section is not ``ξ`` and does not imply a Core mismatch by
    itself.  Core ``E`` exists only after this section is interpreted by the
    same pre-update ``M_B`` and compared with the earlier ``F``.
    """

    if not isinstance(request, BusinessInput):
        raise TypeError("request must be BusinessInput")
    if not isinstance(feedback, FeedbackResult):
        raise TypeError("feedback must be FeedbackResult")

    observed_at = feedback.observed_at
    if context is None:
        context = BoundaryContext(
            boundary_id=f"enterprise.feedback:{request.ticket_id}",
            question=request.query_text,
            observation_time=observed_at,
            purpose="subsequent_interaction_interpretation",
            conditions={"category": request.category or "general"},
        )

    relation_provenance = feedback.provenance
    if provenance is None:
        provenance = Provenance(
            source=(getattr(relation_provenance, "source_type", None) or "feedback"),
            actor=getattr(relation_provenance, "source_id", None),
            observed_at=observed_at,
            authority_ref=getattr(relation_provenance, "authority_scope", None),
            lineage=getattr(relation_provenance, "channel", None),
        )

    payload = {
        "ticket_id": f"{request.ticket_id}:subsequent",
        "user_id": request.user_id,
        "category": request.category,
        "original_ticket_id": request.ticket_id,
        "original_query": request.query_text,
        "user_resolved": feedback.user_resolved,
        "human_approved": feedback.human_approved,
        "human_rejected": feedback.human_rejected,
        "actual_response_text": feedback.actual_response_text,
        "feedback_comment": feedback.feedback_comment,
        "new_knowledge_provided": feedback.new_knowledge_provided,
        "correction_content": feedback.correction_content,
        "observed_at": observed_at,
    }

    text_components = [request.query_text]
    if feedback.human_rejected:
        text_components.append("【後続観測】差し戻し")
    elif not feedback.user_resolved:
        text_components.append("【後続観測】未解決")
    else:
        text_components.append("【後続観測】解決")
    if feedback.correction_content:
        text_components.append(f"【是正・訂正指示】{feedback.correction_content}")
    if feedback.new_knowledge_provided:
        text_components.append(f"【追加情報】{feedback.new_knowledge_provided}")
    if feedback.actual_response_text:
        text_components.append(f"【後続状態】{feedback.actual_response_text}")
    if feedback.feedback_comment:
        text_components.append(f"【フィードバック】{feedback.feedback_comment}")

    return RIBSection(
        section_id=f"rib:{request.ticket_id}:subsequent",
        context=context,
        section_role="subsequent_observation",
        payload=payload,
        projection_text="\n".join(text_components),
        source_refs=(
            f"business_input:{request.ticket_id}",
            f"feedback:{request.ticket_id}",
        ),
        provenance=provenance,
    )
