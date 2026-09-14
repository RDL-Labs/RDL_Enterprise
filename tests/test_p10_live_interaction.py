"""Live P10 evidence for the Core-v2.3 RIB interaction chain.

This test is intentionally read-only against Jira.  It establishes that two
real provider observations can enter the canonical RIB bridge as finite
sections and produce F / F' / Delta(F,F').  It does not manufacture a Jira
state change and therefore does not by itself close the stronger P10 gate that
requires an observed action -> changed interaction conditions chain.
"""

import json
import os

import pytest

from rdl_enterprise import (
    AtlassianJiraConnector,
    AuthorityContext,
    BusinessInput,
    EnterpriseRuntimeRIBBridge,
    FeedbackResult,
    RIBSection,
)
from rdl_enterprise.snapshot import RelationProvenance


LIVE = all(
    os.environ.get(name)
    for name in (
        "RDL_ATLASSIAN_BASE_URL",
        "RDL_ATLASSIAN_EMAIL",
        "RDL_ATLASSIAN_TOKEN",
    )
)


@pytest.mark.skipif(not LIVE, reason="live Atlassian credentials are not configured")
def test_p10_live_jira_observations_form_canonical_rib_f_fprime_e_chain(tmp_path):
    connector = AtlassianJiraConnector.from_environment()
    issue_key = os.environ.get("RDL_ATLASSIAN_TEST_ISSUE", "IT-3")
    first = connector.lookup({"case_id": issue_key})

    runtime = EnterpriseRuntimeRIBBridge(
        store_path=str(tmp_path / "p10-live.sqlite3"),
        theta_0=10.0,
    )
    actor = AuthorityContext(
        "p10-live-operator",
        "operator",
        "workflow",
        "human",
        "idp_sso",
    )
    request = BusinessInput(
        "P10-LIVE-IT3",
        "operator",
        "workflow",
        first["summary"],
    )
    dispatched = runtime.dispatch_ticket(
        request,
        human_override_answer=json.dumps(first, ensure_ascii=False, sort_keys=True),
        authority=actor,
    )

    pending = runtime.pending_snapshots[request.ticket_id]
    assert isinstance(pending.efp, RIBSection)
    assert isinstance(pending.rib_section, RIBSection)
    assert pending.f_pred is not None

    # A second real read is a later observation.  The issue may or may not have
    # changed between reads; either outcome is valid evidence.  If it did not
    # change, canonical E may legitimately be zero.
    second = connector.lookup({"case_id": issue_key})
    feedback = FeedbackResult(
        user_resolved=False,
        actual_response_text=json.dumps(second, ensure_ascii=False, sort_keys=True),
        feedback_comment="subsequent live Jira observation",
        provenance=RelationProvenance(
            source_type="system",
            authority_level="unknown",
            source_id=f"atlassian-jira:{issue_key}",
            channel="standard",
            claim_type="fact",
            relation_type="current_state",
        ),
    )
    resolved = runtime.resolve_ticket_feedback(
        request.ticket_id,
        feedback,
        authority=actor,
    )

    snapshot = runtime.resolved_snapshots[-1]
    assert dispatched.final_output == json.dumps(first, ensure_ascii=False, sort_keys=True)
    assert isinstance(snapshot.efp, RIBSection)
    assert isinstance(snapshot.rib_section_next, RIBSection)
    assert snapshot.v23_f_prime is not None
    assert snapshot.v23_mismatch is not None
    assert snapshot.v23_core_e_status == "OBSERVED"
    assert snapshot.interaction_trace["pre_update_mb_hash"] == snapshot.frozen_context.frozen_mb.content_hash()
    assert resolved.v23_core_e_status == "OBSERVED"
    assert resolved.e_prediction == snapshot.v23_mismatch.value
    assert resolved.v23_operational_h >= 0.0
    assert "RDL_ATLASSIAN_TOKEN" not in repr(snapshot)
