from rdl_enterprise import (
    BusinessInput,
    EnterpriseRuntimeRIBBridge,
    FeedbackResult,
    RIBSection,
    V23OperationalHStateAdapter,
)


class MarkerLLMBridge:
    """Deterministic test bridge whose output changes on the later RIB section."""

    model_name = "marker-test"
    temperature = 0.0
    system_prompt_version = "v1"

    def resolve(self, request, mb_view=None):
        later = "【後続観測】" in request.query_text
        return {
            "type": "direct_reply",
            "payload": "later-state" if later else "initial-state",
        }


class DirectSectionLLMBridge:
    """Expose whether interpretation received the section or a compatibility projection."""

    model_name = "direct-section-test"
    temperature = 0.0
    system_prompt_version = "v1"

    def resolve(self, request, mb_view=None):
        return {
            "type": "direct_reply",
            "payload": (
                "direct-rib-section"
                if isinstance(request, RIBSection)
                else "projected-business-input"
            ),
        }


def test_runtime_bridge_acquires_request_section_before_canonical_interpretation():
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

    assert runtime.migration_stage == "P8_RIB_DIRECT_INTERPRETATION"
    assert isinstance(runtime.h_state, V23OperationalHStateAdapter)
    assert isinstance(snapshot.rib_section, RIBSection)
    assert isinstance(snapshot.efp, RIBSection)
    assert snapshot.efp is snapshot.rib_section
    assert snapshot.raw_business_input is raw
    assert snapshot.rib_section.section_role == "request_observation"
    assert snapshot.rib_section.context.purpose == "business_request_interpretation"
    assert snapshot.efp.metadata["rib_section_id"] == snapshot.rib_section.section_id
    assert snapshot.efp.metadata["interaction_series_id"] == "bridge-series"
    assert snapshot.interaction_semantic_version == "core-v2.3-rib-p8-direct"


def test_request_rib_section_is_directly_interpretable_without_projection():
    runtime = EnterpriseRuntimeRIBBridge(llm_bridge=MarkerLLMBridge())
    raw = BusinessInput(
        "BRIDGE-DIRECT-REQUEST",
        "operator",
        "workflow",
        "inspect state",
        metadata={"interaction_series_id": "direct-series"},
        created_at="2026-09-14T10:00:00+00:00",
    )
    runtime.dispatch_ticket(raw)
    snapshot = runtime.pending_snapshots[raw.ticket_id]

    section = snapshot.rib_section
    assert section.query_text == raw.query_text
    assert section.category == raw.category
    assert section.ticket_id == raw.ticket_id
    assert section.user_id == raw.user_id
    assert section.created_at == raw.created_at
    assert section.metadata["interaction_series_id"] == "direct-series"

    direct = snapshot.frozen_context.interpret_efp(section)
    projected = snapshot.frozen_context.interpret_efp(section.to_business_input())

    # Trace IDs/timestamps are audit-event identities and are expected to differ
    # between two separate executions. The interpreted bounded state must match.
    assert direct.action_type == projected.action_type
    assert direct.content == projected.content
    assert direct.confidence == projected.confidence
    assert direct.matched_node_id == projected.matched_node_id
    assert direct.cost_tier == projected.cost_tier
    assert direct.domain == projected.domain
    assert direct.expected_outcome == projected.expected_outcome
    assert direct.available_locus_ids == projected.available_locus_ids
    assert direct.selected_locus_ids == projected.selected_locus_ids
    assert direct.applied_locus_ids == projected.applied_locus_ids
    assert direct.constraint_locus_ids == projected.constraint_locus_ids


def test_initial_and_subsequent_canonical_interpretation_receive_rib_sections():
    runtime = EnterpriseRuntimeRIBBridge(llm_bridge=DirectSectionLLMBridge())
    raw = BusinessInput(
        "BRIDGE-DIRECT-SUBSEQUENT",
        "operator",
        "workflow",
        "inspect state",
        created_at="2026-09-14T10:05:00+00:00",
    )
    runtime.dispatch_ticket(raw)
    pending = runtime.pending_snapshots[raw.ticket_id]

    assert pending.f_pred.content == "direct-rib-section"
    assert isinstance(pending.efp, RIBSection)

    runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(
            user_resolved=False,
            feedback_comment="still unresolved",
            observed_at="2026-09-14T10:06:00+00:00",
        ),
    )

    snapshot = runtime.resolved_snapshots[-1]
    assert isinstance(snapshot.rib_section_next, RIBSection)
    assert snapshot.rib_section_next.is_prime
    assert snapshot.rib_section_next.metadata["is_efp_prime"] is True
    assert snapshot.v23_f_prime.content == "direct-rib-section"
    assert snapshot.v23_mismatch is not None
    assert snapshot.v23_mismatch.value > 0.0


def test_p8_canonical_path_does_not_call_business_input_projection(monkeypatch):
    def forbidden_projection(self):
        raise AssertionError("canonical F/F' must not project RIBSection to BusinessInput")

    monkeypatch.setattr(RIBSection, "to_business_input", forbidden_projection)
    runtime = EnterpriseRuntimeRIBBridge(llm_bridge=DirectSectionLLMBridge())
    raw = BusinessInput(
        "BRIDGE-PROJECTION-BLOCK",
        "operator",
        "workflow",
        "inspect state",
        created_at="2026-09-14T10:10:00+00:00",
    )

    runtime.dispatch_ticket(raw)
    runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(
            user_resolved=False,
            feedback_comment="still unresolved",
            observed_at="2026-09-14T10:11:00+00:00",
        ),
    )

    snapshot = runtime.resolved_snapshots[-1]
    assert snapshot.f_pred.content == "direct-rib-section"
    assert snapshot.v23_f_prime.content == "direct-rib-section"


def test_p8_request_rib_section_survives_restart_and_forms_later_section(tmp_path):
    store_path = str(tmp_path / "p8-rib-runtime.sqlite3")
    runtime = EnterpriseRuntimeRIBBridge(
        store_path=store_path,
        llm_bridge=DirectSectionLLMBridge(),
    )
    raw = BusinessInput(
        "BRIDGE-P8-RESTART",
        "operator",
        "workflow",
        "inspect state",
        metadata={"interaction_series_id": "restart-series"},
        created_at="2026-09-14T10:15:00+00:00",
    )
    runtime.dispatch_ticket(raw)

    restarted = EnterpriseRuntimeRIBBridge(
        store_path=store_path,
        llm_bridge=DirectSectionLLMBridge(),
    )
    snapshot = restarted.pending_snapshots[raw.ticket_id]
    assert isinstance(snapshot.efp, RIBSection)
    assert snapshot.efp.section_role == "request_observation"
    assert snapshot.efp.provenance is not None
    assert snapshot.efp.metadata["interaction_series_id"] == "restart-series"

    restarted.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(
            user_resolved=False,
            feedback_comment="restart observation",
            observed_at="2026-09-14T10:16:00+00:00",
        ),
    )
    resolved = restarted.resolved_snapshots[-1]
    assert isinstance(resolved.rib_section_next, RIBSection)
    assert resolved.rib_section_next.section_role == "subsequent_observation"
    assert resolved.v23_f_prime is not None


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
    assert snapshot.v23_operational_h_total >= 0.0
    assert snapshot.v23_coverage_gap_score > 0.0
    assert not hasattr(runtime.v23_coverage, "xi_obs")
    assert not hasattr(runtime.v23_h_state, "xi_obs")


def test_input_diagnostic_does_not_enter_operational_h_or_trigger_reconstruction():
    runtime = EnterpriseRuntimeRIBBridge(theta_0=0.1)
    raw = BusinessInput("BRIDGE-INPUT", "operator", None, "x")
    runtime.dispatch_ticket(raw)

    result = runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(
            user_resolved=True,
            new_knowledge_provided="extra context",
        ),
    )

    snapshot = runtime.resolved_snapshots[-1]
    assert result.e_input > 0.0  # legacy diagnostic remains observable
    assert snapshot.v23_mismatch is not None
    assert snapshot.v23_mismatch.value == 0.0
    assert result.v23_retained_mismatch == 0.0
    assert result.current_h == 0.0
    assert result.v23_operational_h == 0.0
    assert result.current_theta_eff == 0.1
    assert not result.transition_to_m_delta
    assert snapshot.v23_coverage_gap_score > 0.0


def test_unresolved_canonical_delta_is_the_only_operational_h_increment():
    runtime = EnterpriseRuntimeRIBBridge(
        theta_0=10.0,
        llm_bridge=MarkerLLMBridge(),
    )
    raw = BusinessInput("BRIDGE-DELTA", "operator", "workflow", "inspect state")
    runtime.dispatch_ticket(raw)

    result = runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(user_resolved=False, feedback_comment="still unresolved"),
    )

    snapshot = runtime.resolved_snapshots[-1]
    assert snapshot.v23_mismatch is not None
    assert snapshot.v23_mismatch.value > 0.0
    assert result.e_prediction == snapshot.v23_mismatch.value
    assert result.v23_retained_mismatch == snapshot.v23_mismatch.value
    assert result.current_h > 0.0
    assert result.difference_reaction_status == "RETAINED_UNRESOLVED"
    assert result.current_theta_eff == 10.0
    assert not result.transition_to_m_delta


def test_resolved_delta_is_observed_but_not_retained_as_h():
    runtime = EnterpriseRuntimeRIBBridge(
        theta_0=0.1,
        llm_bridge=MarkerLLMBridge(),
    )
    raw = BusinessInput("BRIDGE-RESOLVED", "operator", "workflow", "inspect state")
    runtime.dispatch_ticket(raw)

    result = runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(user_resolved=True, feedback_comment="resolved after response"),
    )

    snapshot = runtime.resolved_snapshots[-1]
    assert snapshot.v23_mismatch is not None
    assert snapshot.v23_mismatch.value > 0.0
    assert result.e_prediction == snapshot.v23_mismatch.value
    assert result.v23_retained_mismatch == 0.0
    assert result.current_h == 0.0
    assert result.difference_reaction_status == "RESOLVED_NOT_RETAINED"
    assert not result.transition_to_m_delta


def test_coverage_observations_do_not_lower_operational_theta():
    runtime = EnterpriseRuntimeRIBBridge(theta_0=2.0)
    raw = BusinessInput("BRIDGE-COVERAGE", "operator", None, "unknown")
    runtime.dispatch_ticket(raw)
    runtime.resolve_ticket_feedback(
        raw.ticket_id,
        FeedbackResult(user_resolved=False, human_rejected=True),
    )

    assert runtime.v23_coverage.coverage_gap_score() > 0.0
    assert runtime.h_state.coverage_gap_score() == 0.0
    assert runtime.h_state.theta_eff() == 2.0
    # This adapter never claims that a zero compatibility score means xi == 0.
    assert runtime.h_state.semantic_version == "core-v2.3-operational-h-adapter"


def test_v23_timeout_does_not_fabricate_f_prime_e_or_h():
    runtime = EnterpriseRuntimeRIBBridge()
    raw = BusinessInput("BRIDGE-TIMEOUT", "operator", "workflow", "pending request")
    runtime.dispatch_ticket(raw)
    h_before = runtime.h_state.global_heat.total(
        runtime.h_state.w_pred,
        runtime.h_state.w_input,
    )

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
