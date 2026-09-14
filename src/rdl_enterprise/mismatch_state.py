"""Core-v2.3-aligned mismatch state and Enterprise-local coverage metrics.

The legacy :mod:`rdl_enterprise.h_state` mixes two different roles:

- unresolved F/F' mismatch used as an H-like state;
- input / missing / unknown observations used as an auxiliary heat and as
  ``xi_obs``.

This module separates those roles without immediately removing the legacy
state used by the existing Runtime.

Nothing in this module attempts to quantify Core ``xi``.  Coverage and missing
observation metrics are explicit Enterprise-local observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class InterpretationMismatchObservation:
    """One bounded Enterprise observation of ``Delta(F, F')``.

    The weighting below is an Enterprise comparison policy, not a Core
    definition of distance.  Core fixes the role of ``E`` as a mismatch
    between the two interpreted states; the concrete ``Delta`` may be replaced
    for another Boundary / application.
    """

    value: float
    reasons: Tuple[str, ...] = ()


def compare_interpretation_states(current: Any, subsequent: Any) -> InterpretationMismatchObservation:
    """Compare two interpretation records using the current Enterprise delta.

    Both records are expected to have been formed by the same pre-update
    ``M_B`` and frozen interpretation conditions.  This function does not
    inspect raw input completeness, timeout, queue load, or ``xi``.
    """

    value = 0.0
    reasons = []

    if getattr(subsequent, "matched_node_id", None) != getattr(current, "matched_node_id", None):
        value += 0.5
        reasons.append("matched_node_changed")

    if getattr(subsequent, "action_type", None) != getattr(current, "action_type", None):
        value += 0.4
        reasons.append("action_type_changed")

    if getattr(subsequent, "expected_outcome", None) != getattr(current, "expected_outcome", None):
        value += 0.4
        reasons.append("expected_outcome_changed")

    current_confidence = float(getattr(current, "confidence", 0.0))
    subsequent_confidence = float(getattr(subsequent, "confidence", current_confidence))
    confidence_gap = abs(current_confidence - subsequent_confidence)
    if confidence_gap > 1e-4:
        value += 0.4 * confidence_gap
        reasons.append(f"confidence_gap:{confidence_gap:.4f}")

    if getattr(subsequent, "content", None) != getattr(current, "content", None):
        value += 0.2
        reasons.append("content_changed")

    return InterpretationMismatchObservation(round(value, 4), tuple(reasons))


@dataclass
class MismatchBucket:
    """Accumulated unresolved mismatch for one finite implementation locus."""

    unresolved_mismatch: float = 0.0

    def total(self) -> float:
        return max(0.0, float(self.unresolved_mismatch))


class UnresolvedMismatchState:
    """Enterprise Standard-Model candidate for Core ``H``.

    Core fixes the role of ``H`` as unresolved mismatch carried from ``E``;
    Core does not require this particular scalar accumulation algorithm.
    Therefore this class is an implementation candidate, not a new primitive.

    Acquisition gaps, missing information, uncertainty, queue load and human
    attention are intentionally absent from this state.
    """

    def __init__(self, theta: float = 2.0, gamma: float = 0.05):
        if theta < 0:
            raise ValueError("theta must be non-negative")
        if not 0.0 <= gamma <= 1.0:
            raise ValueError("gamma must be between 0 and 1")
        self.theta = float(theta)
        self.gamma = float(gamma)
        self.node_mismatch: Dict[str, MismatchBucket] = {}
        self.versioned_mismatch: Dict[Tuple[str, str], MismatchBucket] = {}
        self.global_mismatch = MismatchBucket()

    def add_unresolved_mismatch(
        self,
        node_id: Optional[str],
        mismatch: float,
        *,
        mb_version: str = "prod",
        is_canary: bool = False,
        retention_weight: float = 1.0,
    ) -> None:
        """Add only an unresolved component derived from ``E``.

        ``retention_weight`` is an Enterprise Standard-Model parameter.  It is
        not ``xi`` and is not mandated by Core.
        """

        if mismatch < 0:
            raise ValueError("mismatch must be non-negative")
        if retention_weight < 0:
            raise ValueError("retention_weight must be non-negative")
        retained = float(mismatch) * float(retention_weight)
        target = node_id or "__unmatched__"

        key = (mb_version, target)
        bucket = self.versioned_mismatch.setdefault(key, MismatchBucket())
        bucket.unresolved_mismatch += retained

        if not is_canary:
            if node_id:
                node_bucket = self.node_mismatch.setdefault(node_id, MismatchBucket())
                node_bucket.unresolved_mismatch += retained
            self.global_mismatch.unresolved_mismatch += retained

    def total_for_version(self, mb_version: str) -> float:
        return sum(
            bucket.total()
            for (version, _), bucket in self.versioned_mismatch.items()
            if version == mb_version
        )

    def hottest_node_for_version(self, mb_version: str) -> Optional[str]:
        candidates = (
            (node_id, bucket.total())
            for (version, node_id), bucket in self.versioned_mismatch.items()
            if version == mb_version and node_id and not node_id.startswith("__")
        )
        best = max(candidates, key=lambda item: item[1], default=None)
        if best is not None:
            return best[0]
        fallback = max(
            ((node_id, bucket.total()) for node_id, bucket in self.node_mismatch.items()),
            key=lambda item: item[1],
            default=None,
        )
        return fallback[0] if fallback is not None else None

    def should_reconstruct(
        self,
        node_id: Optional[str] = None,
        *,
        threshold: Optional[float] = None,
    ) -> Tuple[bool, str, float]:
        """Evaluate the Core role ``H >= theta`` for this implementation model."""

        theta = self.theta if threshold is None else float(threshold)
        if theta < 0:
            raise ValueError("threshold must be non-negative")

        if node_id and node_id in self.node_mismatch:
            value = self.node_mismatch[node_id].total()
            if value >= theta:
                return True, node_id, value

        hottest = max(
            ((nid, bucket.total()) for nid, bucket in self.node_mismatch.items()),
            key=lambda item: item[1],
            default=("", 0.0),
        )
        if hottest[0] and hottest[1] >= theta:
            return True, hottest[0], hottest[1]

        global_value = self.global_mismatch.total()
        if global_value >= theta:
            return True, "__global__", global_value
        return False, hottest[0], hottest[1]

    def dissipate(self) -> None:
        """Optional Enterprise dissipation model; not a Core requirement."""

        factor = 1.0 - self.gamma
        for bucket in self.node_mismatch.values():
            bucket.unresolved_mismatch *= factor
        for bucket in self.versioned_mismatch.values():
            bucket.unresolved_mismatch *= factor
        self.global_mismatch.unresolved_mismatch *= factor

    def clear_version(self, mb_version: str) -> None:
        for key in [key for key in self.versioned_mismatch if key[0] == mb_version]:
            del self.versioned_mismatch[key]


class ObservationCoverageState:
    """Enterprise-local observations about acquisition and operational coverage.

    This class deliberately has no ``xi`` API.  The score is a modeled summary
    of observed coverage problems, not the unrecovered relation ``xi``.
    """

    def __init__(self) -> None:
        self.versioned: Dict[str, Dict[str, int]] = {}
        self._prod = self._new_pool()

    @staticmethod
    def _new_pool() -> Dict[str, int]:
        return {
            "unclassified_count": 0,
            "missing_info_count": 0,
            "unknown_route_count": 0,
            "rejection_count": 0,
            "total_observations": 0,
        }

    def record(
        self,
        *,
        unclassified: bool = False,
        missing_info: bool = False,
        unknown_route: bool = False,
        rejected: bool = False,
        mb_version: str = "prod",
        is_canary: bool = False,
    ) -> None:
        pool = self.versioned.setdefault(mb_version, self._new_pool()) if is_canary else self._prod
        pool["total_observations"] += 1
        if unclassified:
            pool["unclassified_count"] += 1
        if missing_info:
            pool["missing_info_count"] += 1
        if unknown_route:
            pool["unknown_route_count"] += 1
        if rejected:
            pool["rejection_count"] += 1

    def coverage_gap_score(self, mb_version: str = "prod") -> float:
        """Return a bounded Enterprise policy score; this is not Core ``xi``."""

        pool = self._prod if mb_version == "prod" else self.versioned.get(mb_version, self._new_pool())
        total = pool["total_observations"]
        if total == 0:
            return 0.0
        rates = {
            key: pool[key] / total
            for key in (
                "unclassified_count",
                "missing_info_count",
                "unknown_route_count",
                "rejection_count",
            )
        }
        return min(
            1.0,
            0.3 * rates["unclassified_count"]
            + 0.2 * rates["missing_info_count"]
            + 0.3 * rates["unknown_route_count"]
            + 0.2 * rates["rejection_count"],
        )


@dataclass(frozen=True)
class CoverageAdjustedThresholdPolicy:
    """Optional Enterprise policy for lowering a local review threshold.

    This is explicitly *not* the Core rule ``theta = theta(xi)``.  It uses a
    modeled coverage score for an Enterprise-specific operational policy.
    """

    adjustment_weight: float = 0.8
    lower_bound: float = 0.5

    def apply(self, base_threshold: float, coverage_gap_score: float) -> float:
        if base_threshold < 0:
            raise ValueError("base_threshold must be non-negative")
        if not 0.0 <= coverage_gap_score <= 1.0:
            raise ValueError("coverage_gap_score must be in [0, 1]")
        return max(
            self.lower_bound,
            float(base_threshold) - self.adjustment_weight * coverage_gap_score,
        )
