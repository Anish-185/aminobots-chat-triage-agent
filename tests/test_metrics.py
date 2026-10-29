from dataclasses import dataclass, field

import pytest

from eval.metrics import detection, jaccard, match


@dataclass
class R:
    intent: str
    evidence_msg_ids: list[str] = field(default_factory=list)


def test_jaccard():
    assert jaccard(["m1", "m2"], ["m2", "m3"]) == pytest.approx(1 / 3)
    assert jaccard([], []) == 0.0


def test_match_needs_same_intent_and_threshold():
    gold = [R("order_change", ["m1", "m2"])]
    assert match([R("refund_request", ["m1", "m2"])], gold, 0.5) == []
    assert match([R("order_change", ["m1", "m3", "m4"])], gold, 0.5) == []  # 1/4
    assert match([R("order_change", ["m1"])], gold, 0.5) == [(0, 0, 0.5)]


def test_hungarian_beats_greedy():
    # Greedy takes p0→g0 (1.0) and strands p1 (only g0 ≥ 0.5); the optimum (2/3 + 1/2) keeps both.
    pred = [R("other", ["m1", "m2"]), R("other", ["m1"])]
    gold = [R("other", ["m1", "m2"]), R("other", ["m1", "m2", "m3"])]
    assert {(i, j) for i, j, _ in match(pred, gold, 0.5)} == {(0, 1), (1, 0)}


def test_detection_scores():
    chats = [
        ([R("order_change", ["m1"]), R("other", ["m9"])], [R("order_change", ["m1", "m2"])]),
        ([], [R("complaint", ["m4"])]),
        ([R("refund_request", ["m5"])], [R("complaint", ["m5"])]),  # wrong intent, same evidence
    ]
    s = detection(chats, 0.5)
    assert (s["tp"], s["n_pred"], s["n_gold"]) == (1, 3, 3)
    assert s["precision"] == s["recall"] == s["f1"] == pytest.approx(1 / 3)
    assert s["intent_accuracy"] == pytest.approx(1 / 2)
    assert s["evidence_jaccard"] == pytest.approx(0.5)


def test_detection_nothing_for_nothing_is_perfect():
    s = detection([([], [])], 0.5)
    assert s["f1"] == 1.0 and s["intent_accuracy"] is None and s["evidence_jaccard"] is None
