"""Render messages for the model (SPEC §3.2): one line per message, stable sender handles,
date dividers, and no phone numbers anywhere."""

import re

from triage.schemas import Message

PHONE_IN_TEXT = re.compile(r"\+?\d[\d ()-]{8,}\d")
HIDDEN = "(number hidden)"


def _key(m: Message) -> str | None:
    return m.phone or m.author_raw


def _subject_key(m: Message) -> str | None:
    return m.subject_phone or m.subject_raw


def assign_handles(messages: list[Message]) -> dict[str, str]:
    """Sender key (phone, else raw author) → S1…Sn, in order of first appearance."""
    handles: dict[str, str] = {}
    for m in messages:
        for key in (_key(m), _subject_key(m)):
            if key and key not in handles:
                handles[key] = f"S{len(handles) + 1}"
    return handles


def _mask(text: str) -> str:
    return PHONE_IN_TEXT.sub("[phone]", text)


def render(messages: list[Message]) -> str:
    handles = assign_handles(messages)
    lines: list[str] = []
    day = None
    for m in messages:
        if m.ts.date() != day:
            day = m.ts.date()
            lines.append(f"--- {day.isoformat()} ---")
        prefix = f"[{m.id}] {m.ts:%H:%M}"
        if m.author_raw is None:  # system line, e.g. "S3's security code changed"
            text = m.text
            if m.subject_raw:
                text = text.replace(m.subject_raw, handles[_subject_key(m)])
            lines.append(f"{prefix} | system | {_mask(text)}")
            continue
        name = _mask(m.display_name) if m.display_name else HIDDEN
        text = {"media": "[image]"}.get(m.kind, m.text)
        if m.kind == "system":
            text = "[message deleted]"
        lines.append(f'{prefix} | {handles[_key(m)]} "{name}" | {_mask(text)}')
    return "\n".join(lines)
