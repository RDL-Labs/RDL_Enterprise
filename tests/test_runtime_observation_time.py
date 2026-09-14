from datetime import datetime, timezone

from rdl_enterprise.runtime import EnterpriseRuntime
from rdl_enterprise.snapshot import BusinessInput


def test_dispatch_freezes_explicit_observation_time_into_interpretation_context():
    runtime = EnterpriseRuntime()
    observed_at = "2026-09-14T12:34:56+00:00"
    efp = BusinessInput(
        ticket_id="TICK-OBS-TIME",
        user_id="user-test",
        category="general",
        query_text="bounded observation time",
        created_at=observed_at,
    )

    runtime.dispatch_ticket(efp)

    snapshot = runtime.pending_snapshots[efp.ticket_id]
    frozen_time = snapshot.frozen_context.constraint_evaluation_time
    assert frozen_time == datetime.fromisoformat(observed_at)
    assert frozen_time.tzinfo == timezone.utc
