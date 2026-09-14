"""Two-phase P10 live acceptance harness for RDL Enterprise.

This command does not mutate Jira. It records a real provider observation as
the before-state, persists the pending canonical RIB boundary, then allows an
authorized external action/change to occur. A later invocation restores the
same Runtime boundary, obtains a second real observation, and evaluates the
canonical RIB -> F/F' -> E chain.

P10 closure requires all of the following:

- an explicit durable external action reference;
- a real provider observation that differs from the stored before observation;
- a canonical non-zero Delta(F, F').

The action reference is bounded provenance supplied by the operator. The
harness does not claim causal proof beyond that finite record.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

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


def _provenance_dict(value: Optional[Any]) -> Optional[Dict[str, Any]]:
    return asdict(value) if value is not None else None


def _evidence_path(store_path: str) -> Path:
    return Path(f"{store_path}.p10-before.json")


def _write_before_evidence(store_path: str, evidence: Dict[str, Any]) -> None:
    path = _evidence_path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _read_before_evidence(store_path: str) -> Dict[str, Any]:
    path = _evidence_path(store_path)
    if not path.exists():
        raise SystemExit(
            f"missing P10 before evidence: {path}; run --phase before first"
        )
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("invalid P10 before evidence record")
    return value


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

    evidence = {
        "issue_key": issue_key,
        "ticket_id": ticket_id,
        "provider_observation": observation,
        "request_boundary_id": snapshot.rib_section.boundary_id,
        "request_provenance": _provenance_dict(snapshot.rib_section.provenance),
    }
    _write_before_evidence(store_path, evidence)

    report = {
        "phase": "before",
        "issue_key": issue_key,
        "ticket_id": ticket_id,
        "store_path": str(Path(store_path).resolve()),
        "evidence_path": str(_evidence_path(store_path).resolve()),
        "request_boundary_id": snapshot.rib_section.boundary_id,
        "request_provenance": _provenance_dict(snapshot.rib_section.provenance),
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

    before = _read_before_evidence(store_path)
    if before.get("issue_key") != issue_key:
        raise SystemExit("P10 before evidence targets a different issue")

    connector = _connector()
    runtime = EnterpriseRuntimeRIBBridge(store_path=store_path, theta_0=10.0)
    ticket_id = _ticket_id(issue_key)
    if ticket_id not in runtime.pending_snapshots:
        raise SystemExit(
            f"no persisted pending P10 case for {ticket_id}; run --phase before first"
        )

    later = connector.lookup({"case_id": issue_key})
    before_observation = before.get("provider_observation")
    provider_changed = _json(before_observation) != _json(later)

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
    canonical_changed = mismatch > 0.0
    accepted = bool(action_reference.strip()) and provider_changed and canonical_changed

    if require_change and not provider_changed:
        raise SystemExit(
            "later live provider observation is identical to the stored before observation; "
            "P10 changed-condition gate remains open"
        )
    if require_change and not canonical_changed:
        raise SystemExit(
            "provider state changed, but canonical E is zero; the current finite interpretation "
            "did not recover that change, so P10 remains open"
        )

    report = {
        "phase": "after",
        "issue_key": issue_key,
        "ticket_id": ticket_id,
        "action_reference": action_reference,
        "request_boundary_id": snapshot.efp.boundary_id,
        "later_boundary_id": snapshot.rib_section_next.boundary_id,
        "request_provenance": _provenance_dict(snapshot.efp.provenance),
        "later_provenance": _provenance_dict(snapshot.rib_section_next.provenance),
        "provider_state_changed": provider_changed,
        "before_provider_observation": before_observation,
        "later_provider_observation": later,
        "canonical_e_status": snapshot.v23_core_e_status,
        "canonical_e": mismatch,
        "canonical_e_reasons": list(snapshot.v23_mismatch.reasons),
        "canonical_change_observed": canonical_changed,
        "operational_h": float(resolved.v23_operational_h),
        "operational_theta": float(resolved.v23_operational_theta),
        "p10_bounded_acceptance": accepted,
        "caveat": (
            "action reference + provider before/after change + canonical E are bounded evidence; "
            "they do not constitute universal causal proof"
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
        help="record a later real observation without closing P10 when provider/canonical state is unchanged",
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
