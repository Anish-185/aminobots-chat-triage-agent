"""extract + llm with a mocked HTTP transport: real Instructor retry logic, no network."""

import json
from datetime import datetime
from pathlib import Path

import diskcache
import httpx
import instructor
import openai
import pytest

from triage import llm
from triage.config import load_models
from triage.extract import ExtractionFailed, extract, load_prompt, user_message
from triage.schemas import Message

FAKE_KEY = "sk-or-v1-test-not-a-real-key"
GOOD = {
    "candidates": [
        {
            "intent": "delivery_slot_change",
            "gloss": "Move tomorrow's 8 am slot to 11",
            "primary_msg_id": "m001",
            "evidence_msg_ids": ["m001"],
            "entities": {"slot_datetime": "2026-03-03T08:00:00"},
        }
    ]
}
BAD = {"candidates": [{"intent": "teleport", "gloss": "x"}]}


def _completion(content: dict) -> dict:
    return {
        "id": "x",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(content)},
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }


class Server:
    """Replays canned responses; records every request body."""

    def __init__(self, *responses: tuple[int, dict]):
        self.responses = list(responses)
        self.bodies: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.bodies.append(json.loads(request.content))
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body)

    def client(self, mode: str) -> instructor.Instructor:
        raw = openai.OpenAI(
            base_url=llm.BASE_URL,
            api_key=FAKE_KEY,
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(self)),
        )
        return instructor.from_openai(raw, mode=instructor.Mode[mode])


MSGS = [
    Message(
        id="m001",
        ts=datetime(2026, 3, 2, 9, 0),
        author_raw="Teja",
        phone=None,
        display_name="Teja",
        text="Repu 8am delivery ni 11 ki marchandi",
        kind="text",
    )
]
CAND = load_models().candidates[0]


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch):
    monkeypatch.setattr(llm, "_pace", lambda: None)


@pytest.fixture
def cache(tmp_path: Path):
    with diskcache.Cache(tmp_path / "cache") as c:
        yield c


def _run(server: Server, cache):
    return extract(MSGS, CAND, 0, cache=cache, client=server.client(CAND.instructor_mode))


def test_valid_output(cache):
    server = Server((200, _completion(GOOD)))
    result, info = _run(server, cache)
    assert result.candidates[0].entities.slot_datetime == datetime(2026, 3, 3, 8, 0)
    assert (info.requests, info.schema_failures, info.cached) == (1, 0, False)
    assert info.prompt_tokens == 100
    body = server.bodies[0]
    assert body["model"] == CAND.id
    assert body["messages"][1]["content"].startswith("NOW: 2026-03-02 09:00")


def test_one_repair_retry_then_success(cache):
    server = Server((200, _completion(BAD)), (200, _completion(GOOD)))
    result, info = _run(server, cache)
    assert len(result.candidates) == 1
    assert (info.requests, info.schema_failures) == (2, 1)


def test_second_schema_failure_raises_extraction_failed(cache):
    server = Server((200, _completion(BAD)), (200, _completion(BAD)))
    with pytest.raises(ExtractionFailed) as exc:
        _run(server, cache)
    assert exc.value.__cause__.requests == 2  # exactly one retry, never a loop
    assert not server.responses


def test_429_is_clear_and_not_retried(cache):
    server = Server((429, {"error": {"message": "Rate limit exceeded: free-models-per-day"}}))
    with pytest.raises(llm.RateLimited, match="429"):
        _run(server, cache)
    assert len(server.bodies) == 1


def test_unavailable_model_has_no_fallback(cache):
    server = Server((404, {"error": {"message": "No endpoints found"}}))
    with pytest.raises(llm.ModelUnavailable):
        _run(server, cache)
    assert len(server.bodies) == 1  # no second model tried


def test_auth_error_does_not_leak_key(cache):
    server = Server((401, {"error": {"message": "User not found."}}))
    with pytest.raises(ExtractionFailed) as exc:
        _run(server, cache)
    assert FAKE_KEY not in str(exc.value) and FAKE_KEY not in repr(exc.value.__cause__)


def test_cache_hit_makes_no_request(cache):
    _run(Server((200, _completion(GOOD))), cache)
    empty = Server()  # any request would pop from an empty list and fail
    result, info = _run(empty, cache)
    assert (info.cached, info.requests) == (True, 0)
    assert result.candidates[0].primary_msg_id == "m001"
    assert not empty.bodies


def test_cache_key_varies_with_model_prompt_and_chat():
    keys = {
        llm.cache_key("a:free", "extract/v1", "chat"),
        llm.cache_key("b:free", "extract/v1", "chat"),
        llm.cache_key("a:free", "extract/v2", "chat"),
        llm.cache_key("a:free", "extract/v1", "chat2"),
    }
    assert len(keys) == 4


def test_missing_key_is_clear(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(llm, "load_dotenv", lambda *_a, **_k: None)
    with pytest.raises(llm.LLMError, match="OPENROUTER_API_KEY is not set"):
        llm._client("JSON")


def test_prompt_front_matter_and_coverage():
    meta, body = load_prompt(1)
    assert {"id", "version", "model", "output_schema", "purpose"} <= meta.keys()
    for name in [
        "delivery_slot_change", "order_change", "status_query", "invoice_request",
        "payout_details_change", "refund_request", "complaint", "other",
        "referent_unresolved", "time_unspecified", "intent_unclear", "possible_forward",
        "injection_attempt", "slot_datetime", "NOW",
    ]:  # fmt: skip
        assert name in body, name


def test_user_message_uses_last_timestamp_as_now():
    later = MSGS[0].model_copy(update={"id": "m002", "ts": datetime(2026, 3, 2, 18, 5)})
    assert user_message([MSGS[0], later]).startswith("NOW: 2026-03-02 18:05\n")
