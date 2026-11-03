"""Audit trail (Phase 10): runs/*.jsonl → SQLite for Datasette, facets on real columns."""

from datetime import datetime
from pathlib import Path

import sqlite_utils
import yaml

from triage import audit, route
from triage.schemas import Candidate, GradedRequest, Identity

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 3, 2, 18, 0)


def _graded(grade: str, rule: str, n: int) -> GradedRequest:
    return GradedRequest(
        request_id=f"x-r{n}",
        candidate=Candidate(
            intent="status_query", gloss="g", primary_msg_id="m001", evidence_msg_ids=["m001"]
        ),
        requester_phone="+915555010003",
        requester_name="Lakshmi",
        identity=Identity(state="CONFIRMED", reason="r"),
        grade=grade,
        rule_id=rule,
        matched_rules=[rule],
        rule_checks=[],
    )


def test_build_loads_every_log_and_is_rebuilt_not_appended(tmp_path: Path):
    cases = [("act", "R9"), ("refuse", "R2"), ("act", "R9")]
    recs = [
        route.record("x", _graded(g, r, n), NOW, "Sunrise Foods") for n, (g, r) in enumerate(cases)
    ]
    route.write([*recs, route.unprocessed("y", NOW, "boom")], tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.jsonl")}
    for _ in range(2):
        counts = audit.build(tmp_path)
    assert counts == {"actions": 2, "approvals": 0, "handoffs": 1, "alerts": 1}
    db = sqlite_utils.Database(tmp_path / "audit.db")
    assert db["records"].count == 4
    rows = list(db.query("select log, grade, team, identity_state, simulated from records"))
    assert {r["log"] for r in rows} == {"actions", "handoffs", "alerts"}
    assert all(r["simulated"] == 1 for r in rows)
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*.jsonl")} == before  # read-only


def test_empty_runs_dir_builds_an_empty_db(tmp_path: Path):
    assert audit.build(tmp_path / "runs") == dict.fromkeys(audit.LOGS_ORDER, 0)


def test_datasette_facets_are_columns_of_the_records_table():
    meta = yaml.safe_load((ROOT / "config" / "datasette.yaml").read_text(encoding="utf-8"))
    facets = meta["databases"]["audit"]["tables"]["records"]["facets"]
    assert facets == ["grade", "rule_id", "identity_state", "team"]
    assert set(facets) <= set(audit.COLUMNS)
