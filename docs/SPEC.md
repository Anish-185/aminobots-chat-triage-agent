# SPEC v2 — Aminobots Chat Triage Agent

Status: v2.6 (Phase 6; see §17). Replaces SPEC v1.x, which is kept on the
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
deployment, **iOS exports** (only the Android format `dd/mm/yy, h:mm am - Name: text` parses).

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
- chat-miner parses ordinary messages (`timestamp`, `author`, `message`; multi-line joined). It
  **drops system lines**, so a pre-pass (`triage/parse.py`) marks every message start in file
  order, keeps system lines, and owns timestamps (fixed `dd/mm`); misalignment raises.
- Message IDs `m001`, `m002`, … are assigned in file order, system lines included.
- Author is a phone number or a saved name; a name maps to a phone via optional
  `data/world/contacts.yaml`. System lines carry the person they are about (`subject_phone`).
- `kind`: `system` for "security code changed", added/left/joined, "This message was deleted";
  `media` for `<Media omitted>` (rendered `[image]`); else `text`.

### 3.2 Rendering for the model
One line per message: `[m041] 10:42 | S3 "Ravi (Ameerpet)" | text`.
- Sender handles `S1…Sn` in order of first appearance (as author or system-line subject).
- A date divider line (`--- 2026-10-25 ---`) precedes the first message of each new day, so
  relative dates ("repu" = tomorrow) resolve.
- **Phone numbers are never sent to the model:** a number-only author shows as
  `"(number hidden)"`, and any number in text becomes `[phone]`. System lines: `| system | …`.

### 3.3 Extract
- One prompt, `prompts/extract/v<N>.md` (N = `roles.extractor.prompt_version`, now 3), one call per chat, output validated against the
  `ExtractionResult` schema (§5).
- Models: `nvidia/nemotron-3.5-super-vl:free` (Instructor `JSON_SCHEMA`) and
  `google/gemma-4-31b-it:free` (`JSON`; no `structured_outputs` on OpenRouter). The default is
  chosen by the Phase 4 bake-off (`docs/adr/0002-model-choice.md`); the other is the fallback.
  `nemotron-3-super-120b-a12b:free` was retired by OpenRouter before Phase 4.
- Slot changes: the model gives `entities.slot_day_offset` (days after the primary message's
  date: 0 today, 1 "repu", 2 "ellundi"; null if not stated) and `entities.slot_time` (`"HH:MM"`,
  24 h, the earliest time stated for the affected delivery; null if not stated). Code computes
  `slot_datetime` from the primary message's date, then `slot_hours_ahead` from it (§9). A slot
  change with status `open` and either part null, or an invalid value, gets the flag
  `time_unspecified` (→ R6). A closed (cancelled/handled) request executes nothing, so code does
  not add the flag and R8 decides unless a more cautious rule matches (v2.6). Consequence: with
  no slot, R7 cannot fire on a closed request either (dev d03 r1, see Phase 6 report).
  **Known gap (Phase 5):** nemotron left both fields null in every run (prompt v1–v3, with and
  without schema constraints), so every slot change currently fails closed to R6 and R7 never
  decides. The model fills only `outlet`, `amount`, `details` (v3 dropped free-text date/time).
- Reasoning: `effort: low` (`config/models.yaml`). `none` was tried on 2 dev chats (Phase 5):
  25× faster but lost a gold request, so it was not kept (`eval/results/reasoning-trial-v2/`).
- Responses cached on disk (diskcache, `.cache/`) keyed by model + reasoning setting + prompt
  version + hash of the output schema and the rendered chat.
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
| Transport / other error, incl. timeout (`request_timeout_s`, 300 s) | `UNPROCESSED` + hand off; never retried; never an empty result |
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

Pydantic v2 models are the only contracts between stages; the code is the exact definition.

| Model | Key fields |
|---|---|
| `Message` | `id` (`m001`), `ts`, `author_raw`, `phone` (never sent to the model), `display_name`, `text`, `kind`, `subject_phone?` |
| `Candidate` (LLM) | `intent`, `gloss`, `primary_msg_id`, `evidence_msg_ids[]`, `refers_to_msg_id?`, `on_behalf_of?`, `entities` (outlet, date, time, `slot_day_offset`, `slot_time`, amount, details; `slot_datetime` is computed in code and hidden from the model's schema), `status` (`open`/`cancelled`/`handled`), `flags[]` |
| `ExtractionResult` (LLM) | `candidates[]` |
| `Rejected` | `candidate`, `reason` (`rejected_hallucination: …`), from grounding (§3.4) |
| `Identity` | `state`, `contact_ids[]`, `role?`, `outlets[]`, `authorised`, `on_behalf`, `on_behalf_verified`, `target_outlets[]`, `reason` |
| `GradedRequest` | candidate + requester + identity + `grade`, `rule_id`, `matched_rules[]`, `rule_checks[]`, `internal` |
| `LogRecord` | `run_id`, `request_id`, `grade`, `rule_id` (null only for an UNPROCESSED whole-chat hand-off), `evidence_msg_ids[]`, `now`, `action`, `requester` (phone masked to last 4), `record_only` (R8), `internal`, `simulated: true` |
| `RunResult` | `run_id`, `chat`, `status` (`OK`/`UNPROCESSED`), `error?`, `now`, `model`, `prompt`, `policy_version`, `messages[]`, `rendered`, `extraction`, `llm` (requests, latency, tokens), `requests[]`, `internal_requests[]`, `rejected[]`, `log[]`: every stage, reused by the website |
| `GoldChat` | `chat_id`, `source`, `scenario?` (1/2, challenge), `requests[]` / `internal_requests[]` (intent, evidence, requester, state, status, flags, `facts`, grade, rule) |

Uncertainty flags (from the LLM or code): `referent_unresolved`, `outlet_ambiguous`,
`time_unspecified`, `intent_unclear`, `possible_forward`, `injection_attempt`. The model sets the
five other than `outlet_ambiguous`, which code sets from the roster (§7).

Status: `open` by default; `cancelled` when the requester withdraws it in the chat; `handled`
only when an `aminobots_staff` message in the chat explicitly confirms the request is done (an
acknowledgement such as "ok sir" is not enough).

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
- **Principal:** an outlet named in the request (matched on the roster area, rapidfuzz) is the
  target. Otherwise "maa outlet" resolves to the sender's outlets, and for outlet-scoped intents
  (`delivery_slot_change`, `order_change`) 2+ outlets → flag `outlet_ambiguous`. Account-level
  asks (invoices, statements) are not flagged. An on-behalf request (the model's `on_behalf_of`)
  is verified only if that name matches exactly one roster contact (honorifics such as "garu",
  "madam" removed) and the sender is a roster delegate of them. A request naming another
  partner's outlet is on-behalf and never verified (cross-partner).
- **Roles (fixed):** `owner`, `manager`, `staff`, `accounts`, `aminobots_staff`.
- **Authority:** sender's roster role must be in the intent's allowed roles (§6). An `AMBIGUOUS`
  sender is authorised only if **every** candidate contact is authorised. (`AMBIGUOUS` + payout
  change → hand_off R1, by design: finance verifies out of band.)
- **Internal senders (A6):** requests from role `aminobots_staff` are logged but excluded from
  the request list and from eval.
- Name matching uses rapidfuzz with the threshold in `config/thresholds.yaml`.
- Every decision stores a human-readable `reason`, shown on the website.

## 8. Data

- Format: Android WhatsApp `.txt` exports, gold alongside (`<id>.gold.json`); checked by
  `scripts/validate_gold.py` (pytest + pre-commit). Dev coverage: `data/dev/README.md`.
- `data/world/roster.yaml`: partners, outlets, contacts (phone, name, role, outlets, `shared`,
  `delegate_for`). Must include a shared phone, two contacts with the same first name, an owner
  with 2 outlets, an `accounts` role, a delegate, and Aminobots-staff contacts.
- Phones: `+91` + 10 digits. Generate by drawing candidates whose first digit is 0–5 and keeping
  only those with `phonenumbers.is_valid_number() == False` (Indian landlines starting 2–5 can
  be valid). A test asserts this for every phone in the repo.

| Split | Size | Written by | Status |
|---|---|---|---|
| `data/dev/` | 15 chats | Claude Code (Telugu reviewed by a teammate) | development and scoring |
| `data/challenge/` | 2 chats | humans only: the two mandated scenarios, verbatim | **frozen** |
| `data/test/` | — | dropped (v2.4) | not built |

There is no separate held-out test set (see §12, limitations).

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

`slot_hours_ahead` = hours from the chat's "now" (A4: last message timestamp) to the slot, not
from the request message; `null` when the slot time is unknown. `on_behalf` is also true when the
sender asks about an outlet of a different partner (cross-partner); that is never verified.

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

One long page (`site/index.html`, `app.css`, `app.js`; no build step; design brief in
`docs/design/brief.md`), every view built from `site/data/` (written by
`scripts/build_site_data.py` from the cache: `runs/<chat>.json` are `RunResult`s, plus
`manifest.json`, `policy.json`, `results.json` from the latest dev eval, and `sample.txt`):
1. **Hero** — the problem and the promise; real d07 bubbles stream in and get stamped.
2. **Watch it work** — two pinned, scroll-driven scenes (d01, d07) in six steps: chat arrives →
   noise dims → the model's dockets (with the follow-up's referent line) → roster lookup → all
   rules, the most cautious stamps → the simulated log line (+ security alert for refuse). Below
   861 px or under reduced motion: the same content, static.
3. **How it works** — architecture SVG, model-vs-code split, rules table from `policy.json`;
   hovering a rule highlights where it matched in the demo.
4. **The desk** — five precomputed dev chats (`site/data/`). No API needed.
   - Table: gloss, sender + state badge, grade stamp, rule ID with its text on hover.
   - Click a request → drawer (`<dialog>`): chat with evidence highlighted → extraction →
     identity + reason → rule check (all rules, decider highlighted) → route + simulated log
     record → trace (none in the demo: the API process never traces).
   - Approve/Reject on `seek_approval` items appends to a client-side log (sessionStorage).
5. **Try your own** — paste/upload a chat, optional key, POST to the local API (URL from a
   `<meta>` tag). Progress note with elapsed time; UNPROCESSED shown as a whole-chat hand-off;
   API down → the start command.
6. **Results** — dev metrics, hard gates, grade confusion, approval load, latency, notional cost,
   limitations.
7. **Team** (placeholder names) and GitHub link.

Footer on every page: "Simulation only — no action is executed. Synthetic data only."

**API** (`api/main.py`, FastAPI + uvicorn):
- `POST /api/triage` (chat text + optional key) → `RunResult` with per-stage trace data.
- `GET /api/health`.
- Host, port, CORS origins and the chat size cap from `config/server.yaml`; the loader rejects
  any non-loopback host or origin.
- A visitor key is used only for that request: never stored, logged, part of a cache key or sent
  to Langfuse (tested). Langfuse's drop-in patches the OpenAI SDK process-wide, so the API process
  never traces at all (`llm.TRACING = False`).
- Without a visitor key the server key is capped at `demo_server_key_rpd` (10/day, in memory,
  counting only uncached requests).
- The request runs in FastAPI's worker threadpool; the LLM client's `request_timeout_s` bounds it
  and a timeout returns `UNPROCESSED`.

**One command** (`uv run python -m triage.serve`) starts that process and prints the localhost
URL. Paths are relative and the API URL is configurable, so publishing later needs no code change.

## 12. Evaluation

- **Matching:** predicted ↔ gold by same intent and evidence Jaccard ≥ 0.5, assigned with scipy's
  Hungarian algorithm.
- **Metrics:** detection precision / recall / F1 · attribution accuracy · unconfirmed-sender
  recall · grade accuracy + confusion matrix · over-autonomy rate (overall and high-risk) ·
  rule-citation accuracy · evidence validity · approval load (gold-`act` requests graded
  `seek_approval`) · latency p50 / p95 · tokens + notional cost (paid-variant price; billed $0).
- **No baseline.** Baseline B1 (one prompt that also grades) was dropped in v2.4, so there is no
  number showing how much code-side grading helps over a single prompt.
- **Strict-model mode** for milestones: no fallbacks; paired comparisons only on transcripts
  answered by the same model.
- **Pass rule** (dev, 15 chats, plus challenge, 2 chats: the two mandated scenarios verbatim):
  - Hard gates: high-risk over-autonomy = 0; unconfirmed-sender recall = 1.0; evidence validity =
    100%; both mandated scenarios pass exactly.
  - Targets: detection F1 ≥ 0.85; grade accuracy ≥ 0.85; rule-citation accuracy ≥ 0.90.
- **Limitations (stated plainly):** there is **no separate test set** and **no baseline**. Dev
  chats were written by the same session that writes the prompt and is scored on them, so dev
  scores are optimistic and are not evidence of generalisation. Only the 2 challenge chats are
  human-written and unseen.
- **Results:** `eval/results/<tag>/summary.json` + `report.md`; scores also sent to Langfuse.
  Challenge results store IDs and labels only, never message text.
- **Observability:** Langfuse Hobby keeps data for 30 days, so the durable per-stage record is
  `site/data/*.json` and `eval/results/`. Langfuse links are optional extras.

## 13. Prototypes and request budget

| Tag | Content |
|---|---|
| v0.1 | identity + policy + routing + CLI; eval on dev + 2 challenge chats (P5) |
| v0.3 | website + API running locally (P6) |
| v1.0 | final docs (APPROACH, ARTEFACT, README) (P7) |

v0.2 (test set + B1) was dropped in v2.4.

- Free cap: 50 requests/day, 20/min. A dev + challenge eval ≈ 17 requests; the Phase 4 bake-off
  is 2 models × 10 dev chats ≈ 20 requests.
- 💰 Decision point (not taken): a one-time $10 OpenRouter credit raises the cap to 1,000/day.

## 14. Configuration

| File | Holds |
|---|---|
| `config/models.yaml` | extractor and B1 model IDs (`:free` only, validated), temperature |
| `config/pricing.yaml` | paid-variant list prices for notional cost |
| `config/thresholds.yaml` | name-match threshold, slot cut-off (12 h), rate limits, repair retries, request timeout (300 s), eval evidence Jaccard (0.5), pass-rule targets, `demo_server_key_rpd` |
| `.env` (local, gitignored) | `OPENROUTER_API_KEY`, `LANGFUSE_*` — empty in `.env.example` |

## 15. Assumptions and open questions

- **A1:** Aminobots serves partner outlets with deliveries, orders and payouts.
- **A2:** in scenario 1, "staff member" means partner-side staff.
- **A3:** the slot cut-off is 12 h.
- **A4:** "now" is the timestamp of the chat's last message (§2.8).
- **A5:** `roster.yaml` is the only source of identity (§7).
- **A6:** requests from role `aminobots_staff` are internal (§7): logged, not listed, not scored.

A1–A3 and A6 are unconfirmed (mentor questions: context §7); update SPEC and policy when answered.

## 16. Risks

- Eval runs send synthetic dev/challenge text to OpenRouter free models (free endpoints may log
  prompts) and Langfuse. Accepted: all data is synthetic. Real chats never sent.

## 17. Change log

| Version | Changes |
|---|---|
| v2.0 | Phase 0: simplified design, condensed from context v2 §4. |
| v2.1 | Phase 1: one-process serving under `/api` (§11); phone generation rule (§8); R3 adds critical, R9 needs status open, three new worked checks (§9); `AMBIGUOUS` authority and A6 internal senders (§7, §15); system-line check and date dividers (§3.1, §3.2); observability retention (§12); risks (§16). |
| v2.2 | Phase 2: A4, A5 (§15); fixed roles (§7); nemotron default + gemma fallback, dots removed (§3.3, §13); approval-load metric (§12). |
| v2.3 | Phase 3: parser facts and pre-pass (§3.1), render masking (§3.2), contracts match code (§5), Android-only (§1), gold validator (§8). |
| v2.4 | Phase 4: `slot_hours_ahead` measured from "now" (§9); `handled` = Aminobots staff confirms done (§5); cross-partner ask = unverified on-behalf (§9); `entities.slot_datetime` (§3.3, §5); retired nemotron-3-super replaced by nemotron-3.5-super-vl (§3.3); test set, B1 and v0.2 dropped, pass rule on dev + 2 challenge chats, limitations stated (§8, §12, §13). |
| v2.5 | Phase 5: model outputs `slot_day_offset` + `slot_time`, code computes `slot_datetime`, missing or invalid part → `time_unspecified` (§3.3, §5), known gap stated; `request_timeout_s` 300 (§3.5); prompts v2 and v3; reasoning `low` kept after a trial; schema-aware cache key; principal/outlet and cross-partner rules made precise (§7); `Identity`, `LogRecord`, `RunResult`, `GoldChat.scenario` contracts (§5); pass-rule targets in `config/thresholds.yaml` (§14). |
| v2.6 | Phase 6: `time_unspecified` added by code only to **open** slot changes (§3.3); website + API contracts as built (§11). |
