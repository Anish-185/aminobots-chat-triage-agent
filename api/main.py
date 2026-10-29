"""Local API + static site in one FastAPI process (SPEC §11). Every action stays simulated.

POST /api/triage runs the real pipeline in a worker thread (FastAPI runs sync endpoints in its
threadpool); the LLM client's `request_timeout_s` bounds it, and a timeout fails closed to
UNPROCESSED. A visitor key is passed to a one-off client and then dropped: it is never stored,
logged, traced or part of a cache key.
"""

import tempfile
from datetime import date
from pathlib import Path

import diskcache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, SecretStr

from triage import llm, pipeline
from triage.config import load_models, load_server, load_thresholds
from triage.extract import is_cached
from triage.parse import parse_chat
from triage.schemas import RunResult

ROOT = Path(__file__).resolve().parent.parent
server = load_server()
llm.TRACING = False  # this process may hold a visitor key: Langfuse never loads here

app = FastAPI(
    title="Aminobots Triage Desk (simulation)",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=server.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ponytail: in-memory per-day counter, resets on restart; persist it if the demo runs for days.
_server_key_used: dict[date, int] = {}


class TriageIn(BaseModel):
    chat: str = Field(min_length=1, max_length=server.max_chat_chars)
    key: SecretStr | None = Field(default=None, max_length=300)  # SecretStr: masked in any repr


@app.get("/api/health")
def health() -> dict:
    role = load_models().roles.extractor
    return {
        "ok": True,
        "model": role.model,
        "prompt": f"extract/v{role.prompt_version}",
        "simulated": True,
    }


@app.post("/api/triage")
def triage(body: TriageIn) -> RunResult:
    visitor_key = body.key.get_secret_value().strip() if body.key else ""
    models = load_models()
    cand = next(c for c in models.candidates if c.id == models.roles.extractor.model)
    cache = diskcache.Cache(llm.CACHE_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        chat = Path(tmp) / "your-chat.txt"
        chat.write_text(body.chat, encoding="utf-8")
        client = None
        if visitor_key:
            client = llm._client(cand.instructor_mode, api_key=visitor_key)
        else:
            cap, today = load_thresholds().demo_server_key_rpd or 0, date.today()
            try:
                cached = is_cached(
                    parse_chat(chat, pipeline.WORLD / "contacts.yaml"),
                    cand,
                    models.roles.extractor.prompt_version,
                    cache,
                )
            except Exception:  # unparsable: the pipeline reports it as UNPROCESSED, costs nothing
                cached = True
            if not cached and _server_key_used.get(today, 0) >= cap:
                msg = f"The demo key's daily limit ({cap} requests) is used up."
                raise HTTPException(429, f"{msg} Add your own OpenRouter key.")
        del visitor_key, body  # nothing below can see the key
        result = pipeline.run(chat, cache=cache, client=client)
    if client is None:
        spent = (result.llm or {}).get("requests", 0)
        _server_key_used[date.today()] = _server_key_used.get(date.today(), 0) + spent
    result.chat = "your-chat.txt"
    return result


app.mount("/", StaticFiles(directory=ROOT / "site", html=True), name="site")
