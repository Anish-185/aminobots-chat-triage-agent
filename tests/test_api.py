"""API tests with a mocked pipeline: no network, no LLM (SPEC §11)."""

import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api import main
from triage import llm
from triage.schemas import RunResult

KEY = "visitor-test-value"  # deliberately not key-shaped (gitleaks)
CHAT = "23/10/26, 7:50 am - Lakshmi Sunrise: Repu slot 8 ki marchandi"


def _result(**kw) -> RunResult:
    base = dict(run_id="abc", chat="x.txt", status="OK", model="m:free", prompt="extract/v3",
                policy_version=1, llm={"requests": 1, "cached": False})  # fmt: skip
    return RunResult(**base | kw)


@pytest.fixture
def client(monkeypatch):
    main._server_key_used.clear()
    monkeypatch.setattr(main, "is_cached", lambda *a, **k: False)
    return TestClient(main.app)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] and body["simulated"] and body["model"].endswith(":free")


def test_triage_returns_run_result_and_counts_server_key(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(main.pipeline, "run", lambda chat, **kw: seen.update(kw) or _result())
    r = client.post("/api/triage", json={"chat": "23/10/26, 7:50 am - A: hi"})
    assert (
        r.status_code == 200 and r.json()["status"] == "OK" and r.json()["chat"] == "your-chat.txt"
    )
    assert seen["client"] is None  # server key path
    assert main._server_key_used[date.today()] == 1


def test_unprocessed_is_returned_not_hidden(client, monkeypatch):
    bad = _result(status="UNPROCESSED", error="RateLimited: 429", llm={"requests": 1})
    monkeypatch.setattr(main.pipeline, "run", lambda chat, **kw: bad)
    body = client.post("/api/triage", json={"chat": "x"}).json()
    assert body["status"] == "UNPROCESSED" and body["log"] == []


def test_visitor_key_used_once_never_logged_returned_or_counted(client, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    built = {}

    def fake_client(mode, api_key=None):
        built["key"] = api_key
        return "visitor-client"

    def fake_run(chat, **kw):
        assert kw["client"] == "visitor-client"
        logging.getLogger("triage").info("running %s", chat.name)
        return _result()

    monkeypatch.setattr(main.llm, "_client", fake_client)
    monkeypatch.setattr(main.pipeline, "run", fake_run)
    r = client.post("/api/triage", json={"chat": "x", "key": f"  {KEY} "})
    assert r.status_code == 200 and built["key"] == KEY
    assert KEY not in r.text
    assert all(KEY not in rec.getMessage() for rec in caplog.records)
    assert main._server_key_used == {}  # the visitor's request never counts against the demo key
    assert KEY not in repr(main.TriageIn(chat="x", key=KEY))  # SecretStr masks it


def test_visitor_key_client_never_traced(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setattr(llm, "TRACING", True)
    c = llm._client("JSON", api_key=KEY)
    assert "langfuse" not in type(c.client).__module__
    assert c.client.api_key == KEY


def test_api_process_disables_tracing():
    assert llm.TRACING is False  # set by importing api.main


def test_server_key_daily_cap(client, monkeypatch):
    monkeypatch.setattr(main.pipeline, "run", lambda chat, **kw: _result())
    cap = main.load_thresholds().demo_server_key_rpd
    main._server_key_used[date.today()] = cap
    r = client.post("/api/triage", json={"chat": CHAT})
    assert r.status_code == 429 and "own OpenRouter key" in r.json()["detail"]
    monkeypatch.setattr(main, "is_cached", lambda *a, **k: True)  # cache hits cost nothing
    assert client.post("/api/triage", json={"chat": CHAT}).status_code == 200


def test_input_limits(client):
    assert client.post("/api/triage", json={"chat": ""}).status_code == 422
    too_long = "x" * (main.server.max_chat_chars + 1)
    assert client.post("/api/triage", json={"chat": too_long}).status_code == 422


def test_site_served_at_root(client):
    r = client.get("/")
    assert r.status_code == 200 and "Simulation only" in r.text
