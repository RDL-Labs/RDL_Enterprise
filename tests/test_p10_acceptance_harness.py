import importlib

import pytest

from rdl_enterprise import EnterpriseRuntimeRIBBridge


p10 = importlib.import_module("p10_live_acceptance")


class FakeConnector:
    def __init__(self, observation):
        self.observation = observation

    def lookup(self, payload):
        assert payload["case_id"] == self.observation["case_id"]
        return dict(self.observation)


def test_p10_harness_preserves_pending_boundary_until_real_provider_change(tmp_path, monkeypatch):
    store = str(tmp_path / "p10.sqlite3")
    before = {
        "case_id": "IT-3",
        "summary": "VPN access issue",
        "status": "Open",
        "owner": None,
    }
    after = {
        "case_id": "IT-3",
        "summary": "VPN access issue",
        "status": "Resolved",
        "owner": "operator-a",
    }

    monkeypatch.setattr(p10, "_connector", lambda: FakeConnector(before))
    first = p10.phase_before(store, "IT-3")
    assert first["phase"] == "before"
    assert first["provider_observation"] == before

    # Checking before the external condition changes must not consume the
    # persisted comparison boundary.
    monkeypatch.setattr(p10, "_connector", lambda: FakeConnector(before))
    with pytest.raises(SystemExit, match="pending P10 boundary is preserved"):
        p10.phase_after(store, "IT-3", "jira-change:IT-3")

    restarted = EnterpriseRuntimeRIBBridge(store_path=store, theta_0=10.0)
    assert p10._ticket_id("IT-3") in restarted.pending_snapshots

    # Once the real-provider-shaped bounded observation differs, the same
    # persisted boundary can be consumed to establish the canonical chain.
    monkeypatch.setattr(p10, "_connector", lambda: FakeConnector(after))
    report = p10.phase_after(store, "IT-3", "jira-change:IT-3")

    assert report["provider_state_changed"] is True
    assert report["canonical_e_status"] == "OBSERVED"
    assert report["canonical_e"] > 0.0
    assert report["canonical_change_observed"] is True
    assert report["p10_bounded_acceptance"] is True
    assert report["action_reference"] == "jira-change:IT-3"
