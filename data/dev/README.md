# Dev split

15 synthetic partner group chats (`dNN.txt`, Android WhatsApp export format) with hand-labelled
gold (`dNN.gold.json`). **Development only**; the pass rule is scored on test + challenge.

## Provenance

| | |
|---|---|
| Written by | Claude Code, by hand (no LLM API call, no generator script) |
| Generator prompt | [`docs/build-prompts/phase-03-data.md`](../../docs/build-prompts/phase-03-data.md) |
| World | [`data/world/roster.yaml`](../world/roster.yaml), [`contacts.yaml`](../world/contacts.yaml): fictional people, outlets and invalid phones |
| Gold | grade and rule labelled by applying SPEC §9 by hand; `scripts/validate_gold.py` re-derives every label from the recorded facts |
| Licence | CC BY 4.0 ([data/LICENSE](../LICENSE)) |
| Telugu review | not yet (`telugu_reviewed_by: null` in every gold file) |

The two mandated scenarios appear only as *similar situations* (d01, d07), never in their
verbatim wording; verbatim versions belong in the human-written challenge set.

## Shape

- 30–33 messages per chat; 37 partner requests + 2 internal (Aminobots staff) requests.
- Mostly romanised Telugu–English; about 10% of text messages in Telugu script (d14 is
  script-heavy); d15 is plain English. Spelling variants: repu/repuu, cheyyandi/cheyandi.
- Noise in every chat: greetings, "ok sir 👍", `<Media omitted>`, festival wishes, banter, system
  lines (encryption notice, added/joined/removed, security code changed).
- Grades: 9 act · 15 seek_approval · 10 hand_off · 3 refuse.

## Labelling conventions

- A request is something asked **of Aminobots**. Partners asking their own staff (d02 m021,
  d15 m022) and banter (d12 m014) are not requests.
- Aminobots staff asking a clarifying question is not a request; an explicit task ask from
  Aminobots staff is an **internal request** (A6), stored in `internal_requests`, not scored.
- Requests stay `open` even if Aminobots acknowledges them ("ok sir"); `cancelled` only when the
  requester withdraws it in the chat; `handled` only when an `aminobots_staff` message explicitly
  confirms it is done, and that message is in the evidence (SPEC §5, v2.4).
- `facts.slot_datetime` = the delivery being changed, at the **earliest** time stated for it
  (current or new slot; a follow-up inherits the day of the request it refers to); `null` when
  the day or time is not stated, and then the request carries `time_unspecified` (SPEC v2.5).
  R7 uses hours from the chat's "now" (last message, A4) to that slot, not from the request
  message (SPEC §9, v2.4); the validator derives it.
- A contact asking about another partner's outlet is `on_behalf: true`, `on_behalf_verified:
  false` (SPEC §9, v2.4).
- `facts.authorised` follows the roster role and the intent's allowed roles (SPEC §6); an
  `AMBIGUOUS` sender is authorised only if every candidate contact is (SPEC §7).

## Coverage

| Situation | Chats |
|---|---|
| `delivery_slot_change` | d01, d02, d03, d05, d09, d11, d14, d15 |
| `order_change` | d02, d06, d15 |
| `status_query` | d02, d05, d11, d13, d15 |
| `invoice_request` | d01, d04, d08 |
| `payout_details_change` | d07, d08 |
| `refund_request` | d04, d06, d10, d14, d15 |
| `complaint` | d03, d13 |
| `other` | d10, d14 |
| `CONFIRMED` sender | most chats |
| `AMBIGUOUS` sender (shared phone) | d05 |
| `AMBIGUOUS` sender (duplicate name) | d06 |
| `UNCONFIRMED` sender | d04 (after security-code change), d06 (one name match), d07, d13 (unknown numbers) |
| Vouching / self-claim | d07 |
| Injection attempt | d10 |
| Cancellation (act R8, and seek R7 that stays) | d03, d15 |
| Handled: Aminobots staff confirms done (act R8, record only) | d13 |
| Cross-partner: contact asks about another partner's outlet (seek R5) | d08 |
| Forward | d11 |
| Request split over several messages | d02 |
| On-behalf, verified (delegate) | d09 |
| On-behalf, unverified | d08, d09 |
| Shared phone | d05 |
| Duplicate name | d06 |
| Security-code change | d04 |
| Owner with 2 outlets says "maa shop" | d01 |
| Single-outlet manager says "maa outlet" | d02 |
| Slot change under 12 h from "now" | d01, d03, d05, d09 |
| `aminobots_staff` request (internal) | d07, d13 |
| Unresolved referent / unspecified time | d15 / d14 |
| Zero requests | d12 |
| Mandated scenario 1 (similar situation; slot is 11.5 h from "now", so R7) | d01 |
| Mandated scenario 2 (similar situation) | d07 |
