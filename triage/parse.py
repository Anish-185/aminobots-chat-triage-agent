"""Parse an Android WhatsApp `.txt` export into `Message`s with IDs m001… in file order.

chat-miner parses ordinary messages; it drops system lines, so a small pre-pass recovers them
(SPEC §3.1). Android format only: `dd/mm/yy, h:mm am - Name: text`.
"""

import logging
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import phonenumbers
import yaml

os.environ.setdefault("TQDM_DISABLE", "1")  # chat-miner shows a progress bar per file
from chatminer.chatparsers import WhatsAppParser  # noqa: E402

from triage.schemas import Message  # noqa: E402

# Date order is fixed by the pre-pass, so chat-miner's date-format guess warnings are noise.
logging.getLogger("chatminer.chatparsers").setLevel(logging.ERROR)

START = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}) ?([ap]m) - (.*)$", re.IGNORECASE)
PHONE_AUTHOR = re.compile(r"^\+?[\d ()-]{10,}$")
MEDIA = {"<Media omitted>", "image omitted", "video omitted", "sticker omitted"}
DELETED = {"This message was deleted", "You deleted this message"}
SUBJECT = [
    re.compile(r"^(.+?)'s security code changed"),
    re.compile(r"^(.+?) left$"),
    re.compile(r"^.+? added (.+)$"),
    re.compile(r"^(.+?) joined using this group's invite link$"),
]


def _prepass(path: Path) -> list[tuple[datetime, str | None]]:
    """One entry per message in file order: (time, system text) or (time, None) if ordinary."""
    slots: list[tuple[datetime, str | None]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = unicodedata.normalize("NFKC", raw.replace("‎", "").strip())
        m = START.match(line)
        if not m:
            continue  # continuation of a multi-line message
        date, clock, ampm, rest = m.groups()
        fmt = "%d/%m/%Y" if len(date.split("/")[2]) == 4 else "%d/%m/%y"
        ts = datetime.strptime(f"{date} {clock} {ampm.upper()}", f"{fmt} %I:%M %p")
        # Same test chat-miner uses: no ": " after the time means a system line.
        slots.append((ts, None if ": " in rest else rest))
    return slots


def load_contacts(path: Path | None) -> dict[str, str]:
    """Saved display name → phone, from an optional contacts.yaml."""
    if path is None or not path.exists():
        return {}
    return dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def to_e164(raw: str) -> str:
    return phonenumbers.format_number(
        phonenumbers.parse(raw, "IN"), phonenumbers.PhoneNumberFormat.E164
    )


def _resolve(author: str, contacts: dict[str, str]) -> tuple[str | None, str | None]:
    """(phone, display_name) for an exported author string."""
    if PHONE_AUTHOR.match(author):
        return to_e164(author), None
    phone = contacts.get(author)
    return (to_e164(phone) if phone else None), author


def parse_chat(path: Path, contacts_path: Path | None = None) -> list[Message]:
    contacts = load_contacts(contacts_path)
    parser = WhatsAppParser(str(path))
    parser.parse_file()
    rows = list(reversed(parser.parsed_messages.get_df().rows(named=True)))  # file order
    slots = _prepass(path)
    if sum(1 for _, sys_text in slots if sys_text is None) != len(rows):
        raise ValueError(f"{path}: pre-pass and chat-miner disagree on message count")

    messages: list[Message] = []
    it = iter(rows)
    for n, (ts, sys_text) in enumerate(slots, start=1):
        mid = f"m{n:03d}"
        if sys_text is not None:
            subject = next((m.group(1) for p in SUBJECT if (m := p.match(sys_text))), None)
            subject_phone = _resolve(subject, contacts)[0] if subject else None
            messages.append(
                Message(
                    id=mid,
                    ts=ts,
                    author_raw=None,
                    phone=None,
                    display_name=None,
                    text=sys_text,
                    kind="system",
                    subject_raw=subject,
                    subject_phone=subject_phone,
                )
            )
            continue
        row = next(it)
        if row["timestamp"].time() != ts.time():  # slots and rows must line up
            raise ValueError(f"{path}: {mid} misaligned between pre-pass and chat-miner")
        author, text = row["author"], row["message"]
        phone, name = _resolve(author, contacts)
        kind = "media" if text in MEDIA else "system" if text in DELETED else "text"
        messages.append(
            Message(
                id=mid,
                ts=ts,  # pre-pass time: fixed dd/mm order (chat-miner guesses it per file)
                author_raw=author,
                phone=phone,
                display_name=name,
                text=text,
                kind=kind,
            )
        )
    return messages
