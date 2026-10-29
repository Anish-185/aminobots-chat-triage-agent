"""Phase 4 free-model bake-off on dev chats, strict mode (no fallback). Dev data only.

Run: uv run python -m eval.bakeoff --models <id> [<id> ...] --chats d01 ... --max-requests N
Each model stops at its first 429 / unavailable error; cached responses cost no requests, so a
re-run resumes. Results hold message IDs and labels only, never chat text.
Over ~150 lines: one-off Phase 4 runner plus its report table; Phase 5's run_eval replaces it.
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import diskcache
import numpy as np
import yaml

from eval.metrics import detection, match
from triage import llm
from triage.config import load_models, load_pricing, load_thresholds
from triage.extract import ExtractionFailed, extract, load_prompt, user_message
from triage.ground import ground
from triage.parse import parse_chat, to_e164
from triage.schemas import GoldChat, Roster

ROOT = Path(__file__).resolve().parent.parent
DEV, WORLD = ROOT / "data" / "dev", ROOT / "data" / "world"
OUT = ROOT / "eval" / "results" / "bakeoff-v1"


def run_model(model_id: str, chats: list[str], budget: list[int]) -> dict:
    models = load_models()
    cand = next(c for c in models.candidates if c.id == model_id)
    meta, _ = load_prompt(1)
    version = f"{meta['id']}/v{meta['version']}"
    roster = Roster.model_validate(yaml.safe_load((WORLD / "roster.yaml").read_text()))
    staff = {to_e164(c.phone) for c in roster.contacts if c.role == "aminobots_staff"}
    min_j = load_thresholds().evidence_jaccard
    cache = diskcache.Cache(llm.CACHE_DIR)
    rows, pairs, stopped, spent = [], [], None, 0
    for chat in chats:
        msgs = parse_chat(DEV / f"{chat}.txt", WORLD / "contacts.yaml")
        gold = GoldChat.model_validate_json((DEV / f"{chat}.gold.json").read_text())
        cached = llm.cache_key(cand.id, version, user_message(msgs)) in cache
        if not cached and budget[0] < 2:  # one call can take 2 requests (repair retry)
            stopped = f"request budget exhausted before {chat}"
            break
        row: dict = {"chat": chat, "n_gold": len(gold.requests)}
        try:
            result, info = extract(msgs, cand, models.roles.extractor.temperature, cache=cache)
        except (llm.RateLimited, llm.ModelUnavailable) as exc:
            budget[0] -= exc.requests
            spent += exc.requests
            stopped = f"{type(exc).__name__} at {chat}: {exc}"
            break
        except ExtractionFailed as exc:
            cause = exc.__cause__
            budget[0] -= getattr(cause, "requests", 0)
            spent += getattr(cause, "requests", 0)
            row |= {"error": str(exc)[:300], "requests": getattr(cause, "requests", 0),
                    "schema_failures": getattr(cause, "schema_failures", 0)}  # fmt: skip
            pairs.append(([], gold.requests))  # fail closed: a failed chat predicts nothing
            rows.append(row)
            continue
        budget[0] -= info.requests
        spent += info.requests
        kept, rejected = ground(result, msgs)
        by_id = {m.id: m for m in msgs}
        # A6: requests from Aminobots staff are internal, not scored (roster lookup in code).
        partner = [c for c in kept if by_id[c.primary_msg_id].phone not in staff]
        pairs.append((partner, gold.requests))
        row |= {
            **{k: v for k, v in info.__dict__.items() if k != "errors"},
            "n_pred": len(partner),
            "n_internal": len(kept) - len(partner),
            "n_rejected": len(rejected),
            "predictions": [
                c.model_dump(
                    include={
                        "intent",
                        "primary_msg_id",
                        "evidence_msg_ids",
                        "status",
                        "flags",
                        "refers_to_msg_id",
                    }
                )
                | {
                    "slot_datetime": c.entities.slot_datetime
                    and c.entities.slot_datetime.isoformat()
                }
                for c in partner
            ],  # fmt: skip
        }
        rows.append(row)
    done = [r for r in rows if "error" not in r]
    lat = [r["latency_s"] for r in done if r.get("latency_s") is not None]
    return {
        "model": model_id,
        "prompt": version,
        "chats_attempted": len(rows),
        "chats_planned": len(chats),
        "stopped": stopped,
        "metrics": detection(pairs, min_j) if pairs else None,  # None: no chat attempted
        "schema_failures": sum(r.get("schema_failures", 0) for r in rows),
        "failed_chats": [r["chat"] for r in rows if "error" in r],
        "latency_p50_s": float(np.percentile(lat, 50)) if lat else None,
        "latency_p95_s": float(np.percentile(lat, 95)) if lat else None,
        "prompt_tokens": sum(r.get("prompt_tokens") or 0 for r in done),
        "completion_tokens": sum(r.get("completion_tokens") or 0 for r in done),
        "requests_this_run": spent,
        "chats": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--chats", nargs="+", required=True)
    ap.add_argument("--max-requests", type=int, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    budget = [args.max_requests]
    results = [run_model(m, args.chats, budget) for m in args.models]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    report = write_report(results)
    (args.out / "report.md").write_text(report)
    print(report)


def slot_accuracy(r: dict) -> tuple[int, int]:
    """Matched slot changes whose gold slot is known: (predicted slot_datetime equal, total)."""
    ok = total = 0
    min_j = load_thresholds().evidence_jaccard
    for row in r["chats"]:
        if "predictions" not in row:
            continue
        gold = GoldChat.model_validate_json((DEV / f"{row['chat']}.gold.json").read_text())
        preds = [SimpleNamespace(**p) for p in row["predictions"]]
        for i, j, _ in match(preds, gold.requests, min_j):
            if (want := gold.requests[j].facts.slot_datetime) is not None:
                total += 1
                ok += preds[i].slot_datetime == want.isoformat()
    return ok, total


def write_report(results: list[dict]) -> str:
    prices = load_pricing().models
    f = lambda v: "–" if v is None else f"{v:.2f}"  # noqa: E731
    lines = [
        "# Bake-off v1 (Phase 4, strict mode, prompt extract/v1, dev chats only)",
        "",
        "| Model | Chats | P | R | F1 | Intent acc | Evidence J | Slot datetime | Schema "
        "failures | Latency p50 / p95 (s) | Tokens in / out | Notional $ | Requests |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        m, (ok, n), price = r["metrics"] or {}, slot_accuracy(r), prices[r["model"]]
        cost = (r["prompt_tokens"] * price.input + r["completion_tokens"] * price.output) / 1e6
        lines.append(
            f"| `{r['model']}` | {r['chats_attempted']}/{r['chats_planned']}"
            f" | {f(m.get('precision'))} | {f(m.get('recall'))} | {f(m.get('f1'))}"
            f" | {f(m.get('intent_accuracy'))} | {f(m.get('evidence_jaccard'))} | {ok}/{n}"
            f" | {r['schema_failures']}"
            f" | {f(r['latency_p50_s'])} / {f(r['latency_p95_s'])}"
            f" | {r['prompt_tokens']} / {r['completion_tokens']} | {cost:.4f}"
            f" | {r['requests_this_run']} |"
        )
    lines += ["", "TP / predicted / gold: " + ", ".join(
        f"{r['model']} {r['metrics']['tp']}/{r['metrics']['n_pred']}/{r['metrics']['n_gold']}"
        for r in results if r["metrics"])]  # fmt: skip
    lines += [f"Stopped early: {r['model']}: {r['stopped']}" for r in results if r["stopped"]]
    lines += [
        f"Failed chats: {r['model']}: {r['failed_chats']}" for r in results if r["failed_chats"]
    ]
    lines += [
        "",
        "Request counts exclude cached responses (cost 0). Billed cost is $0 (free models);",
        "notional $ uses the paid variant's list price (config/pricing.yaml).",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
