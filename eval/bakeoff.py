"""Phase 4 free-model bake-off on dev chats, strict mode (no fallback). Dev data only.

Run: uv run python -m eval.bakeoff --models <id> [<id> ...] --chats d01 ... --max-requests N
Each model stops at its first 429 / unavailable error; cached responses cost no requests, so a
re-run resumes. Results hold message IDs and labels only, never chat text.
"""

import argparse
import json
from pathlib import Path

import diskcache
import numpy as np
import yaml

from eval.metrics import detection
from triage import llm
from triage.config import load_models, load_thresholds
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
    rows, pairs, stopped = [], [], None
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
            stopped = f"{type(exc).__name__} at {chat}: {exc}"
            break
        except ExtractionFailed as exc:
            cause = exc.__cause__
            budget[0] -= getattr(cause, "requests", 0)
            row |= {"error": str(exc)[:300], "requests": getattr(cause, "requests", 0),
                    "schema_failures": getattr(cause, "schema_failures", 0)}  # fmt: skip
            pairs.append(([], gold.requests))  # fail closed: a failed chat predicts nothing
            rows.append(row)
            continue
        budget[0] -= info.requests
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
        "metrics": detection(pairs, min_j),
        "schema_failures": sum(r.get("schema_failures", 0) for r in rows),
        "failed_chats": [r["chat"] for r in rows if "error" in r],
        "latency_p50_s": float(np.percentile(lat, 50)) if lat else None,
        "latency_p95_s": float(np.percentile(lat, 95)) if lat else None,
        "prompt_tokens": sum(r.get("prompt_tokens") or 0 for r in done),
        "completion_tokens": sum(r.get("completion_tokens") or 0 for r in done),
        "requests_this_run": sum(r.get("requests", 0) for r in rows),
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
    for r in results:
        m = r["metrics"]
        print(
            f"{r['model']}: chats {r['chats_attempted']}/{r['chats_planned']} "
            f"P={m['precision']} R={m['recall']} F1={m['f1']} intent={m['intent_accuracy']} "
            f"jac={m['evidence_jaccard']} schema_fail={r['schema_failures']} "
            f"p50={r['latency_p50_s']} p95={r['latency_p95_s']} "
            f"tok={r['prompt_tokens']}+{r['completion_tokens']} "
            f"requests={r['requests_this_run']} stopped={r['stopped']}"
        )


if __name__ == "__main__":
    main()
