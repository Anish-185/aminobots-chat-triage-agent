"""End-to-end pipeline on a real dev chat with a mocked model; fail-closed paths."""

import json
from datetime import datetime
from pathlib import Path

import diskcache
import pytest
from typer.testing import CliRunner

from tests.test_extract import BAD, Server, _completion
from triage import llm, pipeline, route
from triage.config import load_models

D01 = Path(__file__).resolve().parent.parent / "data" / "dev" / "d01.txt"
CAND = next(c for c in load_models().candidates if c.id == load_models().roles.extractor.model)


def _c(intent, primary, evidence, **extra):
    return {"intent": intent, "gloss": f"{intent} {primary}", "primary_msg_id": primary,
            "evidence_msg_ids": evidence, **extra}  # fmt: skip


D01_OUT = {
    "candidates": [
        _c("delivery_slot_change", "m011", ["m011"],
           entities={"outlet": "Kukatpally", "slot_day_offset": 1, "slot_time": "07:00"}),
        _c("delivery_slot_change", "m016", ["m016", "m011"], refers_to_msg_id="m011",
           entities={"outlet": "Maa shop", "slot_day_offset": 1, "slot_time": "07:00"}),
        _c("invoice_request", "m019", ["m019"]),
        _c("other", "m999", ["m998"]),  # hallucinated IDs → rejected
    ]
}  # fmt: skip


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch):
    monkeypatch.setattr(llm, "_pace", lambda: None)


@pytest.fixture
def cache(tmp_path: Path):
    with diskcache.Cache(tmp_path / "cache") as c:
        yield c


def _run(tmp_path, cache, *responses, chat=D01):
    server = Server(*responses)
    client = server.client(CAND.instructor_mode)
    return pipeline.run(chat, runs_dir=tmp_path / "runs", cache=cache, client=client)


def _rows(tmp_path, name):
    path = tmp_path / "runs" / name
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def test_d01_end_to_end(tmp_path, cache):
    res = _run(tmp_path, cache, (200, _completion(D01_OUT)))
    assert res.status == "OK" and res.now == datetime(2026, 10, 20, 19, 30)
    got = [(r.candidate.primary_msg_id, r.grade, r.rule_id) for r in res.requests]
    # m011: slot 07:00 next day is 11.5 h after "now" → R7; m016: owner of 2 outlets → R6.
    assert got == [("m011", "seek_approval", "R7"), ("m016", "seek_approval", "R6"),
                   ("m019", "act", "R9")]  # fmt: skip
    assert res.requests[1].candidate.flags == ["outlet_ambiguous"]
    assert res.requests[0].identity.state == "CONFIRMED" and res.requests[0].identity.reason
    assert [r.reason.split(":")[0] for r in res.rejected] == ["rejected_hallucination"]
    assert (
        len(_rows(tmp_path, "approvals.jsonl")) == 2 and len(_rows(tmp_path, "actions.jsonl")) == 1
    )
    assert all(r["simulated"] for r in _rows(tmp_path, "approvals.jsonl"))


def test_internal_staff_request_is_logged_not_listed(tmp_path, cache):
    d13 = D01.with_name("d13.txt")
    out = {"candidates": [_c("delivery_slot_change", "m003", ["m003"])]}
    res = _run(tmp_path, cache, (200, _completion(out)), chat=d13)
    assert res.requests == [] and len(res.internal_requests) == 1
    assert res.log[0].internal


@pytest.mark.parametrize(
    "responses",
    [
        [(200, _completion(BAD)), (200, _completion(BAD))],  # ExtractionFailed after one retry
        [(429, {"error": {"message": "rate limited"}})],
        [(404, {"error": {"message": "No endpoints found"}})],
    ],
    ids=["schema", "429", "unavailable"],
)
def test_failures_are_unprocessed_with_one_whole_chat_hand_off(tmp_path, cache, responses):
    res = _run(tmp_path, cache, *responses)
    assert res.status == "UNPROCESSED" and res.requests == [] and res.error
    rows = _rows(tmp_path, "handoffs.jsonl")
    assert len(rows) == 1 and rows[0]["rule_id"] is None and "UNPROCESSED" in rows[0]["action"]
    assert res.llm["requests"] == len(responses)


def test_unparsable_chat_is_unprocessed(tmp_path, cache):
    bad = tmp_path / "bad.txt"
    bad.write_text("not a whatsapp export\n")
    res = _run(tmp_path, cache, chat=bad)
    assert res.status == "UNPROCESSED" and "parse error" in res.error
    assert len(_rows(tmp_path, "handoffs.jsonl")) == 1


def test_cli_shows_unprocessed_not_empty(tmp_path, monkeypatch):
    from triage import cli

    bad = tmp_path / "bad.txt"
    bad.write_text("garbage\n")
    monkeypatch.setattr(route, "RUNS", tmp_path / "runs")
    out = CliRunner().invoke(cli.app, ["run", str(bad)])
    assert out.exit_code == 1 and "UNPROCESSED" in out.output
