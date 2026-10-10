---
description: Run the evaluation for a split/system/tag via the eval-runner subagent and summarise against the pass rule
argument-hint: <split> <system> <tag> [max-usd]
---

Use the **eval-runner** subagent to evaluate with these arguments: $ARGUMENTS

- If any argument is missing, default to split `dev`, system `pipeline`, and tag
  `wip-<short git sha>`.
- After it reports, add one paragraph of your own: the single most important thing to fix next,
  based only on dev-split evidence.
