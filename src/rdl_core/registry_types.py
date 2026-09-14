"""Current-state projection over immutable Function lifecycle records."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .activation_types import ActiveFunction
from .deactivation_types import DeactivationRecord, DeactivationStatus


class RegistryStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUPERSEDED = "superseded"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class CurrentFunctionState:
    active: ActiveFunction
    status: RegistryStatus
    deactivation: Optional[DeactivationRecord] = None
    replacement: Optional[ActiveFunction] = None


def project_current_function_state(
    active: ActiveFunction,
    *,
    deactivation: Optional[DeactivationRecord] = None,
    replacement: Optional[ActiveFunction] = None,
) -> CurrentFunctionState:
    """Project current status without deleting activation/deactivation history."""
    if replacement is not None and replacement == active:
        raise ValueError("replacementは元のActive Functionと異なる必要があります")
    if replacement is not None and replacement.artifact == active.artifact:
        raise ValueError("SUPERSEDEDには異なるcompiled Function artifactが必要です")
    if replacement is not None:
        return CurrentFunctionState(active, RegistryStatus.SUPERSEDED, deactivation, replacement)
    if deactivation is None:
        return CurrentFunctionState(active, RegistryStatus.ACTIVE)
    if deactivation.active != active:
        raise ValueError("DeactivationRecordが対象ActiveFunctionと一致していません")
    status = (
        RegistryStatus.INACTIVE
        if deactivation.status == DeactivationStatus.DEACTIVATED
        else RegistryStatus.UNRESOLVED
    )
    return CurrentFunctionState(active, status, deactivation)
