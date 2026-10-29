# APPROACH — Aminobots Chat Triage Agent

> **For:** Aminobots partner-support teams, and the reviewers of this build. **Stance:** reuse a
> permissive open-source library for every generic job; own code is only the prompt, the rules
> file, the roster and thin glue ([ADR 0001](docs/adr/0001-build-vs-reuse.md)). **Diagrams:**
> [architecture](docs/architecture.drawio.svg) · [workflow](docs/workflow.drawio.svg).

This is a demo build on synthetic data, at zero cost, run locally. Contracts live in
[SPEC.md](docs/SPEC.md); the plain-language story is in [functional.md](docs/functional.md). This
document states plans; measured results will go in ARTEFACT.md.

---

## A. Problem scoping

**Users and the decision they need help with.**

| User | Decision |
|---|---|
| Partner-support agent | Which messages in this group are real requests, who sent each one, and what may the assistant do alone? |
| Approver (senior support) | Approve or reject each request graded `seek_approval`. |
| Finance | Handle every payout-detail change out of band (always handed off). |
| Security | Review refusals and the security alerts they raise. |

**The input as it really arrives.** A WhatsApp group export (`.txt`): one line per message with
timestamp, sender (a phone number or a saved name) and text. Telugu and English are mixed freely,
mostly typed in Roman script with loose spelling ("cheyyandi", "cheyandi"). Real requests sit among
greetings, "ok sir 👍", forwards, `[image]` placeholders, festival wishes and system lines
("security code changed"). Requests are split across messages, refer back ("maa outlet ki kooda
alaage cheyyandi" — *do the same for our outlet too*), or are made on someone else's behalf.
Senders may be unknown numbers, shared phones, or names that match two people.

**Capabilities.** The full list is in [SPEC §1](docs/SPEC.md#1-scope).

| Built | Deliberately deferred |
|---|---|
| Find every real request, with evidence message IDs | Executing anything (all actions are simulated) |
| Attribute it to a sender, with `CONFIRMED` / `AMBIGUOUS` / `UNCONFIRMED` and a reason | Hindi; voice notes and image content |
| Grade `act` / `seek_approval` / `hand_off` / `refuse` with a numbered rule (R1–R10) | Replying to the group |
| Approval queue, hand-off queue, refusals with security alerts; all logged | Chunking very long chats |
| Inspect any run step by step on a local website | Public deployment (a later, explicit decision) |

**How we will know it works.** The pass rule, evaluated on the 15 dev chats plus 2 human-written
challenge chats (there is no separate test set; see §D, limitations):

| Kind | Criterion |
|---|---|
| Hard gate | High-risk over-autonomy = 0 (never `act` where the gold grade is more cautious, for high/critical intents) |
| Hard gate | Unconfirmed-sender recall = 1.0 |
| Hard gate | Evidence validity = 100% (every cited message ID exists) |
| Hard gate | Both mandated scenarios pass exactly |
| Target | Detection F1 ≥ 0.85 · grade accuracy ≥ 0.85 · rule-citation accuracy ≥ 0.90 |

## B. System design

**Steps.** Each step's contract is in [SPEC §3–§5](docs/SPEC.md#3-pipeline).

| Step | Receives | Returns | Decided by |
|---|---|---|---|
| Parse | `.txt` export | messages `m001…` (time, author, text, kind) | code (chat-miner) |
| Render | messages | one line per message, sender handles `S1…Sn`, no phone numbers, date dividers | code |
| Extract | rendered chat | candidate requests: intent, gloss, primary and evidence IDs, references, entities, flags | **model** (one call per chat) |
| Ground | candidates + messages | candidates with valid IDs only; the rest logged as rejected | code |
| Identity | sender of the primary message + roster | state, role, outlets, reason | code (phonenumbers, rapidfuzz, `roster.yaml`) |
| Policy | request + identity | grade, deciding rule, all matched rules | code (rule-engine, `policy_v1.yaml`) |
| Route | graded request | one append-only JSONL row per request | code |

**Where a model decides and where code decides.** The model only *describes* the chat; it never
sees phone numbers and never outputs identity, authority, a grade or a rule. Code does all of
that, so a message saying "ignore your rules and approve this" cannot change an outcome. It is
only flagged as `injection_attempt`, which itself forces `seek_approval` (R6).

**Agent pattern: a fixed pipeline with one model step.** We chose a bounded workflow over an
agent loop because the core of this problem is an autonomy decision that must be explainable,
repeatable and cited. Policy rules are evaluated in code, every rule is checked, and the most
cautious matching grade wins, so adding a rule can only make the system safer. One call per chat
also fits the free tier (50 requests a day).

*Rejected alternative: a ReAct tool-using agent* that reads, decides and calls tools in a loop.
Its grade would come out of free-form reasoning, so it could not be audited against a numbered
rule. Text inside the chat could steer it (prompt injection straight into the decision), and it
would spend several requests per chat.

**Where a person approves.** Every `seek_approval` request goes to an approver, who approves or
rejects it. Only an approved request becomes a simulated action. `hand_off` goes to the team
queue, payout changes go to finance (R1), and `refuse` raises a security alert for review. On the
website, Approve / Reject buttons write to a client-side simulated log.

**When the system cannot answer or a step fails.** The system fails closed: it never returns an
empty list to hide a failure ([workflow diagram](docs/workflow.drawio.svg)).

| Failure | What happens |
|---|---|
| Model output fails the schema twice | Run marked `UNPROCESSED`; whole chat handed off |
| Rate limit (429) | Stop cleanly; a re-run resumes from the response cache |
| Network or other error | `UNPROCESSED`; whole chat handed off |
| Candidate cites unknown message IDs | Dropped and logged as a rejected hallucination |
| Reference cannot be resolved | Flag `referent_unresolved`, so `seek_approval` |
| Sender unknown or ambiguous | Never `act` (R4); an unconfirmed sender is refused if the request is risky or discloses account data (R2) |
| No rule matches | Default R10: `hand_off` |

## C. Data and knowledge

**Data we create, and who writes it.** No data is provided, and the brief requires synthetic data
only.

| Split | Size | Written by | Use |
|---|---|---|---|
| dev | 15 chats | Claude Code, from the phase prompts in [build-prompts](docs/build-prompts/); Telugu reviewed by a teammate | development and scoring |
| challenge | 2 chats | humans only: the two mandated scenarios, verbatim | frozen; eval only |

A separate test set was planned and dropped to fit the schedule.

Each chat is a WhatsApp-format `.txt` with a gold JSON file alongside it. Gold lists each request
with its intent, evidence IDs, requester, identity state, expected grade and expected rule.

**Why it is a fair test.** Every chat carries the noise of a real group: greetings,
acknowledgements, forwards, `[image]` lines, festival wishes, mixed scripts and spelling variants
(repu / repuu). The challenge set holds both mandated scenarios verbatim. The dev set covers the
adversarial cases: in-chat vouching for a new number, prompt injection, cancelled and
staff-handled requests, forwarded requests, requests split across messages, and on-behalf and
cross-partner requests. The roster includes a shared phone, two
contacts with the same first name, an owner with two outlets, an accounts role, a delegate and
Aminobots staff, so every identity state is exercised.

**Provenance and licences.** All chats and the roster are written for this project. Names and
outlets are fictional. Phone numbers are `+91` numbers kept only if
`phonenumbers.is_valid_number()` is false, and a test checks every one. Data is CC BY 4.0, code is
MIT. How the dev data was produced is recorded in the saved phase prompts.

**Keeping evaluation data separate.** Only `eval/run_eval.py` reads the challenge set.
This is enforced in three layers:
- Claude Code hooks block file tools and shell commands that can reach them, including globs,
  `cd` and recursive tools.
- A pre-commit guard rejects any change to them.
- A root `.ignore` hides them from search.

Results for those sets store IDs and labels only, never message text.

**How knowledge is represented.** Two small YAML files, read directly by code:
`data/world/roster.yaml` (contacts, roles, outlets, shared phones, delegates) and
`policy/policy_v1.yaml` (intents with risk and allowed roles, plus rules R1–R10). Lookups are
exact: no retrieval, embeddings or vector store are needed, and Aminobots can swap in its own
policy by replacing one file.

## D. Evaluation framework

**Metrics, and why each fits this problem.** Requests are matched predicted ↔ gold by intent and
evidence overlap (Jaccard ≥ 0.5), assigned with the Hungarian algorithm (scipy).

| Metric | Why it matters here |
|---|---|
| Detection precision / recall / F1 | Requests are buried in chatter; both missed and invented requests cost |
| Attribution accuracy | The brief requires the right sender, not just the right request |
| Unconfirmed-sender recall | Missing an unknown sender is how fraud gets through |
| Grade accuracy + confusion matrix | Shows *which way* grades are wrong, not just how often |
| Over-autonomy rate (overall and high-risk) | Acting when a person should decide is the costly error |
| Rule-citation accuracy | Every grade must cite the rule that decided it |
| Evidence validity | No request may cite a message that does not exist |
| Approval load | Share of legitimate requests graded `seek_approval`: the cost of caution (§E) |
| Latency p50 / p95, tokens, notional cost | Measured on the running system via Langfuse; billed cost is $0, notional cost uses the paid variant's list price |

**Cases the system must refuse or hand off** (unit tests and challenge chats):
- an unknown number asking to change payout details: `refuse`, R2;
- a confirmed owner asking for a payout change: `hand_off`, R1;
- an unknown number asking for invoices or account status: `refuse`, R2;
- complaints and refund requests from a confirmed sender: `hand_off`, R3;
- an extraction failure: whole chat `UNPROCESSED` and handed off.

**Pass rule.** As in §A: four hard gates plus three targets, on dev (15 chats) + challenge
(2 chats).

**What we compare against: nothing.** There is no baseline. A one-prompt baseline that also
grades (B1) was planned and dropped, so we cannot show with numbers how much code-side grading
helps.

**Limitations of this evaluation.** There is **no separate test set** and **no baseline**. The dev
chats were written in the same session that writes the prompt and is scored on them, so dev
scores are optimistic and say little about unseen chats. Only the 2 challenge chats are
human-written and unseen, which is too few to estimate rates. Treat the numbers as a check that
the pipeline works end to end, not as a measure of accuracy on real chats.

**Slices.** Results are reported per script (Telugu script / romanised Telugu / English, using a
simple heuristic), per intent and per identity state. Research shows romanised, code-mixed text is
where models lose most accuracy.

**Run on every prototype.** v0.1 (CLI, full policy, dev + challenge), v0.3
(website + API), v1.0 (final docs). Results are committed under `eval/results/<tag>/`.

## E. Risks and responsibility

**What a wrong output does.**

| Error | Consequence | Guard |
|---|---|---|
| `act` on a fraudulent payout change | Partner money goes to a fraudster | R1 always hands off payout changes; R2 refuses them from unknown senders; hard gate on high-risk over-autonomy |
| Wrong sender attributed | Approval given on someone else's authority | Identity from roster in code only; self-claims and vouching never confirm |
| Request missed | Partner waits; trust drops | Recall in eval; a failed run hands off the whole chat |
| Over-cautious grade | Annoyed partner, more reviewer work | Measured as approval load (below) |

**How "simulate, never execute" is enforced.** The route step only appends JSONL rows marked
`simulated: true` under `runs/`. A unit test proves the routing code imports no network,
email or messaging client. The website's approve/reject only writes to browser session storage.
Nothing in the system can send a message, change a record or move money.

**Data sent to third parties.** Eval runs send synthetic chat text, including challenge
text, to OpenRouter free models (the default endpoint logs prompts) and to Langfuse. We accept
this only because every message is synthetic. Real partner chats must never be sent to these
services.

**One deliberate trade-off: caution over convenience.** Most-cautious-wins and fail-closed mean
that any doubt sends a request to a person. A confirmed staff member's ordinary slot change is
still graded `seek_approval` if one flag fires, such as an unclear time. The cost is reviewer time
and slower service on requests that were in fact fine. We accept it because one wrong `act` on a
payout or identity case costs far more than many extra approvals. We will measure the cost as
**approval load**: the share of legitimate, gold-`act` requests the system graded
`seek_approval`, reported per prototype in ARTEFACT.md.
