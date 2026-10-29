import logging
from datetime import datetime

from triage.ground import ground
from triage.schemas import Candidate, ExtractionResult, Message

MSGS = [
    Message(
        id=f"m00{i}",
        ts=datetime(2026, 3, 2, 9, i),
        author_raw="Teja",
        phone=None,
        display_name="Teja",
        text="x",
        kind="text",
    )
    for i in (1, 2, 3)
]


def _cand(primary: str, evidence: list[str], refers_to: str | None = None) -> Candidate:
    return Candidate(
        intent="other",
        gloss="g",
        primary_msg_id=primary,
        evidence_msg_ids=evidence,
        refers_to_msg_id=refers_to,
    )


def _ground(*cands: Candidate):
    return ground(ExtractionResult(candidates=list(cands)), MSGS)


def test_valid_candidate_kept_unchanged():
    kept, rejected = _ground(_cand("m001", ["m001", "m002"], refers_to="m003"))
    assert rejected == []
    assert kept[0].evidence_msg_ids == ["m001", "m002"] and kept[0].flags == []


def test_unknown_primary_is_rejected_and_logged(caplog):
    with caplog.at_level(logging.WARNING):
        kept, rejected = _ground(_cand("m009", ["m001"]))
    assert kept == []
    assert rejected[0].reason.startswith("rejected_hallucination") and "m009" in rejected[0].reason
    assert "m009" in caplog.text


def test_all_evidence_unknown_is_rejected():
    kept, rejected = _ground(_cand("m001", ["m008", "m009"]))
    assert kept == [] and len(rejected) == 1


def test_unknown_evidence_removed_and_primary_added(caplog):
    with caplog.at_level(logging.WARNING):
        kept, _ = _ground(_cand("m003", ["m002", "m099"]))
    assert kept[0].evidence_msg_ids == ["m002", "m003"]
    assert "m099" in caplog.text


def test_unknown_referent_becomes_flag():
    kept, _ = _ground(_cand("m002", ["m002"], refers_to="m050"))
    assert kept[0].refers_to_msg_id is None
    assert kept[0].flags == ["referent_unresolved"]
