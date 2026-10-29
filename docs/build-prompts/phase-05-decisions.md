PR #5 approved: merge it yourself once CI is green.

> **Free LLMs only.** Use only OpenRouter models whose ID ends in `:free`, as listed in
> `config/models.yaml`. Never call a paid model, never add a paid provider or SDK, and never use
> a key other than `OPENROUTER_API_KEY` from the local `.env`. Before making any LLM call, state
> which free model and how many requests you will use, and wait for my approval if it is more
> than 10.

Pre-approved for this whole prompt: up to 35 LLM requests in total. Stay under 50 per day across
all work; if the daily limit is near, stop, report, and resume the next day. State the count
before each batch. Never retry in a loop.

## Part A — Phase 4 follow-ups (SPEC change-log v2.5)
1. Slot contract: the model no longer outputs slot_datetime. It outputs slot_day_offset (days
   after the request message's date: 0 = today, 1 = tomorrow/"repu", 2 = day after/"ellundi",
   null if not stated) and slot_time ("HH:MM" 24h, or null). Code computes slot_datetime from the
   primary message's date. If a slot change has either part null, code adds the flag
   time_unspecified, which gives R6 seek_approval. Write this as prompts/extract/v2.md and log
   it in the CHANGELOG. Update the schema, SPEC and tests.
2. Config: request_timeout_s: 300. A timeout still fails closed (no retry).
3. Reasoning: if OpenRouter supports a reasoning-effort or reasoning-exclusion setting for the
   default model (check its docs), try it on 2 dev chats. Keep it only if those chats lose no
   gold requests and latency drops. Record the result.
4. Re-runs: nemotron on d10 and d13 (prompt v2); gemma once on the same 10 bake-off chats. If
   gemma hits 429 again, stop it immediately; nemotron stays default and ADR 0002 says
   "default by availability". Update ADR 0002 and eval/results/bakeoff-v1 (or add bakeoff-v2).
5. Look at nemotron's 3 extra predictions: either the gold missed a real request (fix the gold
   and note it in the dev README) or it's a model false positive (note it for the prompt).
   Don't change gold to match the model unless the request is genuinely in the chat.

# Phase 5 — Decisions, pipeline, evaluation → v0.1

Save this prompt verbatim to docs/build-prompts/phase-05-decisions.md and append your plan.

6. triage/identity.py per SPEC:
   - the three states, with name matching via rapidfuzz at the configured threshold;
   - self-claims and vouching never confirm a sender;
   - a security-code change downgrades the sender to UNCONFIRMED;
   - authority comes from the roster, and AMBIGUOUS is authorised only if every candidate is;
   - principal outlet and the outlet_ambiguous rule, on-behalf and delegate check, and the
     cross-partner case;
   - aminobots_staff requests are marked internal;
   - every result carries a human-readable reason.
7. policy/policy_v1.yaml (R1–R10 as rule-engine expressions) and triage/policy.py:
   - evaluate every rule; the most cautious grade wins; cite the lowest-numbered rule with that
     grade; record all matched rules; nothing matched → R10;
   - every SPEC worked check is a unit test, plus the property test that adding a rule never
     lowers caution.
8. triage/route.py: the JSONL logs per SPEC (simulated: true, phones masked to the last 4 digits,
   record_only for R8). Add a test that route.py imports no network client.
9. triage/pipeline.py:
   - parse → render → extract → ground → identity → policy → route;
   - ExtractionFailed, 429, timeout or a parse error makes the chat UNPROCESSED, with one
     hand-off record for the whole chat (never "no requests");
   - return one result object holding every stage's data, which the website will reuse.

   triage/cli.py: `uv run python -m triage.cli run <chat.txt>` prints a table (gloss, sender +
   state, grade, rule, evidence IDs); `--json` prints the full result.
10. eval/run_eval.py --split dev|challenge --tag <tag>:
    - every metric in SPEC, including approval load and per-script slices;
    - the hard gates;
    - strict mode;
    - writes eval/results/<tag>/summary.json and report.md;
    - challenge results keep IDs and labels only, never message text;
    - it is the only code allowed to read data/challenge.
11. docs/data/challenge-template.md, for humans: the Android export format, the rules
    (synthetic, invalid phones, morning timestamps for scenario 1), how message IDs are counted
    (m001 = first message line), a filled example gold JSON, and the command to validate it. Do
    not create or read anything in data/challenge yourself.
12. Live:
    - run_eval on dev, tag v0.1-dev;
    - if data/challenge contains chats, run them too (tag v0.1-challenge) and report the hard
      gates;
    - if it's empty, say so and stop there.
13. Finish: all checks green; commit; push phase-05-decisions; open a PR. Six-part report with:
    - a metrics table for dev (and challenge if run);
    - the hard-gate results;
    - approval load;
    - total LLM requests used, by day.

    Then stop. I tag v0.1 myself after merging.

---

## Plan (Claude Code)

PR #5 merged (8a80650). Request budget: 35 for this prompt; 11 already used today (2026-10-29).

**Part A**
1. Schema: `Entities.slot_day_offset: int | None` and `slot_time: "HH:MM" | None` replace the
   model's `slot_datetime`. Code computes `slot_datetime` (primary message date + offset + time).
   A slot change missing either part gets `time_unspecified`, which gives R6. This goes in
   `prompts/extract/v2.md`, the CHANGELOG, SPEC v2.5 and tests.
2. `request_timeout_s: 300` in thresholds, passed to the SDK. A timeout is still not retried.
3. Reasoning: check the OpenRouter docs. Try `effort: none` (or exclusion) against `low` on 2
   dev chats with v2. The `low` runs count toward the dev eval, so this costs about 2 extra
   requests.
4. Re-runs with v2: nemotron covers all of dev in the v0.1-dev eval (including d10 and d13).
   Gemma runs once on the 10 bake-off chats and stops at the first 429. Results go to
   `eval/results/bakeoff-v2/`, and ADR 0002 is updated.
5. Review nemotron's 3 extra predictions (d07, d15) against the chat text.

**Phase 5**
6. `triage/identity.py`, `policy/policy_v1.yaml` with `triage/policy.py` (rule-engine),
   `triage/route.py`, `triage/pipeline.py` and `triage/cli.py`, as specified. Tests cover every
   SPEC worked check, the monotonicity property and the no-network import check.
7. `eval/run_eval.py` with the SPEC metrics, gates and slices. Only it touches `data/challenge`.
   Plus `docs/data/challenge-template.md`.
8. Live: v0.1-dev (15 requests). Then challenge only if `run_eval` finds chats there.

Estimated requests: 2 (reasoning trial) + 15 (dev) + 10 (gemma) + up to 2 (challenge), about 29.
Day total about 40 of 50.
