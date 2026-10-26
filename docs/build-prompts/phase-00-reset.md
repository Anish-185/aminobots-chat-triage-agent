@"/root/.claude/uploads/ba6f1a92-c101-5a55-ad79-a8fec440816f/4e99415f-NEW_CHAT_CONTEXT_1.md" you can check the repo and i need docs and also remove the old context if needed give more priority to the new context file do not complicate this project make it as simple as possible at the vewry end we should be able to showcase it in a website also it should be free only no paid subscription should be there if it is there then avoid it or find another alternative this is no a complete product this is just a demo build so you dont have to go all in Read the attached NEW_CHAT_CONTEXT.md completely before doing anything. It is the single source of truth for this project. Where anything already in this repo (old CLAUDE.md, SPEC v1.x, ADRs, config, folders from a first attempt) disagrees with it, the context file wins.

Role adjustment: that file was written for a planning assistant + Claude Code. Here you are Claude Code and do both: plan and build. Keep its working loop anyway. Do ONLY the current phase, end with the six-part phase report from §1, then stop and wait for me.

Guiding principles (from me, highest priority):
- This is a demo build, not a complete product. Choose the simplest thing that meets the brief. Don't go all in.
- Reuse open-source libraries (installed with uv, not copied in) instead of writing from scratch.
- Free only. OpenRouter models whose ID ends in ":free" are the only LLMs. If anything needs a paid plan or subscription, avoid it and propose a free alternative.
- Every API key stays empty in the repo.
- At the very end we showcase it on a website, run LOCALLY only. No deployment or hosting config.

PHASE 0: audit, reset, core docs. No LLM calls and no dependency changes in this phase.

1. Save this prompt verbatim to docs/build-prompts/phase-00-reset.md. Save the attached file verbatim to docs/context/PROJECT_CONTEXT.md.
2. Preserve the old work: create a branch `archive/first-attempt` from the current main and push it, before changing anything.
3. Audit: list every file and folder in the repo in a table with columns path · what it is · KEEP / UPDATE / DELETE · reason (judged against context v2). Show me the table and WAIT for my approval before deleting or rewriting anything.
   - Likely KEEP: guard scripts, Claude Code hooks, CI workflow, LICENSE files, pre-commit config, the :free config validator (see §6).
   - Likely DELETE: everything tied to Streamlit, Neon/SQLAlchemy, the Anthropic SDK, the data generator, SPEC v1.x, and old ADRs. New ADRs come in a later phase.
4. After I approve:
   - apply the audit
   - write CLAUDE.md (§8)
   - write docs/SPEC.md v2 (§4 condensed, ≤ 350 lines)
   - write docs/functional.md (the five portal points in §3, consistent with §4, plain language, Mermaid allowed)
   - write a short README.md with status "Phase 0: reset to simplified design" and links to these docs
   - check .gitignore covers .env, caches, runs/ and .cache/
5. Don't touch pyproject.toml or uv.lock yet; Phase 1 handles dependencies. If existing tests break because their code was deleted, remove those tests and list them in the report.
6. Commit with clear messages on a new branch and open a pull request to main. Don't merge it; I'll review and merge.

Finish with:
- the phase report
- any contradictions you found inside the context file
- what Phase 1 should contain, in at most 5 bullets

Mentor answers so far: [paste them here, or write "none yet"]
