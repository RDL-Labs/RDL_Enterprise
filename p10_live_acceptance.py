"""Two-phase P10 live acceptance harness for RDL Enterprise.

This command does not mutate Jira.  It records a real provider observation as
the before-state, persists the pending canonical RIB boundary, then allows an
authorized external action/change to occur.  A later invocation restores the
same Runtime boundary, obtains a second real observation, and evaluates the
canonical RIB -> F/F' -> E chain.

P10 closure requires an explicit external action reference and an observed
canonical mismatch.  The action reference is provenance supplied by the
operator; the harness does not claim causal proof beyond that bounded record.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from rdl_enterprise import (
    AtlassianJiraConnector,
    AuthorityContext,
    BusinessInput,
    EnterpriseRuntimeRIBBridge,
    FeedbackResult,
    RIBSection,
)
from rdl_enterprise.snapshot import RelationProvenance


def _connector() -> AtlassianJiraConnector:
    missing = [
        name
        for name in (
            "RDL_ATLASSIAN_BASE_URL",
            "RDL_ATLASSIAN_EMAIL",
            "RDL_ATLASSIAN_TOKEN",
        )
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit(
            "missing live Atlassian environment variables: " + ", ".join(missing)
        )
    return AtlassianJiraConnector.from_environment()


def _actor() -> AuthorityContext:
    return AuthorityContext(
        "p10-live-operator",
        "operator",
        "workflow",
        "human",
        "idp_sso",
    )


def _ticket_id(issue_key: str) -> str:
    safe = issue_key.replace("/", "-").replace(" ", "-")
    return f"P10-LIVE-{safe}"


def _json(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def phase_before(store_path: str, issue_key: str) -> Dict[str, Any]:
    connector = _connector()
    observation = connector.lookup({"case_id": issue_key})
    runtime = EnterpriseRuntimeRIBBridge(store_path=store_path, theta_0=10.0)
    ticket_id = _ticket_id(issue_key)

    if ticket_id in runtime.pending_snapshots:
        raise SystemExit(
            f"pending P10 case already exists for {ticket_id}; use --phase after or a fresh store"
        )

    request = BusinessInput(
        ticket_id,
        "operator",
        "workflow",
        observation["summary"],
    )
    dispatched = runtime.dispatch_ticket(
        request,
        human_override_answer=_json(observation),
        authority=_actor(),
    )
    snapshot = runtime.pending_snapshots[ticket_id]
    if not isinstance(snapshot.rib_section, RIBSection):
        raise RuntimeError("canonical request RIBSection was not established")

    report = {
        "phase": "before",
        "issue_key": issue_key,
        "ticket_id": ticket_id,
        "store_path": str(Path(store_path).resolve()),
        "request_boundary_id": snapshot.rib_section.boundary_id,
        "request_provenance": dict(snapshot.rib_section.provenance),
        "initial_f_content": getattr(snapshot.f_pred, "content", None),
        "provider_observation": observation,
        "final_output": dispatched.final_output,
        "next_step": (
            "perform or observe an authorized real external action/change, preserve its durable "
            "reference, then run --phase after with --action-reference"
        ),
    }
    return report


def phase_after(
    store_path: str,
    issue_key: str,
    action_reference: str,
    *,
    require_change: bool = True,
) -> Dict[str, Any]:
    if not action_reference.strip():
        raise SystemExit("--action-reference is required for the after phase")

    connector = _connector()
    runtime = EnterpriseRuntimeRIBBridge(store_path=store_path, theta_0=10.0)
    ticket_id = _ticket_id(issue_key)
    if ticket_id not in runtime.pending_snapshots:
        raise SystemExit(
            f"no persisted pending P10 case for {ticket_id}; run --phase before first"
        )

    later = connector.lookup({"case_id": issue_key})
    feedback = FeedbackResult(
        user_resolved=False,
        actual_response_text=_json(later),
        feedback_comment=f"P10 changed-condition observation after {action_reference}",
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
        ticket_id,
        feedback,
        authority=_actor(),
    )
    snapshot = runtime.resolved_snapshots[-1]

    if not isinstance(snapshot.efp, RIBSection):
        raise RuntimeError("restored request state is not a canonical RIBSection")
    if not isinstance(snapshot.rib_section_next, RIBSection):
        raise RuntimeError("later provider observation did not form a RIBSection")
    if snapshot.v23_f_prime is None or snapshot.v23_mismatch is None:
        raise RuntimeError("canonical F' / E was not established")

    mismatch = float(snapshot.v23_mismatch.value)
    changed = mismatch > 0.0
    accepted = bool(action_reference.strip()) and changed
    if require_change and not changed:
        raise SystemExit(
            "real later observation was acquired, but canonical E is zero; "
            "P10 changed-condition gate remains open"
        )

    report = {
        "phase": "after",
        "issue_key": issue_key,
        "ticket_id": ticket_id,
        "action_reference": action_reference,
        "request_boundary_id": snapshot.efp.boundary_id,
        "later_boundary_id": snapshot.rib_section_next.boundary_id,
        "request_provenance": dict(snapshot.efp.provenance),
        "later_provenance": dict(snapshot.rib_section_next.provenance),
        "canonical_e_status": snapshot.v23_core_e_status,
        "canonical_e": mismatch,
        "canonical_e_reasons": list(snapshot.v23_mismatch.reasons),
        "operational_h": float(resolved.v23_operational_h),
        "operational_theta": float(resolved.v23_operational_theta),
        "changed_condition_observed": changed,
        "p10_bounded_acceptance": accepted,
        "later_provider_observation": later,
        "caveat": (
            "action_reference plus changed provider observation is bounded provenance evidence; "
            "it is not universal causal proof"
        ),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="RDL Enterprise P10 live acceptance")
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--issue", default=os.environ.get("RDL_ATLASSIAN_TEST_ISSUE", "IT-3"))
    parser.add_argument(
        "--store",
        default=os.environ.get("RDL_P10_STORE_PATH", "data/p10_live_acceptance.sqlite3"),
    )
    parser.add_argument("--action-reference", default="")
    parser.add_argument(
        "--allow-unchanged",
        action="store_true",
        help="record a real later observation even when canonical E is zero; does not close P10",
    )
    args = parser.parse_args()

    if args.phase == "before":
        result = phase_before(args.store, args.issue)
    else:
        result = phase_after(
            args.store,
            args.issue,
            args.action_reference,
            require_change=not args.allow_unchanged,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
