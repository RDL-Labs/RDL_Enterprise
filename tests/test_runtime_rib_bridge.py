from rdl_enterprise import (
    BusinessInput,
    EnterpriseRuntimeRIBBridge,
    FeedbackResult,
    RIBSection,
)


def test_runtime_bridge_acquires_request_section_before_legacy_interpretation():
    runtime = EnterpriseRuntimeRIBBridge()
    raw = BusinessInput(
        "BRIDGE-1",
        "operator",
        "workflow",
        "unknown request",
        metadata={"interaction_series_id": "bridge-series"},
    )

    result = runtime.dispatch_ticket(raw)
    snapshot = runtime.pending_snapshots[result.ticket_id]

    assert runtime.migration_stage == "P1_P4_RIB_MISMATCH_TIMEOUT_SHADOW"
    assert isinstance(snapshot.rib_section, RIBSection)
    assert snapshot.raw_business_input is raw
    assert snapshot.rib_section.section_role == "request_observation"
    assert snapshot.rib_section.context.purpose == "business_request_interpretation"
    assert snapshot.efp is not raw
    assert snapshot.efp.metadata["rib_section_id"] == snapshot.rib_section.section_id
    assert snapshot.efp.metadata["interaction_series_id"] == "bridge-series"
    assert snapshot.interaction_semantic_version == "core-v2.3-rib-shadow"


def test_runtime_bridge_acquires_subsequent_section_and_records_separate_v23_states():
    runtime = EnterpriseRuntimeRIBBridge()
    raw = BusinessInput("BRIDGE-2", "operator", "workflow", "unknown request")
    runtime.dispatch_ticket(raw)

    result = runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(
            user_resolved=False,
            actual_response_text="still blocked",
            feedback_comment="subsequent observation",
        ),
    )

    snapshot = runtime.resolved_snapshots[-1]
    assert result.ticket_id == raw.ticket_id
    assert isinstance(snapshot.rib_section_next, RIBSection)
    assert snapshot.rib_section_next.section_role == "subsequent_observation"
    assert snapshot.rib_section_next.context.purpose == "subsequent_interaction_interpretation"
    assert snapshot.rib_section_next.payload["actual_response_text"] == "still blocked"
    assert snapshot.rib_section_next is not snapshot.efp_prime
    assert snapshot.v23_f_prime is not None
    assert snapshot.v23_mismatch is not None
    assert snapshot.v23_h_total >= 0.0
    assert snapshot.v23_coverage_gap_score > 0.0
    assert not hasattr(runtime.v23_coverage, "xi_obs")
    assert not hasattr(runtime.v23_h_state, "xi_obs")


def test_v23_timeout_does_not_fabricate_f_prime_e_or_h():
    runtime = EnterpriseRuntimeRIBBridge()
    raw = BusinessInput("BRIDGE-TIMEOUT", "operator", "workflow", "pending request")
    runtime.dispatch_ticket(raw)
    h_before = runtime.v23_h_state.global_mismatch.total()

    results = runtime.expire_pending_tickets_v23([raw.ticket_id])

    assert len(results) == 1
    result = results[0]
    snapshot = runtime.resolved_snapshots[-1]
    assert result.ticket_id == raw.ticket_id
    assert result.f_prime_status == "NOT_EVALUATED"
    assert result.e_status == "NOT_EVALUATED"
    assert result.e_prediction is None
    assert result.current_h == h_before
    assert result.coverage_gap_score > 0.0
    assert snapshot.rib_section_next is None
    assert snapshot.v23_f_prime is None
    assert snapshot.v23_mismatch is None
    assert snapshot.v23_core_e_status == "NOT_EVALUATED"
