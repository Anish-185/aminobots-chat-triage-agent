"""Build site/data from the real pipeline, cache only (0 LLM requests; exits on a cache miss).

Writes site/data/runs/<chat>.json (RunResult), manifest.json, policy.json, results.json and
sample.txt (dev d01, a cache hit for "Load a sample"), and copies the architecture diagram.
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
EVAL_TAG = "v1.0-dev"
# Together these show every case the site's story and demo need (Phase 6 prompt §16).
CHATS = {
    "d01": "Slot change and the “alaage” follow-up",
    "d07": "Bank details change from an unknown number",
    "d05": "Two people share one phone",
    "d03": "Requests that were cancelled",
    "d10": "A message that tries to give orders",
}


def main() -> None:
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
        (OUT / "runs" / f"{chat_id}.json").write_text(result.model_dump_json(indent=1) + "\n")
        print(f"{chat_id}: {result.status}, {len(result.requests)} requests")
    manifest = [{"id": k, "title": v, "file": f"runs/{k}.json"} for k, v in CHATS.items()]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))  # the configured policy
    (OUT / "policy.json").write_text(json.dumps(policy, indent=1, ensure_ascii=False) + "\n")
    summary = json.loads((ROOT / "eval" / "results" / EVAL_TAG / "summary.json").read_text())
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
    (OUT / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    shutil.copy(ROOT / "data" / "dev" / "d01.txt", OUT / "sample.txt")
    assets = ROOT / "site" / "assets"
    shutil.copy(ROOT / "docs" / "architecture.drawio.svg", assets / "architecture.svg")


if __name__ == "__main__":
    main()
