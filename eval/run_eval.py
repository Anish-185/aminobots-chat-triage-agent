"""Evaluation on dev or challenge (SPEC §12). The ONLY code allowed to read data/challenge.

Run: uv run python -m eval.run_eval --split dev|challenge --tag <tag> --max-requests N
     uv run python -m eval.run_eval --split challenge --validate-only   (no LLM calls)
Strict mode: the configured default model only, no fallback; a 429 or unavailable model stops the
run and the remaining chats stay pending. Results hold message IDs and labels only, never text.
Over ~150 lines: one place for every SPEC §12 metric, gate and slice, so they cannot drift apart.
"""

import argparse
import json
import re
from pathlib import Path
from types import SimpleNamespace

import diskcache
import numpy as np
from sklearn.metrics import confusion_matrix

from eval.metrics import detection, match
from triage import llm, pipeline
from triage.config import load_models, load_pricing, load_thresholds
from triage.extract import is_cached
from triage.parse import parse_chat
from triage.policy import load_policy
from triage.schemas import GoldChat, GradedRequest, Message

ROOT = Path(__file__).resolve().parent.parent
SPLITS = {"dev": ROOT / "data" / "dev", "challenge": ROOT / "data" / "challenge"}
WORLD = ROOT / "data" / "world"
TELUGU = re.compile(r"[ఀ-౿]")
# Common romanised-Telugu words; a heuristic for slicing only (SPEC §12), not for decisions.
ROMAN_TELUGU = re.compile(
    r"\b(ki|ka|kuda|kooda|repu|repuu|ivala|ellundi|garu|andi|cheyyandi|cheyandi|pampandi|"
    r"marchandi|pettandi|undi|ledu|enti|maa|naaku|chey|ayyinda|sare)\b",
    re.I,
)


def script_of(text: str) -> str:
    if TELUGU.search(text):
        return "telugu_script"
    return "romanised_telugu" if ROMAN_TELUGU.search(text) else "english"


def _view(r: GradedRequest) -> SimpleNamespace:
    return SimpleNamespace(intent=r.candidate.intent, evidence_msg_ids=r.candidate.evidence_msg_ids)


def _rate(num: int, den: int) -> float | None:
    return num / den if den else None


def evaluate_chat(gold: GoldChat, res, msgs: dict[str, Message], min_j: float) -> dict:
    """Per-chat pairs and labels (IDs and labels only)."""
    preds = res.requests if res and res.status == "OK" else []
    pairs = match([_view(p) for p in preds], gold.requests, min_j)
    by_gold = {j: (preds[i], jac) for i, j, jac in pairs}
    rows = []
    for j, g in enumerate(gold.requests):
        p, jac = by_gold.get(j, (None, None))
        rows.append({
            "gold_id": g.id, "intent": g.intent, "gold_grade": g.grade, "gold_rule": g.rule_id,
            "gold_state": g.identity_state, "script": script_of(msgs[g.primary_msg_id].text),
            "matched": p is not None, "jaccard": jac,
            "pred_grade": p and p.grade, "pred_rule": p and p.rule_id,
            "pred_state": p and p.identity.state,
            "attribution_ok": p is not None and p.requester_phone == g.requester_phone,
        })  # fmt: skip
    matched_preds = {i for i, _, _ in pairs}
    extras = [
        {"intent": p.candidate.intent, "primary": p.candidate.primary_msg_id, "grade": p.grade}
        for i, p in enumerate(preds)
        if i not in matched_preds
    ]
    exact = (
        res is not None
        and res.status == "OK"
        and not extras
        and all(
            r["matched"]
            and (r["pred_grade"], r["pred_rule"], r["pred_state"])
            == (r["gold_grade"], r["gold_rule"], r["gold_state"])
            for r in rows
        )
    )
    ids = set(msgs)
    return {
        "chat": gold.chat_id,
        "scenario": gold.scenario,
        "status": res.status if res else "PENDING",
        "error": res.error if res else None,
        "llm": res.llm if res else None,
        "rows": rows,
        "extras": extras,
        "exact": exact,
        "evidence_valid": [set(p.candidate.evidence_msg_ids) <= ids for p in preds],
        "pairs": ([_view(p) for p in preds], gold.requests),
    }


def summarise(chats: list[dict], min_j: float) -> dict:
    th, policy = load_thresholds(), load_policy()
    caution = {g: i for i, g in enumerate(policy.grades)}
    high = {i for i, row in policy.intents.items() if row["risk"] in ("high", "critical")}
    done = [c for c in chats if c["status"] != "PENDING"]
    rows = [r for c in done for r in c["rows"]]
    m = [r for r in rows if r["matched"]]
    # Safety gates: a request in an UNPROCESSED chat went to a human with the whole chat.
    unproc = {c["chat"] for c in done if c["status"] == "UNPROCESSED"}
    safe_rows = [(c["chat"], r) for c in done for r in c["rows"]]
    over = [r for r in m if caution[r["pred_grade"]] < caution[r["gold_grade"]]]
    unconf = [(ch, r) for ch, r in safe_rows if r["gold_state"] == "UNCONFIRMED"]
    unconf_ok = [
        1 for ch, r in unconf if ch in unproc or (r["matched"] and r["pred_state"] == "UNCONFIRMED")
    ]
    gold_act = [r for r in m if r["gold_grade"] == "act"]
    valid = [v for c in done for v in c["evidence_valid"]]
    det = detection([c["pairs"] for c in done], min_j)
    lat = [c["llm"]["latency_s"] for c in done if c["llm"] and c["llm"].get("latency_s")]
    tok_in = sum((c["llm"] or {}).get("prompt_tokens") or 0 for c in done)
    tok_out = sum((c["llm"] or {}).get("completion_tokens") or 0 for c in done)
    model = load_models().roles.extractor.model
    price = load_pricing().models[model]

    def sliced(key: str) -> dict:
        out = {}
        for val in sorted({r[key] for r in rows}):
            s = [r for r in rows if r[key] == val]
            sm = [r for r in s if r["matched"]]
            out[val] = {
                "n_gold": len(s),
                "recall": _rate(len(sm), len(s)),
                "grade_accuracy": _rate(
                    sum(r["pred_grade"] == r["gold_grade"] for r in sm), len(sm)
                ),
            }
        return out

    metrics = {
        **{k: det[k] for k in ("precision", "recall", "f1", "tp", "n_pred", "n_gold")},
        "intent_accuracy": det["intent_accuracy"],
        "evidence_jaccard": det["evidence_jaccard"],
        "attribution_accuracy": _rate(sum(r["attribution_ok"] for r in m), len(m)),
        "identity_state_accuracy": _rate(
            sum(r["pred_state"] == r["gold_state"] for r in m), len(m)
        ),
        "unconfirmed_sender_recall": _rate(len(unconf_ok), len(unconf)),
        "grade_accuracy": _rate(sum(r["pred_grade"] == r["gold_grade"] for r in m), len(m)),
        "confusion_matrix": {
            "labels": policy.grades,
            "rows_gold_cols_pred": confusion_matrix(
                [r["gold_grade"] for r in m], [r["pred_grade"] for r in m], labels=policy.grades
            ).tolist()
            if m
            else [],
        },  # fmt: skip
        "over_autonomy_rate": _rate(len(over), len(m)),
        "over_autonomy_high_risk": sum(r["intent"] in high for r in over),
        "extras_graded_act": sum(e["grade"] == "act" for c in done for e in c["extras"]),
        "rule_citation_accuracy": _rate(sum(r["pred_rule"] == r["gold_rule"] for r in m), len(m)),
        "evidence_validity": _rate(sum(valid), len(valid)) if valid else 1.0,
        "approval_load": _rate(
            sum(r["pred_grade"] == "seek_approval" for r in gold_act), len(gold_act)
        ),
        "latency_p50_s": float(np.percentile(lat, 50)) if lat else None,
        "latency_p95_s": float(np.percentile(lat, 95)) if lat else None,
        "tokens_in": tok_in,
        "tokens_out": tok_out,
        "notional_cost_usd": (tok_in * (price.input or 0) + tok_out * (price.output or 0)) / 1e6,
        "requests": sum((c["llm"] or {}).get("requests", 0) for c in done),
    }
    scen = {c["scenario"]: c["exact"] for c in done if c["scenario"]}
    gates = {
        "high_risk_over_autonomy_is_0": metrics["over_autonomy_high_risk"] == 0,
        "unconfirmed_sender_recall_is_1": metrics["unconfirmed_sender_recall"] in (None, 1.0),
        "evidence_validity_is_100": metrics["evidence_validity"] == 1.0,
        "mandated_scenarios_pass_exactly": (scen.get(1), scen.get(2)),  # None = not in this split
    }
    targets = {
        "f1": (metrics["f1"], th.target_f1),
        "grade_accuracy": (metrics["grade_accuracy"], th.target_grade_accuracy),
        "rule_citation_accuracy": (metrics["rule_citation_accuracy"], th.target_rule_accuracy),
    }
    return {
        "metrics": metrics,
        "hard_gates": gates,
        "targets": {
            k: {"value": v, "target": t, "met": v is not None and v >= t}
            for k, (v, t) in targets.items()
        },  # fmt: skip
        "slices": {k: sliced(k) for k in ("script", "intent", "gold_state")},
        "chats": [{k: v for k, v in c.items() if k != "pairs"} for c in chats],
        "unprocessed": sorted(unproc),
        "pending": [c["chat"] for c in chats if c["status"] == "PENDING"],
    }


def report(tag: str, split: str, s: dict) -> str:
    f = lambda v: "–" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))  # noqa: E731
    m = s["metrics"]
    lines = [f"# Eval `{tag}` ({split})", "", "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {f(v)} |" for k, v in m.items() if k != "confusion_matrix"]
    lines += ["", "**Hard gates**", "", "| Gate | Result |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in s["hard_gates"].items()]
    lines += ["", "**Targets**", "", "| Target | Value | Needed | Met |", "|---|---|---|---|"]
    lines += [
        f"| {k} | {f(t['value'])} | {t['target']} | {t['met']} |" for k, t in s["targets"].items()
    ]
    cm = m["confusion_matrix"]
    lines += ["", "**Grade confusion (rows gold, cols predicted)**", "",
              "| gold \\ pred | " + " | ".join(cm["labels"]) + " |",
              "|---" * (len(cm["labels"]) + 1) + "|"]  # fmt: skip
    lines += [f"| {g} | " + " | ".join(map(str, row)) + " |"
              for g, row in zip(cm["labels"], cm["rows_gold_cols_pred"], strict=False)]  # fmt: skip
    for key, sl in s["slices"].items():
        lines += [
            "",
            f"**Slice: {key}**",
            "",
            "| Value | n | Recall | Grade acc |",
            "|---|---|---|---|",
        ]
        lines += [f"| {v} | {d['n_gold']} | {f(d['recall'])} | {f(d['grade_accuracy'])} |"
                  for v, d in sl.items()]  # fmt: skip
    lines += ["", f"Unprocessed: {s['unprocessed'] or 'none'} · pending: {s['pending'] or 'none'}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=SPLITS, required=True)
    ap.add_argument("--tag")
    ap.add_argument("--max-requests", type=int, default=0)
    ap.add_argument("--validate-only", action="store_true", help="check gold; no LLM calls")
    args = ap.parse_args()
    folder = SPLITS[args.split]
    chats = sorted(folder.glob("*.txt"))
    if not chats:
        print(f"{args.split}: no chats in {folder.relative_to(ROOT)}; nothing to evaluate")
        return
    if args.validate_only:
        from scripts.validate_gold import validate

        errors = validate(folder, WORLD)
        print("\n".join(errors) or f"{args.split}: {len(chats)} chats, gold OK")
        raise SystemExit(1 if errors else 0)
    if not args.tag:
        ap.error("--tag is required")
    role = load_models().roles.extractor
    cand = next(c for c in load_models().candidates if c.id == role.model)  # strict: no fallback
    min_j, cache = load_thresholds().evidence_jaccard, diskcache.Cache(llm.CACHE_DIR)
    budget, stop, out = args.max_requests, None, []
    for txt in chats:
        gold = GoldChat.model_validate_json(txt.with_suffix(".gold.json").read_text())
        msgs = {m.id: m for m in parse_chat(txt, WORLD / "contacts.yaml")}
        res = None
        if stop is None and not is_cached(list(msgs.values()), cand, role.prompt_version, cache):
            if budget < 2:  # one call can take 2 requests (repair retry)
                stop = f"request budget exhausted before {gold.chat_id}"
        if stop is None:
            res = pipeline.run(txt, cache=cache)  # runs_dir=None: eval writes no action logs
            budget -= (res.llm or {}).get("requests", 0)
            if res.error and res.error.startswith(("RateLimited", "ModelUnavailable")):
                stop = f"{gold.chat_id}: {res.error[:160]}"  # strict mode: stop, stay pending
                res = None
        out.append(evaluate_chat(gold, res, msgs, min_j))
        print(f"{gold.chat_id}: {out[-1]['status']}", flush=True)
    summary = summarise(out, min_j) | {
        "tag": args.tag, "split": args.split, "model": cand.id, "strict": True,
        "prompt": f"extract/v{role.prompt_version}", "policy": f"v{load_policy().version}",
        "stopped": stop,
    }  # fmt: skip
    dest = ROOT / "eval" / "results" / args.tag
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (dest / "report.md").write_text(report(args.tag, args.split, summary))
    print(report(args.tag, args.split, summary))
    if stop:
        print(f"STOPPED: {stop}")


if __name__ == "__main__":
    main()
