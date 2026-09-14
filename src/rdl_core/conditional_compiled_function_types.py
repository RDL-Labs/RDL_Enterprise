"""Canonical conditional compiled Function artifacts.

``ConditionalCompiledMB`` is retained in ``evolution_types`` for compatibility.
This module gives the same bounded conditional lineage a Function-correct name
without changing the historical serialized shape in one step.
"""

from __future__ import annotations

from dataclasses import dataclass

from .compiled_function_types import CompiledFunction
from .evolution_types import (
    CompilationRecord,
    ConditionalCompilationRecord,
    ConditionalCompiledMB,
    ConditionalFunctionCandidate,
    ConditionalRelationCandidate,
    ConditionalRuptureCoverage,
    ConditionalValidationRecord,
)


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
