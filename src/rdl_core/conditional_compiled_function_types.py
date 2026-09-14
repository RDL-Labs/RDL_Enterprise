"""Canonical conditional compiled Function artifacts and lifecycle wrappers.

``ConditionalCompiledMB`` and its lifecycle records remain in
``evolution_types`` for compatibility.  This module gives the same bounded
conditional lineage Function-correct names without changing the historical
serialized shape in one step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .activation_types import ActiveFunction, activate_promoted_artifact
from .compiled_function_types import CompiledFunction
from .contracts import BoundaryContext
from .evolution_types import (
    CompilationRecord,
    ConditionalCompilationRecord,
    ConditionalCompiledMB,
    ConditionalFunctionCandidate,
    ConditionalRelationCandidate,
    ConditionalRuptureCoverage,
    ConditionalRuptureRecord,
    ConditionalValidationRecord,
    translate_conditional_ruptures_to_function,
)
from .promotion_types import PromotionDecision, evaluate_promotion


@dataclass(frozen=True)
class ConditionalCompiledFunction:
    """Compiled Function plus recoverable conditional learning lineage."""

    generic_artifact: CompiledFunction
    candidate: ConditionalFunctionCandidate
    compilation: ConditionalCompilationRecord

    def __post_init__(self) -> None:
        if not isinstance(self.generic_artifact, CompiledFunction):
            raise TypeError("generic_artifactはCompiledFunctionである必要があります")
        if not isinstance(self.candidate, ConditionalFunctionCandidate):
            raise TypeError("candidateはConditionalFunctionCandidateである必要があります")
        if not isinstance(self.compilation, ConditionalCompilationRecord):
            raise TypeError("compilationはConditionalCompilationRecordである必要があります")
        if self.compilation.candidate != self.candidate:
            raise ValueError("Conditional compilationのCandidateが一致していません")
        if self.generic_artifact.validation != self.compilation.generic_record:
            raise ValueError("CompiledFunctionのValidationがConditional compilationと一致していません")

    @classmethod
    def from_legacy(cls, artifact: ConditionalCompiledMB) -> "ConditionalCompiledFunction":
        if not isinstance(artifact, ConditionalCompiledMB):
            raise TypeError("artifact must be legacy ConditionalCompiledMB")
        return cls(
            CompiledFunction.from_legacy(artifact.generic_artifact),
            artifact.candidate,
            artifact.compilation,
        )

    def to_legacy(self) -> ConditionalCompiledMB:
        return ConditionalCompiledMB(
            self.generic_artifact.to_legacy(),
            self.candidate,
            self.compilation,
        )

    @property
    def conditional_validation(self) -> ConditionalValidationRecord:
        return self.candidate.validation

    @property
    def conditional_candidate(self) -> ConditionalRelationCandidate:
        return self.candidate.conditional_candidate

    @property
    def generic_compilation(self) -> CompilationRecord:
        return self.compilation.generic_record

    @property
    def rupture_coverage(self) -> ConditionalRuptureCoverage:
        return self.candidate.rupture_coverage

    @property
    def artifact(self) -> CompiledFunction:
        """Canonical generic Function artifact used by lifecycle gates."""
        return self.generic_artifact


@dataclass(frozen=True)
class ConditionalFunctionPromotionRecord:
    """Canonical promotion decision plus recoverable conditional lineage."""

    artifact: ConditionalCompiledFunction
    decision: PromotionDecision

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, ConditionalCompiledFunction):
            raise TypeError("artifactはConditionalCompiledFunctionである必要があります")
        if not isinstance(self.decision, PromotionDecision):
            raise TypeError("decisionはPromotionDecisionである必要があります")
        if self.decision.artifact != self.artifact.generic_artifact:
            raise ValueError("PromotionDecisionのArtifactがConditionalCompiledFunctionと一致していません")


@dataclass(frozen=True)
class ConditionalFunctionActivationRecord:
    """Canonical ActiveFunction plus recoverable conditional lineage."""

    promotion: ConditionalFunctionPromotionRecord
    active: ActiveFunction

    def __post_init__(self) -> None:
        if not isinstance(self.promotion, ConditionalFunctionPromotionRecord):
            raise TypeError("promotionはConditionalFunctionPromotionRecordである必要があります")
        if not isinstance(self.active, ActiveFunction):
            raise TypeError("activeはActiveFunctionである必要があります")
        if self.active.artifact != self.promotion.artifact.generic_artifact:
            raise ValueError("Active Function artifactがConditional lineageと一致していません")


def evaluate_conditional_function_promotion(
    artifact: ConditionalCompiledFunction,
    ruptures: Tuple[ConditionalRuptureRecord, ...],
    context: BoundaryContext,
    *,
    required_checks: Tuple[str, ...] = (),
) -> ConditionalFunctionPromotionRecord:
    """Evaluate canonical conditional Function promotion without losing lineage."""

    if not isinstance(artifact, ConditionalCompiledFunction):
        raise TypeError("artifactはConditionalCompiledFunctionである必要があります")
    translated = translate_conditional_ruptures_to_function(
        artifact.candidate.function_candidate,
        artifact.conditional_candidate,
        tuple(ruptures),
    )
    decision = evaluate_promotion(
        artifact.generic_artifact,
        context,
        ruptures=translated,
        required_checks=required_checks,
    )
    return ConditionalFunctionPromotionRecord(artifact, decision)


def activate_conditional_function_promotion(
    promotion: ConditionalFunctionPromotionRecord,
    context: BoundaryContext,
) -> ConditionalFunctionActivationRecord:
    """Activate an approved canonical conditional Function explicitly."""

    if not isinstance(promotion, ConditionalFunctionPromotionRecord):
        raise TypeError("promotionはConditionalFunctionPromotionRecordである必要があります")
    active = activate_promoted_artifact(promotion.decision, context)
    return ConditionalFunctionActivationRecord(promotion, active)
