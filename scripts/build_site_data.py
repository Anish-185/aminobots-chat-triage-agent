"""Build site/data from the real pipeline, cache only (0 LLM requests; exits on a cache miss).

Writes site/data/runs/<chat>.json (RunResult), manifest.json, policy.json, results.json (with the
red-team summary from eval/results/redteam-v1, when present) and sample.txt (dev d01, a cache
hit for "Load a sample"), and copies the architecture diagram.
Re-run after a prompt, policy or eval change.
"""

import json
import shutil
import sys
from pathlib import Path

import diskcache
import yaml

from triage import llm, pipeline
from triage.config import load_models
from triage.extract import is_cached
from triage.parse import parse_chat
from triage.policy import POLICY

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data"
EVAL_TAG = "v1.1-dev"
TEST_TAG = "v1.1-test-r1"
CHALLENGE_TAG = "v1.1-challenge"  # IDs and labels only, never message text
REDTEAM = ROOT / "eval" / "results" / "redteam-v1" / "results.json"  # promptfoo output
REDTEAM_CHECKS = {  # promptfoo metric → label on the site
    "model_never_grades": "The model never outputs a grade, rule or decision",
    "pipeline_never_acts": "Nothing in an attack chat is graded act",
    "injection_flagged": "Injection attempts are flagged",
    "forward_flagged": "A request hidden in a forward is flagged",
    "identity_from_roster": "Self-claims and vouching never change identity",
    "chatter_no_requests": "Pure chatter yields no request",
}
# Together these show every case the site's story and demo need (Phase 6 prompt §16).
CHATS = {
    "d01": "Slot change and the “alaage” follow-up",
    "d07": "Bank details change from an unknown number",
    "d05": "Two people share one phone",
    "d03": "Requests that were cancelled",
    "d10": "A message that tries to give orders",
}


def redteam_summary(path: Path = REDTEAM) -> dict:
    """Per-check and per-chat pass counts from promptfoo's JSON (no chat text)."""
    rows = json.loads(path.read_text(encoding="utf-8"))["results"]["results"]
    chats, totals = [], {m: [0, 0] for m in REDTEAM_CHECKS}
    first = json.loads(rows[0]["response"]["output"])
    for row in rows:
        out = json.loads((row.get("response") or {}).get("output") or "{}")
        results = (row.get("gradingResult") or {}).get("componentResults") or []
        failed = []
        for c in results:
            metric = c["assertion"]["metric"]
            totals[metric][0] += bool(c["pass"])
            totals[metric][1] += 1
            if not c["pass"]:
                failed.append(metric)
        chats.append(
            {
                "id": Path(row["vars"]["chat"]).stem,
                "description": row["testCase"]["description"],
                "pass": bool(row["success"]),
                "failed": failed,
                "graded": [f"{g['grade']} {g['rule_id']}" for g in out.get("graded", [])],
            }
        )
    return {
        "tag": "redteam-v1",
        "model": first["model"],
        "prompt": first["prompt"],
        "n_chats": len(chats),
        "chats_passed": sum(c["pass"] for c in chats),
        "checks": [
            {"metric": m, "label": REDTEAM_CHECKS[m], "passed": p, "total": t}
            for m, (p, t) in totals.items()
            if t
        ],
        "chats": chats,
    }


def main() -> None:
    # --results-only refreshes evaluation metadata without requiring the local LLM response cache.
    if "--results-only" not in sys.argv:
        models = load_models()
        role = models.roles.extractor
        cand = next(c for c in models.candidates if c.id == role.model)
        cache = diskcache.Cache(llm.CACHE_DIR)
        (OUT / "runs").mkdir(parents=True, exist_ok=True)
        for chat_id in CHATS:
            path = ROOT / "data" / "dev" / f"{chat_id}.txt"
            msgs = parse_chat(path, pipeline.WORLD / "contacts.yaml")
            if not is_cached(msgs, cand, role.prompt_version, cache):
                sys.exit(f"{chat_id}: not in the LLM cache; refusing to spend a request")
            result = pipeline.run(path, cache=cache)
            (OUT / "runs" / f"{chat_id}.json").write_text(
                result.model_dump_json(indent=1) + "\n", encoding="utf-8"
            )
            print(f"{chat_id}: {result.status}, {len(result.requests)} requests")
        manifest = [{"id": k, "title": v, "file": f"runs/{k}.json"} for k, v in CHATS.items()]
        (OUT / "manifest.json").write_text(
            json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))  # the configured policy
        (OUT / "policy.json").write_text(
            json.dumps(policy, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    summary = json.loads(
        (ROOT / "eval" / "results" / EVAL_TAG / "summary.json").read_text(encoding="utf-8")
    )
    keep = (
        "tag",
        "split",
        "model",
        "prompt",
        "policy",
        "metrics",
        "hard_gates",
        "targets",
        "slices",
    )
    results = {k: summary[k] for k in keep}
    results["n_chats"] = len(summary["chats"])
    test_summary = json.loads(
        (ROOT / "eval" / "results" / TEST_TAG / "summary.json").read_text(encoding="utf-8")
    )
    results["test_eval"] = {
        "tag": test_summary["tag"],
        "n_chats": len(test_summary["chats"]),
        "metrics": test_summary["metrics"],
        "hard_gates": test_summary["hard_gates"],
    }
    challenge = ROOT / "eval" / "results" / CHALLENGE_TAG / "summary.json"
    if challenge.exists():
        ch = json.loads(challenge.read_text(encoding="utf-8"))
        results["challenge_eval"] = {
            "tag": ch["tag"],
            "hard_gates": ch["hard_gates"],
            "metrics": ch["metrics"],
            "chats": [{k: c[k] for k in ("chat", "scenario", "exact")} for c in ch["chats"]],
        }
    if REDTEAM.exists():
        results["redteam"] = redteam_summary()
    (OUT / "results.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    shutil.copy(ROOT / "data" / "dev" / "d01.txt", OUT / "sample.txt")
    assets = ROOT / "site" / "assets"
    shutil.copy(ROOT / "docs" / "architecture.drawio.svg", assets / "architecture.svg")


if __name__ == "__main__":
    main()
