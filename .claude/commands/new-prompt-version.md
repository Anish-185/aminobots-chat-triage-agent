---
description: Create the next immutable version of a runtime prompt with changelog and review
argument-hint: <prompt-id> <what to change and why>
---

Create a new version of the runtime prompt `prompts/<id>/`, as described: $ARGUMENTS

1. Find the highest existing `vN.md`. Copy it to `v{N+1}.md`. **Never edit `vN.md`.**
2. Apply only the requested change. Update the front-matter `version`.
3. Add a `prompts/CHANGELOG.md` entry: what changed, why, the target failure cases (dev IDs
   only), and the expected effect.
4. Run the dev eval before and after (`/run-eval dev pipeline wip-before` then `wip-after`,
   switching the prompt version through config), and show the delta table.
5. Invoke the **prompt-reviewer** subagent. Do not propose a commit unless its verdict is PASS.
