from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class HeatVector:
    prediction: float = 0.0  # legacy retained F/F' mismatch component
    # Pre-v2.3 compatibility field. This is an Enterprise acquisition/input
    # metric that legacy Runtime still mixes into total heat. It is NOT Core H.
    input_err: float = 0.0

    def total(self, w_pred: float = 1.0, w_input: float = 0.4) -> float:
        """Legacy total used by the pre-v2.3 Runtime compatibility path."""
        return w_pred * self.prediction + w_input * self.input_err


class HState:
    """Legacy Enterprise heat state kept for Runtime compatibility.

    This class predates Core v2.3 role separation. In particular, its
    ``input_err`` component is not Core H. New migration work should use
    ``UnresolvedMismatchState`` and ``ObservationCoverageState`` from
    ``mismatch_state.py``.

    The class remains operational while the existing Runtime is migrated in
    stages; keeping it does not make its full scalar policy a Core primitive.
    """

    def __init__(
        self,
        theta_0: float = 2.0,
        gamma: float = 0.05,
        w_pred: float = 1.0,
        w_input: float = 0.4,
    ):
        self.theta_0 = theta_0
        self.gamma = gamma
        self.w_pred = w_pred
        self.w_input = w_input

        # ノード別またはドメイン別のlegacy heat管理: node_id -> HeatVector
        self.node_heats: Dict[str, HeatVector] = {}
        # バージョン別複合キーheat管理: (mb_version, node_id) -> HeatVector
        self.versioned_heats: Dict[Tuple[str, str], HeatVector] = {}
        # バージョン別coverage観測統計プール
        self.versioned_observations: Dict[str, Dict[str, int]] = {}
        self.global_heat = HeatVector()
        # Enterprise-local coverage / unresolved-observation counters.
        # These counters do NOT measure Core xi.
        self.unclassified_count = 0
        self.missing_info_count = 0
        self.unknown_input_count = 0
        self.rejection_events_count = 0
        self.total_tickets = 0

    def add_heat(
        self,
        node_id: Optional[str],
        pred_err: float = 0.0,
        input_err: float = 0.0,
        mb_version: str = "prod",
        is_canary: bool = False,
        opposing_constraint_strength: float = 1.0,
    ):
        """Legacy heat accumulation.

        ``pred_err`` may represent retained F/F' mismatch in the current
        Runtime. ``input_err`` is a pre-v2.3 compatibility metric and must not
        be interpreted as Core E/H. The v2.3 shadow path does not mix it into
        ``UnresolvedMismatchState``.

        ``opposing_constraint_strength`` is an Enterprise Standard-Model
        weighting parameter, not a mandatory Core law.
        """
        weighted_pred_err = pred_err * max(0.0, opposing_constraint_strength)
        weighted_input_err = input_err * max(0.0, opposing_constraint_strength)

        target_nid = node_id or "__unmatched__"
        v_key = (mb_version, target_nid)
        if v_key not in self.versioned_heats:
            self.versioned_heats[v_key] = HeatVector()
        self.versioned_heats[v_key].prediction += weighted_pred_err
        self.versioned_heats[v_key].input_err += weighted_input_err

        if not is_canary:
            if node_id:
                if node_id not in self.node_heats:
                    self.node_heats[node_id] = HeatVector()
                self.node_heats[node_id].prediction += weighted_pred_err
                self.node_heats[node_id].input_err += weighted_input_err

            self.global_heat.prediction += weighted_pred_err
            self.global_heat.input_err += weighted_input_err

    def get_heat_for_version(self, node_id: str, mb_version: str = "prod") -> HeatVector:
        """特定バージョンのlegacy heatを取得。"""
        return self.versioned_heats.get((mb_version, node_id), HeatVector())

    def clear_version_heat(self, mb_version: str):
        """ロールバック時などに特定バージョンのheatおよび観測統計を全消去。"""
        keys_to_del = [k for k in self.versioned_heats if k[0] == mb_version]
        for k in keys_to_del:
            del self.versioned_heats[k]
        if mb_version in self.versioned_observations:
            del self.versioned_observations[mb_version]

    def record_observation(
        self,
        unclassified: bool = False,
        missing_info: bool = False,
        unknown_input: bool = False,
        rejected: bool = False,
        mb_version: str = "prod",
        is_canary: bool = False,
    ):
        """Update Enterprise-local coverage statistics.

        Historical code called the derived score ``xi_obs``. Core v2.3 does
        not permit that identification: these are modeled observable rates,
        not the unrecovered relation ``xi``.
        """
        if is_canary:
            if mb_version not in self.versioned_observations:
                self.versioned_observations[mb_version] = {
                    "unclassified_count": 0,
                    "missing_info_count": 0,
                    "unknown_input_count": 0,
                    "rejection_events_count": 0,
                    "total_tickets": 0,
                }
            pool = self.versioned_observations[mb_version]
            pool["total_tickets"] += 1
            if unclassified:
                pool["unclassified_count"] += 1
            if missing_info:
                pool["missing_info_count"] += 1
            if unknown_input:
                pool["unknown_input_count"] += 1
            if rejected:
                pool["rejection_events_count"] += 1
            return

        self.total_tickets += 1
        if unclassified:
            self.unclassified_count += 1
        if missing_info:
            self.missing_info_count += 1
        if unknown_input:
            self.unknown_input_count += 1
        if rejected:
            self.rejection_events_count += 1

    def coverage_gap_score(self, mb_version: str = "prod") -> float:
        """Enterprise-local bounded coverage score in [0, 1]; NOT Core xi."""
        if mb_version != "prod" and mb_version in self.versioned_observations:
            pool = self.versioned_observations[mb_version]
            total = pool["total_tickets"]
            if total == 0:
                return 0.0
            r_unclass = pool["unclassified_count"] / total
            r_miss = pool["missing_info_count"] / total
            r_unknown = pool["unknown_input_count"] / total
            r_reject = pool["rejection_events_count"] / total
            return min(1.0, 0.3 * r_unclass + 0.2 * r_miss + 0.3 * r_unknown + 0.2 * r_reject)

        if self.total_tickets == 0:
            return 0.0
        r_unclass = self.unclassified_count / self.total_tickets
        r_miss = self.missing_info_count / self.total_tickets
        r_unknown = self.unknown_input_count / self.total_tickets
        r_reject = self.rejection_events_count / self.total_tickets
        return min(1.0, 0.3 * r_unclass + 0.2 * r_miss + 0.3 * r_unknown + 0.2 * r_reject)

    def xi_obs(self, mb_version: str = "prod") -> float:
        """Deprecated compatibility alias for ``coverage_gap_score``.

        The return value is NOT an observation or estimate of Core ``xi``.
        New code must call ``coverage_gap_score`` instead.
        """
        return self.coverage_gap_score(mb_version=mb_version)

    def theta_eff(self, mb_version: str = "prod") -> float:
        """Legacy Enterprise coverage-adjusted threshold policy.

        This is an Enterprise policy:

            theta_eff = max(0.5, theta_0 - 0.8 * coverage_gap_score)

        It is NOT a Core rule ``theta = theta(xi)``.
        """
        coverage = self.coverage_gap_score(mb_version=mb_version)
        return max(0.5, self.theta_0 - 0.8 * coverage)

    def theta_eff_for_base(self, base_threshold: float, mb_version: str = "prod") -> float:
        """Apply the legacy Enterprise coverage policy to a revision base."""
        coverage = self.coverage_gap_score(mb_version=mb_version)
        return max(0.5, base_threshold - 0.8 * coverage)

    def dissipate(self, node_inertias: Dict[str, float]):
        """Legacy passive dissipation Standard Model.

        The dependence on ``I(M_B)`` is an Enterprise implementation candidate,
        not a mandatory Core law.
        """
        for nid, heat in list(self.node_heats.items()):
            inertia = node_inertias.get(nid, 0.5)
            cooling_rate = min(0.3, self.gamma / (1.0 + inertia))
            heat.prediction *= (1.0 - cooling_rate)
            heat.input_err *= (1.0 - cooling_rate)

        self.global_heat.prediction *= (1.0 - self.gamma)
        self.global_heat.input_err *= (1.0 - self.gamma)

    def should_leap(self, node_id: Optional[str] = None) -> Tuple[bool, str, float]:
        """Legacy Runtime transition check using its Enterprise threshold policy."""
        threshold = self.theta_eff()

        if node_id and node_id in self.node_heats:
            h = self.node_heats[node_id].total(self.w_pred, self.w_input)
            if h >= threshold:
                return True, node_id, h

        max_nid = None
        max_h = 0.0
        for nid, heat in self.node_heats.items():
            h_val = heat.total(self.w_pred, self.w_input)
            if h_val > max_h:
                max_h = h_val
                max_nid = nid

        if max_nid and max_h >= threshold:
            return True, max_nid, max_h

        g_h = self.global_heat.total(self.w_pred, self.w_input)
        if g_h >= threshold:
            return True, "__global__", g_h

        return False, max_nid or "", max_h

    def apply_remaining_heat_after_leap(self, target_node_id: str, remaining_ratio: float = 0.2):
        """Legacy residual-state handling after an Enterprise reorganization."""
        if target_node_id in self.node_heats:
            self.node_heats[target_node_id].prediction *= remaining_ratio
            self.node_heats[target_node_id].input_err *= remaining_ratio

        self.global_heat.prediction *= remaining_ratio
        self.global_heat.input_err *= remaining_ratio

    def inherit_canary_state_to_prod(
        self,
        canary_version: str,
        heat_ratio: float = 0.5,
    ):
        """Merge legacy canary heat and Enterprise coverage observations.

        The observation statistics merged here are coverage metrics, not
        inherited ``xi``.
        """
        keys_to_merge = [k for k in self.versioned_heats.keys() if k[0] == canary_version]
        for (ver, nid) in keys_to_merge:
            c_heat = self.versioned_heats[(ver, nid)]
            if nid not in self.node_heats:
                self.node_heats[nid] = HeatVector()
            self.node_heats[nid].prediction += c_heat.prediction * heat_ratio
            self.node_heats[nid].input_err += c_heat.input_err * heat_ratio

        if canary_version in self.versioned_observations:
            c_obs = self.versioned_observations[canary_version]
            self.total_tickets += c_obs["total_tickets"]
            self.unclassified_count += c_obs["unclassified_count"]
            self.missing_info_count += c_obs["missing_info_count"]
            self.unknown_input_count += c_obs["unknown_input_count"]
            self.rejection_events_count += c_obs["rejection_events_count"]

        self.clear_version_heat(canary_version)

    def version_total_heat(self, mb_version: str) -> float:
        """Return legacy total heat for one implementation version."""
        total = 0.0
        for (ver, _), h in self.versioned_heats.items():
            if ver == mb_version:
                total += h.total(self.w_pred, self.w_input)
        return total

    def hottest_node_for_version(self, mb_version: str) -> Optional[str]:
        """Return the locus with the largest legacy heat for one version."""
        max_nid = None
        max_h = 0.0
        for (ver, nid), h in self.versioned_heats.items():
            if ver == mb_version and nid and not nid.startswith("__"):
                h_val = h.total(self.w_pred, self.w_input)
                if h_val > max_h:
                    max_h = h_val
                    max_nid = nid

        if max_nid:
            return max_nid

        for nid, h in self.node_heats.items():
            if nid and not nid.startswith("__"):
                h_val = h.total(self.w_pred, self.w_input)
                if h_val > max_h:
                    max_h = h_val
                    max_nid = nid

        return max_nid
