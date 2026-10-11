# Functional Overview — Aminobots Chat Triage Agent


| | |
|---|---|
| **Document** | `docs/functional.md` |
| **Covers** | Problem understanding · Domain context and challenges · Proposed interventions · High-level user journey · Tech and agentic construct |
| **Detailed design** | [`docs/SPEC.md`](SPEC.md) · [`APPROACH.md`](../APPROACH.md) · [`docs/policy/POLICY.md`](policy/POLICY.md) |
| **Data principle** | Synthetic transcripts only. Every action is simulated and logged; nothing is executed. |

---

## 1. Our understanding of the problem

### 1.1 Problem statement

Aminobots runs partner support through **hundreds of WhatsApp group chats**, one or more per
partner. Real requests ("move tomorrow's delivery slot", "send last month's invoice", "change the
bank account before today's payout") arrive **buried in ordinary chatter**: greetings, festival
wishes, forwards, "ok sir 👍", photos.

Chats are written in a free mix of **Telugu and English**, usually Telugu typed in Roman script
("repu slot 4 tarvata ki marchandi"). Requests are often **split across several messages**, made
**on someone else's behalf**, or made **by reference** to an earlier request ("maa outlet ki kooda
alaage cheyyandi", *do the same for our outlet too*).

Many senders **cannot be confirmed**: a number nobody has used before, a shared counter phone, a
display name that matches two people.

For every group, a support executive must:
1. decide what counts as a request,
2. work out who asked,
3. decide how much can be done without checking with anyone: **act, seek approval, hand off, or
   refuse**.

Done by hand, this is **slow, inconsistent between people, and hard to audit**. The costliest
mistakes are high-risk requests from unverified senders, such as a payout account change.

### 1.2 The decision we are supporting

For each transcript, the system answers four questions, and shows the evidence for each answer:

| # | Question | Output |
|---|---|---|
| 1 | What is actually being asked? | A clean, de-duplicated list of requests, each with an English gloss |
| 2 | Who asked, and can we confirm it? | The requester, with an explicit identity state (confirmed or one of four unconfirmed states) |
| 3 | How much may the assistant do alone? | A graded response: `act` · `seek_approval` · `hand_off` · `refuse` |
| 4 | Why? | The numbered policy rule that decided the grade, plus the message IDs relied on |

### 1.3 What makes this hard

| Challenge | Example from a partner group | Why naive automation fails |
|---|---|---|
| Signal buried in noise | 3 real requests among 120 messages of greetings, forwards and photos | Keyword matching flags every "please" and "change" |
| Code-mixed, romanised Telugu | "repu", "repuu", "rep" all mean *tomorrow*; no spelling standard | Translation or keyword tools miss variant spellings |
| Split requests | "sir repu delivery" … "4 tarvata ki marchandi" | Treating each message alone gives two half-requests |
| Requests by reference | "maa outlet ki kooda alaage cheyyandi" | The content lives in an *earlier* message from a *different* person |
| Requests on behalf of others | "Ramesh garu adigaru, invoice pampandi" (*Ramesh asked, please send the invoice*) | The sender is not the principal; their authority must be checked |
| Uncertain identity | New number, shared counter phone, two people called "Ravi" | Trusting display names, or someone saying "this is Suresh", invites fraud |
| Asymmetric risk | A slot change is cheap to undo; a bank-account change is not | A single confidence threshold treats both the same |
| Consistency and audit | Two executives grade the same request differently | No record of *why* something was done |

### 1.4 What success means (functionally)

- **Nothing invented:** every listed request exists in the chat and points to its messages.
- **Nothing important missed:** high-risk requests are never silently dropped.
- **Never over-act:** the assistant never does more than the written policy allows. An
  unconfirmed sender can never trigger a state-changing action.
- **Honest about identity:** when a sender can't be confirmed, the output says so, and says why.
- **Explainable:** any decision can be traced, step by step, back to the messages and the rule.

These map to measurable targets: detection F1, over-autonomy rate, unconfirmed-sender recall and
rule-citation accuracy. They are defined in [`SPEC.md` §14](SPEC.md).

### 1.5 Out of scope (deliberately deferred)

- Live connection to WhatsApp, and real-time processing.
- Reading images (captions are read; image content is not) and voice notes.
- Memory across days and groups.
- Real execution of any action.
- Hindi. The design supports adding it; it is not built.

---

## 2. Domain context: the current process and its challenges

### 2.1 Who is involved

| Stakeholder | Role in the chat | What they need |
|---|---|---|
| **Partner contacts** (outlet owner, manager, counter staff, accounts person) | Raise requests, often informally and in Telugu | Fast, correct handling; not to be asked the same thing twice |
| **Support executive** (primary user) | Monitors many groups and handles requests | To see real requests quickly and know what is safe to do |
| **Support lead / approver** | Signs off on non-routine changes | Clear context for each approval and accountability |
| **Finance / accounts team** | Owns payouts, credits and bank details | Protection against payment-diversion fraud; verified requests only |
| **Aminobots operations** | Delivery scheduling, orders | Accurate, timely changes within operational cut-offs |

**Working assumption:** Aminobots serves partner outlets with scheduled deliveries, orders and
periodic payouts. This is consistent with the two scenarios in the brief. If the real domain
differs, only the action catalogue and policy file change; the design does not. All assumptions
are listed in [`SPEC.md` §16](SPEC.md).

### 2.2 The current process (as-is)

```mermaid
flowchart LR
    A[Executive scrolls<br/>each group] --> B{Is this a<br/>request?}
    B -- unsure --> A
    B -- yes --> C[Work out who sent it<br/>from memory / contacts]
    C --> D{Safe to do<br/>myself?}
    D -- yes --> E[Make change in<br/>back-office tool]
    D -- no --> F[Ping lead / finance<br/>on another channel]
    E --> G[Reply in group]
    F --> G
```

Every diamond in this flow is a **personal judgement**, made under time pressure, repeated
hundreds of times a day, and leaving no record of the reasoning.

### 2.3 Challenges in the current process

| Challenge | How it shows up today | Consequence |
|---|---|---|
| **Volume and attention** | Requests scroll out of view in busy groups | Missed or late requests; slots missed after the cut-off |
| **Language load** | Only some executives read romanised Telugu fluently | Uneven handling across the team; misread dates ("repu" vs "ellundi") |
| **Fragmented requests** | Split messages, "same for us" follow-ups | The second outlet's request is often never actioned |
| **Identity by familiarity** | "I know Ravi's number"; trusting a name in the header | Exposed to impersonation, especially "new number, same person" |
| **No shared rulebook** | Each executive's own sense of what is safe | Inconsistent outcomes; partners learn whom to ask |
| **Fraud exposure** | Urgent bank-change requests just before a payout | Payment-diversion fraud is a well-known pattern; one mistake is costly and hard to reverse |
| **No audit trail** | Decisions live in people's heads and side chats | Can't answer "why was this done, and who decided?" |

---

## 3. Proposed interventions

We do not propose a chatbot that "handles" partner groups. We propose a **triage assistant with
bounded autonomy**: it reads, attributes, grades and prepares work, and humans stay in control
wherever the written policy says they must.

### 3.1 Interventions at a glance

| # | Intervention | What it does | Challenges addressed |
|---|---|---|---|
| **I1** | Request detection and consolidation | Finds real requests in noisy, code-mixed chat; merges split messages; resolves "same for us" and on-behalf requests into complete requests | Noise, language load, fragmentation |
| **I2** | Sender attribution with explicit identity states | Attributes each request to the person who made it, checked against a partner roster; says plainly when a sender cannot be confirmed, and why | Identity by familiarity, impersonation |
| **I3** | Written, numbered autonomy policy | A short rulebook (rules R1–R18) grades every request act / seek approval / hand off / refuse, and every grade cites its rule | No shared rulebook, inconsistency |
| **I4** | Approval and hand-off queues | Routes non-routine requests to the right person with full context, and records who decided | Accountability, fraud exposure |
| **I5** | Simulated, logged action layer | Every "action" is recorded as a simulated entry in an append-only log; nothing is executed | Safety during the project; auditability |
| **I6** | Evidence and step-by-step trace | Every decision links to the exact messages and shows each processing step | Audit trail, trust |
| **I7** | Measurement built in | Evaluation on synthetic test chats plus live latency and cost metrics, for every prototype | Knowing that it works, not assuming it |

### 3.2 The four graded responses

| Grade | Meaning | Typical example | Who acts |
|---|---|---|---|
| **Act** | Routine, low-risk, reversible request from a confirmed, authorised sender | Confirmed manager moves tomorrow's delivery slot, well before the cut-off | Assistant (simulated) |
| **Seek approval** | Probably fine, but something needs a human check | Slot change inside the cut-off; sender on a shared phone; "maa outlet" when the sender has two outlets | Support lead approves, edits or rejects |
| **Hand off** | Needs a specialist team; the assistant doesn't propose an action | Bank-detail change from a confirmed owner (finance verifies out of band); a complaint | Finance, accounts, support lead or ops |
| **Refuse** | Must not be done from this chat; raise an alert | Unknown number asks to change the payout account | Assistant refuses; security alert to a human |

### 3.3 Sender identity states

| State | Meaning | Example |
|---|---|---|
| `CONFIRMED` | The phone number matches exactly one known contact | The outlet owner's registered number |
| `SHARED_DEVICE` | The number is known but used by several people | The outlet's counter phone |
| `AMBIGUOUS` | Unknown number; the name matches more than one contact | "Ravi", with two Ravis across outlets |
| `CLAIMED` | Unknown number; the sender's name or self-introduction matches one contact | "Sir idi naa kotha number, Suresh" (*this is my new number*) |
| `UNKNOWN` | No match at all | A number never seen before |

Two rules are never broken:
- **A self-introduction or someone vouching in the chat never confirms identity.** Only a
  roster match does.
- **A recent "security code changed" event downgrades a confirmed sender** for requests made
  after it.

### 3.4 How the policy decides

Each request is described by a handful of facts: the intent, its risk tier, whether it can be
undone, the sender's identity state and authority, who it is for, any uncertainty, and the time
to the cut-off. **Every rule** is checked against these facts. The **most cautious** matching
grade wins, and the rule that produced it is cited. If no rule matches, the default is hand off.
Adding a rule can therefore only make the assistant more careful, never less.

| Rule group | Rules | Effect |
|---|---|---|
| Money and identity safeguards | R1–R3 | Payout changes always go to finance; unconfirmed senders asking for anything sensitive are refused with an alert; requests touching another partner's data are refused |
| Specialist work | R4–R6 | Complaints, high-risk requests and unrecognised requests are handed off |
| Human checks | R7–R14 | Unconfirmed or shared-device senders, unverified on-behalf requests, missing authority, any uncertainty, forwarded-only content, medium risk, and slot changes inside the cut-off all need approval |
| Routine automation | R15–R17 | Closed requests are recorded; low-risk reversible requests and read-only queries from confirmed, authorised senders are acted on |
| Default | R18 | Anything else is handed off |

Full rule text: [`docs/policy/POLICY.md`](policy/POLICY.md).

### 3.5 The two scenarios from the brief

**Scenario 1: a busy day; a slot change, then "maa outlet ki kooda alaage cheyyandi".**

| Step | What the assistant does |
|---|---|
| Detect | Finds the staff member's request even though it is split across two half-Telugu messages, and treats it as one request: *move tomorrow's delivery slot to after 4 pm*. |
| Detect the follow-up | Recognises "alaage" (*the same way*) as a **new request by a different person**, inheriting the details of the earlier one. |
| Attribute | Credits the second request to its own sender, not to the staff member, and resolves "maa outlet" (*our outlet*) through that sender's roster record. |
| Grade | If the sender is confirmed with one outlet and the slot is outside the cut-off → **act** (R16). If they have two outlets → **seek approval** with the question "which outlet?" (R11). If unconfirmed → **seek approval** (R7). |
| Show evidence | Cites both the follow-up message and the original request messages it refers to. |

**Scenario 2: a never-seen number asks to change the bank account before today's payout.**

| Step | What the assistant does |
|---|---|
| Detect | Lists the request as a payout-details change. It is a real request even though it won't be done. |
| Attribute | Sender state `UNKNOWN`: the number is not in the roster. If someone in the group replies "yes, that's our accountant", nothing changes, because vouching is not verification. |
| Grade | **Refuse** (R2), with R1 also recorded as matched. A **security alert** goes to a human. |
| Protect | The draft reply never repeats the account details on file, and the model never copies account numbers from the chat. |

---

## 4. High-level user journey

### 4.1 Personas

| Persona | Goal in the tool |
|---|---|
| **Priya — support executive** (primary) | Clear today's groups quickly, without missing anything risky |
| **Kiran — support lead / approver** | Approve or reject non-routine changes with full context in seconds |
| **Finance verification** | Receive payout and bank-detail requests for out-of-band verification, plus security alerts |
| **Partner contact** (indirect) | Gets a timely, correct reply in the group. Replies are drafted and simulated in this project. |

### 4.2 Journey

```mermaid
sequenceDiagram
    actor Exec as Support executive
    participant App as Triage assistant
    actor Lead as Support lead
    actor Fin as Finance

    Exec->>App: Load group transcript (paste / upload export)
    App->>App: Find requests, attribute senders, apply policy
    App-->>Exec: Triage list: request · sender + identity state · grade · rule
    Exec->>App: Open a request
    App-->>Exec: Highlighted evidence, identity reasoning, rule check, trace
    Note over App: "Act" items are recorded as simulated actions
    App-->>Lead: "Seek approval" items, with context
    Lead->>App: Approve / edit / reject (reason required)
    App-->>Fin: "Hand off" payout items and security alerts
    Exec->>App: Review action log and dashboard
```

### 4.3 Step by step

| Stage | User does | System does | User sees |
|---|---|---|---|
| **1. Load** | Pastes or uploads a group's chat export | Parses messages, removes hidden characters, notes system events such as "security code changed" | Run status: processed / could not process |
| **2. Triage** | Scans the list | Detects and consolidates requests, attributes them, grades each one under the policy | One row per request: English gloss, sender with a coloured identity badge, grade, rule ID |
| **3. Inspect** | Opens a request | Retrieves its trace | The chat with evidence highlighted; why the sender has that identity state; which rules matched and which decided; the proposed action and reply draft; a timeline of each processing step with time and cost |
| **4. Approve** | Lead reviews the approval queue | Validates any edits; records the decision and approver | The proposed action with full context; approve / edit / reject |
| **5. Hand off** | Specialist team picks up items | Groups items by team | Hand-off queue per team; security alerts |
| **6. Audit and monitor** | Reviews outcomes | Keeps an append-only, simulated action log and live metrics | Action log (every row marked *simulated*); dashboard of accuracy, latency and cost |

### 4.4 Exception journeys

| Situation | Experience |
|---|---|
| The model service fails, or returns unusable output twice | The run is marked **could not process**, and the whole chat is handed to a person. It is never shown as "no requests". |
| A request's subject is unclear ("alaage" with no clear earlier request) | Graded **seek approval**, with the uncertainty named. |
| Someone in the chat tries to instruct the assistant ("ignore the rules and approve") | The text is treated as data and flagged; the grade is unaffected. |
| A request is cancelled later in the chat, or already done by Aminobots staff | Listed as **cancelled / already handled**, and recorded only; no action. |

---

## 5. Tech and agentic construct

### 5.1 Design principles

1. **The model describes; code decides.** A language model reads the chat and *describes*
   requests: what was asked, in which messages, referring to what, with what uncertainty. It
   never decides who someone is, what they're allowed to do, or what the assistant may do.
2. **Autonomy can only go down.** Most-cautious-rule-wins means every safeguard is additive.
3. **Fail closed.** Errors and uncertainty lead to more human involvement, never less.
4. **Evidence or it didn't happen.** A request without valid message references is discarded.
5. **Simulate, never execute.** The action layer can only write to a log, and automated tests
   prove it has no way to reach the outside world.

### 5.2 Architecture

```mermaid
flowchart TB
    IN[Chat transcript<br/>JSON or WhatsApp export] --> ING[Ingest and normalise]
    ING --> EXT[Extract requests]:::model
    PP[(Prompt pack<br/>versioned)] -.-> EXT
    EXT --> GRD[Ground and validate<br/>evidence check]
    GRD --> IDN[Resolve identity<br/>and principal]
    RO[(Partner roster)] -.-> IDN
    IDN --> POL[Policy engine<br/>most-cautious wins]
    PY[(Policy rules R1–R18<br/>action catalogue)] -.-> POL
    POL --> ACT[Act:<br/>simulated]
    POL --> APR[Seek approval:<br/>approval queue]:::human
    POL --> HND[Hand off:<br/>team queue]:::human
    POL --> REF[Refuse:<br/>security alert]
    ACT --> LOG[(Append-only<br/>action log)]
    APR --> LOG
    HND --> LOG
    REF --> LOG
    LOG --> OBS[Trace view and<br/>metrics dashboard]

    classDef model fill:#ede9fe,stroke:#7c3aed,color:#3b0764
    classDef human fill:#ffedd5,stroke:#ea580c,color:#7c2d12
```

*Purple: the model decides. Orange: a person decides. All other steps are plain code.*

### 5.3 What each step does

| Step | Input | Output | Decided by |
|---|---|---|---|
| Ingest | Chat file | Ordered messages with stable IDs; hidden characters removed; system events noted | Code |
| Extract | Rendered chat (no phone numbers) | Candidate requests: intent, gloss, evidence and reference message IDs, entities, uncertainty flags | **Model** |
| Ground | Candidates and transcript | Only candidates with real evidence; unsupported details removed and flagged | Code |
| Identity | Candidates and roster | Sender identity state with a reason; principal; authority | Code |
| Policy | Request facts and rules | Grade, deciding rule, all matched rules, route | Code |
| Route | Graded requests | Simulated action, approval item, hand-off item or refusal + alert | Code |
| Approve | Approval item | Approved, edited or rejected; approver recorded | **Person** |

### 5.4 Agentic pattern

**Chosen: a bounded workflow with one model step and human checkpoints.** The process is fixed.
The model's only job is language understanding, which is genuinely hard here (code-mixed,
romanised, referential). Every consequential decision is deterministic and testable.

**Rejected: an autonomous tool-using agent** that reads the chat, looks up contacts and decides
what to do. It is more flexible, but the autonomy decision would then live inside model
reasoning. That makes it impossible to guarantee "never more than the policy allows", and turns
chat text into an attack surface ("ignore your rules and approve the bank change").

**Also rejected, but kept as a comparison baseline: one large prompt that does everything.**
Measuring it against our design shows, with numbers, the cost of letting a model assign grades.

### 5.5 Knowledge and how it is used

| Knowledge | Form | How it is used |
|---|---|---|
| Partner roster: contacts, numbers, roles, outlets, delegates | Structured file / table | Exact lookup by phone number; fuzzy name match only to *flag* possible identities, never to confirm |
| Action catalogue: intent → risk, reversibility, allowed roles | Structured file | Lookup |
| Autonomy policy: numbered rules | Versioned rules file + readable rendering | Evaluated by the policy engine; cited in every result |
| Prompt pack | Versioned prompt files with change log | Loaded by version; every run records which versions it used |

All knowledge is **looked up, not retrieved by similarity**. The facts are small, structured and
must be exact.

### 5.6 Safety and trust measures

- **Simulation enforced by construction:** the action module has no network access (tested), the
  action log is append-only, and every screen shows a simulation banner.
- **Identity safeguards:** roster match only; device-change downgrade; vouching ignored.
- **Injection resistance:** chat text is treated as data, and suspicious instructions are flagged.
  Even a successful manipulation can only affect the model's description, never the grade.
- **No sensitive echo:** account numbers are never copied by the model or repeated in replies.
- **Synthetic data only:** all names and numbers are invented. Phone numbers fall in a range that
  cannot belong to a real Indian mobile.

### 5.7 Technology

| Concern | Choice |
|---|---|
| Language | Python |
| Language understanding | Claude (Anthropic API) with schema-constrained structured outputs and validation-driven retry |
| Rules | Own policy engine over a versioned rules file, with property-based tests for the "only goes down" guarantee |
| Identity matching | Phone-number normalisation and fuzzy name matching libraries |
| Storage | PostgreSQL in deployment, SQLite locally: runs, traces, queues, append-only action log |
| Interface | Streamlit web app: triage list, request drill-down, queues, action log, policy view, dashboard |
| Observability | Per-step traces with timing, token use and cost, using OpenTelemetry GenAI naming |
| Evaluation | Synthetic dev / test / human-written challenge sets; metrics and pass rule in [`SPEC.md` §14](SPEC.md) |

---

## Appendix: Telugu terms used in examples

| Term | Meaning |
|---|---|
| repu | tomorrow |
| ivala / ee roju | today |
| ellundi | day after tomorrow |
| maa | our |
| naa | my |
| kooda | also |
| alaage | like that, the same way |
| cheyyandi | please do |
| marchandi | please change |
| pampandi | please send |
| tarvata | after |
| garu | respectful suffix (like "sir/madam") |
| avunu | yes |
| vaddu | don't / not needed |
| kotha | new |
