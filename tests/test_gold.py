"""Dev gold and world validate; the validator catches each kind of labelling error."""

import importlib.util
import json
import shutil
from pathlib import Path

import phonenumbers
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("validate_gold", ROOT / "scripts/validate_gold.py")
vg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vg)


def test_dev_gold_and_world_are_valid():
    assert vg.validate() == []


@pytest.fixture
def copy(tmp_path: Path):
    shutil.copytree(ROOT / "data" / "dev", tmp_path / "dev")
    shutil.copytree(ROOT / "data" / "world", tmp_path / "world")
    return tmp_path


def _edit(path: Path, fn) -> None:
    gold = json.loads(path.read_text(encoding="utf-8"))
    fn(gold)
    path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize(
    ("chat", "mutate", "expected"),
    [
        ("d01", lambda g: g["requests"][0].update(evidence_msg_ids=["m999", "m011"]), "m999"),
        ("d01", lambda g: g["requests"][0].update(requester_phone="+915555010001"), "!= sender"),
        ("d05", lambda g: g["requests"][0].update(identity_state="CONFIRMED"), "AMBIGUOUS"),
        ("d04", lambda g: g["requests"][0].update(identity_state="CONFIRMED"), "roster says"),
        ("d07", lambda g: g["requests"][0].update(grade="act", rule_id="R9"), "SPEC §9 gives"),
        ("d08", lambda g: g["requests"][0].update(rule_id="R3"), "SPEC §9 gives"),
        ("d02", lambda g: g["requests"][2].update(grade="act"), "R7 gives"),
        ("d13", lambda g: g["requests"].append(g["internal_requests"][0]), "internal request"),
        ("d01", lambda g: g["requests"][2]["facts"].update(authorised=False), "contradicts role"),
        # 07:00 next day is 11.5 h after "now" (19:32), so R7 applies even though the request
        # message was 22 h before the slot (SPEC §9: hours from "now").
        (
            "d02",
            lambda g: g["requests"][0]["facts"].update(slot_datetime="2026-10-23T07:00:00"),
            "SPEC §9 gives",
        ),
        ("d13", lambda g: g["requests"][2].update(evidence_msg_ids=["m031"]), "handled needs"),
    ],
)
def test_validator_catches(copy: Path, chat: str, mutate, expected: str):
    _edit(copy / "dev" / f"{chat}.gold.json", mutate)
    errors = vg.validate(copy / "dev", copy / "world")
    assert any(expected in e for e in errors), errors


def test_validator_catches_valid_phone(copy: Path):
    # The library's documented example number, so no real person's number is ever used.
    example = phonenumbers.format_number(
        phonenumbers.example_number("IN"), phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    roster = copy / "world" / "roster.yaml"
    roster.write_text(roster.read_text().replace("+91 55550 10001", example))
    assert any("VALID number" in e for e in vg.validate(copy / "dev", copy / "world"))
