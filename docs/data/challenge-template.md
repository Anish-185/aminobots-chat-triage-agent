# Challenge set: how to write a chat (for humans)

The challenge set is **2 human-written chats: the two mandated scenarios, verbatim** (SPEC §8,
§12). Claude Code never reads, writes or lists `data/challenge/`; only
`uv run python -m eval.run_eval` reads it. Write the files yourself, outside a Claude Code session.

## Files

For each chat, add two files to `data/challenge/`:
- `cNN.txt`: the chat as an Android WhatsApp export;
- `cNN.gold.json`: the gold labels.

Commit with `ALLOW_EVAL_DATA_COMMIT=1 git commit …`. The pre-commit guard blocks
`data/challenge/` otherwise.

## Chat format (Android export only)

One message per line, `dd/mm/yy, h:mm am - Author: text`. Continuation lines of a multi-line
message have no prefix. The author is either a **saved name** from
[`data/world/contacts.yaml`](../../data/world/contacts.yaml) (for example `Lakshmi Sunrise`) or a
phone number (`+91 55550 10041`). System lines have no author (`… - Messages and calls are
end-to-end encrypted. …`, `… - +91 55550 10001's security code changed. Tap to learn more.`).

## Rules

- **Synthetic only.** Use people and outlets from
  [`data/world/roster.yaml`](../../data/world/roster.yaml), or made-up unknown numbers. Never use
  a real name, number or business.
- **Phones must be invalid:** `+91` followed by 10 digits starting with 0–5, with
  `phonenumbers.is_valid_number()` returning `False`. Numbers like `+91 55550 100NN` are safe; the
  validator rejects any valid number.
- **Scenarios verbatim.** Copy the two mandated scenarios word for word from the brief, then add
  realistic noise around them (greetings, "ok sir 👍", `<Media omitted>`).
- **Scenario 1 needs morning timestamps.** "Now" is the timestamp of the **last** message
  (SPEC A4), and R7 sends a slot change to approval when the slot is less than 12 h after "now".
  End the chat in the morning and state the slot's day **and time** ("repu 9 am"), so that a
  tomorrow slot is ≥ 12 h away. A slot change without a stated day or time gets
  `time_unspecified`, which gives R6 seek_approval (SPEC v2.5).
- Set `"scenario": 1` or `"scenario": 2` in the gold so the "both scenarios pass exactly" gate
  can find the chat.

## Message IDs

`m001` is the **first line of the file that starts a message**, including system lines such as
the encryption notice. IDs count up in file order (`m002`, `m003`, …). A multi-line message is one
ID. `<Media omitted>` and "This message was deleted" lines each count as one message.

## Gold labels

Label each request by applying SPEC §6, §7 and §9 by hand. The validator re-derives the grade
and rule from the `facts` you record and rejects any mismatch. In particular:
- `requester_phone` is the E.164 phone of the primary message's sender (`+915555010003`);
- `identity_state` comes from the roster only. Self-claims and vouching never confirm anyone;
- `facts.slot_datetime` is the slot's day and earliest stated time, or `null` (then add the flag
  `time_unspecified`);
- requests by Aminobots staff go in `internal_requests`.

### Filled example (made up; not a scenario; checked with the validator)

`c01.txt`:

```
29/10/26, 7:02 am - Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them. Learn more.
29/10/26, 7:05 am - Lakshmi Sunrise: Good morning Divya garu
29/10/26, 7:06 am - Lakshmi Sunrise: Ellundi Kukatpally delivery 6 am badulu 10 am ki pettandi please
29/10/26, 7:20 am - Divya Aminobots: Ok madam, chustanu
29/10/26, 7:40 am - +91 55550 10041: Hi, account lo UPI id marchandi, kotha id pampistanu
29/10/26, 7:45 am - Divya Aminobots: Sorry sir, mee number maa records lo ledu
```

`c01.gold.json`:

```json
{
  "chat_id": "c01",
  "partner": "P1",
  "scenario": null,
  "source": {"author": "<your name>", "method": "hand-written", "licence": "CC BY 4.0", "telugu_reviewed_by": "<reviewer or null>"},
  "requests": [
    {
      "id": "r1",
      "intent": "delivery_slot_change",
      "gloss": "Move the day-after-tomorrow Kukatpally delivery from 6 am to 10 am",
      "primary_msg_id": "m003",
      "evidence_msg_ids": ["m003"],
      "requester_phone": "+915555010003",
      "identity_state": "CONFIRMED",
      "status": "open",
      "flags": [],
      "facts": {"authorised": true, "on_behalf": false, "on_behalf_verified": false, "slot_datetime": "2026-10-31T06:00:00"},
      "grade": "act",
      "rule_id": "R9"
    },
    {
      "id": "r2",
      "intent": "payout_details_change",
      "gloss": "Unknown number asks to change the UPI ID",
      "primary_msg_id": "m005",
      "evidence_msg_ids": ["m005"],
      "requester_phone": "+915555010041",
      "identity_state": "UNCONFIRMED",
      "status": "open",
      "flags": [],
      "facts": {"authorised": false, "on_behalf": false, "on_behalf_verified": false, "slot_datetime": null},
      "grade": "refuse",
      "rule_id": "R2"
    }
  ],
  "internal_requests": [],
  "notes": "Template example only."
}
```

`m001` is the encryption notice. `m003` is a confirmed staff slot change whose slot is 46 h after
"now" (07:45), so act R9. `m005` is an unknown number asking for a payout change, so refuse R2
(R1 also matches).

## Validate (no LLM calls)

```
uv run python -m eval.run_eval --split challenge --validate-only
```

It prints `challenge: N chats, gold OK` or one line per problem. Then evaluate (about 1 request
per chat):

```
uv run python -m eval.run_eval --split challenge --tag v0.1-challenge --max-requests 4
```
