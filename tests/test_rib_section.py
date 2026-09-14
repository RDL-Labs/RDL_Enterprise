from rdl_core import BoundaryContext
from rdl_enterprise import (
    BusinessInput,
    FeedbackResult,
    RIBSection,
    acquire_feedback_rib_section,
    acquire_request_rib_section,
)


def test_request_acquisition_keeps_raw_input_and_rib_section_distinct():
    raw = BusinessInput(
        "RIB-REQ-1",
        "operator-1",
        "workflow",
        "What is the current state?",
        metadata={"interaction_series_id": "series-1", "unselected": "raw-only"},
    )

    section = acquire_request_rib_section(raw)

    assert isinstance(section, RIBSection)
    assert section.section_role == "request_observation"
    assert section.boundary_id == "enterprise.request:RIB-REQ-1"
    assert section.context.purpose == "business_request_interpretation"
    assert section.payload["query_text"] == raw.query_text
    assert section.payload["interaction_series_id"] == "series-1"
    # Acquisition selects a finite section; arbitrary raw metadata is not
    # silently promoted into RIB_B.
    assert "unselected" not in section.payload

    compatibility_input = section.to_business_input()
    assert compatibility_input is not raw
    assert compatibility_input.query_text == raw.query_text
    assert compatibility_input.metadata["rib_section_id"] == section.section_id
    assert compatibility_input.metadata["rib_boundary_id"] == section.boundary_id
    assert compatibility_input.metadata["interaction_series_id"] == "series-1"


def test_feedback_acquisition_forms_subsequent_section_without_declaring_e_or_xi():
    request = BusinessInput(
        "RIB-FB-1",
        "operator-2",
        "workflow",
        "Restart the service?",
    )
    feedback = FeedbackResult(
        user_resolved=False,
        feedback_comment="Still blocked after the response",
        actual_response_text="Service remains blocked",
    )

    section = acquire_feedback_rib_section(request, feedback)

    assert section.section_role == "subsequent_observation"
    assert section.context.purpose == "subsequent_interaction_interpretation"
    assert section.payload["user_resolved"] is False
    assert section.payload["feedback_comment"] == "Still blocked after the response"
    assert "【後続観測】未解決" in section.projection_text
    assert "【後続状態】Service remains blocked" in section.projection_text
    # RIBSection is still an uninterpreted finite section.  The acquisition
    # contract itself contains no Core E/H/xi state.
    assert not any(name in section.payload for name in ("E", "H", "xi", "ξ"))


def test_acquisition_accepts_explicit_boundary_context():
    raw = BusinessInput("RIB-REQ-2", "operator-3", "security", "Inspect this")
    context = BoundaryContext(
        boundary_id="audit-boundary",
        question="security review",
        purpose="durability_inspection",
        conditions={"scope": "security"},
    )

    section = acquire_request_rib_section(raw, context=context)

    assert section.context is context
    assert section.boundary_id == "audit-boundary"
    assert section.context.conditions["scope"] == "security"
