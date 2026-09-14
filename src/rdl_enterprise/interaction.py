"""Enterprise interaction acquisition for the Core v2.3 RIB / RIB_B model.

This module deliberately separates raw Enterprise events from the finite
interaction section interpreted by the current runtime.

Canonical role:

    raw observation / request / later feedback
        -> acquisition under Purpose / B
        -> RIBSection   (Enterprise representation of RIB_B)
        -> interp(M_B, RIBSection)
        -> F

``RIBSection`` exposes the small read-only attribute contract consumed by the
existing Cascade, so canonical interpretation can use the section directly.
``to_business_input`` remains only for unmigrated product/lifecycle surfaces;
it is not required to form canonical F or F'.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple

from rdl_core import BoundaryContext, Provenance

from .snapshot import BusinessInput, FeedbackResult


def _plain_persistence_value(value: Any) -> Any:
    """Return a pickle-safe plain representation of frozen finite values."""
    if isinstance(value, Mapping):
        return {key: _plain_persistence_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_plain_persistence_value(item) for item in value)
    if isinstance(value, frozenset):
        return {_plain_persistence_value(item) for item in value}
    return value


def _restore_rib_section(
    section_id: str,
    context_record: Tuple[Any, ...],
    section_role: str,
    payload: Mapping[str, Any],
    projection_text: str,
    source_refs: Tuple[str, ...],
    provenance: Optional[Provenance],
):
    """Reconstruct a frozen section from its persistence-safe record."""
    boundary_id, question, observation_time, purpose, conditions = context_record
    context = BoundaryContext(
        boundary_id=boundary_id,
        question=question,
        observation_time=observation_time,
        purpose=purpose,
        conditions=conditions,
    )
    return RIBSection(
        section_id=section_id,
        context=context,
        section_role=section_role,
        payload=payload,
        projection_text=projection_text,
        source_refs=source_refs,
        provenance=provenance,
    )


@dataclass(frozen=True)
class RIBSection:
    """One finite, uninterpreted interaction section under a declared Boundary.

    ``RIBSection`` is an Enterprise implementation representation of Core
    ``RIB_B``. It is *not* the relation network, not the complete set of RIBs,
    and not an interpreted state ``F``.

    ``payload`` contains only fields selected for this finite section. Raw
    provider/world state may be broader and must not be silently promoted into
    the section.

    The compatibility-shaped properties below are views over this finite
    section. They do not reconstruct a raw ``BusinessInput`` and do not change
    the section's identity or payload.
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

    def __reduce__(self):
        """Persist without serializing MappingProxyType implementation objects.

        SQLiteCaseStore uses pickle at the Enterprise boundary.  Both this
        payload and Core BoundaryContext.conditions are intentionally frozen by
        MappingProxyType, which is not pickleable.  Persist a plain finite
        record and reconstruct through the normal constructors so the frozen
        invariants are restored after restart.
        """
        context_record = (
            self.context.boundary_id,
            self.context.question,
            self.context.observation_time,
            self.context.purpose,
            _plain_persistence_value(self.context.conditions),
        )
        return (
            _restore_rib_section,
            (
                self.section_id,
                context_record,
                self.section_role,
                _plain_persistence_value(self.payload),
                self.projection_text,
                self.source_refs,
                self.provenance,
            ),
        )

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

    @property
    def user_id(self) -> str:
        value = self.payload.get("user_id")
        return value if isinstance(value, str) and value else "interaction-section"

    @property
    def query_text(self) -> str:
        """Finite text view consumed by the current interpretation cascade."""
        return self.projection_text

    @property
    def created_at(self) -> str:
        """Recover the section observation time without introducing wall time."""
        value = (
            self.context.observation_time
            or self.payload.get("created_at")
            or self.payload.get("observed_at")
        )
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    @property
    def is_prime(self) -> bool:
        """Legacy Cascade hint for a later interaction section."""
        return self.section_role == "subsequent_observation"

    @property
    def metadata(self) -> Dict[str, Any]:
        """Detached finite metadata view for the current Cascade contract.

        The returned dict is rebuilt on every access. Mutating it cannot mutate
        the frozen RIB section. Fields with old names exist only because the
        inherited Cascade still reads them while P8 removes that dependency.
        """
        metadata: Dict[str, Any] = {
            "rib_section_id": self.section_id,
            "rib_section_role": self.section_role,
            "rib_boundary_id": self.context.boundary_id,
            "rib_source_refs": list(self.source_refs),
        }
        interaction_series_id = self.payload.get("interaction_series_id")
        if isinstance(interaction_series_id, str) and interaction_series_id:
            metadata["interaction_series_id"] = interaction_series_id
        if self.is_prime:
            metadata.update({
                "is_efp_prime": True,
                "original_query": self.payload.get("original_query"),
                "user_resolved": self.payload.get("user_resolved", True),
                "human_approved": self.payload.get("human_approved", False),
                "human_rejected": self.payload.get("human_rejected", False),
                "actual_response_text": self.payload.get("actual_response_text"),
                "feedback_comment": self.payload.get("feedback_comment"),
                "new_knowledge_provided": self.payload.get("new_knowledge_provided"),
                "correction_content": self.payload.get("correction_content"),
            })
        return metadata

    def to_business_input(self) -> BusinessInput:
        """Project this section into the legacy product/lifecycle input type.

        This is a compatibility adapter only. Canonical interpretation may pass
        ``RIBSection`` directly to the Cascade. Callers must not infer
        ``BusinessInput == RIB_B`` from this adapter's existence.
        """

        return BusinessInput(
            ticket_id=self.ticket_id or self.section_id,
            user_id=self.user_id,
            category=self.category,
            query_text=self.query_text,
            metadata=self.metadata,
            created_at=self.created_at or datetime.utcnow().isoformat(),
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
    itself. Core ``E`` exists only after this section is interpreted by the
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
