"""Canonical compiled Function artifacts for Core v2.3 migration.

Historically this repository used ``CompiledMB`` for the artifact produced by
Function validation.  Core v2.3 keeps ``M_B`` as a finite structural section
and treats Function as a reusable finite operator contract, so a compiled
Function artifact must not be named as though it were ``M_B`` itself.

``CompiledMB`` remains available from ``evolution_types`` as a compatibility
type while downstream lifecycle modules migrate to this canonical name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .evolution_types import (
    CompiledMB,
    CompilationRecord,
    CompilationValidationStatus,
    StructureCandidate,
)
from .function_types import FunctionDescription


@dataclass(frozen=True)
class CompiledFunction:
    """Validated versioned Function artifact under a finite structure boundary.

    ``structure`` is the finite relation structure used by the Function; the
    artifact itself is not ``M_B`` and its existence does not activate it.
    """

    function: FunctionDescription
    structure: StructureCandidate
    validation: CompilationRecord

    def __post_init__(self) -> None:
        if self.validation.candidate.function != self.function:
            raise ValueError("CompiledFunctionのFunctionとValidation候補が一致していません")
        if self.validation.candidate.structure != self.structure:
            raise ValueError("CompiledFunctionのStructureとValidation候補が一致していません")
        if self.validation.validation_status != CompilationValidationStatus.PASSED:
            raise ValueError("CompiledFunctionにはPASSEDのCompilationRecordが必要です")

    @classmethod
    def from_legacy(cls, artifact: CompiledMB) -> "CompiledFunction":
        """Convert the legacy-named artifact without changing its bounded content."""

        if not isinstance(artifact, CompiledMB):
            raise TypeError("artifact must be legacy CompiledMB")
        return cls(artifact.function, artifact.structure, artifact.validation)

    def to_legacy(self) -> CompiledMB:
        """Project to the historical compatibility type for unmigrated callers."""

        return CompiledMB(self.function, self.structure, self.validation)


CompiledFunctionArtifact = Union[CompiledFunction, CompiledMB]


def as_compiled_function(artifact: CompiledFunctionArtifact) -> CompiledFunction:
    """Return the canonical artifact while accepting the legacy compatibility type."""

    if isinstance(artifact, CompiledFunction):
        return artifact
    if isinstance(artifact, CompiledMB):
        return CompiledFunction.from_legacy(artifact)
    raise TypeError("artifact must be CompiledFunction or legacy CompiledMB")
