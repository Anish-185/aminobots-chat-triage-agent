"""Slot fields (SPEC §3.3, v2.8): code fills what the model left null, then computes the datetime.

The model often leaves `slot_day_offset` / `slot_time` null. For a slot change, code reads the
requester's own evidence messages (not the referenced message, not other people's replies):
1. a small map turns Telugu day words into English (repu → tomorrow, ellundi → in 2 days,
   ivala / ee roju → today) and every stated time into "HH:MM" ("7 ki", "9am", "madhyanam 2");
2. dateparser's search_dates finds the day (RELATIVE_BASE = that message's timestamp, future
   dates preferred); a match that is not a plain day expression makes the day ambiguous.
A field is filled only if it is null and the text gives one reading: exactly one day; the
earliest stated time (the contract in SPEC §3.3, and the cautious choice for R7), unless a bare
number that is not a time is left over. A standing change ("Monday nunchi", "every day") is not one
slot and is left null. A follow-up ("alaage", "same", "kuda") inherits the null fields of the
slot-change request it refers to. Anything left null keeps `time_unspecified` (→ R6).
dateparser 1.4.3 misreads "9 am", "X o'clock" and "day after tomorrow" (probed in Phase 9), so
times never reach it and "ellundi" becomes "in 2 days".
Over ~150 lines: mostly this docstring and the word patterns; dateparser resolves the dates.
"""

import logging
import re
from datetime import date, datetime, time, timedelta

from dateparser.search import search_dates

from triage.schemas import Candidate, Entities, Message

log = logging.getLogger(__name__)

SLOT_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DAY_WORDS = [  # romanised and Telugu-script day words → English that dateparser reads correctly
    (re.compile(r"\b(ellundi|ellundu)\b|ఎల్లుండి"), "in 2 days"),
    (re.compile(r"\bre+pu+\b|రేపు"), "tomorrow"),
    (re.compile(r"\b(ivala|ee\s*roju)\b|ఈ\s*రోజు"), "today"),
]
TIME = re.compile(
    r"(?:\b(?P<pm>madhyanam|madhyaanam|sayantram|saayantram|afternoon|evening|night)\s+)?"
    r"(?<![\d:])(?P<h>\d{1,2})(?::(?P<m>[0-5]\d))?(?!\d)"
    r"\s*(?P<suf>am|pm|o'?clock|gantalaki|gantalaku|ki|కి|గంటలకు)?(?![a-z])"
)
HHMM = re.compile(r"\b\d\d:\d\d\b")
BARE_NUMBER = re.compile(r"\b\d{1,2}\b")
DAY_OK = re.compile(
    r"^(today|tomorrow|in \d+ days|(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"|(the )?\d{1,2}(st|nd|rd|th))$"
)
_DAY = r"(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
STANDING = re.compile(
    rf"\b{_DAY}\s+(nunchi|nundi|onwards)\b|\bfrom\s+{_DAY}\b|\b(every|daily|everyday|prati)\b"
)


def _time(mt: re.Match) -> str:
    """One stated time → " HH:MM "; a bare number (no suffix, colon or pm word) is kept as is."""
    h, m, suf, pm = int(mt["h"]), int(mt["m"] or 0), mt["suf"], mt["pm"]
    if not (suf or mt["m"] or pm):
        return mt[0]
    if (suf == "pm" or (pm and suf != "am")) and h < 12:
        h += 12
    elif suf == "am" and h == 12:
        h = 0
    return f" {h:02d}:{m:02d} " if h <= 23 else mt[0]


def read(msg: Message) -> tuple[set[date] | None, list[str] | None]:
    """(days, times) stated in one message; None = ambiguous, so that field stays null."""
    text = TIME.sub(_time, msg.text.lower())
    times = sorted(HHMM.findall(text))
    rest = HHMM.sub(" ", text)
    times_out = None if BARE_NUMBER.search(rest) else times  # a stray number may be a time
    for pattern, word in DAY_WORDS:
        rest = pattern.sub(word, rest)
    if STANDING.search(rest):
        return None, None  # not one slot
    found = search_dates(
        rest,
        languages=["en"],
        settings={"RELATIVE_BASE": msg.ts, "PREFER_DATES_FROM": "future"},
    )
    days: set[date] | None = set()
    for sub, when in found or []:
        if not DAY_OK.match(sub.strip()):
            return None, times_out  # e.g. "we" read as Wednesday: do not guess
        days.add(when.date())
    return days, times_out


def _own(c: Candidate, by_id: dict[str, Message]) -> tuple[int | None, str | None, str]:
    """Day offset and time from the requester's own evidence messages, with a note."""
    primary = by_id[c.primary_msg_id]
    days: set[date] | None = set()
    times: list[str] | None = []
    for mid in c.evidence_msg_ids:
        m = by_id[mid]
        if mid == c.refers_to_msg_id or m.author_raw != primary.author_raw:
            continue
        d, t = read(m)
        days = None if days is None or d is None else days | d
        times = None if times is None or t is None else times + t
    offset = None
    if days is not None and len(days) == 1:
        offset = (next(iter(days)) - primary.ts.date()).days
        offset = offset if offset >= 0 else None
    at = min(times) if times else None
    return offset, at, f"evidence: days {sorted(map(str, days or []))}, times {times}"


def fill(cands: list[Candidate], by_id: dict[str, Message]) -> list[Candidate]:
    """Fill null slot fields of slot changes in code (never overwrite what the model gave)."""
    out = list(cands)
    order = sorted(range(len(out)), key=lambda i: out[i].refers_to_msg_id is not None)
    for i in order:  # requests that refer to nothing first, so follow-ups can inherit
        c = out[i]
        e = c.entities
        if c.intent != "delivery_slot_change" or None not in (e.slot_day_offset, e.slot_time):
            continue
        offset, at, note = _own(c, by_id)
        update = {
            k: v
            for k, v in (("slot_day_offset", offset), ("slot_time", at))
            if getattr(e, k) is None and v is not None
        }
        ref = _referenced(c, out)
        if ref is not None:
            day = _date_of(ref, by_id)
            own_date = by_id[c.primary_msg_id].ts.date()
            inherit = {
                "slot_day_offset": (day - own_date).days if day and day >= own_date else None,
                "slot_time": ref.entities.slot_time,
            }
            for k, v in inherit.items():
                if getattr(e, k) is None and k not in update and v is not None:
                    update[k] = v
            note += f"; inherits from {ref.primary_msg_id}"
        if update:
            note = f"code filled {sorted(update)} ({note})"
            log.info("candidate %s: %s", c.primary_msg_id, note)
            out[i] = c.model_copy(
                update={"entities": e.model_copy(update=update), "slot_note": note}
            )
    return out


def _referenced(c: Candidate, cands: list[Candidate]) -> Candidate | None:
    """The slot-change request a follow-up refers to: its primary message, else its evidence."""
    if c.refers_to_msg_id is None:
        return None
    others = [o for o in cands if o is not c and o.intent == "delivery_slot_change"]
    return next(
        (o for o in others if o.primary_msg_id == c.refers_to_msg_id),
        next((o for o in others if c.refers_to_msg_id in o.evidence_msg_ids), None),
    )


def _date_of(c: Candidate, by_id: dict[str, Message]) -> date | None:
    off = c.entities.slot_day_offset
    return None if off is None or off < 0 else by_id[c.primary_msg_id].ts.date() + timedelta(off)


def slot_datetime(e: Entities, primary: Message) -> datetime | None:
    """None (→ time_unspecified) unless the offset is ≥ 0 and the time is a valid "HH:MM"."""
    off, at = e.slot_day_offset, e.slot_time
    if off is None or off < 0 or at is None or not SLOT_TIME.match(at):
        return None
    return datetime.combine(primary.ts.date() + timedelta(days=off), time.fromisoformat(at))
