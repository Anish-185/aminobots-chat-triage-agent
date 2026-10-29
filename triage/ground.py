"""Grounding (SPEC §3.4): every message ID a candidate cites must exist in the chat.

A candidate whose primary message, or every evidence message, is unknown is dropped as
`rejected_hallucination`. Unknown evidence IDs are removed, the primary ID is always in the
evidence, and an unknown `refers_to_msg_id` becomes the flag `referent_unresolved`. Every drop is
logged; nothing is dropped silently.

Slot changes (SPEC §3.3, v2.5): code computes `entities.slot_datetime` from the primary message's
date + `slot_day_offset` + `slot_time`; if either part is missing it adds `time_unspecified`.
"""

import logging
import re
from datetime import datetime, time, timedelta

from triage.schemas import Candidate, Entities, ExtractionResult, Flag, Message, Rejected

log = logging.getLogger(__name__)


SLOT_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def slot_datetime(e: Entities, primary: Message) -> datetime | None:
    """None (→ time_unspecified) unless the offset is ≥ 0 and the time is a valid "HH:MM"."""
    off, at = e.slot_day_offset, e.slot_time
    if off is None or off < 0 or at is None or not SLOT_TIME.match(at):
        return None
    return datetime.combine(primary.ts.date() + timedelta(days=off), time.fromisoformat(at))


def ground(
    result: ExtractionResult, messages: list[Message]
) -> tuple[list[Candidate], list[Rejected]]:
    by_id = {m.id: m for m in messages}
    kept: list[Candidate] = []
    rejected: list[Rejected] = []
    for c in result.candidates:
        valid = [i for i in c.evidence_msg_ids if i in by_id]
        if c.primary_msg_id not in by_id or not valid:
            unknown = sorted({c.primary_msg_id, *c.evidence_msg_ids} - by_id.keys())
            reason = f"rejected_hallucination: unknown message IDs {unknown}"
            log.warning("dropped candidate %r: %s", c.gloss, reason)
            rejected.append(Rejected(candidate=c, reason=reason))
            continue
        if dropped := [i for i in c.evidence_msg_ids if i not in by_id]:
            log.warning("candidate %s: dropped unknown evidence IDs %s", c.primary_msg_id, dropped)
        evidence = list(dict.fromkeys(valid + [c.primary_msg_id]))
        flags: list[Flag] = list(c.flags)
        refers_to = c.refers_to_msg_id
        if refers_to is not None and refers_to not in by_id:
            log.warning("candidate %s: unknown refers_to %s", c.primary_msg_id, refers_to)
            refers_to = None
            flags.append("referent_unresolved")
        slot = slot_datetime(c.entities, by_id[c.primary_msg_id])
        if c.intent == "delivery_slot_change" and slot is None and c.status == "open":
            flags.append("time_unspecified")
        kept.append(
            c.model_copy(
                update={
                    "evidence_msg_ids": evidence,
                    "refers_to_msg_id": refers_to,
                    "flags": list(dict.fromkeys(flags)),
                    "entities": c.entities.model_copy(update={"slot_datetime": slot}),
                }
            )
        )
    return kept, rejected
