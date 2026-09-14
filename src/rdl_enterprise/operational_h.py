"""Compatibility adapter for Core-v2.3 operational H semantics.

The legacy ``HState`` API is deeply integrated with Enterprise Runtime,
persistence, Canary and state-digest code.  This adapter preserves that API
while removing two pre-v2.3 operational effects:

- ``input_err`` does not enter H;
- Enterprise coverage observations do not lower theta.

The adapter is intentionally a migration device.  It does not make the
legacy ``HState`` scalar/dissipation model a Core primitive.
"""

from __future__ import annotations

from typing import Optional

from .h_state import HState


class V23OperationalHStateAdapter(HState):
    """Legacy-compatible state whose operational total contains mismatch only.

    ``pred_err`` is expected to be an unresolved mismatch derived from a
    bounded ``Delta(F, F')``.  ``input_err`` is accepted only so existing
    Runtime call sites remain source-compatible; it is intentionally discarded.

    Coverage observations are managed outside this adapter by
    ``ObservationCoverageState``.  Consequently they cannot alter the Core
    transition check ``H >= theta`` through this compatibility surface.
    """

    semantic_version = "core-v2.3-operational-h-adapter"

    def __init__(self, theta_0: float = 2.0, gamma: float = 0.05):
        super().__init__(
            theta_0=theta_0,
            gamma=gamma,
            w_pred=1.0,
            w_input=0.0,
        )

    def add_heat(
        self,
        node_id: Optional[str],
        pred_err: float = 0.0,
        input_err: float = 0.0,
        mb_version: str = "prod",
        is_canary: bool = False,
        opposing_constraint_strength: float = 1.0,
    ) -> None:
        """Retain only the supplied unresolved mismatch component.

        ``input_err`` is deliberately ignored.  ``opposing_constraint_strength``
        remains available as an Enterprise Standard-Model retention parameter;
        the RIB bridge currently supplies a neutral value until a RIB_B-native
        constraint weighting path is established.
        """

        super().add_heat(
            node_id=node_id,
            pred_err=pred_err,
            input_err=0.0,
            mb_version=mb_version,
            is_canary=is_canary,
            opposing_constraint_strength=opposing_constraint_strength,
        )

    def record_observation(
        self,
        unclassified: bool = False,
        missing_info: bool = False,
        unknown_input: bool = False,
        rejected: bool = False,
        mb_version: str = "prod",
        is_canary: bool = False,
    ) -> None:
        """Do not mix coverage observations into the operational H adapter."""

        return None

    def coverage_gap_score(self, mb_version: str = "prod") -> float:
        """Compatibility surface only; operational H owns no coverage state."""

        return 0.0

    def xi_obs(self, mb_version: str = "prod") -> float:
        """Deprecated legacy alias retained only for API compatibility.

        Returning zero here does *not* mean ``xi = 0``.  It means this adapter
        has no modeled coverage score at all.
        """

        return 0.0

    def theta_eff(self, mb_version: str = "prod") -> float:
        """Return the declared operational threshold without coverage coupling."""

        return float(self.theta_0)

    def theta_eff_for_base(self, base_threshold: float, mb_version: str = "prod") -> float:
        """Return an explicit Enterprise revision threshold unchanged."""

        return float(base_threshold)
