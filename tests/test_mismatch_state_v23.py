from rdl_enterprise import (
    CoverageAdjustedThresholdPolicy,
    ObservationCoverageState,
    UnresolvedMismatchState,
)


def test_unresolved_mismatch_state_contains_only_retained_e_mismatch():
    state = UnresolvedMismatchState(theta=1.0)
    state.add_unresolved_mismatch("node-1", 0.4)

    assert state.node_mismatch["node-1"].total() == 0.4
    should_reconstruct, node_id, value = state.should_reconstruct("node-1")
    assert should_reconstruct is False
    assert node_id == "node-1"
    assert value == 0.4

    state.add_unresolved_mismatch("node-1", 0.7)
    should_reconstruct, node_id, value = state.should_reconstruct("node-1")
    assert should_reconstruct is True
    assert node_id == "node-1"
    assert value == 1.1


def test_coverage_observations_do_not_enter_h_state():
    h_state = UnresolvedMismatchState(theta=1.0)
    coverage = ObservationCoverageState()

    coverage.record(unclassified=True, missing_info=True, unknown_route=True)
    coverage.record(rejected=True)

    assert coverage.coverage_gap_score() > 0.0
    assert h_state.global_mismatch.total() == 0.0
    assert h_state.should_reconstruct()[0] is False


def test_coverage_threshold_adjustment_is_explicit_enterprise_policy_not_xi():
    coverage = ObservationCoverageState()
    coverage.record(unclassified=True, missing_info=True, unknown_route=True, rejected=True)
    score = coverage.coverage_gap_score()

    policy = CoverageAdjustedThresholdPolicy(adjustment_weight=0.8, lower_bound=0.5)
    adjusted = policy.apply(2.0, score)

    assert 0.5 <= adjusted < 2.0
    # The policy accepts a modeled coverage score explicitly; there is no xi API.
    assert not hasattr(coverage, "xi_obs")
    assert not hasattr(h_state := UnresolvedMismatchState(), "xi_obs")
