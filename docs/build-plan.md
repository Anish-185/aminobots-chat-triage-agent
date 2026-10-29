# Build plan

Phases follow [context §4.12](context/PROJECT_CONTEXT.md). One phase prompt at a time; each ends
with a phase report and a PR. Tags are created by the human after reviewing eval results.
Owners are placeholders until the team assigns them.

## Phases

| Phase | Deliverable | Exit criterion | LLM requests | Owner |
|---|---|---|---|---|
| P0 | Reset: CLAUDE.md, SPEC v2, functional.md, README | Old work archived; docs merged | 0 | Member A |
| P1 | Bootstrap: deps, config + `:free` validator, guards, CI | CI green; guard tests pass | 0 | Member A |
| P2 | Submission docs: APPROACH.md, two `.drawio.svg` diagrams, this plan | Diagrams parse and open in diagrams.net; APPROACH ≤ 4 pages | 0 | Member B |
| P3 | Schemas, parser (chat-miner), roster, ~15 dev chats + gold, gold validator | Every dev chat parses; gold validates; all phones invalid | 0 | Member C |
| P4 | Extract + ground + cache + Langfuse; free-model bake-off | Valid structured output on dev; default model chosen | ≤ 25 (smoke + 2 models × 10 chats) | Member B |
| P5 | Identity + policy + routing + CLI + eval script; eval on dev + 2 human-written challenge chats (the two mandated scenarios, verbatim) | All worked checks pass; pass rule evaluated on dev + challenge → **v0.1** | ≈ 17 | Member A |
| P6 | Website + API, local only, one serve command | Demo opens on localhost; "try your own" works or explains → **v0.3** | ≤ 10 (precompute uses cache) | Member C |
| P7 | ARTEFACT.md, final APPROACH/README, link check; publish decision | Final eval committed → **v1.0** | ≈ 17 | Member D |

Total ≈ 70 requests over the project.

**Dropped (plan change in Phase 4):** the separate test set and baseline B1 (old P6, v0.2), and
the error-analysis / prompt-iteration phase (old P8). **This is a limitation:** there is no
held-out test set and no baseline, so dev scores are optimistic and nothing shows with numbers
how much code-side grading beats a single prompt. Only the 2 challenge chats are unseen.

## Request budget

- OpenRouter free tier: **50 requests/day**, 20/minute. Free models only (`:free`); billed cost is
  $0. Retries count against the quota, so there are no retry loops and every request is cached.
- A dev + challenge eval costs about 17 requests.
- Any step needing more than 10 requests is announced first and needs approval.
- 💰 **Declined option:** a one-time $10 OpenRouter credit purchase would raise the cap to 1,000
  requests/day (free models stay $0). Not taken; revisit only if the daily cap becomes the
  bottleneck.

## Deployment option

**Not done: the team decided to submit local only.** Kept here for later (CLAUDE.md invariant 12: local only until
publishing is approved). The brief asks for a public URL. The code is ready for it: one process
serves the site and API, paths are relative, the API URL is a `<meta>` tag and the host and CORS
origins live in `config/server.yaml`. The smallest option is one container running
`uv run python -m triage.serve` on a free container host, with:

- `config/server.yaml` widened to the public origin (its local-only validator changed on purpose);
- the demo key's daily cap made persistent (it is in memory today);
- `OPENROUTER_API_KEY` set as a host secret, never in the repo.

Which host, and whether its free tier still exists, must be checked against its current docs
before choosing; nothing here is verified.

## Top risks

| Risk | Impact | Mitigation |
|---|---|---|
| Free models rotate out or get rate-limited at peak times (nemotron-3-super:free was retired before P4) | Extraction stops; results not comparable | Two configured models (bake-off picks default, other is fallback); response cache; strict-model mode for milestones; re-check models in P4 |
| Daily request cap (50/day) | Slow iteration; milestone evals take 1–2 days | Cache every response; small dev set; plan evals across days |
| Telugu realism of synthetic chats; no held-out test set | Eval overstates real performance | Teammate reviews Telugu; humans write the 2 challenge chats; per-script slices; stated as a limitation |
| chat-miner parsing gaps (system lines, formats) | Lost messages or wrong IDs | Verify in P3; ≤ 30-line pre-pass for system lines; parser tests on edge cases |
| Deployment requirement deferred (brief asks for a public URL) | Submission gap | Site and API stay deploy-ready (relative paths, configurable API URL); publishing decided explicitly before P7 |
