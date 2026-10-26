"""Invariant 9: every phone in the synthetic world, dev chats, gold and fixtures is INVALID."""

import json
import re
from pathlib import Path

import phonenumbers
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
PHONE = re.compile(r"\+91[\d ]{10,13}\d")
FILES = [
    ROOT / "data" / "world" / "roster.yaml",
    ROOT / "data" / "world" / "contacts.yaml",
    *sorted((ROOT / "data" / "dev").glob("*.txt")),
    *sorted((ROOT / "data" / "dev").glob("*.gold.json")),
    *sorted((ROOT / "tests" / "fixtures").glob("*.txt")),
]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_every_phone_is_invalid(path: Path):
    phones = PHONE.findall(path.read_text(encoding="utf-8"))
    valid = [p for p in phones if phonenumbers.is_valid_number(phonenumbers.parse(p, "IN"))]
    assert not valid, f"{path.name}: valid numbers {valid}"


def test_world_has_phones_and_they_follow_the_rule():
    roster = yaml.safe_load((ROOT / "data/world/roster.yaml").read_text())
    for c in roster["contacts"]:
        digits = c["phone"].replace(" ", "")
        assert re.fullmatch(r"\+91[0-5]\d{9}", digits), c


def test_gold_phones_are_e164_and_invalid():
    for path in sorted((ROOT / "data" / "dev").glob("*.gold.json")):
        gold = json.loads(path.read_text(encoding="utf-8"))
        for r in gold["requests"] + gold["internal_requests"]:
            num = phonenumbers.parse(r["requester_phone"])
            assert not phonenumbers.is_valid_number(num), (path.name, r["id"])
