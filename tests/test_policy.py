"""SPEC §9 worked checks, citation rules, and monotonicity (adding a rule never lowers caution)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from triage.policy import POLICY as POLICY_FILE
from triage.policy import POLICY_DIR, Rule, decide, load_policy

POLICY = load_policy()


def ctx(**kw) -> dict:
    """A CONFIRMED, authorised staff slot change 20 h ahead; override what a case changes."""
    intent = kw.pop("intent", "delivery_slot_change")
    row = POLICY.intents[intent]
    base = {
        "intent": intent,
        "risk": row["risk"],
        "discloses": row["discloses"],
        "sender_state": "CONFIRMED",
        "authorised": True,
        "on_behalf": False,
        "on_behalf_verified": False,
        "flags": [],
        "status": "open",
        "slot_hours_ahead": 20.0,
        "slot_cutoff_hours": 12.0,
    }
    return base | kw


UNKNOWN = {"sender_state": "UNCONFIRMED", "authorised": False}

WORKED = [  # SPEC §9 "Worked checks", in order
    ("scenario 2: unknown number, payout",
     ctx(intent="payout_details_change", **UNKNOWN), "refuse", "R2"),
    ("scenario 1: staff slot change ≥ 12 h", ctx(), "act", "R9"),
    ("follow-up 'maa outlet', 1 outlet", ctx(), "act", "R9"),
    ("follow-up, sender has 2 outlets", ctx(flags=["outlet_ambiguous"]), "seek_approval", "R6"),
    ("follow-up, sender unknown", ctx(**UNKNOWN), "seek_approval", "R4"),
    ("cancelled, CONFIRMED sender", ctx(status="cancelled"), "act", "R8"),
    ("cancelled payout, unknown number",
     ctx(intent="payout_details_change", status="cancelled", **UNKNOWN), "refuse", "R2"),
    ("CONFIRMED owner payout change", ctx(intent="payout_details_change"), "hand_off", "R1"),
    ("CONFIRMED staff, slot 6 h away", ctx(slot_hours_ahead=6.0), "seek_approval", "R7"),
    ("v2: cancelled slot change under 12 h, CONFIRMED staff",
     ctx(status="cancelled", slot_hours_ahead=6.0), "act", "R8"),
]  # fmt: skip


@pytest.mark.parametrize(("case", "context", "grade", "rule"), WORKED, ids=[w[0] for w in WORKED])
def test_spec_worked_checks(case, context, grade, rule):
    got_grade, got_rule, matched, checks = decide(context, POLICY)
    assert (got_grade, got_rule) == (grade, rule)
    assert rule in matched
    assert [c.rule_id for c in checks] == [f"R{i}" for i in range(1, 11)]


def test_scenario_2_records_r1_too():
    _, _, matched, _ = decide(ctx(intent="payout_details_change", **UNKNOWN), POLICY)
    assert {"R1", "R2"} <= set(matched)


def test_unknown_slot_time_never_triggers_r7_but_flag_does():
    assert decide(ctx(slot_hours_ahead=None), POLICY)[:2] == ("act", "R9")
    assert decide(ctx(slot_hours_ahead=None, flags=["time_unspecified"]), POLICY)[1] == "R6"


def test_cross_partner_on_behalf_unverified_is_r5():
    assert decide(ctx(intent="status_query", on_behalf=True), POLICY)[:2] == ("seek_approval", "R5")


def test_nothing_matched_is_default_r10():
    grade, rule, matched, checks = decide(ctx(), POLICY.model_copy(update={"rules": []}))
    assert (grade, rule, matched) == ("hand_off", "R10", ["R10"])
    assert checks[-1].matched


def test_policy_rejects_out_of_order_rules(tmp_path):
    bad = tmp_path / "p.yaml"
    bad.write_text(POLICY_FILE.read_text().replace("id: R1\n", "id: R9\n", 1))
    with pytest.raises(ValueError, match="ID order"):
        load_policy(bad)


contexts = st.builds(
    lambda intent, state, auth, ob, obv, flags, status, hours: ctx(
        intent=intent,
        sender_state=state,
        authorised=auth,
        on_behalf=ob,
        on_behalf_verified=obv,
        flags=flags,
        status=status,
        slot_hours_ahead=hours,
    ),
    st.sampled_from(sorted(POLICY.intents)),
    st.sampled_from(["CONFIRMED", "AMBIGUOUS", "UNCONFIRMED"]),
    st.booleans(),
    st.booleans(),
    st.booleans(),
    st.lists(st.sampled_from(["outlet_ambiguous", "injection_attempt"]), max_size=2),
    st.sampled_from(["open", "cancelled", "handled"]),
    st.one_of(st.none(), st.floats(-48, 96)),
)
extra_rules = st.builds(
    lambda grade, when: Rule(id="R9", grade=grade, text="extra", when=when),
    st.sampled_from(POLICY.grades),
    st.sampled_from(["true", "authorised", 'status == "open"', "flags.length > 0", "false"]),
)


@given(contexts, extra_rules)
def test_adding_a_rule_never_lowers_caution(context, extra):
    before = decide(context, POLICY)[0]
    widened = POLICY.model_copy(update={"rules": [*POLICY.rules, extra]})
    after = decide(context, widened)[0]
    assert POLICY.caution(after) >= POLICY.caution(before)


def test_config_selects_policy_v2():
    assert POLICY.version == 2 and POLICY_FILE.name == "policy_v2.yaml"


def test_v1_unchanged_and_v2_only_changes_r7_for_closed_requests():
    v1 = load_policy(POLICY_DIR / "policy_v1.yaml")
    assert v1.version == 1
    closed_slot = ctx(status="cancelled", slot_hours_ahead=6.0)
    closed_order = ctx(intent="order_change", status="cancelled")
    assert decide(closed_slot, v1)[:2] == ("seek_approval", "R7")
    assert decide(closed_order, v1)[:2] == ("seek_approval", "R7")
    assert decide(closed_order, POLICY)[:2] == ("act", "R8")
    assert decide(ctx(intent="order_change"), POLICY)[:2] == ("seek_approval", "R7")  # open: kept
    assert [r.id for r in v1.rules] == [r.id for r in POLICY.rules]
    changed = [a.id for a, b in zip(v1.rules, POLICY.rules, strict=True) if a != b]
    assert changed == ["R7"]
