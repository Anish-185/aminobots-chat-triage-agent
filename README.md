<div align="center">

# 🛎️ Aminobots Chat Triage Agent

**Read the whole group. Stamp only what's real.**

An agent that reads a WhatsApp partner group chat in Telugu–English (mostly romanised) and
lists every real request in it. For each one it shows **who asked** and whether that is confirmed,
a **grade**, the **numbered rule** that decided the grade, and the **message IDs** it relied on.

![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/managed%20with-uv-DE5FE9)
![Tests](https://img.shields.io/badge/tests-323%20passing-2ea44f)
![LLM cost](https://img.shields.io/badge/LLM%20spend-%240-success)
![Simulated](https://img.shields.io/badge/actions-simulated%20only-orange)
![Local only](https://img.shields.io/badge/runs-localhost%20only-lightgrey)
![License: MIT](https://img.shields.io/badge/code-MIT-blue)
![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-blue)

[**Run the demo**](#run-the-demo) · [**What it does**](#-what-it-does) · [**How it works**](#-how-it-works) · [**Results**](#-results) · [**Docs**](#-documentation)

![Scenario 1 stamped by rule R6](docs/screenshots/1440-story-d01-6.jpg)

</div>

> [!IMPORTANT]
> **Simulation only:** no action is ever executed. **Synthetic data only:** every name, outlet and
> phone number is fictional. **Free LLMs only:** $0 billed.

---

## ✨ Highlights

|  |  |
|---|---|
| 🧠 **The model describes; code decides** | The LLM only extracts requests, evidence and flags. Identity, authority, grade and rule are all decided in plain, tested code. |
| 🔻 **Autonomy only goes down** | All ten rules are checked and the most cautious match wins. If nothing matches, the request is handed off. |
| 🧾 **Evidence or it doesn't exist** | Every request cites message IDs. A candidate whose IDs are not in the chat is dropped and logged. |
| 🔒 **Fails closed** | A failed run marks the chat `UNPROCESSED` and hands the whole chat to a person. It is never shown as "no requests". |
| 🎭 **Simulate, never execute** | Each decision appends one `simulated: true` line to a JSONL log. A test proves the action layer imports no network client. |
| 🕵️ **Phones never reach the model** | Senders become `S1…Sn`, numbers in the text are masked, and the UI shows only the last 4 digits. |

---

## 🎯 What it does

### 1 · Read the chat
- **Finds every real request** in Telugu script, romanised Telugu and English, while greetings and banter fade out.
- **Follows a follow-up:** "maa outlet ki kooda *alaage* cheyyandi" ("do the same for our outlet") is linked to the earlier message it refers to.
- **Cites its evidence:** every request lists the message IDs it relies on.
- **Flags what it is unsure of:** injection attempts, forwards, unclear outlets, and asks that nobody actually made (`implicit_request`).
- **Reads delivery slots:** if the model leaves a slot day or time empty, code fills it from the requester's own words, using a Telugu day-word map ("repu", "madhyanam") and `dateparser`.

### 2 · Decide in code
- **Checks who sent it:** the phone number is looked up in a roster and the sender is marked `CONFIRMED`, `AMBIGUOUS` or `UNCONFIRMED`, with a reason. A claim like "I'm the owner" never counts.
- **Checks authority:** each request type has its own list of roles allowed to ask for it, a risk level, and a note on whether it discloses data.
- **Applies ten written rules** ([policy v2](policy/policy_v2.yaml)) with `rule-engine`. All matches are recorded and the cited rule is shown.
- **Knows what's cancelled:** a request withdrawn later in the chat is still tracked, but it is only recorded and nothing is done.

### 3 · Act, simulated
| Grade | Meaning | Goes to |
|---|---|---|
| 🟢 `act` | Safe to do automatically (simulated) | `runs/actions.jsonl` |
| 🟡 `seek_approval` | A person approves or rejects it first | `runs/approvals.jsonl` |
| 🔵 `hand_off` | The team (or finance) takes it over | `runs/handoffs.jsonl` |
| 🔴 `refuse` | Refused, and security gets an alert | `runs/alerts.jsonl` |

### 4 · Prove it
- 🖥️ **A local website** that walks through the system step by step, a request desk with a per-request drawer (chat → model output → roster check → every rule → log line), and approve / reject buttons.
- 🧪 **Try your own chat:** paste an export and the local API runs the real pipeline.
- 📊 **An evaluation harness** with hard gates, targets, a confusion grid, and results by script and by intent.
- 🛡️ **A red-team suite** of 10 attack chats run through [promptfoo](https://www.promptfoo.dev/).
- 🗂️ **An audit trail** of every simulated decision in [Datasette](https://datasette.io/), faceted by grade, rule, identity state and team.

---

## 🖼️ Screenshots

| Watch it work | The desk | Every step, per request |
|---|---|---|
| ![Scenario 1 stamped](docs/screenshots/1440-story-d01-6.jpg) | ![Request table](docs/screenshots/1440-desk.jpg) | ![Request drawer](docs/screenshots/1440-drawer.jpg) |
| **Fraud refused (scenario 2)** | **Try your own** | **Results** |
| ![Scenario 2: bank change refused](docs/screenshots/1440-story-d07-6.jpg) | ![Try your own result](docs/screenshots/1440-try-result.jpg) | ![Results section](docs/screenshots/1440-results.jpg) |
| **Dark mode** | **Phone (375 px)** | **Audit trail** |
| ![Dark mode desk](docs/screenshots/dark-1440-desk.jpg) | ![Hero at 375 px](docs/screenshots/375-top.jpg) | ![Datasette audit trail](docs/screenshots/1440-audit-trail.jpg) |

More in [docs/screenshots/](docs/screenshots/).

---

## ⚙️ How it works

```mermaid
flowchart LR
    A[📄 WhatsApp export<br/>.txt] --> B[parse<br/><sub>chat-miner</sub>]
    B --> C[extract<br/><sub>free LLM · Instructor<br/>prompt v4</sub>]
    C --> D[ground<br/><sub>evidence IDs exist?</sub>]
    D --> E[identity<br/><sub>roster lookup</sub>]
    E --> F[policy<br/><sub>R1–R10 · rule-engine</sub>]
    F -->|act| G1[(actions.jsonl)]
    F -->|seek_approval| G2[(approvals.jsonl)]
    F -->|hand_off| G3[(handoffs.jsonl)]
    F -->|refuse| G4[(alerts.jsonl)]

    classDef llm fill:#fde68a,stroke:#b45309,color:#000
    classDef code fill:#bfdbfe,stroke:#1d4ed8,color:#000
    class C llm
    class B,D,E,F code
```

<sub>🟨 the only LLM step · 🟦 deterministic code. One model call per chat. "Now" is the timestamp of
the chat's last message, so runs are reproducible.</sub>

Editable diagrams: [architecture](docs/architecture.drawio.svg) · [workflow](docs/workflow.drawio.svg)
(diagrams.net; regenerate with `uv run python scripts/make_diagrams.py`).

### The autonomy policy

Every rule is evaluated, the most cautious grade wins, and the lowest-numbered matching rule
with that grade is cited.

| Rule | Grade | When |
|---|---|---|
| **R1** | 🔵 hand_off | Payout details change → finance verifies out of band |
| **R2** | 🔴 refuse | Unconfirmed sender asks for a high/critical-risk action or account data → security alert |
| **R3** | 🔵 hand_off | Complaint, other, or high/critical risk |
| **R4** | 🟡 seek_approval | Sender not confirmed |
| **R5** | 🟡 seek_approval | Sender lacks authority, or an on-behalf request is not verified |
| **R6** | 🟡 seek_approval | Any uncertainty flag |
| **R7** | 🟡 seek_approval | Open medium-risk request, or a slot change less than the cut-off before the slot |
| **R8** | 🟢 act | Not open (cancelled / already handled) → record only |
| **R9** | 🟢 act | Open, confirmed, authorised, risk none or low |
| **R10** | 🔵 hand_off | Default: nothing else matched |

<details>
<summary><b>Request types and their risk</b></summary>

| Intent | Risk | Discloses data | Who may ask |
|---|---|---|---|
| `delivery_slot_change` | low | no | owner, manager, staff |
| `order_change` | medium | no | owner, manager |
| `status_query` | none | yes | owner, manager, staff, accounts |
| `invoice_request` | none | yes | owner, manager, accounts |
| `payout_details_change` | critical | yes | owner |
| `refund_request` | high | no | owner, manager, accounts |
| `complaint` / `other` | — | no | anyone |

History: [policy/CHANGELOG.md](policy/CHANGELOG.md).
</details>

---

## 📊 Results

**Dev split:** 15 chats, 37 gold requests, `nvidia/nemotron-3.5-super-vl:free`, v1.1
([report](eval/results/v1.1-dev/report.md)).

| Metric | Value | Target |
|---|---|---|
| Detection P / R / F1 | 0.90 / 0.95 / **0.92** | F1 ≥ 0.85 ✅ |
| Grade accuracy | **1.00** | ≥ 0.85 ✅ |
| Rule-citation accuracy | **1.00** | ≥ 0.90 ✅ |
| Attribution / identity state | 1.00 / 1.00 | |
| Over-autonomy (all / high-risk) | 0.00 / 0 | gate ✅ |
| Phantom acts | 0 | gate ✅ |
| Evidence validity | 100 % | gate ✅ |
| Unconfirmed-sender recall | 1.00 | gate ✅ |
| Latency per chat (p50 / p95) | 38 s / 197 s | |
| Cost | **$0 billed** (≈ $0.004/chat notional) | |

**Mandated scenarios** ([challenge report](eval/results/v1.1-challenge/report.md)):

- ✅ **Scenario 1:** staff move tomorrow's slot, and another outlet says "alaage" (same for us). Both are graded `act` by R9.
- ✅ **Scenario 2:** an unknown number asks to change bank details. The request is refused by R2 and security gets an alert.

**Red team** ([redteam-v1](eval/results/redteam-v1/)): 7 of 10 attack chats pass every check.
Nothing in any attack chat was stamped `act`, and self-claimed identities never changed the
sender's state. The weak spot is that an injection was flagged only when it sat in the same
message as the ask (1 of 4 cases).

> [!NOTE]
> **Read the scores with care.** The dev scores are fitted: the slot rules were tuned on these
> chats. The challenge chats were generated by the builder and have been seen, so no blind
> test remains. Telugu has not been reviewed by a native speaker. The full error analysis and
> limitations are in [ARTEFACT.md](ARTEFACT.md).

---

## Run the demo

Needs [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
git clone https://github.com/Anish-185/aminobots-chat-triage-agent.git && cd aminobots-chat-triage-agent
uv sync
uv run python -m triage.serve     # → http://127.0.0.1:8000/
```

The story, the desk and the results run from precomputed pipeline output in `site/data/`, so
they **need no key and make no LLM call**.

<details>
<summary><b>🔑 Try your own chat (optional key)</b></summary>

`cp .env.example .env` and fill in `OPENROUTER_API_KEY` locally. Never commit it.

**Try your own** sends a chat to the local API, which runs the real pipeline with the free model
in [config/models.yaml](config/models.yaml). It uses your `.env` key (capped at 10 new requests a
day) or a key typed into the page, which is used once and never stored, logged or traced.
Rebuild the site data from the cache with `uv run python scripts/build_site_data.py`.
</details>

<details>
<summary><b>💻 CLI, tests and evaluation</b></summary>

```bash
uv run pytest                                          # unit tests, no API calls
uv run python -m triage.cli run data/dev/d01.txt       # one chat in the terminal
uv run python -m eval.run_eval --split dev --tag <tag> # eval (cached answers cost nothing)
```
</details>

### Audit trail (Datasette)

Every simulated decision the CLI writes to `runs/*.jsonl` goes into one table you can explore,
with facets on grade, rule, identity state and team (the requester's partner). It runs locally,
and the site's Results section links to it.

```bash
uv run python -m triage.audit                              # runs/*.jsonl → runs/audit.db
uv run datasette runs/audit.db -m config/datasette.yaml    # → http://127.0.0.1:8001/audit/records
```

### Red team (promptfoo)

Ten synthetic attack chats (injection, fake authority, self-claimed identity, a request hidden in
a forward, pure chatter) run through the real pipeline with promptfoo via `npx`. This needs Node
but adds no project dependency. Details and assertions are in
[eval/redteam/README.md](eval/redteam/README.md).

```bash
PROMPTFOO_DISABLE_TELEMETRY=1 uv run npx -y promptfoo@0.125.1 eval -c eval/redteam/promptfooconfig.yaml \
  -j 1 --no-cache -o eval/results/redteam-v1/report.html -o eval/results/redteam-v1/results.json
```

---

## 🧰 Tech stack

| Layer | Tools |
|---|---|
| Parsing | [chat-miner](https://github.com/joweich/chat-miner) |
| Extraction | [Instructor](https://python.useinstructor.com/) + OpenRouter `:free` models, Pydantic v2 |
| Decisions | [rule-engine](https://github.com/zeroSteiner/rule-engine), YAML policy, `dateparser`, `phonenumbers` |
| API & site | FastAPI, static HTML + Tailwind CDN + vanilla JS, GSAP, Lenis |
| Observability | Langfuse (wired in, off by default), Datasette + sqlite-utils |
| Quality | pytest (323 tests), ruff, promptfoo red team, Claude Code hooks guarding frozen eval data |

<details>
<summary><b>📁 Repository layout</b></summary>

```
triage/    parse · extract · ground · identity · slots · policy · route · pipeline · cli · serve · audit
api/       FastAPI app for "Try your own"
site/      static website + precomputed data
policy/    policy_v1.yaml, policy_v2.yaml (in use), CHANGELOG
prompts/   extract/v1–v4 (v4 in use), CHANGELOG
config/    models (:free only), pricing, thresholds, datasette
data/      world/ (roster), dev/ (15 chats + gold), test/ & challenge/ (frozen)
eval/      run_eval, metrics, bake-off, red team, results/<tag>/
docs/      SPEC, functional doc, ADRs, diagrams, screenshots, build prompts
```
</details>

---

## 📚 Documentation

| Doc | What's inside |
|---|---|
| [ARTEFACT.md](ARTEFACT.md) | What was built, prototypes, results, error analysis, limitations |
| [APPROACH.md](APPROACH.md) | Problem scoping, system design, data, evaluation, risks |
| [SPEC v2.9](docs/SPEC.md) | Contracts, policy, evaluation |
| [Functional document](docs/functional.md) | Problem, current process, interventions, user journey, tech construct |
| [Build plan](docs/build-plan.md) | Phases, request budget, risks |
| [Policy v2](policy/policy_v2.yaml) · [Prompt pack](prompts/CHANGELOG.md) | The rules and the prompts, versioned |
| [ADRs](docs/adr/) | Build-vs-reuse, model choice, website |
| [Website design brief](docs/design/brief.md) · [self-review](docs/design/review.md) | How the site was designed |
| [Screenshots](docs/screenshots/) · [Submission checklist](docs/submission-checklist.md) | |
| [Project context](docs/context/PROJECT_CONTEXT.md) | Decisions and the original brief |
| [Build prompts](docs/build-prompts/README.md) · [CLAUDE.md](CLAUDE.md) | How it was built with Claude Code, phase by phase |

**Status:** v1.1 plus the Phase 10 integrations (Datasette audit trail, promptfoo red team). This
is a complete local demo. Tagged prototypes: v0.1, v0.3 and v1.0 (v1.1 is tagged by the human).
The first attempt is kept in `main`'s history (its last commit is `3ca1d2e`).

---

## 📄 Licence

Code: MIT ([LICENSE](LICENSE)). Synthetic data: CC BY 4.0 ([data/LICENSE](data/LICENSE)).
