"""Slot fallback in code (SPEC §3.3, v2.8) on made-up messages: fill only nulls, one reading."""

from datetime import datetime

import pytest

from triage.ground import ground
from triage.schemas import Candidate, ExtractionResult, Message
from triage.slots import read

TS = datetime(2026, 3, 2, 9, 0)  # a Monday


def _msg(i: int, text: str, author: str = "Teja", ts: datetime = TS) -> Message:
    return Message(
        id=f"m{i:03d}",
        ts=ts,
        author_raw=author,
        phone=None,
        display_name=author,
        text=text,
        kind="text",
    )


def _slot(primary, evidence, refers_to=None, offset=None, at=None, status="open") -> Candidate:
    return Candidate(
        intent="delivery_slot_change",
        gloss="g",
        primary_msg_id=primary,
        evidence_msg_ids=evidence,
        refers_to_msg_id=refers_to,
        status=status,
        entities={"slot_day_offset": offset, "slot_time": at},
    )


def _run(msgs, *cands):
    kept, _ = ground(ExtractionResult(candidates=list(cands)), msgs)
    return kept


@pytest.mark.parametrize(
    ("text", "day", "times"),
    [
        ("Repu 6 ki kakunda 8 ki pampandi", 3, ["06:00", "08:00"]),
        ("reepu delivery 7 am badulu 11 am", 3, ["07:00", "11:00"]),
        ("ellundi slot madhyanam 3 gantalaki marchandi", 4, ["15:00"]),
        ("ivala sayantram 5 ki pettandi", 2, ["17:00"]),
        ("ee roju 12 pm ki", 2, ["12:00"]),
        ("Thursday delivery 9:30 ki", 5, ["09:30"]),
        ("రేపు 10 గంటలకు", 3, ["10:00"]),
        ("delivery late cheyyandi", None, []),
    ],
)
def test_read_normalises_days_and_times(text, day, times):
    days, got = read(_msg(1, text))
    assert days == ({datetime(2026, 3, day).date()} if day else set())
    assert got == times


def test_read_leaves_ambiguous_parts_null():
    assert read(_msg(1, "Repu 2 boxes extra, 9 ki pampandi"))[1] is None  # stray number
    assert read(_msg(1, "Can we move repu slot to 9 am"))[0] is None  # "we" read as a weekday
    assert read(_msg(1, "Monday nunchi 6 ki pettandi")) == (None, None)  # standing change
    assert read(_msg(1, "every day 7 am slot kavali")) == (None, None)


def test_fills_null_fields_with_earliest_time_and_one_day():
    msgs = [_msg(1, "Kondagal outlet ki"), _msg(2, "repu 10 ki kakunda madhyanam 2 ki pettandi")]
    [c] = _run(msgs, _slot("m002", ["m001", "m002"]))
    assert (c.entities.slot_day_offset, c.entities.slot_time) == (1, "10:00")
    assert c.entities.slot_datetime == datetime(2026, 3, 3, 10, 0)
    assert c.flags == [] and "code filled" in c.slot_note


def test_never_overwrites_the_models_values():
    msgs = [_msg(1, "repu 10 ki pettandi")]
    [c] = _run(msgs, _slot("m001", ["m001"], offset=2, at=None))
    assert (c.entities.slot_day_offset, c.entities.slot_time) == (2, "10:00")
    [c] = _run(msgs, _slot("m001", ["m001"], offset=0, at="7.30 pm"))  # invalid stays invalid
    assert c.entities.slot_time == "7.30 pm" and c.flags == ["time_unspecified"]


def test_two_days_stay_null_and_flagged():
    msgs = [_msg(1, "ivala kaadu, repu 9 ki")]
    [c] = _run(msgs, _slot("m001", ["m001"]))
    assert c.entities.slot_day_offset is None and c.flags == ["time_unspecified"]


def test_only_the_requesters_own_messages_are_read():
    msgs = [_msg(1, "slot marchandi please"), _msg(2, "repu 9 ki aa madam?", author="Ops")]
    [c] = _run(msgs, _slot("m001", ["m001", "m002"]))
    assert c.entities.slot_datetime is None and c.flags == ["time_unspecified"]


def test_follow_up_inherits_the_referenced_slot():
    msgs = [
        _msg(1, "Repu 7 ki kakunda 9 ki pampandi"),
        _msg(2, "Maa outlet ki kooda alaage cheyyandi", author="Kavya"),
        _msg(3, "Maa outlet ki kuda 11 ki pettandi", author="Ravi"),
    ]
    first, same, own_time = _run(
        msgs,
        _slot("m001", ["m001"]),
        _slot("m002", ["m002", "m001"], refers_to="m001"),
        _slot("m003", ["m003", "m001"], refers_to="m001"),
    )
    assert first.entities.slot_datetime == datetime(2026, 3, 3, 7, 0)
    assert same.entities.slot_datetime == datetime(2026, 3, 3, 7, 0) and same.flags == []
    assert own_time.entities.slot_datetime == datetime(2026, 3, 3, 11, 0)  # own time, inherited day


def test_follow_up_offset_counts_from_its_own_date():
    msgs = [
        _msg(1, "ellundi 8 ki pettandi"),
        _msg(2, "same for us", author="Kavya", ts=datetime(2026, 3, 3, 9, 0)),
    ]
    _, same = _run(msgs, _slot("m001", ["m001"]), _slot("m002", ["m002"], refers_to="m001"))
    assert same.entities.slot_day_offset == 1
    assert same.entities.slot_datetime == datetime(2026, 3, 4, 8, 0)


def test_follow_up_without_a_resolved_referent_inherits_nothing():
    msgs = [_msg(1, "Repu 7 ki pampandi"), _msg(2, "same for us", author="Kavya")]
    _, same = _run(msgs, _slot("m001", ["m001"]), _slot("m002", ["m002"], refers_to="m009"))
    assert same.entities.slot_datetime is None
    assert same.flags == ["referent_unresolved", "time_unspecified"]


def test_explicit_ask_false_becomes_implicit_request():
    msgs = [_msg(1, "Invoice already mail chesanu sir")]
    cand = Candidate(
        intent="invoice_request",
        gloss="g",
        primary_msg_id="m001",
        evidence_msg_ids=["m001"],
        explicit_ask=False,
    )
    [c] = _run(msgs, cand)
    assert c.flags == ["implicit_request"]
    [c] = _run(msgs, cand.model_copy(update={"explicit_ask": None}))  # v3: field not asked
    assert c.flags == []
