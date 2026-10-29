# Submission checklist (v1.0)

Portal items from [PROJECT_CONTEXT §3](context/PROJECT_CONTEXT.md#3-submission-portal-items-known-so-far)
and the repository requirements in the brief ([Appendix A](context/PROJECT_CONTEXT.md#appendix-a--original-brief-verbatim)).
✅ done · ⚠️ needs attention (reason given).

## Portal items

| Portal item | File / link | Status |
|---|---|---|
| Functional document | [docs/functional.md](functional.md) | ✅ |
| Approach document | [APPROACH.md](../APPROACH.md) | ✅ sections A–E, 1,439 words of prose, links both diagrams |
| Architecture diagram | [docs/architecture.drawio.svg](architecture.drawio.svg) | ✅ editable `.drawio.svg`, regenerated for v1.0 |
| Workflow diagram | [docs/workflow.drawio.svg](workflow.drawio.svg) | ✅ |
| UX prototype (optional, not graded) | the local website (`uv run python -m triage.serve`), [design brief](design/brief.md), [design review](design/review.md), [screenshots](screenshots/) | ✅ |
| Build plan | [docs/build-plan.md](build-plan.md) | ✅ includes the deployment option |
| AI transcript (share link + file) | outside the repo | ⚠️ **human**: claude.ai share link of the planning chats, plus one file of Claude Code `/export`s |

## Repository requirements (brief)

| Requirement | File / link | Status |
|---|---|---|
| README to set up and run from scratch | [README.md](../README.md#run-the-demo) | ✅ 3 commands |
| ARTEFACT.md, sections a–i | [ARTEFACT.md](../ARTEFACT.md) | ⚠️ complete except team names in §i and the transcript location (TODO placeholders) |
| Tagged prototypes | git tags `v0.1`, `v0.3` | ⚠️ `v1.0` is tagged by the human after this PR merges |
| Deployed system at a public URL | [build plan → deployment option](build-plan.md#deployment-option) | ⚠️ deliberate: local only; deployment option in build plan (team decision for this submission) |
| Step-by-step inspection of any input | website drawer + Try your own ([screenshots](screenshots/)) | ✅ locally |
| Prompt pack, versioned | [prompts/](../prompts/CHANGELOG.md) | ✅ extract v1–v3 + CHANGELOG |
| Evaluation set | [data/dev/](../data/dev/README.md) (15 chats + gold) | ⚠️ the 2 human-written challenge chats do not exist yet |
| Evaluation code | [eval/run_eval.py](../eval/run_eval.py), [scripts/validate_gold.py](../scripts/validate_gold.py) | ✅ |
| Committed results per prototype | [v0.1-dev](../eval/results/v0.1-dev/report.md), [v0.1.1-dev](../eval/results/v0.1.1-dev/report.md), [v1.0-dev](../eval/results/v1.0-dev/report.md), bake-offs | ✅ dev; ⚠️ no challenge results |
| Observability view (problem metrics + accuracy, latency, cost) | website Results section; [eval reports](../eval/results/v1.0-dev/report.md) | ⚠️ local metrics page only; Langfuse traces off (keys empty) |
| Code or prompts that generated the data | [phase-03-data prompt](build-prompts/phase-03-data.md), [data/dev/README.md](../data/dev/README.md) | ✅ hand-written by Claude Code, no generator script |
| Data provenance and licence | [data/LICENSE](../data/LICENSE), [ARTEFACT §c](../ARTEFACT.md#c-data-provenance) | ✅ CC BY 4.0 |
| Coding-agent setup | [CLAUDE.md](../CLAUDE.md), [.claude/](../.claude/), [SPEC](SPEC.md), [build prompts](build-prompts/README.md) | ✅ |
| No secrets in the repo | [.env.example](../.env.example), gitleaks pre-commit hook | ✅ |
| Hard gate: mandated scenarios pass exactly | `run_eval --split challenge` | ⚠️ not run: challenge set empty |
| Telugu reviewed by a native speaker | `telugu_reviewed_by` in each gold file | ⚠️ null in all 15 dev chats |
