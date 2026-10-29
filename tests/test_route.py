import ast
import json
from datetime import datetime
from pathlib import Path

from triage import route
from triage.schemas import Candidate, GradedRequest, Identity

NETWORK = {"socket", "http", "urllib", "requests", "httpx", "aiohttp", "smtplib", "ftplib",
           "openai", "instructor", "langfuse", "telnetlib", "websocket", "websockets"}  # fmt: skip
NOW = datetime(2026, 3, 2, 18, 0)


def test_route_imports_no_network_client():
    tree = ast.parse(Path(route.__file__).read_text())
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not {n.split(".")[0] for n in names} & NETWORK, names


def _graded(grade, rule, status="open") -> GradedRequest:
    return GradedRequest(
        request_id="x-r1",
        candidate=Candidate(
            intent="delivery_slot_change",
            gloss="move slot",
            primary_msg_id="m001",
            evidence_msg_ids=["m001"],
            status=status,
        ),
        requester_phone="+915555010003",
        requester_name="Lakshmi",
        identity=Identity(state="CONFIRMED", reason="r"),
        grade=grade,
        rule_id=rule,
        matched_rules=[rule],
        rule_checks=[],
    )


def test_each_grade_goes_to_its_log_simulated_and_masked(tmp_path: Path):
    cases = [("act", "R9"), ("seek_approval", "R6"), ("hand_off", "R3"), ("refuse", "R2")]
    route.write([route.record("x", _graded(g, r), NOW) for g, r in cases], tmp_path)
    for grade, rule in cases:
        rows = [
            json.loads(line) for line in (tmp_path / route.LOGS[grade]).read_text().splitlines()
        ]
        assert len(rows) == 1 and rows[0]["simulated"] is True and rows[0]["rule_id"] == rule
        assert rows[0]["requester"] == "••••0003"
        assert "5555010003" not in json.dumps(rows[0])


def test_r8_is_record_only():
    rec = route.record("x", _graded("act", "R8", status="cancelled"), NOW)
    assert rec.record_only and rec.action.startswith("record only")


def test_logs_are_append_only(tmp_path: Path):
    rec = route.record("x", _graded("act", "R9"), NOW)
    route.write([rec], tmp_path)
    route.write([rec], tmp_path)
    assert len((tmp_path / "actions.jsonl").read_text().splitlines()) == 2


def test_unprocessed_is_one_whole_chat_hand_off():
    rec = route.unprocessed("x", None, "boom")
    assert rec.grade == "hand_off" and rec.rule_id is None and "UNPROCESSED" in rec.action
