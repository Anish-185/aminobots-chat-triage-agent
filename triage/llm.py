"""OpenRouter client (SPEC §3.3): openai SDK → Langfuse drop-in (only when its keys are set) →
Instructor. Responses are cached on disk; calls are sequential and paced; nothing retries except
Instructor's single schema-repair retry. The API key is never logged or printed."""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import diskcache
import instructor
import openai
from dotenv import load_dotenv
from pydantic import BaseModel

from triage.config import Candidate, load_thresholds

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache" / "llm"
BASE_URL = "https://openrouter.ai/api/v1"


class LLMError(RuntimeError):
    """The call failed for a reason a retry will not fix right now."""

    requests = 0  # API requests spent before the failure (they count against the daily cap)
    schema_failures = 0


class RateLimited(LLMError):
    """429 from OpenRouter: stop; a re-run resumes from the cache (SPEC §3.5)."""


class ModelUnavailable(LLMError):
    """The model is gone or has no live endpoint. Strict mode: no fallback (SPEC §3.5)."""


class SchemaFailed(LLMError):
    """Output still failed validation after the one repair retry."""


@dataclass
class CallInfo:
    model: str
    cached: bool
    requests: int  # API requests made by this call (0 when cached)
    schema_failures: int  # attempts whose output failed validation
    latency_s: float | None  # of the original uncached call
    prompt_tokens: int | None
    completion_tokens: int | None
    errors: list[str] = field(default_factory=list)


_last_call = 0.0  # monotonic time of the last request, for pacing only (not pipeline logic)


def _pace() -> None:
    global _last_call
    gap = 60 / load_thresholds().requests_per_minute
    wait = _last_call + gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def cache_key(model: str, prompt_version: str, rendered: str) -> str:
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    return f"{model}|{prompt_version}|{digest}"


def _client(mode: str) -> instructor.Instructor:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise LLMError("OPENROUTER_API_KEY is not set")
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        from langfuse.openai import OpenAI
    else:
        from openai import OpenAI
    # max_retries=0: the SDK would otherwise silently retry 429s and burn the daily quota.
    raw = OpenAI(base_url=BASE_URL, api_key=key, max_retries=0)
    return instructor.from_openai(raw, mode=instructor.Mode[mode])


def _classify(exc: BaseException) -> LLMError:
    cause = exc.__cause__ or exc
    if isinstance(cause, openai.RateLimitError):
        return RateLimited(f"rate limited (429): {cause.message}")
    if isinstance(cause, openai.NotFoundError | openai.InternalServerError):
        return ModelUnavailable(f"model unavailable ({cause.status_code}): {cause.message}")
    if isinstance(cause, openai.APIStatusError):
        return LLMError(f"OpenRouter error {cause.status_code}: {cause.message}")
    if isinstance(cause, openai.APIError):
        return LLMError(f"transport error: {type(cause).__name__}")
    return SchemaFailed(f"invalid output after retry: {str(cause)[:300]}")


def call(
    candidate: Candidate,
    prompt_version: str,
    system: str,
    user: str,
    response_model: type[BaseModel],
    temperature: float,
    cache: diskcache.Cache | None = None,
    client: instructor.Instructor | None = None,
) -> tuple[BaseModel, CallInfo]:
    """One structured call, cached by (model, prompt version, hash of the rendered chat)."""
    key = cache_key(candidate.id, prompt_version, user)
    cache = cache if cache is not None else diskcache.Cache(CACHE_DIR)
    if (hit := cache.get(key)) is not None:
        info = CallInfo(**{**hit["info"], "cached": True, "requests": 0})
        return response_model.model_validate(hit["data"]), info

    client = client or _client(candidate.instructor_mode)
    usage = {"requests": 0, "schema_failures": 0, "prompt": 0, "completion": 0}

    def on_response(resp) -> None:
        usage["requests"] += 1
        if u := getattr(resp, "usage", None):
            usage["prompt"] += u.prompt_tokens or 0
            usage["completion"] += u.completion_tokens or 0

    def on_parse_error(*_args, **_kwargs) -> None:
        usage["schema_failures"] += 1

    client.on("completion:kwargs", lambda *a, **k: _pace())
    client.on("completion:response", on_response)
    client.on("parse:error", on_parse_error)
    start = time.monotonic()
    try:
        result = client.chat.completions.create(
            model=candidate.id,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_model=response_model,
            temperature=temperature,
            max_retries=load_thresholds().llm_max_repair_retries,
            extra_body={
                "reasoning": {"effort": candidate.reasoning_effort},
                "provider": {"require_parameters": True},
            },
        )
    except Exception as exc:  # every failure is classified and re-raised
        err = _classify(exc)
        err.requests, err.schema_failures = usage["requests"], usage["schema_failures"]
        raise err from exc
    info = CallInfo(
        model=candidate.id,
        cached=False,
        requests=usage["requests"],
        schema_failures=usage["schema_failures"],
        latency_s=round(time.monotonic() - start, 2),
        prompt_tokens=usage["prompt"] or None,
        completion_tokens=usage["completion"] or None,
    )
    data = json.loads(result.model_dump_json())
    cache.set(key, {"data": data, "info": {**info.__dict__, "cached": False}})
    return result, info
