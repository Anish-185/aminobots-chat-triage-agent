"""Identity and authority (SPEC §7): a roster lookup in code; the model never decides it.

State: CONFIRMED = phone in the roster and not shared; AMBIGUOUS = shared phone, or unknown phone
whose saved name matches 2+ roster contacts; UNCONFIRMED otherwise. Only the phone and the saved
name are used, never message text, so self-claims and vouching cannot confirm anyone. A
"security code changed" line for the sender before the request downgrades CONFIRMED.
"""

import re

from rapidfuzz import fuzz, utils

from triage.parse import to_e164
from triage.schemas import Candidate, Contact, Flag, Identity, Message, Outlet, Roster

OUTLET_INTENTS = {"delivery_slot_change", "order_change"}  # requests scoped to one outlet
HONORIFICS = re.compile(r"\b(garu|gaaru|madam|madem|sir|anna|akka|amma|ji|mam)\b", re.I)


def name_matches(name: str | None, contacts: list[Contact], threshold: int) -> list[Contact]:
    if not name or not (name := HONORIFICS.sub(" ", name).strip()):
        return []
    return [
        c
        for c in contacts
        if fuzz.WRatio(name, c.name, processor=utils.default_process) >= threshold
    ]


def _outlets_named(text: str | None, roster: Roster, threshold: int) -> list[Outlet]:
    if not text:
        return []
    return [
        o
        for p in roster.partners
        for o in p.outlets
        if fuzz.partial_ratio(o.area.lower(), text.lower()) >= threshold
    ]


def identify(
    c: Candidate, messages: list[Message], roster: Roster, allowed: set[str], threshold: int
) -> tuple[Identity, list[Flag], bool]:
    """(identity, flags added in code, internal) for the sender of the candidate's primary msg."""
    by_id = {m.id: m for m in messages}
    primary = by_id[c.primary_msg_id]
    phone, name = primary.phone, primary.display_name
    people = [p for p in roster.contacts if phone and to_e164(p.phone) == phone]
    code_changed = any(
        m.kind == "system" and phone and m.subject_phone == phone and m.id < primary.id
        for m in messages
    )

    if people and any(p.shared for p in people):
        state, reason = "AMBIGUOUS", f"shared phone used by {len(people)} roster contacts"
    elif people and code_changed:
        state = "UNCONFIRMED"
        reason = f"phone belongs to {people[0].name}, but its security code changed before this"
    elif people:
        state, reason = "CONFIRMED", f"phone is in the roster: {people[0].name}"
    else:
        people = name_matches(name, roster.contacts, threshold)
        if len(people) >= 2:
            state = "AMBIGUOUS"
            reason = f"unknown phone; saved name {name!r} matches {len(people)} roster contacts"
        else:
            state = "UNCONFIRMED"
            reason = "unknown phone" + (
                f"; saved name {name!r} matches only {people[0].name}, which is not proof"
                if people
                else ""
            )
    reason += " (self-claims and vouching in the chat never confirm a sender)"

    role = people[0].role if people and len({p.role for p in people}) == 1 else None
    # AMBIGUOUS is authorised only if every candidate contact is (SPEC §7).
    authorised = state != "UNCONFIRMED" and bool(people) and all(p.role in allowed for p in people)
    internal = state == "CONFIRMED" and role == "aminobots_staff"
    sender_outlets = sorted({o for p in people for o in p.outlets}) if state == "CONFIRMED" else []
    partners = {p.partner for p in people}

    flags: list[Flag] = []
    named = _outlets_named(c.entities.outlet, roster, threshold)
    targets = [o.id for o in named] or sender_outlets  # "maa outlet" → the sender's outlets
    if c.intent in OUTLET_INTENTS and not named and len(sender_outlets) >= 2:
        flags.append("outlet_ambiguous")
        reason += f"; 'our outlet' could be any of {', '.join(sender_outlets)}"

    other_partner = (
        state == "CONFIRMED"
        and not internal
        and any(p.id not in partners for p in roster.partners if any(o in p.outlets for o in named))
    )
    principals = name_matches(c.on_behalf_of, roster.contacts, threshold)
    on_behalf = c.on_behalf_of is not None or other_partner
    verified = (
        on_behalf
        and not other_partner
        and state == "CONFIRMED"
        and len(principals) == 1
        and principals[0].id in people[0].delegate_for
    )
    if other_partner:
        reason += "; asks about another partner's outlet (on-behalf, never verified)"
    elif on_behalf:
        reason += f"; asks on behalf of {c.on_behalf_of!r}: " + (
            "sender is a roster delegate" if verified else "not a verified delegate"
        )

    identity = Identity(
        state=state,
        contact_ids=[p.id for p in people],
        role=role,
        outlets=sender_outlets,
        authorised=authorised,
        on_behalf=on_behalf,
        on_behalf_verified=verified,
        target_outlets=targets,
        reason=reason,
    )
    return identity, flags, internal
