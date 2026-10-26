PR #3 approved: merge it yourself once CI is green. Branch deletion: skip it; I'm enabling
GitHub's auto-delete, so ignore that 403 from now on.

Guard fix APPROVED: in .claude/hooks/guard_bash.py, strip heredoc bodies before checking and
treat newlines as command separators, with the 3 test cases you proposed. I will allow the edit
when prompted. Do this first, as its own commit.

# Phase 3 — Schemas, parser, roster, dev data

Save this prompt verbatim to docs/build-prompts/phase-03-data.md and append your plan below it.
No LLM API calls in this phase. You write the dev chats yourself; this prompt is their generator
prompt, so record that in the provenance. Demo build: aim for coverage, not volume.

1. Parser check (do this before writing anything else). Make a tiny synthetic fixture in
   tests/fixtures/ in Android WhatsApp export format ("dd/mm/yy, h:mm am - Name: text"),
   including:
   - multi-line messages;
   - a leading U+200E;
   - U+202F (narrow no-break space) before am/pm, which newer exports use;
   - an emoji in an author name, and a phone-number author;
   - "<Media omitted>" lines;
   - system lines: security code changed, added, left, and "This message was deleted".
   Run chat-miner on it and record in the build log which columns it returns and what it drops.
   Then implement per SPEC §4: if it drops system lines, use a pre-pass of 30 lines or fewer.
   If chat-miner cannot parse this format at all, stop and report.
   We support the Android format only; add that to the SPEC limitations.

2. triage/schemas.py (Pydantic v2): Message, Candidate, ExtractionResult, Identity,
   GradedRequest, LogRecord, GoldChat, matching SPEC.

3. triage/parse.py:
   - IDs m001… in file order;
   - author resolution via the optional contacts.yaml;
   - kind = text | media | system.

   triage/render.py:
   - the SPEC §4 line format, with date dividers;
   - handles S1…Sn in order of first appearance;
   - phones never appear, including phone-number display names, which are masked.

   Tests: render output for a fixture never contains a +91 number; handles are stable; system
   and media lines render correctly.

4. data/world/roster.yaml must include each of these:
   - 2–3 partners and about 6 outlets;
   - a shared phone;
   - two contacts with the same first name;
   - an owner with 2 outlets;
   - an accounts contact;
   - a delegate;
   - two aminobots_staff.

   Roles are exactly owner, manager, staff, accounts and aminobots_staff. Phones are hand-picked
   and tested invalid per SPEC §4.6 (the test covers the roster, every contacts.yaml and every
   dev chat).

5. data/dev/: about 15 chats, each 30–80 messages, plus <id>.gold.json.
   Mix: mostly romanised Telugu–English, about 10% Telugu-script lines, some plain English,
   spelling variants. Noise per SPEC §12.

   Across the set, cover:
   - every intent at least twice;
   - every identity state;
   - each of: vouching / self-claim, injection attempt, cancellation, forward, a request split
     over several messages, on-behalf (verified and unverified), shared phone, duplicate name,
     security-code change, owner with 2 outlets saying "maa outlet", a slot change under 12 h,
     an aminobots_staff request (internal), and one chat with zero requests.

   Situations like the two mandated scenarios are fine in dev, but NOT their verbatim wording;
   verbatim versions go only in the human-written challenge set.

   Gold: label grade and rule by applying SPEC §9 by hand. Set source = {author: "Claude Code",
   method: "hand-written from phase-03 prompt", licence: "CC BY 4.0",
   telugu_reviewed_by: null}.

   Write a coverage table (situation → chat IDs) in data/dev/README.md.

6. scripts/validate_gold.py, run on data/dev and data/world only. It checks:
   - schema;
   - every message ID exists;
   - each requester matches the sender of the primary message;
   - rule_id and grade agree with SPEC §9's table;
   - all phones are invalid.

   Wire it into pytest and pre-commit.

7. Finish: all checks green; commit; push phase-03-data; open a

---

## Plan (Claude Code)

Note: the prompt arrived truncated after "open a". Read as: open a PR, give the phase report,
stop. SPEC section numbers in the prompt map to SPEC v2.2 as: parser/pre-pass §3.1, line format
§3.2, phones §8, noise §8, rules §9.

0. Merge PR #3 (CI green). Guard fix as its own commit (done, 3aa51c8).
1. Parser check: `tests/fixtures/android_sample.txt`; run chat-miner; record columns and drops
   below; decide on the pre-pass.
2. `triage/schemas.py`: Message, Candidate, ExtractionResult, Identity, GradedRequest, LogRecord,
   GoldChat (+ small helpers: Roster, Contact, GoldRequest).
3. `triage/parse.py` (chat-miner + pre-pass, IDs, contacts.yaml, kind) and `triage/render.py`
   (line format, dividers, handles, phone masking). Tests on the fixture.
4. `data/world/roster.yaml` (+ `data/world/contacts.yaml`). Phone test over roster, contacts and
   dev chats.
5. A small, deterministic policy oracle is needed to label gold "by applying SPEC §9": put it in
   `scripts/validate_gold.py` as a plain table check (grade ↔ rule consistency + per-request
   facts recorded in gold), not the runtime policy engine (that is Phase 5).
6. ~15 dev chats + gold + coverage table in data/dev/README.md.
7. `scripts/validate_gold.py` wired into pytest and pre-commit. SPEC: Android-only limitation.
8. Checks, commits, push, PR, phase report.

## Parser check results

(filled in below after running chat-miner on the fixture)
