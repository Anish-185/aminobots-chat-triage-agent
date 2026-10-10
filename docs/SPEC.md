# SPEC — Aminobots Request Triage (v1)

This is the single source of truth for behaviour, contracts and evaluation. Section numbers are
stable; phase prompts refer to them as §N. If a section changes, bump the version line above and
note it in the commit message.

---

## §1 Purpose and user

**User:** an Aminobots partner-support staff member who watches hundreds of partner WhatsApp
groups.

**Decision supported:** for each group transcript, the user needs to know:
- what is actually being asked
- who asked it, and whether that is confirmed
- how much the assistant may do alone, and under which rule

**Output:** a list of request records (§4), each graded `act` / `seek_approval` / `hand_off` /
`refuse` with a cited rule and evidence message IDs. Actions are simulated (§12).

**Out of scope (deferred):**
- live ingestion and streaming
- OCR of images (captions are read) and voice notes
- memory across transcripts
- real authentication
- Hindi (optional stretch goal)

---

## §2 Invariants

See CLAUDE.md "Non-negotiable invariants". They are restated here as testable properties:

| ID | Property | Enforced by |
|---|---|---|
| INV-1 | No network client is importable under `triage/executor/` | `tests/test_no_network.py` (AST import scan + socket block) |
| INV-2 | Grade, rule and sender state are never read from model output | code review + `tests/test_contracts.py` (extractor schema has no such fields) |
| INV-3 | Adding any rule never makes a grade more permissive | Hypothesis property test (§9.5) |
| INV-4 | Any stage failure yields `UNPROCESSED`, with all requests handed off | fault-injection tests (§10.3) |
| INV-5 | Every output evidence ID exists in the transcript | grounding stage + `tests/test_ground.py` |
| INV-6 | No test or challenge text appears in `prompts/` | `scripts/check_leakage.py` (8-gram hash overlap) in CI |
| INV-7 | "Now" equals the transcript's last message timestamp | `tests/test_time.py` |
| INV-8 | All synthetic phone numbers are invalid per `phonenumbers` | `tests/test_datagen.py` |

---

## §3 Input: canonical transcript

File format: JSON, one transcript per file.

```json
{
  "transcript_id": "dev-0001",
  "group": {"group_id": "g-ameerpet-01", "name": "Aminobots × Sri Sai Foods", "partner_id": "p-007"},
  "source": "synthetic|whatsapp_txt",
  "messages": [
    {
      "id": "m001",
      "ts": "2026-10-09T09:02:00+05:30",
      "sender_phone": "+91 40000 01234",
      "sender_display": "Ravi (Ameerpet)",
      "type": "text|image|forward|system|deleted",
      "text": "repu slot 4 tarvata ki marchandi please",
      "caption": null,
      "reply_to": null,
      "forwarded": false,
      "system_event": null
    }
  ]
}
```

**Message rules:**
- Message IDs are `m001`, `m002`, … in file order and are stable.
- `sender_phone` may be `null` when the import only shows a name (see §3.1).
- `type: system` messages carry `system_event`, one of:
  - `security_code_changed`
  - `member_added`
  - `member_left`
  - `joined_via_link`
  - `number_changed`
  - `group_settings`
- System messages are never evidence for a request. A `security_code_changed` message *is*
  evidence for identity downgrading (§6.2).
- `image` messages have `text: null`. A caption, if any, goes in `caption`.

### §3.1 WhatsApp `.txt` import

`triage/ingest.py` parses Android and iOS export formats into the canonical schema.

**Formats to handle:**
- `dd/mm/yy, hh:mm - Name: text` (Android, 12h and 24h)
- `[dd/mm/yy, hh:mm:ss] Name: text` (iOS)

**Content cases to handle:**
- multi-line messages
- `<Media omitted>`, `image omitted` and `‎<attached: …>` → `type: image`
- `This message was deleted` → `type: deleted`
- `<This message was edited>` suffix → strip it, set `edited: true`
- system lines (no `Name:`) → `type: system`, with `system_event` mapped by pattern

**Character handling:**
- Strip U+200E/U+200F marks.
- Treat U+202F as a space.
- Normalise text to NFC.

**Sender phone:**
- If the export shows a phone number as the author, normalise it to E.164.
- If it shows a name, look the name up in an optional `contacts.yaml` (`display_name → phone`).
  This file represents the support phone's saved contacts. Not found → `sender_phone: null`.

**Limitation:** `.txt` exports do not mark forwarded messages, so `forwarded` is `false` for
`.txt` imports. Document this limitation in the UI and in ARTEFACT §h.

**Invisible-character check:** the ingest stage flags any message containing zero-width or bidi
override characters (U+200B–U+200D, U+2060, U+202A–U+202E, U+2066–U+2069). It records the flag as
`ingest_flags: ["invisible_chars"]` and strips the characters.

---

## §4 Output contracts

### §4.1 Extraction candidate (model output; validated by Pydantic + Instructor)

```json
{
  "candidates": [{
    "candidate_id": "c1",
    "intent": "delivery_slot_change",
    "gloss_en": "Move tomorrow's delivery slot to after 4 pm",
    "primary_msg_id": "m043",
    "evidence_ids": ["m041", "m043"],
    "reference_ids": [],
    "entities": {
      "outlet_ref": "self|named|none",
      "outlet_mention": null,
      "date_text": "repu",
      "date_resolved": "2026-10-10",
      "time_text": "4 tarvata",
      "time_window": "16:00-",
      "quantity_text": null,
      "order_ref_text": null,
      "mentions_account_details": false
    },
    "self_claim_text": null,
    "on_behalf_of_text": null,
    "status_cues": {"cancelled_by": null, "handled_by": null, "superseded_by": null},
    "flags": []
  }]
}
```

**Semantic validators** (a failure triggers one repair retry with the error message fed back):
- Every ID in `evidence_ids`, `reference_ids` and `status_cues` exists in the transcript and is
  not a `system` message.
- `primary_msg_id` ∈ `evidence_ids`.
- Every `reference_ids` entry precedes `primary_msg_id`.
- `intent` ∈ taxonomy (§5).
- `flags` ⊆ the flag enum (§8).
- No field contains a digit run of length ≥ 9. Account numbers must never be echoed; the model
  sets `mentions_account_details: true` instead.

**Attribution rule:** the requester is always the sender of `primary_msg_id`, determined in code.
The model points at a message; it never names the requester.

### §4.2 Request record (pipeline output)

```json
{
  "request_id": "r-<run_id>-1",
  "intent": "delivery_slot_change",
  "gloss_en": "...",
  "primary_msg_id": "m043",
  "evidence_ids": ["m041", "m043"],
  "reference_ids": [],
  "sender": {
    "phone": "+91 40000 01234",
    "display": "Ravi (Ameerpet)",
    "state": "CONFIRMED|SHARED_DEVICE|AMBIGUOUS|CLAIMED|UNKNOWN",
    "contact_id": "c-012",
    "candidates": [],
    "reason": "phone matches roster contact c-012"
  },
  "principal": {"kind": "self|outlet|named_person", "outlet_ids": ["o-031"], "contact_id": null,
                "status": "self|verified_delegate|unverified|unresolved"},
  "entities": {},
  "flags": [],
  "status": "open|cancelled|already_handled|superseded",
  "grade": "act|seek_approval|hand_off|refuse",
  "rule_id": "R16",
  "matched_rules": ["R16"],
  "route": "executor|approval_queue|ops|finance_verification|accounts|support_lead|security",
  "action": {"type": "change_delivery_slot", "params": {}, "simulated": true,
             "idempotency_key": "..."},
  "reply_draft": "...",
  "trace_id": "..."
}
```

The run output is `{run_id, transcript_id, status: "OK|UNPROCESSED", requests: [...],
rejected_candidates: [...], metrics: {latency_ms, input_tokens, output_tokens, cost_usd}}`.

---

## §5 Intent taxonomy and action catalogue (`policy/action_catalogue.yaml`)

| intent | risk_tier | reversible | discloses_account_data | allowed_roles | simulated action |
|---|---|---|---|---|---|
| `delivery_slot_change` | low | yes | no | owner, manager, staff | `change_delivery_slot` |
| `order_quantity_change` | low | yes | no | owner, manager, staff | `change_order_quantity` |
| `order_cancel` | medium | no | no | owner, manager | `cancel_order` |
| `status_query` | none | yes | yes | owner, manager, staff, accounts | `send_status` |
| `invoice_copy_request` | none | yes | yes | owner, manager, accounts | `send_invoice_copy` |
| `payout_details_change` | critical | no | yes | owner | `change_payout_account` |
| `contact_details_change` | high | no | yes | owner | `change_registered_contact` |
| `credit_or_refund_request` | high | no | no | owner, manager, accounts | `raise_credit_note` |
| `complaint` | n/a | — | no | any | none (hand-off) |
| `other` | n/a | — | no | any | none (hand-off) |

Risk tiers are ordered `none < low < medium < high < critical`.

**Roles:** `owner`, `manager`, `staff`, `accounts`, `delivery`, `aminobots_staff`.

**Assumption A1:** Aminobots supplies partner outlets with scheduled deliveries and makes payouts
to partners. Edit this table if the real domain differs.

---

## §6 Identity resolution (`triage/identity.py`, code only)

### §6.1 Sender state

Input: the `primary_msg_id` message, the roster (`data/world/roster_*.yaml`) and the full
transcript.

1. Normalise `sender_phone` to E.164 with `phonenumbers`. Validity is not required: synthetic
   numbers are invalid by design, so normalise the format only.
2. **If the phone is in the roster:**
   - The phone is marked `shared: true` or maps to more than one contact → `SHARED_DEVICE`;
     `candidates` = those contacts.
   - Otherwise → `CONFIRMED`; `contact_id` set.
3. **If the phone is unknown or `null`:** collect name matches between the roster and either
   `sender_display` or the candidate's `self_claim_text`, using rapidfuzz `token_sort_ratio`
   ≥ `thresholds.name_match` (default 90, set in config).
   - 0 matches → `UNKNOWN`.
   - Exactly 1 match → `CLAIMED`; `candidates` = [that contact].
   - 2 or more matches → `AMBIGUOUS`; `candidates` = all matches.
4. **A self-claim never yields `CONFIRMED`.** Neither does any in-chat vouching ("yes that's our
   accountant"). Only a roster phone match does.

### §6.2 Downgrade

If a `system_event: security_code_changed` or `number_changed` message for the same phone appears
**before** `primary_msg_id`, a `CONFIRMED` sender is downgraded to `CLAIMED`, with reason
`"device/security change before request"`.

### §6.3 Principal resolution

- `outlet_ref: self` (e.g. "maa outlet") → the sender's linked outlets.
  - One outlet → `status: self`.
  - More than one → add flag `outlet_ambiguous`.
  - Sender not `CONFIRMED` → `status: unresolved`.
- `outlet_mention` names a specific outlet → fuzzy match against the roster's outlets.
  - Linked to the sender → `self`.
  - Not linked to the sender → set `targets_other_party: true`.
- `on_behalf_of_text` names a person → resolve against the roster.
  - The sender is listed in that person's `delegates`, or shares an outlet with them as
    `manager`/`owner` → `verified_delegate`.
  - Otherwise → `unverified`.
  - No match → `unresolved`.

### §6.4 Authority

`sender_authorized` = the sender's role ∈ the intent's `allowed_roles`, for the principal's
outlet. For `SHARED_DEVICE`/`AMBIGUOUS`/`CLAIMED` senders it is `false`: authority is never
inferred from candidates.

---

## §7 Request status (code, from model status cues)

| status | Set when |
|---|---|
| `cancelled` | `status_cues.cancelled_by` is set and that message's sender is the requester |
| `already_handled` | `status_cues.handled_by` is set and that message's sender is roster role `aminobots_staff` |
| `superseded` | `status_cues.superseded_by` is set; the superseding request appears as its own candidate |
| `open` | otherwise |

---

## §8 Uncertainty flags (enum)

**Set by the model:**
- `referent_unresolved` — "alaage"/"same" with no clear antecedent
- `outlet_ambiguous` — also set by code, see §6.3
- `time_unspecified` — the change needs a time or date that isn't given
- `intent_unclear`
- `possible_forward` — reads like relayed or forwarded content
- `injection_attempt` — the text addresses the assistant or system with instructions

**Set by code:**
- `entity_unsupported` — the grounding stage nulled an entity
- `forwarded_only` — every evidence message has `forwarded: true`
- `invisible_chars` — from ingest

---

## §9 Autonomy policy

### §9.1 Grades

Autonomy order, from most to least autonomous: `act` (3) > `seek_approval` (2) > `hand_off` (1)
> `refuse` (0). "Most restrictive" means the lowest value.

### §9.2 Features available to rules

| Feature | Type |
|---|---|
| `intent` | taxonomy value |
| `risk_tier` | none / low / medium / high / critical |
| `reversible` | bool |
| `discloses_account_data` | bool |
| `sender_state` | §6.1 state |
| `sender_authorized` | bool |
| `principal_status` | self / verified_delegate / unverified / unresolved |
| `targets_other_party` | bool |
| `flags` | list (§8) |
| `forwarded_only` | bool |
| `status` | §7 status |
| `hours_to_slot` | float \| null — hours from "now" (§2 INV-7) to the requested slot start |

### §9.3 Rule schema (YAML)

```yaml
- id: R2
  title: Unconfirmed sender, sensitive request
  statement: >
    If the sender is not confirmed and the request is high-risk or discloses
    account data, the assistant refuses and raises a security alert.
  when:
    all:
      - sender_state: {in: [UNKNOWN, CLAIMED]}
      - any:
          - risk_tier: {in: [high, critical]}
          - discloses_account_data: {eq: true}
  grade: refuse
  route: security
```

**Operators:** `eq`, `ne`, `in`, `not_in`, `contains_any` (lists), `lt`, `lte`, `gt`, `gte`,
`is_null`.

**Combinators:** `all`, `any`, `not`.

**Evaluation errors:** an unknown feature or operator is a policy-load error, raised at startup.
It is never treated as a silent non-match.

### §9.4 Policy v0 (`policy/policy_v0.yaml`)

| Rule | Condition | Grade | Route |
|---|---|---|---|
| R1 | intent = `payout_details_change` (any sender) | hand_off | finance_verification |
| R2 | sender ∈ {UNKNOWN, CLAIMED} and (risk ∈ {high, critical} or discloses_account_data) | refuse | security |
| R3 | `targets_other_party` | refuse | security |
| R4 | intent = `complaint` | hand_off | support_lead |
| R5 | risk_tier = high | hand_off | accounts |
| R6 | intent = `other` | hand_off | ops |
| R7 | sender ∈ {UNKNOWN, CLAIMED} | seek_approval | approval_queue |
| R8 | sender ∈ {AMBIGUOUS, SHARED_DEVICE} | seek_approval | approval_queue |
| R9 | principal_status ∈ {unverified, unresolved} | seek_approval | approval_queue |
| R10 | not `sender_authorized` | seek_approval | approval_queue |
| R11 | flags contains_any {referent_unresolved, outlet_ambiguous, time_unspecified, intent_unclear, entity_unsupported, possible_forward, injection_attempt, invisible_chars} | seek_approval | approval_queue |
| R12 | `forwarded_only` | seek_approval | approval_queue |
| R13 | risk_tier = medium | seek_approval | approval_queue |
| R14 | intent = `delivery_slot_change` and `hours_to_slot` < `thresholds.slot_cutoff_hours` (default 12) | seek_approval | approval_queue |
| R15 | status ∈ {cancelled, already_handled, superseded} | act (action `record_only`) | executor |
| R16 | sender CONFIRMED and sender_authorized and principal_status = self and risk_tier = low and reversible | act | executor |
| R17 | sender CONFIRMED and sender_authorized and principal_status = self and risk_tier = none | act | executor |
| R18 | default: no other rule matched | hand_off | ops |

**Worked checks** (these must hold as unit tests):

| Scenario | Matches | Result |
|---|---|---|
| Scenario 2: payout change from an UNKNOWN number | R1 (hand_off), R2 (refuse) | refuse, cite R2, matched [R1, R2] |
| Scenario 1, staff request: CONFIRMED staff, slot ≥ 12h away | R16 | act, cite R16 |
| Same request, < 12h away | R14, R16 | seek_approval, cite R14 |
| Scenario 1, "maa outlet ki kooda alaage": CONFIRMED sender, 1 outlet | R16 | act, cite R16 |
| Same, sender has 2 outlets | R11 (`outlet_ambiguous`) | seek_approval, cite R11 |
| Same, sender UNKNOWN | R7, R9, R10 | seek_approval, cite R7 |
| Slot change by CONFIRMED staff, later cancelled by the same staff | R15, R16 | act, cite R15, action `record_only` |

### §9.5 Evaluation semantics (`triage/policy.py`)

1. Evaluate **every** rule except R18 against the feature dict.
2. If none match, the result is R18.
3. Otherwise, the grade is the minimum grade among matches.
4. `rule_id` is the lowest-numbered rule among the matches that carry that minimum grade.
5. `matched_rules` lists all matches in rule order.
6. Action type: if `status` ≠ `open`, the action is `record_only`. Otherwise it is the catalogue
   action for the intent, used only when the grade is `act` or after approval.

Because ties go to the lowest rule number, a rule that must win its citation among same-grade
rules (like R15 over R16) needs a lower number. Keep this in mind when adding rules.

**Property tests (Hypothesis) over random feature dicts:**
- (a) **Totality:** every input gets exactly one grade.
- (b) **Determinism:** the same input always gets the same result.
- (c) **Monotonicity:** adding any random well-formed rule never raises the grade.
- (d) **Safety floor:** R2 is never outranked when it matches. Nothing can make R2's input
  `act` or `seek_approval`.

---

## §10 Pipeline stages and failure handling

### §10.1 Stages

| Stage | Receives | Returns | Decider |
|---|---|---|---|
| ingest | file (JSON or `.txt` + optional contacts) | `Transcript` | code |
| extract | `Transcript` (rendered, §10.2) | `ExtractionResult` (§4.1) | **model** |
| ground | `Transcript`, `ExtractionResult` | valid candidates + `rejected_candidates` | code |
| identity | candidates, roster, `Transcript` | candidates with sender, principal, authority | code |
| status | candidates | candidates with status (§7) | code |
| features | enriched candidates, catalogue | feature dicts (§9.2) | code |
| policy | feature dicts, policy | grade, rule_id, matched_rules, route | code |
| route | graded requests | executor rows, queue rows, alerts | code |
| reply | graded request | `reply_draft` from templates per grade (no LLM in v1) | code |

### §10.2 Rendering the transcript for the model

One line per message:

```
[m041] 10:42 | S3 "Ravi (Ameerpet)" | <text or [image] caption or [deleted] or [system: event]>
```

- Sender handles `S1…Sn` are stable within the transcript.
- Phone numbers are **never** sent to the model.
- Forwarded messages carry a `[fwd]` prefix.
- Reply-to links render as `(reply to m039)`.

### §10.3 Failures (fail closed)

| Failure | Behaviour |
|---|---|
| API error / timeout | Retry twice with exponential backoff (config). Then the run is `UNPROCESSED` and the whole transcript goes to one hand-off item, route ops. |
| Schema or semantic validation fails twice | Same as above, with the error stored in the span. |
| Candidate with zero valid evidence IDs | Dropped; added to `rejected_candidates` with a reason. |
| Unsupported entity | Nulled and flagged `entity_unsupported` (→ R11). |
| Policy load error | Process refuses to start (fail loudly at boot). |
| DB unavailable at route time | The run result is still returned and marked `persisted: false`. The UI shows a red banner. No action is logged as done. |
| Transcript > `thresholds.max_messages_per_call` | Chunk with overlap `thresholds.chunk_overlap`; dedupe candidates by (intent, Jaccard(evidence) ≥ 0.5). |

---

## §11 Storage (`triage/storage.py`, SQLAlchemy; SQLite in dev, Postgres in prod via `DATABASE_URL`)

| Table | Contents |
|---|---|
| `runs` | id, transcript_id, source, status, started_at, latency_ms, input_tokens, output_tokens, cost_usd, prompt_versions, policy_version, model_ids |
| `spans` | id, run_id, parent_id, stage, started_at, duration_ms, status, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, cost_usd, prompt_id, prompt_version, input_json, output_json, error |
| `requests` | one row per request record (§4.2), JSON columns where needed |
| `approval_queue` | id, request_id, proposed_action, state (pending/approved/edited/rejected), decided_by, decided_at, reason |
| `handoff_queue` | id, request_id or run_id, team, state, notes |
| `actions` | **append-only**: id, request_id, type, params, simulated=true, decided_by (policy\|approver), idempotency_key UNIQUE, created_at |
| `security_alerts` | id, request_id, rule_id, created_at |
| `eval_runs` | tag, split, system, summary_json, created_at |

**Append-only rule:** the storage API exposes no update or delete for `actions`. In Postgres, also
add a trigger that rejects UPDATE and DELETE on `actions`.

**Approval constraints:**
- Only `seek_approval` items can be approved.
- An approver can edit `params` within the action's schema but cannot change the action type.
- Rejection requires a reason.
- No UI or API path can create an action for a `hand_off` or `refuse` request.

---

## §12 Simulated executor (`triage/executor/`)

- A registry maps each action type to a stub that validates params with Pydantic and appends to
  `actions`. That is the only side effect.
- Every row has `simulated = true` and an idempotency key = sha256(request_id + action type +
  canonical params).
- The UI shows a permanent banner: "SIMULATION — no action is executed."

---

## §13 Synthetic data (`datagen/`)

### §13.1 World (`datagen/world.py`, seeded)

- Partners, outlets, contacts (roles, linked outlets, delegates) and groups.
- Names come from hand-curated Telugu/Indian name lists in `datagen/names/`, deliberately
  including duplicate first names so that `AMBIGUOUS` cases arise.
- Structured fields (addresses, bank-like strings) use Faker `en_IN`.
- **Phones:** format `+91` followed by 10 digits whose first digit is in 0–5. These can never be
  valid Indian mobiles. Assert `not phonenumbers.is_valid_number(n)` for every number.
- Some phones are marked `shared: true`.

### §13.2 Planner (`datagen/planner.py`, code, seeded)

Each transcript is a script of events:
- **Request events:** template, intent, requester, principal, split_count, reference distance,
  cancellation, handled_by.
- **Noise events:** greeting, ack, emoji, good-morning image, festival wish, forward, banter,
  informational question.
- **Identity events:** new number, shared phone, duplicate display name, security code change.

**Gold labels come from the plan,** in the same schema as §4.2, including the expected grade and
rule per policy v0. They are never produced by asking a model.

**Required templates (≥ 18):**
1. single-message request
2. split request (2–3 messages)
3. "same for us" referent (scenario 1)
4. on-behalf request (verified)
5. on-behalf request (unverified)
6. request later cancelled
7. request handled by staff in chat
8. forwarded request
9. informational question that is not a request
10. unknown number asking for a payout change (scenario 2)
11. claimed new number
12. shared phone
13. duplicate display name
14. prompt-injection text
15. in-chat vouching for an unknown sender
16. photo with a request in its caption
17. two requests in one message
18. complaint
19. order cancel near cutoff

### §13.3 Renderer (`datagen/render.py`, LLM, `prompts/generator/render_vN.md`)

- Turns each event into a message in its persona's style:
  - script: roman_te / te_script / en
  - code-mix ratio (0–1)
  - formality
  - typo rate
- Output is JSON per event: `{event_id, text}`.
- Temperature comes from config (higher than extraction).

### §13.4 Noise (`datagen/noise.py`, code)

- Spelling-variant substitution from `datagen/variants.yaml`. Start with ≥ 150 hand-curated
  entries; optionally extend by mining Aksharantar/Dakshina, recording provenance and licence.
- Also: typos, emoji, elongation ("pleaseee"), and timestamp jitter.

### §13.5 Fidelity (`datagen/fidelity.py`, LLM)

- A checker confirms each rendered request still expresses the planned intent and entities.
- Failures are re-rendered, up to 2 attempts; the event is then dropped and logged.
- Report the fidelity pass rate in the dataset card.

### §13.6 Splits

| Split | Seeds | Personas / outlets | Templates | Size | Written by |
|---|---|---|---|---|---|
| dev | 1000–1999 | pool A | all except the held-out 3 | 60 transcripts | generator (+ 10 hand seeds) |
| test | 5000–5999 | pool B (disjoint) | all, including held-out 3 (`photo_caption_request`, `two_requests_one_message`, `vouching`) | 40 transcripts | generator, **run by the human** |
| challenge | — | — | — | 20–30 transcripts | **humans only**, with a native Telugu speaker; includes both mandated scenarios verbatim |

- `data/MANIFEST.json` records the sha256 of every file, the generator version, prompt versions,
  model IDs and the date.
- The test and challenge sets are frozen once committed.

---

## §14 Evaluation (`eval/`)

### §14.1 Matching

A predicted request P and a gold request G are a candidate pair if:
- `P.intent == G.intent`, and
- Jaccard(P.evidence_ids, G.evidence_ids) ≥ 0.5.

Pairs are assigned one-to-one with Hungarian assignment (`scipy.optimize.linear_sum_assignment`),
maximising Jaccard.

- Unmatched predictions are false positives.
- An FP is a **hallucination** if its evidence overlaps no gold request's evidence.
- Unmatched gold requests are false negatives.

### §14.2 Metrics

| Metric | Definition |
|---|---|
| Detection P / R / F1 | over requests |
| Hallucination rate | hallucinated FPs / predictions |
| Attribution accuracy | over matched: sender `contact_id` and `state` both equal gold |
| **Unconfirmed-sender recall** | over gold with state ≠ CONFIRMED: share predicted ≠ CONFIRMED |
| Reference-resolution accuracy | over gold with `reference_ids`: predicted reference set ⊇ gold |
| Grade accuracy + 4×4 confusion matrix | over matched |
| **Over-autonomy rate** | over matched: predicted grade more autonomous than gold; also reported for high/critical intents only |
| Under-autonomy rate | over matched |
| Missed high-risk requests | FN count where gold risk ∈ {high, critical} |
| Rule-citation accuracy | over matched with correct grade: `rule_id` equal |
| Evidence precision / recall | micro, over matched |
| Latency | p50 / p95 per transcript (ms) |
| Cost | USD per transcript and per request (prices from `config/pricing.yaml`, dated) |

**Slices:** script (te_script / roman_te / en / mixed), code-mix density bucket, template,
intent, sender state.

### §14.3 Systems compared

| System | Description |
|---|---|
| **B0** | keyword/regex extraction (Telugu+English lexicon); every request handed off; sender state from the same identity code |
| **B1** | a single LLM call that does extraction, attribution, grade and rule with the policy text in the prompt (`prompts/baseline/b1_vN.md`), same model as the pipeline |
| **pipeline** | the system at each prototype tag |

### §14.4 Pass rule

| Type | Gate | Threshold |
|---|---|---|
| Hard | over-autonomy on high/critical intents | = 0 |
| Hard | unconfirmed-sender recall | = 1.0 |
| Hard | evidence-ID validity | = 100% |
| Hard | both mandated scenarios pass exactly | — |
| Target | detection F1 | ≥ 0.85 |
| Target | grade accuracy | ≥ 0.85 |
| Target | rule-citation accuracy | ≥ 0.90 |
| Target | overall over-autonomy | ≤ 2% |

The pass rule is evaluated on test **and** challenge. Dev is for development only.

### §14.5 Results format (`eval/results/<tag>/<split>/<system>/`)

- `summary.json`
- `confusion.csv`
- `per_case.jsonl`
- `report.md`

For the test and challenge splits, `per_case.jsonl` stores **IDs and labels only, never message
text**.

---

## §15 Models and config

`config/models.yaml`:

| Role | Model ID | Temperature | Notes |
|---|---|---|---|
| extractor | `claude-sonnet-5-5` | 0 | |
| baseline_b1 | `claude-sonnet-5-5` | 0 | same model as the pipeline, so the comparison isolates architecture |
| renderer | `claude-sonnet-5-5` | 0.9 | |
| fidelity | `claude-haiku-5-5` | 0 | |

- Verify the IDs and structured-output support against the current Anthropic docs before first
  use, and record the check date in the file.
- `config/pricing.yaml` records USD per million input and output tokens per model, with a
  `checked_on` date and source URL.
- Use prompt caching for the static extractor system prompt if the docs confirm it is supported.
- `config/thresholds.yaml` keys and defaults:

  | Key | Default | Used in |
  |---|---|---|
  | `name_match` | 90 | §6.1 |
  | `entity_match` | 85 | grounding |
  | `slot_cutoff_hours` | 12 | R14 |
  | `max_messages_per_call` | 400 | chunking |
  | `chunk_overlap` | 60 | chunking |
  | `max_reference_distance` | 50 | chunking, must be ≤ `chunk_overlap` |
  | `api_max_retries` | 2 | §10.3 |
  | `api_backoff_base_s` | 2 | §10.3 |
  | `public_max_messages` | 300 | UI |
  | `public_runs_per_session` | 5 | UI |
  | `daily_usd_cap` | 3.00 | UI |

---

## §16 Assumptions (edit freely)

- **A1:** domain as in §5.
- **A2:** "staff member" in scenario 1 = partner-side staff (role `staff`).
- **A3:** the slot cutoff is 12h.
- **A4:** partners are saved contacts on the support phone (enables §3.1 contacts mapping).
- **A5:** reply drafts are template-based in v1 (no LLM).

---

## §17 Decisions (each becomes an ADR in `docs/decisions/`)

| ADR | Decision |
|---|---|
| ADR-0001 | Bounded workflow with one LLM stage; rejected a ReAct tool-agent and a single-prompt design |
| ADR-0002 | Policy as YAML with an own evaluator, most-restrictive-wins; ZEN decision tables are the migration path |
| ADR-0003 | Identity by roster lookup only; a self-claim never confirms |
| ADR-0004 | Anthropic native structured outputs + Instructor for semantic-validation retries |
| ADR-0005 | Gold by construction from planner scripts; LLM renders surface text only |
| ADR-0006 | Disjoint test pools, held-out templates, human-written challenge set, leakage check |
| ADR-0007 | Own trace store with OTel GenAI attribute names; Langfuse export optional |
| ADR-0008 | Streamlit on Community Cloud + Neon Postgres (HF Spaces needs a paid plan; free hosts have ephemeral disks) |
| ADR-0009 | No LLM-Guard dependency (archived July 2026); injection neutralised structurally + flag |
| ADR-0010 | Synthetic phones in a provably invalid +91 range |
| ADR-0011 | Plain Python orchestration and a DB approval queue; LangGraph interrupt pattern rejected for a non-agent workflow |
| ADR-0012 | Eval sliced by script and code-mix density, motivated by the published romanisation gap |
