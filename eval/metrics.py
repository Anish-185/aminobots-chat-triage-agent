"""Predicted ↔ gold matching and detection metrics (SPEC §12).

A pair matches when the intents agree and the evidence Jaccard is at least the threshold; pairs
are assigned one-to-one with the Hungarian algorithm (scipy), maximising total Jaccard.
Intent accuracy uses an evidence-only matching, since the full matching already fixes intent.
"""

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from scipy.optimize import linear_sum_assignment


class Request(Protocol):  # Candidate and GoldRequest both fit
    intent: str
    evidence_msg_ids: list[str]


def jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def match(
    pred: Sequence[Request],
    gold: Sequence[Request],
    min_jaccard: float,
    same_intent: bool = True,
) -> list[tuple[int, int, float]]:
    """(pred index, gold index, Jaccard) for each matched pair."""
    if not pred or not gold:
        return []
    score = np.zeros((len(pred), len(gold)))
    for i, p in enumerate(pred):
        for j, g in enumerate(gold):
            jac = jaccard(p.evidence_msg_ids, g.evidence_msg_ids)
            if jac >= min_jaccard and (not same_intent or p.intent == g.intent):
                score[i, j] = jac
    rows, cols = linear_sum_assignment(score, maximize=True)
    return [
        (int(i), int(j), float(score[i, j]))
        for i, j in zip(rows, cols, strict=True)
        if score[i, j] > 0
    ]


def _ratio(num: int, den: int, empty: float | None) -> float | None:
    return num / den if den else empty


def detection(
    chats: Sequence[tuple[Sequence[Request], Sequence[Request]]], min_jaccard: float
) -> dict:
    """Micro-averaged over (predicted, gold) pairs of chats."""
    tp = n_pred = n_gold = intent_pairs = intent_ok = 0
    jaccards: list[float] = []
    for pred, gold in chats:
        pairs = match(pred, gold, min_jaccard)
        tp, n_pred, n_gold = tp + len(pairs), n_pred + len(pred), n_gold + len(gold)
        jaccards += [jac for _, _, jac in pairs]
        loose = match(pred, gold, min_jaccard, same_intent=False)
        intent_pairs += len(loose)
        intent_ok += sum(pred[i].intent == gold[j].intent for i, j, _ in loose)
    nothing = 1.0 if n_pred == n_gold == 0 else 0.0  # predicting nothing for nothing is perfect
    p, r = _ratio(tp, n_pred, nothing), _ratio(tp, n_gold, nothing)
    return {
        "tp": tp,
        "n_pred": n_pred,
        "n_gold": n_gold,
        "precision": p,
        "recall": r,
        "f1": 2 * p * r / (p + r) if p + r else 0.0,
        "intent_accuracy": _ratio(intent_ok, intent_pairs, None),
        "evidence_jaccard": float(np.mean(jaccards)) if jaccards else None,
    }
