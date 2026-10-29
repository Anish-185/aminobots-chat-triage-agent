"""Eval maths offline: perfect predictions score 1.0 and pass the gates; errors are counted."""

from pathlib import Path
from types import SimpleNamespace

from eval.run_eval import evaluate_chat, script_of, summarise
from triage.parse import parse_chat
from triage.schemas import Candidate, GoldChat, GradedRequest, Identity

ROOT = Path(__file__).resolve().parent.parent
DEV, WORLD = ROOT / "data" / "dev", ROOT / "data" / "world"


def _load(chat: str):
    gold = GoldChat.model_validate_json((DEV / f"{chat}.gold.json").read_text())
    msgs = {m.id: m for m in parse_chat(DEV / f"{chat}.txt", WORLD / "contacts.yaml")}
    return gold, msgs


def _as_pred(g, grade=None) -> GradedRequest:
    return GradedRequest(
        request_id=g.id,
        candidate=Candidate(
            intent=g.intent,
            gloss="",
            primary_msg_id=g.primary_msg_id,
            evidence_msg_ids=g.evidence_msg_ids,
            status=g.status,
        ),
        requester_phone=g.requester_phone,
        requester_name=None,
        identity=Identity(state=g.identity_state, reason="r"),
        grade=grade or g.grade,
        rule_id=g.rule_id,
        matched_rules=[g.rule_id],
        rule_checks=[],
    )


def _res(preds, status="OK"):
    llm = {"requests": 1, "latency_s": 2.0, "prompt_tokens": 10, "completion_tokens": 5}
    return SimpleNamespace(status=status, requests=preds, error=None, llm=llm)


def test_perfect_predictions_pass_everything():
    chats = []
    for c in ("d01", "d07", "d13"):
        gold, msgs = _load(c)
        chats.append(evaluate_chat(gold, _res([_as_pred(g) for g in gold.requests]), msgs, 0.5))
    s = summarise(chats, 0.5)
    m = s["metrics"]
    assert m["f1"] == m["grade_accuracy"] == m["rule_citation_accuracy"] == 1.0
    assert m["unconfirmed_sender_recall"] == 1.0 and m["over_autonomy_rate"] == 0.0
    gates = s["hard_gates"]
    assert gates["high_risk_over_autonomy_is_0"] and gates["evidence_validity_is_100"]
    assert all(c["exact"] for c in s["chats"])


def test_under_caution_is_over_autonomy_and_fails_gates():
    gold, msgs = _load("d07")  # unknown number, payout change: gold refuse/R2
    s = summarise([evaluate_chat(gold, _res([_as_pred(gold.requests[0], "act")]), msgs, 0.5)], 0.5)
    assert s["metrics"]["over_autonomy_high_risk"] == 1
    assert not s["hard_gates"]["high_risk_over_autonomy_is_0"]


def test_unprocessed_chat_counts_as_handed_off_for_safety_not_detection():
    gold, msgs = _load("d07")
    s = summarise([evaluate_chat(gold, _res([], status="UNPROCESSED"), msgs, 0.5)], 0.5)
    assert s["metrics"]["recall"] == 0.0
    assert s["metrics"]["unconfirmed_sender_recall"] == 1.0 and s["unprocessed"] == ["d07"]


def test_approval_load_counts_gold_act_graded_seek():
    gold, msgs = _load("d01")  # r3 is gold act/R9
    preds = [_as_pred(g, "seek_approval" if g.grade == "act" else None) for g in gold.requests]
    s = summarise([evaluate_chat(gold, _res(preds), msgs, 0.5)], 0.5)
    assert s["metrics"]["approval_load"] == 1.0


def test_results_hold_no_message_text():
    gold, msgs = _load("d01")
    s = summarise([evaluate_chat(gold, _res([_as_pred(g) for g in gold.requests]), msgs, 0.5)], 0.5)
    dump = str(s)
    assert all(m.text not in dump for m in msgs.values() if len(m.text) > 12)


def test_script_slices():
    assert script_of("మా ఆర్డర్") == "telugu_script"
    assert script_of("repu delivery 9 ki marchandi") == "romanised_telugu"
    assert script_of("Please send the invoice") == "english"


def test_only_run_eval_mentions_the_challenge_folder():
    hits = [
        p.relative_to(ROOT).as_posix()
        for d in ("triage", "eval", "scripts", "api", "site")
        for p in (ROOT / d).rglob("*.py")
        if '"challenge"' in p.read_text() or "data/challenge" in p.read_text()
    ]
    assert set(hits) <= {"eval/run_eval.py", "scripts/guard_eval_data.py"}, hits
