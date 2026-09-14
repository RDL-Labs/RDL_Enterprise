from rdl_enterprise import (
    BusinessInput,
    EnterpriseRuntimeRIBBridge,
    FeedbackResult,
    RIBSection,
)


class PersistenceMarkerBridge:
    model_name = "p9-persistence-marker"
    temperature = 0.0
    system_prompt_version = "v1"

    def resolve(self, request, mb_view=None):
        later = "【後続観測】" in request.query_text
        return {
            "type": "direct_reply",
            "payload": "later-state" if later else "initial-state",
        }


def test_canonical_mismatch_coverage_and_sections_survive_restart(tmp_path):
    store_path = str(tmp_path / "p9-canonical-state.sqlite3")
    runtime = EnterpriseRuntimeRIBBridge(
        store_path=store_path,
        theta_0=10.0,
        llm_bridge=PersistenceMarkerBridge(),
    )
    raw = BusinessInput(
        "P9-STATE-1",
        "operator",
        "workflow",
        "inspect state",
        created_at="2026-09-14T12:00:00+00:00",
    )

    runtime.dispatch_ticket(raw)
    runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(
            user_resolved=False,
            feedback_comment="still unresolved",
            observed_at="2026-09-14T12:01:00+00:00",
        ),
    )

    h_before = runtime.v23_h_state.global_mismatch.total()
    coverage_before = runtime.v23_coverage.coverage_gap_score()
    operational_h_before = runtime.h_state.global_heat.total(
        runtime.h_state.w_pred,
        runtime.h_state.w_input,
    )
    assert h_before > 0.0
    assert coverage_before > 0.0
    assert operational_h_before > 0.0

    stored_case = runtime.case_store.load_case(raw.ticket_id)
    assert isinstance(stored_case.efp, RIBSection)
    assert isinstance(stored_case.rib_section_next, RIBSection)
    assert stored_case.v23_mismatch is not None
    assert stored_case.v23_h_total == h_before
    assert stored_case.v23_coverage_gap_score == coverage_before

    restarted = EnterpriseRuntimeRIBBridge(
        store_path=store_path,
        theta_0=10.0,
        llm_bridge=PersistenceMarkerBridge(),
    )

    assert restarted.persistence_stage == "P9_CANONICAL_RIB_STATE_RESTART"
    assert restarted.v23_h_state.global_mismatch.total() == h_before
    assert restarted.v23_coverage.coverage_gap_score() == coverage_before
    assert restarted.h_state.global_heat.total(
        restarted.h_state.w_pred,
        restarted.h_state.w_input,
    ) == operational_h_before


def test_canonical_timeout_coverage_survives_restart_without_fabricating_h(tmp_path):
    store_path = str(tmp_path / "p9-timeout-state.sqlite3")
    runtime = EnterpriseRuntimeRIBBridge(store_path=store_path)
    raw = BusinessInput(
        "P9-TIMEOUT-1",
        "operator",
        "workflow",
        "pending observation",
        created_at="2026-09-14T13:00:00+00:00",
    )
    runtime.dispatch_ticket(raw)
    h_before = runtime.v23_h_state.global_mismatch.total()

    runtime.expire_pending_tickets_v23(
        [raw.ticket_id],
        at="2026-09-14T13:05:00+00:00",
    )
    coverage_before = runtime.v23_coverage.coverage_gap_score()
    assert coverage_before > 0.0
    assert runtime.v23_h_state.global_mismatch.total() == h_before

    restarted = EnterpriseRuntimeRIBBridge(store_path=store_path)
    assert restarted.v23_coverage.coverage_gap_score() == coverage_before
    assert restarted.v23_h_state.global_mismatch.total() == h_before

    stored_case = restarted.case_store.load_case(raw.ticket_id)
    assert stored_case.v23_f_prime is None
    assert stored_case.v23_mismatch is None
    assert stored_case.v23_core_e_status == "NOT_EVALUATED"
