"""Explicit activation records after a successful Function promotion decision."""

from dataclasses import dataclass
from typing import Optional

from .compiled_function_types import CompiledFunctionArtifact
from .contracts import BoundaryContext, Provenance
from .function_types import FunctionDescription
from .promotion_types import PromotionDecision, PromotionDecisionStatus


@dataclass(frozen=True)
class ActiveFunction:
    """An explicitly registered compiled Function; creation requires approval.

    Activation registers a versioned operator artifact under one finite
    boundary.  It does not turn the Function into ``M_B`` and does not certify
    truth or completeness.
    """

    artifact: CompiledFunctionArtifact
    promotion: PromotionDecision
    registry: FunctionDescription
    context: BoundaryContext
    provenance: Optional[Provenance] = None

    def __post_init__(self) -> None:
        if self.promotion.artifact != self.artifact:
            raise ValueError("ActiveFunctionのArtifactとPromotionDecisionが一致していません")
        if self.promotion.status != PromotionDecisionStatus.APPROVED:
            raise ValueError("ActiveFunctionにはAPPROVEDのPromotionDecisionが必要です")
        if not isinstance(self.registry, FunctionDescription):
            raise TypeError("registryはFunctionDescriptionである必要があります")


# LEGACY compatibility name.  New code should use ActiveFunction.
ActiveCompiledMB = ActiveFunction


def activate_promoted_artifact(
    decision: PromotionDecision,
    context: BoundaryContext,
    *,
    registry: FunctionDescription = FunctionDescription("rdl_core.active_registry", "0"),
    provenance: Optional[Provenance] = None,
) -> ActiveFunction:
    """Register an approved Function artifact without changing the decision."""
    return ActiveFunction(
        artifact=decision.artifact,
        promotion=decision,
        registry=registry,
        context=context,
        provenance=provenance or decision.provenance,
    )
