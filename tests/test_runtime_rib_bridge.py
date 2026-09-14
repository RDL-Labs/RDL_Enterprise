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

    assert runtime.migration_stage == "P1_P2_RIB_ACQUISITION_BRIDGE"
    assert isinstance(snapshot.rib_section, RIBSection)
    assert snapshot.raw_business_input is raw
    assert snapshot.rib_section.section_role == "request_observation"
    assert snapshot.rib_section.context.purpose == "business_request_interpretation"
    assert snapshot.efp is not raw
    assert snapshot.efp.metadata["rib_section_id"] == snapshot.rib_section.section_id
    assert snapshot.efp.metadata["interaction_series_id"] == "bridge-series"
    assert snapshot.interaction_semantic_version == "core-v2.3-rib-bridge"


def test_runtime_bridge_acquires_subsequent_section_before_legacy_feedback_metabolism():
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
    # The canonical acquisition state exists independently from the legacy
    # efp_prime compatibility field used by the old metabolism implementation.
    assert snapshot.rib_section_next is not snapshot.efp_prime
