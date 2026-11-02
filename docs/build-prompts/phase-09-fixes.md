Context (new session): read CLAUDE.md, docs/SPEC.md, ARTEFACT.md and
docs/build-prompts/phase-08-challenge.md first. Main is at v1.0. PR #9 (challenge chats + results:
scenario 2 passes exactly, scenario 1 fails) is open.

PR #9 approved: merge it yourself once CI is green. Then start this phase from the updated main.
Save this prompt verbatim to docs/build-prompts/phase-09-fixes.md and append your plan.
Prefer existing open-source libraries over own code: install with uv add, check the licence and
current docs first, and add a line to ADR 0001.

> **Free LLMs only.** Use only OpenRouter models whose ID ends in `:free`, as listed in
> `config/models.yaml`. Never call a paid model, never add a paid provider or SDK, and never use
> a key other than `OPENROUTER_API_KEY` from the local `.env`. Before making any LLM call, state
> which free model and how many requests you will use, and wait for my approval if it is more
> than 10.

Pre-approved: up to 20 LLM requests. Stay under 50 per day. Develop and tune ONLY on data/dev.
Run the challenge eval exactly ONCE, at the end, only through eval.run_eval.

# Phase 9 — Fix the two scenario-1 failures → v1.1

## A. Slot fallback using dateparser (0 LLM requests)
1. Add `dateparser` (BSD). Check that its licence is permissive and whether it supports Telugu
   script ("te").
2. In triage/slots.py: when the model leaves slot_day_offset or slot_time null, take the
   request's evidence messages and normalise romanised Telugu with a small map:
   - repu/reepu → tomorrow;
   - ellundi → day after tomorrow;
   - ivala/ee roju → today;
   - "X ki" / "X gantalaki" → "X o'clock".

   Then parse with dateparser (search_dates), with RELATIVE_BASE set to the primary message's
   timestamp and prefer future dates.
3. Fill only fields that are null, and only when there's exactly one candidate; otherwise leave
   them null, which stays safe (R6).
4. For an "alaage" / "same" follow-up, inherit the slot of the referenced request.
5. Tests on synthetic fixtures. Record the method in SPEC (change-log v2.8).

## B. No acting on requests nobody made
6. Eval: add the metric "phantom acts" (a predicted act with no matching gold request) as a new
   hard gate, "phantom acts = 0". Note in ARTEFACT that it was added after the challenge run
   revealed the gap.
7. OPTIONAL (do it only if today's request budget allows; otherwise skip and report): prompt v4
   adds one field, explicit_ask (true only when a message directly asks Aminobots to do or send
   something). Code adds the flag implicit_request when it is false, which gives R6 instead of
   act. Log it in the prompts CHANGELOG and SPEC.

## C. Re-evaluate and finish
8. Re-run dev as v1.1-dev (Part A alone is cache-only; v4 costs about 15 requests). Report the
   v1.0 → v1.1 table, including phantom acts and approval load. Over-autonomy must stay 0.
9. Then run the challenge eval once as v1.1-challenge (cache, or 2 requests if v4 is used) and
   report every hard gate, including mandated_scenarios_pass_exactly.
10. Update ARTEFACT honestly: the challenge exposed two issues; the fixes were built on dev only;
    the challenge was re-run once, so it is no longer a blind test. Also update the site results
    (rebuild site/data from cache), the submission checklist, and the README (status v1.1, SPEC
    version).
11. Branch phase-09-fixes, commit, push, open a PR, six-part report with the merge SHA of PR #9
    at the top, then stop. I'll tag v1.1.

---

## Plan (Claude Code)

PR #9 merged at `3f2232d` (CI green). Branch `phase-09-fixes` from that main. LLM budget: 20
pre-approved, nemotron-3.5-super-vl:free only: dev v4 ≤ 17 (`--max-requests 17`), challenge ≤ 3.

**A (0 requests):** `uv add dateparser` (BSD-3-Clause; "te" locale present). Probing 1.4.3 showed
`search_dates` misreads "9 am" (→ September), "X o'clock" (nothing) and "day after tomorrow"
(→ +1 day), but reads "HH:MM", "tomorrow", "in 2 days", weekdays and "30th" correctly. So the
small normaliser in `triage/slots.py` maps the Telugu words to English day words and every time to
"HH:MM" first; dateparser then finds the dates. Only the requester's own evidence messages are
read (not the referenced message, not other people's replies). Fill only null fields; the day
must have exactly one candidate; the time is the earliest stated (SPEC §3.3's contract, and the
cautious choice for R7). Standing changes ("Monday nunchi", "from Monday", "every day") are left
null: d11 shows the model can miss `possible_forward`, and `time_unspecified` is then the only
thing between it and `act`. A follow-up with a resolved `refers_to_msg_id` inherits the null
fields of the referenced slot-change request. Tests on synthetic fixtures; SPEC v2.8.

**B:** `phantom_acts` (predicted act with no matching gold request) replaces `extras_graded_act`
in run_eval, plus the hard gate `phantom_acts_is_0`. Prompt v4 (optional, done, budget allows):
one required field `explicit_ask` in a v4-only response model chosen by the prompt's
`output_schema` front-matter, so the v3 schema and cache stay byte-identical; code adds the flag
`implicit_request` when it is false (→ R6).

**C:** v1.1-dev (v4, ~15 requests), compare with v1.0-dev; then v1.1-challenge once (2 requests).
ARTEFACT, site data, checklist, README, build-prompts index; PR; report.
