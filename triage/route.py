"""Routing (SPEC §10): each graded request becomes one append-only JSONL row, `simulated: true`.

Nothing is executed and this module imports no network client (tests/test_route.py checks it).
"""

from datetime import datetime
from pathlib import Path

from triage.schemas import GradedRequest, LogRecord

RUNS = Path(__file__).resolve().parent.parent / "runs"
LOGS = {
    "act": "actions.jsonl",
    "seek_approval": "approvals.jsonl",
    "hand_off": "handoffs.jsonl",
    "refuse": "alerts.jsonl",
}


def mask(phone: str | None) -> str | None:
    return f"••••{phone[-4:]}" if phone else None


def _action(r: GradedRequest) -> str:
    gloss = r.candidate.gloss
    if r.rule_id == "R8":
        return f"record only (request {r.candidate.status}): {gloss}"
    return {
        "act": f"simulated action: {gloss}",
        "seek_approval": f"queued for human approval: {gloss}",
        "hand_off": f"handed to the team queue: {gloss}",
        "refuse": f"refused and security alert raised: {gloss}",
    }[r.grade]


def record(run_id: str, r: GradedRequest, now: datetime) -> LogRecord:
    return LogRecord(
        run_id=run_id,
        request_id=r.request_id,
        grade=r.grade,
        rule_id=r.rule_id,
        evidence_msg_ids=r.candidate.evidence_msg_ids,
        now=now,
        action=_action(r),
        requester=mask(r.requester_phone),
        record_only=r.rule_id == "R8",
        internal=r.internal,
    )


def unprocessed(run_id: str, now: datetime | None, error: str) -> LogRecord:
    """One hand-off for the whole chat: a failed run is never shown as 'no requests'."""
    return LogRecord(
        run_id=run_id,
        request_id=f"{run_id}-chat",
        grade="hand_off",
        rule_id=None,
        evidence_msg_ids=[],
        now=now,
        action=f"UNPROCESSED: whole chat handed to the team ({error})",
    )


def write(records: list[LogRecord], runs_dir: Path = RUNS) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        with (runs_dir / LOGS[rec.grade]).open("a", encoding="utf-8") as f:
            f.write(rec.model_dump_json() + "\n")
