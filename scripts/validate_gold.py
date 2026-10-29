"""Validate the dev gold labels and the synthetic world (data/dev and data/world ONLY).

Checks: schema; every message ID exists; requester = sender of the primary message; identity
state consistent with the roster; grade and rule agree with SPEC §9 (re-derived from the facts
recorded in gold); all phones invalid. Exit 1 on any error.
Run: uv run python scripts/validate_gold.py
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import phonenumbers
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from triage.config import load_thresholds  # noqa: E402
from triage.parse import parse_chat, to_e164  # noqa: E402
from triage.schemas import GoldChat, GoldRequest, Message, Roster  # noqa: E402

WORLD, DEV = ROOT / "data" / "world", ROOT / "data" / "dev"
PHONE = re.compile(r"\+91[\d ]{10,13}\d")

# SPEC §6 intent table (policy_v1.yaml arrives in Phase 5): risk, discloses, allowed roles.
INTENTS = {
    "delivery_slot_change": ("low", False, {"owner", "manager", "staff"}),
    "order_change": ("medium", False, {"owner", "manager"}),
    "status_query": ("none", True, {"owner", "manager", "staff", "accounts"}),
    "invoice_request": ("none", True, {"owner", "manager", "accounts"}),
    "payout_details_change": ("critical", True, {"owner"}),
    "refund_request": ("high", False, {"owner", "manager", "accounts"}),
    "complaint": (None, False, None),
    "other": (None, False, None),
}
RULE_GRADE = {"R1": "hand_off", "R2": "refuse", "R3": "hand_off", "R4": "seek_approval",
              "R5": "seek_approval", "R6": "seek_approval", "R7": "seek_approval",
              "R8": "act", "R9": "act", "R10": "hand_off"}  # fmt: skip
CAUTION = ["act", "seek_approval", "hand_off", "refuse"]
SLOT_CUTOFF = load_thresholds().slot_cutoff_hours


def expected_grade(r: GoldRequest, now: datetime) -> tuple[str, str]:
    """Apply SPEC §9 by hand: all rules, most cautious grade wins, lowest rule ID cited."""
    risk, discloses, _ = INTENTS[r.intent]
    f, state = r.facts, r.identity_state
    # SPEC §9: hours from the chat's "now" (A4), not from the request message.
    hours = (f.slot_datetime - now).total_seconds() / 3600 if f.slot_datetime else None
    matched = [
        rid
        for rid, cond in [
            ("R1", r.intent == "payout_details_change"),
            ("R2", state == "UNCONFIRMED" and (risk in ("high", "critical") or discloses)),
            ("R3", r.intent in ("complaint", "other") or risk in ("high", "critical")),
            ("R4", state != "CONFIRMED"),
            ("R5", not f.authorised or (f.on_behalf and not f.on_behalf_verified)),
            ("R6", bool(r.flags)),
            ("R7", risk == "medium"
             or (r.intent == "delivery_slot_change" and hours is not None
                 and hours < SLOT_CUTOFF)),
            ("R8", r.status != "open"),
            ("R9", r.status == "open" and state == "CONFIRMED" and f.authorised
             and risk in ("none", "low")),
        ]
        if cond
    ] or ["R10"]  # fmt: skip
    grade = max((RULE_GRADE[m] for m in matched), key=CAUTION.index)
    return grade, next(m for m in matched if RULE_GRADE[m] == grade)


def phone_errors(text: str, where: str) -> list[str]:
    return [
        f"{where}: {p} is a VALID number; synthetic phones must be invalid"
        for p in PHONE.findall(text)
        if phonenumbers.is_valid_number(phonenumbers.parse(p, "IN"))
    ]


def check_request(
    r: GoldRequest, msgs: dict[str, Message], roster: Roster, staff: set[str], where: str
) -> list[str]:
    errs = []
    ids = [r.primary_msg_id, *r.evidence_msg_ids]
    errs += [f"{where}: message {i} does not exist" for i in ids if i not in msgs]
    if r.primary_msg_id not in r.evidence_msg_ids:
        errs.append(f"{where}: primary message missing from evidence")
    if r.primary_msg_id not in msgs:
        return errs
    primary = msgs[r.primary_msg_id]
    if r.requester_phone != primary.phone:
        errs.append(f"{where}: requester {r.requester_phone} != sender {primary.phone}")
    people = [c for c in roster.contacts if to_e164(c.phone) == primary.phone]
    code_changed = any(
        m.kind == "system" and m.subject_phone == primary.phone and m.id < primary.id
        for m in msgs.values()
    )
    if people and not people[0].shared:
        state = "UNCONFIRMED" if code_changed else "CONFIRMED"
        if r.identity_state != state:
            errs.append(f"{where}: identity {r.identity_state}, roster says {state}")
        allowed = INTENTS[r.intent][2]
        if state == "CONFIRMED" and allowed and r.facts.authorised != (people[0].role in allowed):
            errs.append(f"{where}: authorised={r.facts.authorised} contradicts role")
    elif people and r.identity_state != "AMBIGUOUS":
        errs.append(f"{where}: shared phone must be AMBIGUOUS")
    elif not people and r.identity_state == "CONFIRMED":
        errs.append(f"{where}: unknown phone cannot be CONFIRMED")
    if (
        r.intent == "delivery_slot_change"
        and r.status == "open"
        and r.facts.slot_datetime is None
        and ("time_unspecified" not in r.flags)
    ):
        errs.append(f"{where}: open slot change without a slot needs time_unspecified (SPEC v2.6)")
    if r.status == "handled" and not any(
        msgs[i].phone in staff and i > r.primary_msg_id for i in r.evidence_msg_ids if i in msgs
    ):
        errs.append(f"{where}: handled needs an aminobots_staff confirmation in evidence")
    if RULE_GRADE[r.rule_id] != r.grade:
        errs.append(f"{where}: {r.rule_id} gives {RULE_GRADE[r.rule_id]}, not {r.grade}")
    now = max(m.ts for m in msgs.values())
    if (r.grade, r.rule_id) != (exp := expected_grade(r, now)):
        errs.append(f"{where}: labelled {r.grade}/{r.rule_id}, SPEC §9 gives {exp[0]}/{exp[1]}")
    return errs


def validate(dev: Path = DEV, world: Path = WORLD) -> list[str]:
    errs: list[str] = []
    roster = Roster.model_validate(yaml.safe_load((world / "roster.yaml").read_text()))
    contacts = world / "contacts.yaml"
    staff = {to_e164(c.phone) for c in roster.contacts if c.role == "aminobots_staff"}
    for f in (world / "roster.yaml", contacts):
        errs += phone_errors(f.read_text(encoding="utf-8"), f.name)
    for txt in sorted(dev.glob("*.txt")):
        errs += phone_errors(txt.read_text(encoding="utf-8"), txt.name)
        gold_path = txt.with_suffix(".gold.json")
        if not gold_path.exists():
            errs.append(f"{txt.name}: missing {gold_path.name}")
            continue
        gold = GoldChat.model_validate(json.loads(gold_path.read_text(encoding="utf-8")))
        msgs = {m.id: m for m in parse_chat(txt, contacts)}
        for r in gold.requests + gold.internal_requests:
            errs += check_request(r, msgs, roster, staff, f"{gold.chat_id}/{r.id}")
        errs += [f"{gold.chat_id}/{r.id}: internal request listed as a partner request"
                 for r in gold.requests if r.requester_phone in staff]  # fmt: skip
        errs += [f"{gold.chat_id}/{r.id}: internal request not from aminobots_staff"
                 for r in gold.internal_requests if r.requester_phone not in staff]  # fmt: skip
    return errs


if __name__ == "__main__":
    problems = validate()
    print("\n".join(problems) or "gold OK")
    sys.exit(1 if problems else 0)
