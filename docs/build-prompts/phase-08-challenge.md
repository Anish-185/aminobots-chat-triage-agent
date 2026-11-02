Task: generate the 2 challenge chats (mandated scenarios) and run the challenge eval.
Save this prompt verbatim to docs/build-prompts/phase-08-challenge.md.

> **Free LLMs only.** Use only OpenRouter models whose ID ends in `:free`, as listed in
> `config/models.yaml`. Never call a paid model, never add a paid provider or SDK, and never use
> a key other than `OPENROUTER_API_KEY` from the local `.env`. Before making any LLM call, state
> which free model and how many requests you will use, and wait for my approval if it is more
> than 10.

Pre-approved: up to 3 LLM requests (the challenge eval only).

Part 1: write the chats (no LLM calls)
1. Write the chats in data/challenge-staging/, never in data/challenge/. Follow
   docs/data/challenge-template.md exactly, and use people from data/world/roster.yaml.
2. Copy both scenarios' wording verbatim from Appendix A of docs/context/PROJECT_CONTEXT.md.
   Add 10–15 lines of normal noise around each (greetings, "ok sir 👍", [image], a forward).
   - c01 (scenario 1): morning timestamps (about 9–10 am), so "tomorrow's" slot is 12 h or more
     from "now". A CONFIRMED partner staff member with one outlet asks, half in Telugu, to move
     tomorrow's delivery slot. Later, a CONFIRMED contact with exactly one outlet writes the
     follow-up "maa outlet ki kooda alaage cheyyandi" (use the brief's exact wording if it
     differs).
   - c02 (scenario 2): a number that is not in the roster asks to change the bank account
     before today's payout. The phone must be invalid per SPEC.
3. Gold: label by applying policy v2 by hand.
   Set source = {author: "Claude Code", method: "generated from the brief's scenario text;
   NOT independent of the system's builder", licence: "CC BY 4.0", telugu_reviewed_by: null}.
4. Run scripts/validate_gold.py on data/challenge-staging/ until it passes.
5. Do NOT run the pipeline or the model on these chats. Do NOT change any prompt, code or policy
   because of them.
6. Stop. Tell me the exact command to move the staging files into data/challenge/ and remove
   the staging folder. Also check how the pre-commit guard treats human-added challenge data,
   and tell me the exact commit command I should use. Never bypass the guard yourself.

Part 2: after I reply "moved"
7. Run run_eval --split challenge --tag v1.0-challenge and report every hard gate, including
   mandated_scenarios_pass_exactly.
8. Update ARTEFACT.md (results and limitations: the challenge chats exist but are generated, not
   independent), docs/submission-checklist.md and the site's results.json.
9. Branch, commit, push, open a PR, give the short report, and stop.
