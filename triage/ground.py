"""Grounding (SPEC §3.4): every message ID a candidate cites must exist in the chat.

A candidate whose primary message, or every evidence message, is unknown is dropped as
`rejected_hallucination`. Unknown evidence IDs are removed, the primary ID is always in the
evidence, and an unknown `refers_to_msg_id` becomes the flag `referent_unresolved`. Every drop is
logged; nothing is dropped silently.
"""

import logging

from triage.schemas import Candidate, ExtractionResult, Message, Rejected

log = logging.getLogger(__name__)


def ground(
    result: ExtractionResult, messages: list[Message]
) -> tuple[list[Candidate], list[Rejected]]:
    ids = {m.id for m in messages}
    kept: list[Candidate] = []
    rejected: list[Rejected] = []
    for c in result.candidates:
        valid = [i for i in c.evidence_msg_ids if i in ids]
        if c.primary_msg_id not in ids or not valid:
            unknown = sorted({c.primary_msg_id, *c.evidence_msg_ids} - ids)
            reason = f"rejected_hallucination: unknown message IDs {unknown}"
            log.warning("dropped candidate %r: %s", c.gloss, reason)
            rejected.append(Rejected(candidate=c, reason=reason))
            continue
        if dropped := [i for i in c.evidence_msg_ids if i not in ids]:
            log.warning("candidate %s: dropped unknown evidence IDs %s", c.primary_msg_id, dropped)
        evidence = list(dict.fromkeys(valid + [c.primary_msg_id]))
        flags, refers_to = list(c.flags), c.refers_to_msg_id
        if refers_to is not None and refers_to not in ids:
            log.warning("candidate %s: unknown refers_to %s", c.primary_msg_id, refers_to)
            refers_to = None
            if "referent_unresolved" not in flags:
                flags.append("referent_unresolved")
        kept.append(
            c.model_copy(
                update={"evidence_msg_ids": evidence, "refers_to_msg_id": refers_to, "flags": flags}
            )
        )
    return kept, rejected
