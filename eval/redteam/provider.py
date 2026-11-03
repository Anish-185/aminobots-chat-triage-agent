"""promptfoo provider: one red-team chat → the real pipeline (extract, ground, identity, policy).

Returns JSON with the model's extraction (what it output, after schema validation) and the graded
requests, so the assertions can check the model and the code separately. LLM responses are cached
by triage.llm, so a re-run costs 0 requests. Nothing is written to runs/. A ledger refuses to start
a call that could take the suite past BUDGET requests (Phase 10 pre-approval).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import diskcache  # noqa: E402

from triage import llm, pipeline  # noqa: E402
from triage.config import load_models, load_thresholds  # noqa: E402
from triage.extract import is_cached  # noqa: E402
from triage.parse import parse_chat  # noqa: E402

BUDGET = 12
LEDGER = ROOT / "eval" / "tmp" / "redteam-requests.json"


def call_api(prompt: str, options: dict, context: dict) -> dict:
    chat = ROOT / prompt.strip()
    models = load_models()
    role = models.roles.extractor
    cand = next(c for c in models.candidates if c.id == role.model)
    cache = diskcache.Cache(llm.CACHE_DIR)
    spent = json.loads(LEDGER.read_text(encoding="utf-8"))["requests"] if LEDGER.exists() else 0
    cached = is_cached(
        parse_chat(chat, pipeline.WORLD / "contacts.yaml"), cand, role.prompt_version, cache
    )
    worst = 1 + load_thresholds().llm_max_repair_retries
    if not cached and spent + worst > BUDGET:
        return {"error": f"request budget: {spent} spent, a new call could pass {BUDGET}"}
    result = pipeline.run(chat, cache=cache)
    spent += (result.llm or {}).get("requests", 0)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps({"requests": spent}), encoding="utf-8")
    extraction = result.extraction.model_dump(mode="json") if result.extraction else None
    graded = [
        {
            "gloss": r.candidate.gloss,
            "intent": r.candidate.intent,
            "flags": r.candidate.flags,
            "identity_state": r.identity.state,
            "grade": r.grade,
            "rule_id": r.rule_id,
        }
        for r in result.requests + result.internal_requests
    ]
    out = {
        "chat": chat.name,
        "status": result.status,
        "error": result.error,
        "model": result.model,
        "prompt": result.prompt,
        "llm": result.llm,
        "extraction": extraction,
        "graded": graded,
    }
    return {"output": json.dumps(out, ensure_ascii=False)}
