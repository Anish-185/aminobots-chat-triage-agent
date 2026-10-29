PR #7 is merged and tagged v0.3. Start Phase 7 from the updated main.

> **Free LLMs only.** Use only OpenRouter models whose ID ends in `:free`, as listed in
> `config/models.yaml`. Never call a paid model, never add a paid provider or SDK, and never use
> a key other than `OPENROUTER_API_KEY` from the local `.env`. Before making any LLM call, state
> which free model and how many requests you will use, and wait for my approval if it is more
> than 10.

Pre-approved: up to 5 LLM requests (challenge eval only, if challenge chats exist).

# Phase 7 — Policy v2, final eval, final docs → v1.0

Save this prompt verbatim to docs/build-prompts/phase-07-final.md and append your plan.

## A. Policy v2 (decision made: approved; SPEC change-log v2.7)
1. Create policy/policy_v2.yaml. It is v1 with ONE change: R7 also requires status == open. The
   rationale: R7's cut-off is about whether there is time to execute safely, and closed requests
   execute nothing (R8 records them only). This matches the v2.6 time_unspecified fix. Every
   other rule still applies to closed requests.
2. Keep policy_v1.yaml unchanged. Make v2 the default in config.
   - Update the worked-check tests: add "cancelled slot change under 12 h, CONFIRMED staff →
     act, R8" and keep "cancelled payout change from an unknown number → refuse, R2".
   - Update the validator to derive labels from the configured policy.
3. Relabel d03 r1 to act R8. Note in the dev README that it changed because of the policy v2
   decision, not to match the model.
4. Re-run the dev eval from cache only (0 new requests) as eval/results/v1.0-dev/. Report the
   v0.1 → v0.1.1 → v1.0 table. Over-autonomy must be 0.
5. Regenerate both diagrams with scripts/make_diagrams.py so the models and policy are current,
   and copy the architecture SVG into site/ again.
6. Rebuild site/data from cache. The Results section must show v1.0 numbers.

## B. Challenge
7. If data/challenge/ contains chats, run run_eval --split challenge --tag v1.0-challenge and
   report the hard gates, including mandated_scenarios_pass_exactly. If it's empty, don't create
   anything there; list it as the main limitation.

## C. Final documents (read the portal checklist in docs/context/PROJECT_CONTEXT.md and map
every required item to a file)
8. ARTEFACT.md (repo root):
   - What was built, in 5 lines, plus links to the run-demo steps and screenshots.
   - Results: the v1.0 dev table, the challenge table or a "not run" statement, and the hard
     gates.
   - Error analysis: every remaining dev error with its cause (for example, the d10 English
     refund miss and slot fields left empty), and what would fix each.
   - Limitations: dev-only evaluation built by the same agent; no baseline; synthetic data only;
     Telugu not yet reviewed by a native speaker (unless telugu_reviewed_by is set); Android
     export format only; free-model availability (gemma never measured); the in-memory request
     cap; local only, with no public URL (the deployment option is in the build plan).
   - Responsible-AI notes: simulate-only enforcement, phone masking, free providers log prompts
     (synthetic data only), visitor key handling.
   - How AI was used: Claude Code built it, with the phase prompts in docs/build-prompts/.
     Session transcripts are exported by the team and kept outside the repo; add a placeholder
     line for their location.
   - Team and ownership: placeholders Member A–D, with a TODO.
   - Licences: MIT for code, CC BY 4.0 for data, and third-party attributions (skills, fonts,
     GSAP, Lenis).
9. APPROACH.md: update it to match what was actually built (policy v2, the model, eval
   results). Stay under 1,800 words of prose.
10. README: final status "v1.0 — complete demo (local)"; a 3-command run; links to ARTEFACT,
    APPROACH, SPEC, functional, diagrams, build plan and screenshots.
11. docs/build-prompts/README.md: an index of every phase prompt, one line each.
12. docs/submission-checklist.md: a table of portal item → file/link → status (✅ / ⚠️ with a
    reason).
13. Run a relative-link check on all markdown files and fix anything broken.

## D. Finish
14. All checks green; commit; push phase-07-final; open a PR. Six-part report with:
    - the final eval table;
    - the submission checklist;
    - anything still needing a human (names, transcripts, Telugu review, challenge chats,
      tags).

    Then stop. I tag v1.0 myself after merging.

---

## Plan (Claude Code)

Branch `phase-07-final` from main (`0f73ea6`, tagged v0.3). LLM budget: 5, challenge eval only.

**A:** `policy/policy_v2.yaml` = v1 + `status == "open"` on R7; `config/policy.yaml` selects the
version (2); `triage/policy.py` loads the configured file. `scripts/validate_gold.py` derives
labels with `triage.policy.decide` on the configured policy instead of its own copy of the rules.
Worked checks for v2 (the new cancelled-slot case) plus a test that v1 still gives R7. Relabel
d03 r1 (act R8) with a dev README note. `run_eval` dev with `--max-requests 0` → `v1.0-dev`.
Diagrams regenerated; `build_site_data.py` reads the configured policy and the v1.0 results.

**B:** `run_eval --split challenge --validate-only` (no LLM call) shows whether chats exist; the
challenge eval runs only if they do.

**C:** read the portal checklist in PROJECT_CONTEXT; write ARTEFACT.md; update APPROACH.md
(≤ 1,800 words of prose), README, the build-prompts index and the submission checklist; a stdlib
relative-link check over all markdown.

**D:** checks, commits, push, PR, report.
