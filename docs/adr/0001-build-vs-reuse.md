# ADR 0001 — Build vs reuse (2026-10-26)

**Decision:** reuse a permissive open-source library for every generic job; own code is the prompt,
rules file, roster and thin glue (SPEC §4). Licences read from PyPI; versions from `uv.lock`.

| Job | Library | Licence | Version |
|---|---|---|---|
| Parse WhatsApp exports | chat-miner | MIT | 0.6.0 |
| LLM client / schema output | openai · instructor | Apache-2.0 · MIT | 3.3.0 · 1.17.0 |
| Cache | diskcache | Apache-2.0 | 5.6.3 |
| Traces | langfuse | MIT | 5.0.4 |
| Rules | rule-engine | BSD-3-Clause | 5.1.0 |
| Identity | phonenumbers · rapidfuzz | Apache-2.0 · MIT | 9.0.41 · 3.14.6 |
| Schemas / config | pydantic · pyyaml · python-dotenv | MIT · MIT · BSD-3 | 2.14.0 · 6.0.3 · 1.2.4 |
| Eval | scikit-learn · scipy | BSD-3 · BSD-3 | 1.9.1 · 1.18.1 (1.17.x on 3.11) |
| API / server | fastapi · uvicorn | MIT · BSD-3 | 0.162.0 · 0.54.0 |
| CLI | typer | MIT | 0.27.3 |

**Rejected:** own policy evaluator (rule-engine) · own trace store (Langfuse) · Postgres/Neon/
SQLAlchemy (JSONL is enough) · LLM data generator (hand-written chats) · Streamlit (website wanted)
· Hugging Face Spaces (paid) · LangGraph/Burr (not an agent loop) · ReAct tool-agent (unauditable,
injection risk) · LLM Guard (archived) · whatstk (GPL-3.0) · IndicLID/IndicXlit/promptfoo/chunking
(deferred).

**Cost:** chat-miner pulls matplotlib, polars[pandas], pyarrow, wordcloud (`.venv` ≈ 800 MB); all
permissive, accepted for a working parser. No GPL in the 106 installed packages.
