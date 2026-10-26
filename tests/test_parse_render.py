import re
from pathlib import Path

import pytest

from triage.parse import parse_chat
from triage.render import HIDDEN, assign_handles, render

FIXTURE = Path(__file__).parent / "fixtures" / "android_sample.txt"
PHONE = re.compile(r"\+?91[\d ]{8,}|\d{5} \d{5}")


@pytest.fixture(scope="module")
def messages():
    return parse_chat(FIXTURE)


def test_ids_in_file_order_including_system_lines(messages):
    assert [m.id for m in messages] == [f"m{n:03d}" for n in range(1, 12)]
    assert [m.ts for m in messages] == sorted(m.ts for m in messages)


def test_kinds(messages):
    kinds = {m.id: m.kind for m in messages}
    assert kinds["m001"] == kinds["m002"] == kinds["m003"] == "system"
    assert kinds["m007"] == "media"
    assert kinds["m008"] == "system"  # security code changed
    assert kinds["m009"] == "system"  # this message was deleted
    assert kinds["m010"] == "system"  # left
    assert kinds["m006"] == "text"


def test_special_characters_and_multiline(messages):
    m6 = messages[5]
    assert m6.phone == "+911234567801"  # leading U+200E and U+202F handled
    assert "Ameerpet outlet ki" in m6.text and "Thanks" in m6.text
    assert messages[9].ts.hour == 22  # 10:05 pm with U+202F
    assert messages[4].author_raw == "Lakshmi 🌸"


def test_security_code_subject_resolves_to_sender(messages):
    assert messages[7].subject_phone == messages[5].phone


def test_contacts_yaml_resolves_saved_names(tmp_path):
    contacts = tmp_path / "contacts.yaml"
    contacts.write_text('"Ravi Kumar": "+91 12345 67802"\n')
    ravi = parse_chat(FIXTURE, contacts)[3]
    assert ravi.phone == "+911234567802" and ravi.display_name == "Ravi Kumar"


def test_render_never_contains_a_phone(messages):
    out = render(messages)
    assert not PHONE.search(out), out
    assert f'"{HIDDEN}"' in out


def test_render_lines_and_dividers(messages):
    lines = render(messages).splitlines()
    assert lines[0] == "--- 2026-10-24 ---"
    assert "--- 2026-10-25 ---" in lines
    assert '[m007] 09:16 | S2 "Ravi Kumar" | [image]' in lines
    assert "[m008] 09:20 | system | S1's security code changed. Tap to learn more." in lines
    assert '[m009] 09:21 | S3 "Lakshmi 🌸" | [message deleted]' in lines
    assert "[m010] 22:05 | system | S3 left" in lines


def test_handles_stable_and_in_order_of_first_appearance(messages):
    h = assign_handles(messages)
    assert list(h.values()) == [f"S{i}" for i in range(1, len(h) + 1)]
    assert assign_handles(messages) == h
    assert render(messages) == render(parse_chat(FIXTURE))
