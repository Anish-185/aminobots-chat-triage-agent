# ADR 0002 — Extractor model choice (2026-10-29)

**Decision:** default extractor `nvidia/nemotron-3.5-super-vl:free` (Instructor `JSON_SCHEMA`);
fallback `google/gemma-4-31b-it:free` (`JSON`). **Default by availability:** gemma could not be
measured in two attempts (v1, v2).

**Context:** `nemotron-3-super-120b-a12b:free` was retired by OpenRouter before Phase 4; its
same-family successor took its place. Bake-off: strict mode, prompt `extract/v1`, the same 10 dev
chats (d01 d02 d03 d05 d07 d08 d10 d12 d13 d15). Rule: F1, then evidence Jaccard, then latency.

| Model | Chats done | P / R / F1 | Intent acc | Evidence J | Schema fails | p50 / p95 s |
|---|---|---|---|---|---|---|
| nemotron-3.5-super-vl | 8/10 (2 timeouts) | 0.88 / 0.81 / 0.84 | 1.00 | 0.92 | 0 | 65 / 213 |
| gemma-4-31b-it | 0/10 (429 upstream) | – | – | – | – | – |

Failed chats count as predicting nothing. On the 8 chats that finished, nemotron missed no gold
request (21/21) and added 3 extras. It never filled `slot_datetime` (0/6), which R7 needs; see
the Phase 4 report.

**Why:** nemotron is the only measured model and passed the schema on every answered chat. Gemma
returned 429 (Google AI Studio shared pool) on its first chat and was stopped without a retry
(rule: no retry loops).

**Phase 5 re-run (prompt `extract/v3`, 300 s timeout):** gemma again hit 429 on d01 (1 request,
stopped). With the longer timeout nemotron finished d10 (172 s, 1/2 gold) and d13 (70 s, 3/3 gold)
in the `v0.1-dev` eval.

**Revisit** when gemma's free pool has capacity: rerun `eval.bakeoff` for gemma only (10 requests).
Results: `eval/results/bakeoff-v1/`, `eval/results/bakeoff-v2/`, `eval/results/v0.1-dev/`.
