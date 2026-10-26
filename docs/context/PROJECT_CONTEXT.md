# Context handoff — Aminobots Chat Triage Agent (fresh start)

> **To the assistant reading this:** this file carries the full context of a previous planning
> conversation. Everything in it is a **decision already made**, unless it is marked *open*. Read
> it completely before replying. Your role and the working process are in §1. The original brief is
> in Appendix A, verbatim.

---

## 1. Your role and how we work

**Your role.** You are the project's **core brain and senior engineer**. You do not write the
application code. **Claude Code** writes it, on the human's machine. Your job is to:

1. understand each task the human brings from the Aminobots submission portal;
2. make design decisions and keep them consistent;
3. write **one phase prompt at a time** for Claude Code;
4. review Claude Code's **phase report** when the human pastes it back, decide the open questions,
   and write the next phase prompt with the fixes included;
5. flag every point where money might be needed as a **💰 decision point**. Never assume spending.

**The loop.**

```
human brings task → you write phase prompt → Claude Code builds → Claude Code ends with a phase report
→ human pastes report to you → you decide open questions + write next prompt (fixes included) → …
```

**Phase prompt conventions.** Every phase prompt you write must:

- open by telling Claude Code to save the prompt verbatim to
  `docs/build-prompts/phase-NN-<short-name>.md`;
- ask for a plan first and wait for approval, when the phase touches more than one file;
- tell Claude Code to check the current docs of any library or service before using it, and never
  rely on memory for APIs, versions or prices;
- end with the **phase report**, in exactly these six sections:
  1. **Done** — what was built and the files touched.
  2. **Tests / eval** — commands and results, with failures quoted verbatim.
  3. **Errors / blockers** — full error text.
  4. **Deviations** — anything done differently from the prompt or SPEC, and why.
  5. **Open questions** — SPEC ambiguities left unresolved.
  6. **Proposed commits** — Claude Code commits only when the human says "commit", and pushes only
     when the human says "push".
- never ask Claude Code to create git tags. The human tags prototypes;
- **in any phase that touches an LLM** (writing LLM code, running extraction, running evals,
  bake-offs, or the website's "try your own"), include near the top, verbatim:
  > **Free LLMs only.** Use only OpenRouter models whose ID ends in `:free`, as listed in
  > `config/models.yaml`. Never call a paid model, never add a paid provider or SDK, and never use
  > a key other than `OPENROUTER_API_KEY` from the local `.env`. Before making any LLM call, state
  > which free model and how many requests you will use, and wait for my approval if it is more
  > than 10.

**Human preferences (hard requirements):**

- **As simple as possible.** Reuse existing open-source libraries for every generic job. Install
  them with `uv add`; don't copy their code into the repo. Own code covers only what is specific to
  this project: the prompt, the rules file, the roster, and thin glue.
- **$0 total.** LLM access is through **OpenRouter free models only** (IDs ending in `:free`). All
  hosting is free tier. **Every API key stays empty in the repo**; the human fills a local `.env`.
- **A website, not an app**, to showcase the product (§4.9). **For now it runs locally only.** Do
  not publish or deploy it: no GitHub Pages, no Render, no deploy workflows. Publishing is a later
  decision the human makes explicitly.
- **Free LLMs only, always.** Every phase prompt that involves an LLM must restate the free-LLM rule
  (§1, phase prompt conventions).
- **Phase by phase.** Write prompts one at a time, never all in advance.

---

## 2. Status

- A first attempt existed: repo `aminobots-chat-triage-agent`, phases 0–1b done. The human has
  chosen to **restart from scratch** with the simplified design below.
- **The repo name must stay `aminobots-chat-triage-agent`**, because the submission portal's file
  fields are prefixed with it. Phase 0 must handle the old repo. Recommended: rename the old GitHub
  repo to `aminobots-chat-triage-agent-v0` and archive it, then create a fresh repo under the
  original name. Ask the human to confirm.
- Lessons from the first attempt are in §6. Some files from the old repo can be reused.

---

## 3. Submission portal items known so far

| Portal item | Path / form | Content |
|---|---|---|
| Functional document | `docs/functional.md` | (1) Understanding of the problem · (2) Domain-level context of the current process and its challenges · (3) Proposed interventions · (4) High-level user journey · (5) The tech and agentic construct |
| Approach document | `APPROACH.md` (repo root) | "Who it's for, build-vs-reuse, architecture." It must also satisfy the brief's spec: sections A–E, ≤ 4 pages, linking an architecture diagram AND a workflow diagram |
| Architecture diagram (optional) | `docs/architecture.drawio.svg` | Accepted formats: .drawio, .drawio.svg, .drawio.xml, .svg or .png. Use a real `.drawio.svg` (SVG with the mxfile XML embedded in its `content` attribute, white background, editable in diagrams.net) |
| UX prototype (optional, not graded) | Figma link | skip unless time allows |
| Build plan (optional) | `docs/build-plan.md` | phases, deliverables, exit criteria, budget, risks, owners |
| AI transcript ("one for approach & build") | share link + file upload | a claude.ai share link of the planning chats (the earlier chat AND this new one; use "Update shared chat" before submitting) + one file combining Claude Code session exports (`/export` per session, saved outside the repo) |

Later submissions per the brief: **ARTEFACT.md** (sections a–i), tagged prototypes, a deployed
public URL, an observability view, a prompt pack, and eval results per prototype.

**Note:** the brief eventually requires "a deployed system … at a public URL". The human has chosen
**local-only for now**. Keep the site and API deploy-ready (relative paths, configurable API URL,
CORS origins from config) but add no hosting config. Raise deployment as a decision before the
final submission (§4.11).

---

## 4. The design (v2: simplified, website, zero cost)

### 4.1 One-line summary

A system that reads a WhatsApp-style partner group chat (Telugu–English, mostly romanised) and
returns every real request, each with:

- who asked it, and whether that is confirmed;
- a graded response: `act` / `seek_approval` / `hand_off` / `refuse`;
- the numbered rule that decided the grade;
- the message IDs it relied on.

Every action is **simulated and logged; nothing is executed.**

### 4.2 Core principles (become CLAUDE.md invariants)

1. **The model describes; code decides.** The LLM only extracts requests, evidence IDs, references,
   entities and uncertainty flags. Identity, authority, grade and rule are decided in code.
2. **Autonomy only goes down.** Every rule is evaluated and the most cautious grade wins, so adding
   a rule can only make the system safer. No match → default rule (`hand_off`).
3. **Fail closed.** Errors or uncertainty lead to more human involvement, never less. A failed run
   is marked `UNPROCESSED` and the whole chat is handed off, never shown as "no requests".
4. **Evidence or it doesn't exist.** A candidate whose message IDs are not in the chat is dropped
   and logged.
5. **Simulate, never execute.** The action layer only appends to JSONL logs. A test proves it
   imports no network client.
6. **Frozen eval data.** Never read `data/test/` or `data/challenge/` except through
   `eval/run_eval.py`. Never copy their text into prompts.
7. **No secrets in the repo.**
8. **Deterministic time.** "Now" = the timestamp of the chat's last message.
9. **Synthetic data only.** Phones are `+91` followed by 10 digits starting with 0–5, which is
   provably not a valid Indian mobile. Assert this with `phonenumbers.is_valid_number() == False`.
10. **Zero spend, free LLMs only.** Only `:free` OpenRouter model IDs (enforced by a config
    validator, with a test). No other LLM provider SDKs. State the model and request count before
    any LLM call; ask before more than 10 requests. CI and unit tests never call an LLM.
11. **Prefer libraries.** Any own module over about 150 lines needs a one-line justification.
12. **Local only.** The website and API run on localhost. No deployment config or workflows until
    the human explicitly approves publishing.

### 4.3 Pipeline

```
WhatsApp .txt ──► parse (chat-miner) ──► extract (LLM via OpenRouter :free, Instructor, diskcache, Langfuse)
──► ground (drop invalid IDs) ──► identity (phonenumbers + rapidfuzz + roster.yaml)
──► policy (rule-engine expressions in policy_v1.yaml) ──► route:
     act → runs/actions.jsonl · seek_approval → runs/approvals.jsonl
     hand_off → runs/handoffs.jsonl · refuse → runs/alerts.jsonl   (all simulated=true, append-only)
```

**Rendering for the model:** one line per message, `[m041] 10:42 | S3 "Ravi (Ameerpet)" | text`.
Sender handles S1…Sn are stable within a chat. **Phone numbers are never sent to the model.**
Media lines render as `[image]`.

**Attribution:** the model only names a `primary_msg_id`. The requester is that message's sender,
determined in code.

**Failures:**
- Instructor retries once on validation failure; still failing → `UNPROCESSED` + hand off.
- Rate limit / 429 → stop cleanly; re-running resumes via the cache.
- Calls are sequential with a sleep to respect 20 requests per minute.

### 4.4 Libraries (build vs reuse)

| Job | Reuse | Licence | Own part |
|---|---|---|---|
| Parse WhatsApp exports | **chat-miner** | MIT | none (verify its API and output columns) |
| Call the LLM with a schema | **OpenRouter** `:free` models + **openai** SDK + **Instructor** | MIT | prompt file + Pydantic schema |
| Cache LLM responses | **diskcache** | Apache-2.0 | one decorator |
| Traces / latency / cost | **Langfuse Cloud** Hobby (free: 50k units/month, 2 users, 30-day retention), via its OpenAI drop-in | MIT (OSS) | one import |
| Rules | **rule-engine** (zeroSteiner) — safe expression language, no `eval` | BSD-3 | ~15 lines for most-cautious-wins |
| Identity | **phonenumbers**, **rapidfuzz** | Apache-2.0, MIT | ~30 lines of lookup |
| Validation | **pydantic** v2 | MIT | schemas |
| Eval | **scikit-learn**, **scipy** (Hungarian matching) | BSD | small eval script |
| API | **FastAPI** + uvicorn | MIT/BSD | one endpoint |
| Website (local) | static HTML + **Tailwind** (CDN) + vanilla JS, from an MIT-licensed landing-page template (licence verified, attribution kept) | MIT | content + demo panel |
| Tooling | uv, ruff, pytest, pre-commit, gitleaks, GitHub Actions | permissive | config |

**Rejected:**

| Rejected | Why |
|---|---|
| Own policy evaluator | rule-engine does the job |
| Own trace store | Langfuse |
| Postgres / Neon / SQLAlchemy | JSONL logs are enough |
| LLM-based data generator | hand-written synthetic chats |
| Streamlit | human wants a website; it also sleeps |
| Hugging Face Spaces | Docker and Gradio Spaces now need a paid plan |
| LangGraph / Burr | not an agent loop |
| ReAct tool-agent | autonomy decision would be unauditable; injection risk |
| LLM Guard | archived 9 July 2026 |
| whatstk | GPL-3.0 |
| IndicLID / IndicXlit / promptfoo / chunking | cut for simplicity; candidates for later |

### 4.5 Intents (8)

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

**Working assumption A1:** Aminobots serves partner outlets with deliveries, orders and payouts.
**A2:** in scenario 1, "staff member" means partner-side staff. **A3:** the slot cut-off is 12 h.
All three are unconfirmed; they are listed among the mentor questions (§7).

### 4.6 Identity (3 states)

| State | Rule |
|---|---|
| `CONFIRMED` | phone is in the roster and not marked shared |
| `AMBIGUOUS` | phone is marked shared, OR phone unknown and the display name matches 2+ roster contacts |
| `UNCONFIRMED` | phone unknown, with 0 or 1 name match |

Additional rules:
- A self-claim ("idi naa kotha number, Suresh" — *this is my new number*) or in-chat vouching
  **never** confirms a sender.
- A "security code changed" line for the same sender before the request downgrades `CONFIRMED` to
  `UNCONFIRMED`.
- **Principal:** "maa outlet" (*our outlet*) resolves to the sender's outlets. 2+ outlets → flag
  `outlet_ambiguous`. An on-behalf request is verified only if the roster lists the sender as a
  delegate.
- A `reason` string is stored for every identity decision and shown on the website.

### 4.7 Autonomy policy v1 (`policy/policy_v1.yaml`, rule-engine expressions)

Grade order: `act` > `seek_approval` > `hand_off` > `refuse`. The most cautious matching grade
wins. The cited rule is the lowest-numbered rule with that grade. All matched rules are recorded.

| Rule | Condition | Grade |
|---|---|---|
| R1 | intent is `payout_details_change` | hand_off (finance, out-of-band verification) |
| R2 | sender `UNCONFIRMED` and (risk high/critical or discloses account data) | **refuse** + security alert |
| R3 | intent `complaint` or `other`, or risk high | hand_off |
| R4 | sender not `CONFIRMED` | seek_approval |
| R5 | sender lacks authority for the intent, or on-behalf request not verified | seek_approval |
| R6 | any uncertainty flag (referent unresolved, outlet ambiguous, time unspecified, intent unclear, possible forward, injection attempt) | seek_approval |
| R7 | risk medium, or slot change < 12 h before the slot | seek_approval |
| R8 | status not open (cancelled / already handled) | act (record only) |
| R9 | sender `CONFIRMED`, authorised, risk none/low | **act** |
| R10 | default — nothing else matched | hand_off |

**Worked checks (must be unit tests):**

| Case | Result |
|---|---|
| Scenario 2: unknown number, payout change | refuse, cite R2 (R1 also matched) |
| Scenario 1: staff slot change, `CONFIRMED`, ≥ 12 h away | act, R9 |
| Scenario 1 follow-up "maa outlet ki kooda alaage cheyyandi", sender `CONFIRMED` with 1 outlet | act, R9 |
| Same follow-up, sender has 2 outlets | seek_approval, R6 |
| Same follow-up, sender unknown | seek_approval, R4 |
| Cancelled request from a `CONFIRMED` sender | act, R8 (record only) |

### 4.8 Data

- Input format is **WhatsApp `.txt` exports only**, with gold JSON alongside. Message IDs are
  m001… in parse order. The author is a phone number or a saved name; a name maps to a phone via an
  optional `contacts.yaml`.
- `data/world/roster.yaml`: partners, outlets and contacts. Include a shared phone, two contacts
  with the same first name, an owner with 2 outlets, an `accounts` role, a delegate, and
  Aminobots-staff contacts.

| Split | Size | Written by | Status |
|---|---|---|---|
| `data/dev/` | ~15 chats | Claude Code (Telugu reviewed by a teammate) | used for development |
| `data/test/` | ~15 chats | the team, outside the repo session (e.g., in a separate AI chat with different names) | **frozen** |
| `data/challenge/` | 8–10 chats | humans only; both mandated scenarios verbatim + adversarial cases (vouching, injection, cancellations, forwards, split requests, on-behalf) | **frozen** |

- Noise to include in every chat: greetings, "ok sir 👍", forwards, `[image]` lines, festival
  wishes, mixed scripts, spelling variants (cheyyandi / cheyandi; repu / repuu).
- Data licence: CC BY 4.0. Code licence: MIT.

### 4.9 Website + API (local only for now)

**Static site** (`site/`), served locally with `python -m http.server` (or FastAPI's static files
mount, whichever is simpler; verify), at e.g. `http://localhost:8000`. Not published. Sections:

1. **Home:** the problem, a one-line solution, the two scenarios.
2. **How it works:** the architecture SVG, the model-vs-code split, and the rules table rendered
   from a JSON export of the policy.
3. **Live demo:** precomputed results for the sample chats from `site/data/*.json`, produced by the
   real pipeline via a build script. Opens instantly; uses no API.
   - The request table shows gloss, sender + state badge, grade badge, and the rule ID with its
     text on hover.
   - Clicking a request opens a step-by-step panel: parsed chat with evidence highlighted →
     extraction output → identity decision + reason → rule check table (all rules, matched yes/no,
     decider highlighted) → route + simulated action → Langfuse trace link.
   - Approve/Reject on `seek_approval` items appends to a **client-side** simulated action log
     (sessionStorage).
4. **Try your own:** paste or upload a chat, with an optional "your OpenRouter key" field, and
   POST it to the local API (the API URL is configurable). If the API isn't running, show a clear
   message with the command to start it.
5. **Results:** eval metrics per prototype, the pass-rule table, and a link to the Langfuse
   dashboard.
6. **Team** (placeholder names) and a GitHub link.

Footer on every page: "Simulation only — no action is executed. Synthetic data only."

**One command to run everything locally** (e.g. `uv run python -m triage.serve` or a `make serve`
target) that starts the API and serves the site, and prints the localhost URL. The README
documents it.

**Deferred hosting option** (only if the human approves publishing later): GitHub Pages for
`site/` + Render free for `api/` (sleeps after 15 min idle; 30–60 s cold start; ephemeral
filesystem). Hugging Face Spaces is not free for Docker/Gradio.

**API** (`api/main.py`, FastAPI), run locally with `uvicorn`.
- `POST /triage` (chat + optional key) → full result with per-stage trace data. Free OpenRouter
  models only.
- `GET /health`.
- CORS: localhost only. Allowed origins come from config, so publishing later needs no code
  change.
- The visitor's key is used only for that request; it is never stored, logged or sent to Langfuse
  (tested).
- Without a visitor key, the server key is capped at `demo_server_key_rpd: 10`.

### 4.10 Evaluation

- **Matching:** predicted ↔ gold by intent + evidence Jaccard ≥ 0.5, assigned with scipy's
  Hungarian algorithm.
- **Metrics:**
  - detection precision / recall / F1
  - attribution accuracy
  - **unconfirmed-sender recall**
  - grade accuracy + confusion matrix
  - **over-autonomy rate** (overall and high-risk intents)
  - rule-citation accuracy
  - latency p50 / p95
  - tokens + **notional cost** (tokens × the paid variant's list price; billed cost = $0)
- **Baseline B1:** one prompt that does everything, including grading, on the same model. It
  exists to show, with numbers, why code must decide.
- **Strict-model mode** for milestone runs: no fallbacks. A transcript whose model is unavailable
  stays pending. Paired comparisons count only transcripts answered by the same model.
- **Pass rule.** Evaluated on test + challenge; dev is for development only.
  - *Hard gates:* high-risk over-autonomy = 0; unconfirmed-sender recall = 1.0; evidence validity =
    100%; both mandated scenarios pass exactly.
  - *Targets:* detection F1 ≥ 0.85; grade accuracy ≥ 0.85; rule-citation accuracy ≥ 0.90.
- **Results:** `eval/results/<tag>/summary.json` + `report.md`, scores also pushed to Langfuse.
  Test and challenge results store IDs and labels only, never message text.

### 4.11 Prototypes and request budget (50 free requests/day)

| Tag | Content |
|---|---|
| v0.1 | CLI end-to-end on dev + eval |
| v0.2 | full identity/policy + test/challenge eval + B1 |
| v0.3 | website + API running locally (deployment deferred) |
| v1.0 | final docs (APPROACH, ARTEFACT, README) |

- A dev iteration costs about 15 requests.
- A milestone eval costs about 65 requests (pipeline on dev + test + challenge, B1 on test +
  challenge). That is about 1–2 days at 50/day.
- 💰 **Decision point:** a one-time $10 OpenRouter credit purchase permanently raises the cap to
  1,000 requests/day while free models stay $0. **Not taken**; re-ask only if cadence becomes the
  bottleneck.

### 4.12 Proposed phase plan (adjust as tasks arrive)

| Phase | Content |
|---|---|
| P0 | Repo init (handle old repo), CLAUDE.md, docs/SPEC.md (v2, ≤ 350 lines), docs/functional.md, .gitignore, README |
| P1 | Bootstrap: uv project, deps, config (+ `:free` validator), CI, pre-commit, gitleaks, eval-data guard, Claude Code hooks, ADRs, LICENSE files |
| P2 | Submission docs: APPROACH.md, `docs/architecture.drawio.svg`, `docs/workflow.drawio.svg`, `docs/build-plan.md` |
| P3 | Schemas, parse (chat-miner), roster, ~15 dev chats + gold, gold validator |
| P4 | Extract + ground + cache + Langfuse; **free-model bake-off** (3 models × ~10 chats ≈ 30 requests); reasoning off/low |
| P5 | Identity + policy + routing + CLI + eval script → **v0.1** |
| P6 | Human test/challenge sets, B1, milestone eval → **v0.2** |
| P7 | Website + API, local only (one serve command, README instructions) → **v0.3** |
| P8 | Error analysis + prompt iteration (dev only) + hardening |
| P9 | ARTEFACT.md, final APPROACH/README, links check → **v1.0**. Before this: ask the human whether to publish (the brief requires a public URL) |

---

## 5. Verified facts to rely on (checked October 2026)

| Topic | Fact |
|---|---|
| OpenRouter limits | 20 requests/min; 50 requests/day on accounts that have bought under $10 of credits; 1,000/day once $10+ has ever been purchased. Free models get rate-limited at peak times and rotate out without warning. Retries count against the quota. |
| Candidate free models (metadata read 2026-10-10, not yet tested) | `nvidia/nemotron-3-super-120b-a12b:free` (262k ctx; supports structured_outputs + response_format; paid variant $0.08/$0.45 per M) · `google/gemma-4-31b-it:free` (262k ctx; response_format only → Instructor JSON/MD_JSON mode; paid $0.09/$0.34) · `dots-studio/dots-3-note-preview:free` (512k ctx; structured_outputs; no paid variant). All expose reasoning params → run with reasoning off/low. |
| Instructor + OpenRouter | `instructor.from_provider("openrouter/<id>")` reads `OPENROUTER_API_KEY`; modes TOOLS / JSON_SCHEMA / JSON / MD_JSON. Use JSON_SCHEMA where structured_outputs is listed. With Langfuse, wrap the instrumented OpenAI client pointed at OpenRouter's base URL (verify in docs). |
| Free-model privacy | Some free providers may log prompts. Acceptable only because all data is synthetic; real partner chats must never be sent. Enable the matching OpenRouter privacy setting only for this project. |
| Langfuse | Cloud Hobby: free, 50k units/month, 2 users, 30-day data access. OpenAI SDK drop-in instrumentation. MIT open source; acquired by ClickHouse in Jan 2026 and remains open source. |
| rule-engine | `pip install rule-engine`, BSD-3. Expressions are evaluated against dicts. It uses its own parser, not `eval`, so it is safe for configurable rules. Check list syntax (`in`, length) in its docs. |
| chat-miner | MIT; parses WhatsApp (and other platforms) exports into dataframes. Its test cases include messages starting with U+200E and emojis in author names. |
| Render free | Sleeps after 15 min idle; 30–60 s cold start; ephemeral filesystem; 750 free instance-hours/month per workspace. |
| GitHub Pages | Free for public repos; deploy via an Actions workflow. |
| Hugging Face Spaces | Gradio/Docker Spaces now require a paid plan; the Streamlit SDK was deprecated in favour of the Docker template. **Not usable for free.** |
| Claude Code | Project hooks load only when the session starts from the repo root. A version ≥ 2.1.295 is needed for `onFailure: "block"`. `/export` saves a session transcript; `claude --resume` reopens old sessions. |
| Research on romanised text | Khullar et al. (2025), "Script Gap: Evaluating LLM Triage on Indian Languages in Native vs Roman Scripts in a Real World Setting", arXiv:2512.10780 — romanised messages trail native script by 5–12 F1 points; Telugu traffic was mostly romanised. Das et al. (2026), "Indi-RomCoM", arXiv:2606.30790 — performance degrades as code-mixing density rises. Used to justify per-script eval slicing (simple heuristic: Telugu Unicode block vs. romanised lexicon vs. English). |
| Phone numbers | No official fictional range for Indian mobiles exists, hence the +91 + leading 0–5 rule. |
| LLM Guard (protectai) | Archived 9 July 2026; do not depend on it. Injection is neutralised structurally (the model cannot change grades) and flagged as `injection_attempt`. |

---

## 6. Lessons from the first attempt (reuse what worked)

- **uv** project with Python 3.12 (`requires-python >=3.11`); `uv sync --locked` in CI. CI used
  checkout v7, setup-uv v10 and gitleaks-action v3 with only the automatic token. Re-verify these
  versions.
- **Guards that worked:**
  - `.claude/hooks/guard_paths.py` blocks Write/Edit/Read/Grep/Glob on frozen data.
  - `guard_bash.py` blocks any command that mentions frozen folders, plus `git tag` and
    `git push --force`.
  - `format_py.py` runs ruff format after edits.
  - `scripts/guard_eval_data.py` is a pre-commit hook rejecting adds, modifies, deletes and renames
    under `data/test` and `data/challenge` unless `ALLOW_EVAL_DATA_COMMIT=1`.

  If the old repo still exists, Claude Code may copy these files from it instead of rewriting them.
- **Config validator** rejecting non-`:free` model IDs, with a test.
- The **human** must live-test the git guard (Claude's hooks rightly block it from doing so).
- Claude Code's ADRs ran slightly long; keep them to ≤ 25 lines.
- Config values that can't be verified are set to `null` with a TODO; never guessed.
- `demo_server_key_rpd: 10` ("shares the 50/day quota; leaves 40/day for development"). With
  local-only hosting this matters only if the site is published later.

---

## 7. Open questions for Aminobots mentors (*open* until the human reports answers)

1. Will they provide API credits or a key, or is the OpenRouter free tier / local inference fine?
2. Will they share a sample of their real autonomy policy, and when? (The brief says to build
   against it if shared; our rules file must be easy to swap.)
3. What does Aminobots actually do, and what are the 5–10 most common partner requests? (This
   confirms or corrects A1.)
4. How will they evaluate — their own hidden chats? In what format?
5. What's worse: over-acting or missing a request?
6. Do they keep a roster of partner numbers and roles? How do they verify senders today?
7. Can someone review our synthetic chats for realism?
8. Does our design (one LLM step, code decides) match their expectations, or do they expect
   "more agentic"?

Others: "staff member" in scenario 1 (A2) · real slot cut-off (A3) · Telugu script vs. Roman
ratio · voice notes/photos frequency · whether replies to the group are wanted · acceptable hosting
· target thresholds.

When answers arrive, update SPEC, policy and assumptions in the next phase prompt.

---

## 8. What to do first in this new chat

1. Reply with a **short** confirmation of your understanding (≤ 10 bullets), plus any
   contradictions you spot in this file.
2. Ask the human **one** question: has the old repo been renamed/archived, and are there any
   mentor answers yet?
3. Then produce, as downloadable files:
   - `CLAUDE.md` — invariants from §4.2, layout, conventions, commands, phase-report format,
     working style;
   - `docs/SPEC.md` v2 — §4 condensed to ≤ 350 lines, numbered sections;
   - `docs/functional.md` — the five portal points; consistent with §4; Mermaid diagrams allowed;
     functional language;
   - the **Phase 0 prompt** for Claude Code: create the fresh repo, place the three files, add
     `.gitignore` + a minimal README, save the prompt, commit, ask public/private (recommend
     public), `gh repo create`, push, phase report. (This creates the GitHub *code* repository
     only. Nothing is published as a website.)

---

## Appendix A — Original brief (verbatim)

Aminobots has brought this problem to your team. Partner support runs through hundreds of group chats. Requests arrive buried in ordinary chatter — greetings, forwards, acknowledgements, photos — in a mix of Telugu and English, often typed in Roman script, sometimes split across several messages or made on someone else's behalf. Many senders cannot be confirmed: a new number, a shared phone, a display name that matches two people. Someone has to read each group, decide what counts as a request, work out who asked, and then decide how much can be done without checking with anyone — act, ask for approval, hand off to a person, or refuse. Done by hand, that decision is slow and hard to keep consistent.

Aminobots wants a system that finds and attributes each request, then decides how much the assistant may do alone and states the rule behind that choice.

Your task
Build a system that takes a group-chat transcript and returns a clear list of the requests in it — each attributed to the person who made it, each with a graded response (act, seek approval, hand off, or refuse) and the rule that justifies that grade. The system applies a written autonomy policy — a short, numbered set of rules — and every graded response cites one of them. If Aminobots shares a sample of its own policy during the project, build against it; until then, your team writes the policy. Chats are mainly Telugu and English, mixed freely; handling Hindi as well is optional.

How the system behaves is the core of this build. It should list only requests that are really in the chat, attribute each to the sender the evidence supports — and say so when a sender cannot be confirmed — never do more than its policy allows, and show the messages each decision relied on. Which kinds of request and sender situation your system handles, how it behaves on each, and how you know it behaves that way is your design.

Two situations your system has to handle:

In a busy day of one partner group, a staff member asks — half in Telugu — to move tomorrow's delivery slot, and a few messages later someone else replies "maa outlet ki kooda alaage cheyyandi".
A message from a number nobody in the group has used before asks for the bank account on file to be changed before today's payout.
Project principle (from Aminobots): Work from synthetic transcripts only; simulate and log every action, never execute it.

Data
No data is provided, and the project principle means you work from synthetic transcripts only. What chats you create, how many, and how you make them as messy as a real partner group are your team's decisions — make them, and defend them in APPROACH.md.

Whatever you bring, record where it came from, its licence and how anything synthetic was generated; keep the data you evaluate on separate from the data you build against; and never use a real person's personal data without their consent.

Approach document spec
APPROACH.md at the repository root is the entry point to your design. Keep it short — up to 4 pages — and link out to diagrams, tables and supporting documents rather than writing everything as prose. It must include or link to an architecture diagram (the components, models, data stores and tools, and how a request flows through them) and a workflow diagram (the steps from input to output, where a model decides and where plain code decides, where a person approves, and what happens on failure). Organise it in these sections:

A. Problem scoping — the user and the decision or task they need help with, the input as it really arrives, the capabilities you build and those you deliberately defer, and how you will know the system works, stated so it can be measured.
B. System design — the steps, what each receives and returns, where a model decides and where plain code decides, the agent pattern you chose and the alternative you rejected, where a person approves, and what happens when the system cannot answer or a step fails.
C. Data and knowledge — the data you chose or created and why it is a fair test of the problem, where it came from and its licence, how anything synthetic was generated, how your evaluation data is kept separate, and how the system's knowledge is represented and retrieved.
D. Evaluation framework — the metrics that measure this problem well (not a single generic accuracy number) and why you chose them, the cases you test — including those the system must refuse or hand off — the pass rule, and what you compare against.
E. Risks and responsibility — what a wrong output does to the person relying on it, how the project principle is enforced in the system, and one trade-off you made deliberately and what it cost.
What your solution must demonstrate
Finding the actual requests in noisy, code-mixed Telugu–English group chat — including requests split across messages or made on someone else's behalf — and attributing each to its sender, with an explicit state for senders who cannot be confirmed.
A written, numbered autonomy policy that the system applies consistently, with every graded response citing the rule that decided it.
A human approval step wherever your policy requires one, and a simulated, logged action layer for everything the system decides to do.
An agent design whose pattern you can justify for this problem, including which decisions belong to a model and which to plain code.
An evaluation framework with metrics chosen for this problem — what a practitioner working on it would measure — run on every prototype, with accuracy, latency and cost measured on the running system and visible in its observability.
A deployed system someone outside your team can use, whose handling of any input can be inspected step by step.
Execution & submission
Build the system through working prototypes rather than all at once at the end. Keep each prototype as a tagged version in the repository — from the first end-to-end slice to the final system — so that how it grew is visible. Deploy the final system at a public URL that someone outside your team can open and use.

The repository must contain: a README that lets someone else set up and run the system from scratch; APPROACH.md and ARTEFACT.md together with everything they link to — diagrams as images or as the source files that produce them; the code, together with the code or prompts that generated any data you created; a prompt pack — every prompt the system runs on, kept as versioned files; your evaluation framework — the evaluation set, the code that runs it, and the committed results for each prototype; an observability view — a dashboard, trace view or metrics page — showing your problem's metrics alongside accuracy, latency and cost; and the coding-agent setup your team built with — rules files, the specification, and any subagents, hooks or reusable prompts. Keep secrets and API keys out of the repository.

ARTEFACT.md contract
ARTEFACT.md at the repository root is the entry point to your evidence and your team's self-audit. Use tables, charts and screenshots where they show more than prose, and link to the files that hold the detail. State:

a) What was built — what the system does today, and what you designed but did not build.

b) Prototypes — each tagged prototype, what it could do, what the evaluation showed, and what you changed next because of it.

c) Data provenance — every dataset or generator used, its source and licence, and what it does and does not represent of the real problem.

d) Autonomy policy — where the policy lives, how its rules were chosen, and how a rule is matched to a request.

e) Evaluation results — the metrics in your evaluation framework and the results for each prototype, the pass rule, and the cases your evaluation does not cover.

f) Accuracy, latency and cost — measured on the deployed system for each kind of request it handles, with a link to the observability view the numbers come from.

g) Prompt pack — where the prompts live, what each one is for, the output it expects, and what changed between versions and why.

h) Known limitations — where the system breaks, and where it should not be trusted.

i) Ownership — which team member owned which component.

State what you decided and measured — not a running commentary on how you got there.
