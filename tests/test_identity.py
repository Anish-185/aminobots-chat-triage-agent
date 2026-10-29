"""Identity against every dev gold label, plus the SPEC §7 special cases on real dev chats."""

from pathlib import Path
from typing import get_args

import pytest
import yaml

from triage.config import load_thresholds
from triage.identity import identify
from triage.parse import parse_chat
from triage.policy import load_policy
from triage.schemas import Candidate, GoldChat, Role, Roster

ROOT = Path(__file__).resolve().parent.parent
DEV, WORLD = ROOT / "data" / "dev", ROOT / "data" / "world"
ROSTER = Roster.model_validate(yaml.safe_load((WORLD / "roster.yaml").read_text()))
POLICY, TH = load_policy(), load_thresholds()


def _msgs(chat: str):
    return parse_chat(DEV / f"{chat}.txt", WORLD / "contacts.yaml")


def _identify(chat: str, primary: str, intent: str = "delivery_slot_change", **entities_or_ob):
    on_behalf = entities_or_ob.pop("on_behalf_of", None)
    c = Candidate(
        intent=intent,
        gloss="g",
        primary_msg_id=primary,
        evidence_msg_ids=[primary],
        on_behalf_of=on_behalf,
        entities=entities_or_ob,
    )
    allowed = set(POLICY.intents[intent]["roles"] or get_args(Role))
    return identify(c, _msgs(chat), ROSTER, allowed, TH.name_match)


GOLD = [
    (g.chat_id, r, internal)
    for p in sorted(DEV.glob("*.gold.json"))
    for g in [GoldChat.model_validate_json(p.read_text())]
    for internal, reqs in ((False, g.requests), (True, g.internal_requests))
    for r in reqs
]


@pytest.mark.parametrize(("chat", "r", "internal"), GOLD, ids=[f"{c}-{r.id}" for c, r, _ in GOLD])
def test_matches_gold_state_authority_and_internal(chat, r, internal):
    ident, _, is_internal = _identify(chat, r.primary_msg_id, r.intent)
    assert ident.state == r.identity_state, ident.reason
    assert is_internal == internal
    if ident.state != "UNCONFIRMED":
        assert ident.authorised == r.facts.authorised
    assert ident.reason


def test_vouching_and_self_claim_never_confirm():
    ident, _, _ = _identify("d07", "m005", "payout_details_change")
    assert ident.state == "UNCONFIRMED" and "never confirm" in ident.reason


def test_security_code_change_downgrades():
    ident, _, _ = _identify("d04", "m004", "invoice_request")
    assert ident.state == "UNCONFIRMED" and "security code" in ident.reason


def test_two_outlet_owner_saying_maa_shop_is_outlet_ambiguous():
    ident, flags, _ = _identify("d01", "m016", outlet="Maa shop")
    assert flags == ["outlet_ambiguous"] and ident.target_outlets == ["O1", "O2"]


def test_single_outlet_manager_maa_outlet_resolves():
    ident, flags, _ = _identify("d02", "m007", outlet="Maa outlet")
    assert flags == [] and ident.target_outlets == ["O1"]


def test_named_outlet_resolves_even_for_two_outlet_owner():
    ident, flags, _ = _identify("d01", "m011", outlet="Kukatpally")
    assert flags == [] and ident.target_outlets == ["O2"]


def test_delegate_on_behalf_is_verified():
    ident, _, _ = _identify("d09", "m006", on_behalf_of="Vani madam")
    assert ident.on_behalf and ident.on_behalf_verified


def test_non_delegate_on_behalf_is_not_verified():
    ident, _, _ = _identify("d09", "m013", on_behalf_of="Vani madam")
    assert ident.on_behalf and not ident.on_behalf_verified


def test_cross_partner_outlet_is_unverified_on_behalf():
    ident, _, _ = _identify("d08", "m031", "status_query", outlet="Sunrise Kukatpally outlet")
    assert ident.on_behalf and not ident.on_behalf_verified
    assert ident.authorised and "another partner" in ident.reason


def test_shared_phone_is_ambiguous_and_authorised_only_if_all_are():
    slot, _, _ = _identify("d05", "m006")
    refund, _, _ = _identify("d05", "m006", "refund_request")  # staff may not refund
    assert slot.state == refund.state == "AMBIGUOUS"
    assert slot.authorised and not refund.authorised
