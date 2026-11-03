# Submission checklist (v1.1)

Portal items from [PROJECT_CONTEXT §3](context/PROJECT_CONTEXT.md#3-submission-portal-items-known-so-far)
and the repository requirements in the brief ([Appendix A](context/PROJECT_CONTEXT.md#appendix-a--original-brief-verbatim)).
✅ done · ⚠️ needs attention (reason given).

## Portal items

| Portal item | File / link | Status |
|---|---|---|
| Functional document | [docs/functional.md](functional.md) | ✅ |
| Approach document | [APPROACH.md](../APPROACH.md) | ✅ sections A–E, 1,482 words of prose (v1.0 count + 43 words of v1.1 edits), links both diagrams |
| Architecture diagram | [docs/architecture.drawio.svg](architecture.drawio.svg) | ✅ editable `.drawio.svg`, regenerated for v1.1 |
| Workflow diagram | [docs/workflow.drawio.svg](workflow.drawio.svg) | ✅ |
| UX prototype (optional, not graded) | the local website (`uv run python -m triage.serve`), [design brief](design/brief.md), [design review](design/review.md), [screenshots](screenshots/) | ✅ |
| Build plan | [docs/build-plan.md](build-plan.md) | ✅ includes the deployment option |
| AI transcript (share link + file) | outside the repo | ⚠️ **human**: claude.ai share link of the planning chats, plus one file of Claude Code `/export`s |

## Repository requirements (brief)

| Requirement | File / link | Status |
|---|---|---|
| README to set up and run from scratch | [README.md](../README.md#run-the-demo) | ✅ 3 commands |
| ARTEFACT.md, sections a–i | [ARTEFACT.md](../ARTEFACT.md) | ⚠️ complete except team names in §i and the transcript location (TODO placeholders) |
| Tagged prototypes | git tags `v0.1`, `v0.3`, `v1.0` | ⚠️ `v1.1` is tagged by the human after this PR merges |
| Deployed system at a public URL | [build plan → deployment option](build-plan.md#deployment-option) | ⚠️ deliberate: local only; deployment option in build plan (team decision for this submission) |
| Step-by-step inspection of any input | website drawer + Try your own ([screenshots](screenshots/)) | ✅ locally |
| Prompt pack, versioned | [prompts/](../prompts/CHANGELOG.md) | ✅ extract v1–v4 + CHANGELOG |
| Evaluation set | [data/dev/](../data/dev/README.md) (15 chats + gold); blind set in `data/test/` | ⚠️ blind set added (8 chats / 11 requests); results pending a run of `eval/run_eval.py` |
| Evaluation code | [eval/run_eval.py](../eval/run_eval.py), [scripts/validate_gold.py](../scripts/validate_gold.py) | ✅ |
| Committed results per prototype | [v0.1-dev](../eval/results/v0.1-dev/report.md), [v0.1.1-dev](../eval/results/v0.1.1-dev/report.md), [v1.0-dev](../eval/results/v1.0-dev/report.md), [v1.0-challenge](../eval/results/v1.0-challenge/report.md), [v1.1-partA-dev](../eval/results/v1.1-partA-dev/report.md), [v1.1-dev](../eval/results/v1.1-dev/report.md), [v1.1-challenge](../eval/results/v1.1-challenge/report.md), bake-offs | ✅ |
| Observability view (problem metrics + accuracy, latency, cost) | website Results section; [eval reports](../eval/results/v1.1-dev/report.md) | ⚠️ local metrics page only; Langfuse traces off (keys empty) |
| Code or prompts that generated the data | [phase-03-data prompt](build-prompts/phase-03-data.md), [data/dev/README.md](../data/dev/README.md) | ✅ hand-written by Claude Code, no generator script |
| Data provenance and licence | [data/LICENSE](../data/LICENSE), [ARTEFACT](../ARTEFACT.md#c-data-provenance) | ✅ CC BY 4.0, including the blind test set |
| Coding-agent setup | [CLAUDE.md](../CLAUDE.md), [.claude/](../.claude/), [SPEC](SPEC.md), [build prompts](build-prompts/README.md) | ✅ |
| No secrets in the repo | [.env.example](../.env.example), gitleaks pre-commit hook | ✅ |
| Hard gate: mandated scenarios pass exactly | [v1.1-challenge](../eval/results/v1.1-challenge/report.md) | ✅ both pass exactly in v1.1 (v1.0: scenario 1 failed). ⚠️ the fixes were built on dev only, but the challenge was re-run once, so it is no longer blind ([ARTEFACT §e](../ARTEFACT.md#e-evaluation-results)) |
| Hard gate: phantom acts = 0 (added in v1.1) | [v1.1-dev](../eval/results/v1.1-dev/report.md), [v1.1-challenge](../eval/results/v1.1-challenge/report.md) | ✅ 0 on both (v1.0-challenge had 1) |
| Telugu reviewed by a native speaker | blind test set; `telugu_reviewed_by` in each gold file | ⚠️ blind test set reviewed by Ch Pranav; dev (15 chats) and challenge (2 chats) remain unreviewed |
