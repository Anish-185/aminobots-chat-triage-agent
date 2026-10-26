# SPEC v2 — Aminobots Chat Triage Agent

Status: v2.1 (Phase 1; see §17). Replaces SPEC v1.x, which is kept on the
`archive/first-attempt` branch. Decisions come from `docs/context/PROJECT_CONTEXT.md` §4; if this
file and the context disagree, the context wins.

This is a **demo build**: the simplest system that meets the brief, built from open-source
libraries, at **$0**, shown on a **local** website.

---

## 1. Scope

**Input:** one WhatsApp `.txt` group-chat export from a partner group (Telugu–English, mostly
romanised, noisy).

**Output:** a list of requests. Each request has:

| Field | Meaning |
|---|---|
| `gloss` | one-line English summary |
| `intent` | one of the 8 intents (§6) |
| `requester` | sender of the primary message + identity state (§7) + reason |
| `grade` | `act` / `seek_approval` / `hand_off` / `refuse` |
| `rule` | the rule ID that decided the grade, plus all matched rules (§9) |
| `evidence` | message IDs the request relies on (all exist in the chat) |

**Not in scope (deferred):** real execution of anything, Hindi, voice notes and image content,
replying to the group, chunking long chats, script detection beyond a simple heuristic,
deployment.

## 2. Invariants

1. The model describes; code decides (identity, authority, grade, rule).
2. Autonomy only goes down: most cautious matching grade wins; no match → R10 `hand_off`.
3. Fail closed: any failure → run `UNPROCESSED`, whole chat handed off.
4. Evidence or it doesn't exist: candidates citing unknown message IDs are dropped and logged.
5. Simulate, never execute: the action layer only appends JSONL; a test proves no network import.
6. Frozen eval data: `data/test/` and `data/challenge/` are read only by `eval/run_eval.py`.
7. No secrets in the repo.
8. Deterministic time: "now" = timestamp of the last message.
9. Synthetic data only; phones fail `phonenumbers.is_valid_number()`.
10. Zero spend: OpenRouter `:free` models only; ≤ 10 requests without approval; CI never calls an
    LLM.
11. Prefer libraries; own modules > ~150 lines need a justification.
12. Local only: no deployment config until the human approves publishing.

## 3. Pipeline

```
WhatsApp .txt
  → parse     (code: chat-miner)          messages m001… in parse order
  → extract   (LLM: OpenRouter :free via Instructor; diskcache; Langfuse trace)
  → ground    (code)                       drop candidates with invalid IDs
  → identity  (code: phonenumbers + rapidfuzz + roster.yaml)
  → policy    (code: rule-engine expressions in policy/policy_v1.yaml)
  → route     (code)                       append to runs/*.jsonl, simulated=true
```

### 3.1 Parse
- chat-miner parses the export into rows (timestamp, author, text). Its API and columns are
  verified in Phase 3 before use.
- Message IDs `m001`, `m002`, … are assigned in parse order.
- Author is a phone number or a saved name; a name maps to a phone via optional
  `data/world/contacts.yaml`.
- System lines are kept as messages with `kind = system` ("security code changed", added/left,
  "This message was deleted"). Phase 3 checks whether chat-miner keeps them; if not, a ≤ 30-line
  pre-pass recovers them before IDs are assigned.
- Media placeholders become `kind = media`, rendered `[image]`.

### 3.2 Rendering for the model
One line per message: `[m041] 10:42 | S3 "Ravi (Ameerpet)" | text`.
- Sender handles `S1…Sn` are stable within a chat.
- A date divider line (`--- 2026-10-25 ---`) precedes the first message of each new day, so
  relative dates ("repu" = tomorrow) resolve.
- **Phone numbers are never sent to the model.**

### 3.3 Extract
- One prompt, `prompts/extract/v1.md`, one call per chat, output validated against the
  `Extraction` schema (§5).
- Instructor mode: `JSON_SCHEMA` where the model supports structured outputs, otherwise `JSON` /
  `MD_JSON`. Reasoning off or low.
- Responses cached on disk (diskcache, `.cache/`) keyed by model + prompt version + chat hash.
- Calls are sequential with a sleep to respect 20 requests/min.

### 3.4 Ground
- Every `primary_msg_id`, `evidence_msg_ids` and `refers_to_msg_id` must exist in the chat.
- A candidate whose primary or all evidence IDs are invalid is dropped and logged as
  `rejected_hallucination`. A bad `refers_to_msg_id` is replaced by flag `referent_unresolved`.
- The requester is the sender of `primary_msg_id`, decided here in code.

### 3.5 Failures

| Failure | Behaviour |
|---|---|
| Schema validation fails | Instructor retries once; still failing → `UNPROCESSED` + hand off |
| 429 / rate limit | stop cleanly; re-running resumes via the cache |
| Transport / other error | `UNPROCESSED` + hand off; never an empty result |
| Model unavailable (strict mode) | transcript stays pending; no fallback model |

## 4. Libraries (build vs reuse)

| Job | Reuse | Own part |
|---|---|---|
| Parse WhatsApp exports | chat-miner (MIT) | none |
| LLM with a schema | OpenRouter `:free` + openai SDK + Instructor (MIT) | prompt + schema |
| Cache | diskcache (Apache-2.0) | one decorator |
| Traces, latency, cost | Langfuse Cloud Hobby (free), OpenAI drop-in | one import |
| Rules | rule-engine (BSD-3, no `eval`) | ~15 lines most-cautious-wins |
| Identity | phonenumbers, rapidfuzz | ~30 lines lookup |
| Validation | pydantic v2 | schemas |
| Eval | scikit-learn, scipy (Hungarian) | small script |
| API | FastAPI + uvicorn | one endpoint |
| Website | static HTML + Tailwind (CDN) + vanilla JS, MIT template | content + demo panel |
| Tooling | uv, ruff, pytest, pre-commit, gitleaks, GitHub Actions | config |

Rejected: own policy evaluator, own trace store, Postgres/Neon/SQLAlchemy, LLM data generator,
Streamlit, Hugging Face Spaces (paid), LangGraph/Burr, ReAct tool-agent, LLM Guard (archived),
whatstk (GPL-3.0), IndicLID/IndicXlit/promptfoo/chunking (deferred).

## 5. Data contracts (`triage/schemas.py`)

Pydantic v2 models are the only contracts between stages. Field lists are binding; exact types
are fixed in Phase 3.

| Model | Key fields |
|---|---|
| `Message` | `id` (`m001`), `ts`, `author_raw`, `handle` (`S1`), `display_name`, `text`, `kind` (`text`/`media`/`system`) |
| `Candidate` (LLM) | `intent`, `gloss`, `primary_msg_id`, `evidence_msg_ids[]`, `refers_to_msg_id?`, `on_behalf_of?`, `entities` (outlet, date, slot time, amount…), `status` (`open`/`cancelled`/`handled`), `flags[]` |
| `Extraction` (LLM) | `candidates[]` |
| `Identity` | `state` (`CONFIRMED`/`AMBIGUOUS`/`UNCONFIRMED`), `contact_id?`, `role?`, `outlets[]`, `reason` |
| `PolicyResult` | `grade`, `rule_id`, `matched_rules[]`, `rule_checks[]` (rule, matched yes/no) |
| `Request` | candidate + identity + policy result + `route` |
| `RunResult` | `run_id`, `status` (`OK`/`UNPROCESSED`), `requests[]`, `rejected[]`, `trace_url?` |

Uncertainty flags (from the LLM or code): `referent_unresolved`, `outlet_ambiguous`,
`time_unspecified`, `intent_unclear`, `possible_forward`, `injection_attempt`.

## 6. Intents

| Intent | Risk | Discloses account data | Allowed roles |
|---|---|---|---|
| `delivery_slot_change` | low | no | owner, manager, staff |
| `order_change` | medium | no | owner, manager |
| `status_query` | none | yes | owner, manager, staff, accounts |
| `invoice_request` | none | yes | owner, manager, accounts |
| `payout_details_change` | critical | yes | owner |
| `refund_request` | high | no | owner, manager, accounts |
| `complaint` | — | no | any |
| `other` | — | no | any |

The table lives in `policy/policy_v1.yaml` next to the rules, so swapping the policy swaps both.

## 7. Identity

| State | Rule |
|---|---|
| `CONFIRMED` | phone is in the roster and not marked shared |
| `AMBIGUOUS` | phone is marked shared, OR phone unknown and display name matches 2+ roster contacts |
| `UNCONFIRMED` | phone unknown, with 0 or 1 name match |

- A self-claim ("idi naa kotha number, Suresh") or vouching by others **never** confirms a sender.
- A "security code changed" line for the same sender before the request downgrades `CONFIRMED`
  to `UNCONFIRMED`.
- **Principal:** "maa outlet" resolves to the sender's outlets; 2+ outlets → flag
  `outlet_ambiguous`. An on-behalf request is verified only if the roster lists the sender as a
  delegate of the principal.
- **Authority:** sender's roster role must be in the intent's allowed roles (§6). An `AMBIGUOUS`
  sender is authorised only if **every** candidate contact is authorised. (`AMBIGUOUS` + payout
  change → hand_off R1, by design: finance verifies out of band.)
- **Internal senders (A6):** requests from role `aminobots_staff` are logged but excluded from
  the request list and from eval.
- Name matching uses rapidfuzz with the threshold in `config/thresholds.yaml`.
- Every decision stores a human-readable `reason`, shown on the website.

## 8. Data

- Format: WhatsApp `.txt` exports only, with gold JSON alongside (`<id>.txt` + `<id>.gold.json`).
- `data/world/roster.yaml`: partners, outlets, contacts (phone, name, role, outlets, `shared`,
  `delegate_for`). Must include a shared phone, two contacts with the same first name, an owner
  with 2 outlets, an `accounts` role, a delegate, and Aminobots-staff contacts.
- Phones: `+91` + 10 digits. Generate by drawing candidates whose first digit is 0–5 and keeping
  only those with `phonenumbers.is_valid_number() == False` (Indian landlines starting 2–5 can
  be valid). A test asserts this for every phone in the repo.

| Split | Size | Written by | Status |
|---|---|---|---|
| `data/dev/` | ~15 chats | Claude Code (Telugu reviewed by a teammate) | development |
| `data/test/` | ~15 chats | the team, outside the repo session | **frozen** |
| `data/challenge/` | 8–10 chats | humans only: both mandated scenarios verbatim + adversarial cases (vouching, injection, cancellations, forwards, split requests, on-behalf) | **frozen** |

- Noise in every chat: greetings, "ok sir 👍", forwards, `[image]`, festival wishes, mixed
  scripts, spelling variants (cheyyandi / cheyandi; repu / repuu).
- Licences: data CC BY 4.0, code MIT.

## 9. Autonomy policy v1 (`policy/policy_v1.yaml`)

Grade order, least to most cautious: `act` < `seek_approval` < `hand_off` < `refuse`.
Every rule is evaluated with rule-engine against a flat context dict. The **most cautious**
matching grade wins. The cited rule is the **lowest-numbered** matching rule with that grade. All
matched rules are recorded.

Context fields: `intent`, `risk`, `discloses`, `sender_state`, `authorised`, `on_behalf`,
`on_behalf_verified`, `flags`, `status`, `slot_hours_ahead`.

| Rule | Condition | Grade |
|---|---|---|
| R1 | intent is `payout_details_change` | hand_off (finance, out-of-band verification) |
| R2 | sender `UNCONFIRMED` and (risk high/critical or discloses account data) | refuse + security alert |
| R3 | intent `complaint` or `other`, or risk high or critical | hand_off |
| R4 | sender not `CONFIRMED` | seek_approval |
| R5 | sender lacks authority for the intent, or on-behalf request not verified | seek_approval |
| R6 | any uncertainty flag | seek_approval |
| R7 | risk medium, or slot change < `slot_cutoff_hours` (12) before the slot | seek_approval |
| R8 | status not open (cancelled / already handled) | act (record only) |
| R9 | status open, sender `CONFIRMED`, authorised, risk none/low | act |
| R10 | default — nothing else matched | hand_off |

**Worked checks (unit tests):**

| Case | Result |
|---|---|
| Scenario 2: unknown number, payout change | refuse, cite R2 (R1 also matched) |
| Scenario 1: staff slot change, `CONFIRMED`, ≥ 12 h away | act, R9 |
| Follow-up "maa outlet ki kooda alaage cheyyandi", sender `CONFIRMED`, 1 outlet | act, R9 |
| Same follow-up, sender has 2 outlets | seek_approval, R6 |
| Same follow-up, sender unknown | seek_approval, R4 |
| Cancelled request from a `CONFIRMED` sender | act, R8 (record only) |
| Cancelled payout change from an unknown number | refuse, R2 |
| `CONFIRMED` owner, payout change | hand_off, R1 |
| `CONFIRMED` staff, slot change 6 h before the slot | seek_approval, R7 |

R8 never lowers caution: a non-open request still gets the most cautious matching grade.
A property test checks monotonicity: adding any rule never makes a grade less cautious.

## 10. Routing and logs

| Grade | Log (append-only JSONL, `simulated: true`) | Extra |
|---|---|---|
| `act` | `runs/actions.jsonl` | simulated action description |
| `seek_approval` | `runs/approvals.jsonl` | approve/reject handled by a human (website: client-side only) |
| `hand_off` | `runs/handoffs.jsonl` | team queue, with reason |
| `refuse` | `runs/alerts.jsonl` | refusal + security alert |

Each row carries `run_id`, request ID, grade, rule, evidence IDs and the time "now" (§2.8).
`runs/` is gitignored. The route module imports no network client (tested).

## 11. Website and API (local only)

**Serving: one process.** FastAPI on `127.0.0.1:8000` mounts the static `site/` at `/` and the
API under `/api` (no second server, no port clash). The site's API base URL is configurable and
defaults to same origin. Not published.

1. **Home** — the problem, a one-line solution, the two scenarios.
2. **How it works** — architecture SVG, model-vs-code split, rules table rendered from a JSON
   export of the policy.
3. **Live demo** — precomputed results for sample dev chats (`site/data/*.json`, produced by the
   real pipeline via a build script). No API needed.
   - Table: gloss, sender + state badge, grade badge, rule ID with its text on hover.
   - Click a request → step panel: chat with evidence highlighted → extraction → identity +
     reason → rule check table (all rules, matched yes/no, decider highlighted) → route +
     simulated action → Langfuse trace link (optional extra; see §12).
   - Approve/Reject on `seek_approval` items appends to a client-side log (sessionStorage).
4. **Try your own** — paste/upload a chat, optional "your OpenRouter key", POST to the local API
   (URL configurable). If the API isn't running, show the command to start it.
5. **Results** — eval metrics per prototype, the pass-rule table, link to Langfuse.
6. **Team** (placeholder names) and GitHub link.

Footer on every page: "Simulation only — no action is executed. Synthetic data only."

**API** (`api/main.py`, FastAPI + uvicorn):
- `POST /api/triage` (chat text + optional key) → `RunResult` with per-stage trace data.
- `GET /api/health`.
- CORS origins from config (localhost only now).
- A visitor key is used only for that request: never stored, logged or sent to Langfuse (tested).
- Without a visitor key the server key is capped at `demo_server_key_rpd` (10/day).

**One command** (`uv run python -m triage.serve`) starts that process and prints the localhost
URL. Paths are relative and the API URL is configurable, so publishing later needs no code change.

## 12. Evaluation

- **Matching:** predicted ↔ gold by same intent and evidence Jaccard ≥ 0.5, assigned with scipy's
  Hungarian algorithm.
- **Metrics:** detection precision / recall / F1 · attribution accuracy · unconfirmed-sender
  recall · grade accuracy + confusion matrix · over-autonomy rate (overall and high-risk) ·
  rule-citation accuracy · evidence validity · latency p50 / p95 · tokens + notional cost
  (tokens × paid-variant list price; billed = $0).
- **Baseline B1:** one prompt that does everything incl. grading, same model — shows with numbers
  why code must decide.
- **Strict-model mode** for milestones: no fallbacks; paired comparisons only on transcripts
  answered by the same model.
- **Pass rule** (test + challenge; dev is for development only):
  - Hard gates: high-risk over-autonomy = 0; unconfirmed-sender recall = 1.0; evidence validity =
    100%; both mandated scenarios pass exactly.
  - Targets: detection F1 ≥ 0.85; grade accuracy ≥ 0.85; rule-citation accuracy ≥ 0.90.
- **Results:** `eval/results/<tag>/summary.json` + `report.md`; scores also sent to Langfuse.
  Test and challenge results store IDs and labels only, never message text.
- **Observability:** Langfuse Hobby keeps data for 30 days, so the durable per-stage record is
  `site/data/*.json` and `eval/results/`. Langfuse links are optional extras.

## 13. Prototypes and request budget

| Tag | Content |
|---|---|
| v0.1 | CLI end-to-end on dev + eval |
| v0.2 | full identity/policy + test/challenge eval + B1 |
| v0.3 | website + API running locally |
| v1.0 | final docs (APPROACH, ARTEFACT, README) |

- Free cap: 50 requests/day, 20/min. A dev iteration ≈ 15 requests; a milestone eval ≈ 65
  (1–2 days).
- 💰 Decision point (not taken): a one-time $10 OpenRouter credit raises the cap to 1,000/day.

## 14. Configuration

| File | Holds |
|---|---|
| `config/models.yaml` | extractor and B1 model IDs (`:free` only, validated), temperature |
| `config/pricing.yaml` | paid-variant list prices for notional cost |
| `config/thresholds.yaml` | name-match threshold, slot cut-off (12 h), rate limits, `demo_server_key_rpd` |
| `.env` (local, gitignored) | `OPENROUTER_API_KEY`, `LANGFUSE_*` — empty in `.env.example` |

## 15. Assumptions and open questions

- **A1:** Aminobots serves partner outlets with deliveries, orders and payouts.
- **A2:** in scenario 1, "staff member" means partner-side staff.
- **A3:** the slot cut-off is 12 h.
- **A6:** requests from role `aminobots_staff` are internal (§7): logged, not listed, not scored.

All four are unconfirmed and listed with the mentor questions in
`docs/context/PROJECT_CONTEXT.md` §7. When answers arrive, update this SPEC, the policy and the
assumptions in the next phase.

## 16. Risks

- Eval runs send synthetic test and challenge chat text to OpenRouter free models (some
  providers may log prompts) and to Langfuse. Accepted because all data is synthetic; noted for
  APPROACH §E. Real partner chats must never be sent.

## 17. Change log

| Version | Changes |
|---|---|
| v2.0 | Phase 0: simplified design, condensed from context v2 §4. |
| v2.1 | Phase 1: one-process serving under `/api` (§11); phone generation rule (§8); R3 adds critical, R9 needs status open, three new worked checks (§9); `AMBIGUOUS` authority and A6 internal senders (§7, §15); system-line check and date dividers (§3.1, §3.2); observability retention (§12); risks (§16). |
