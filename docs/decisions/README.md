# Architecture decision records

| ADR | Title | Status |
|---|---|---|
| [0001](ADR-0001-bounded-workflow.md) | Bounded workflow with one LLM stage | Accepted |
| [0002](ADR-0002-policy-yaml-own-evaluator.md) | Policy as YAML with an own evaluator, most-restrictive-wins | Accepted |
| [0003](ADR-0003-identity-by-roster.md) | Identity by roster lookup only | Accepted |
| [0004](ADR-0004-structured-outputs.md) | Structured outputs via Instructor, with semantic-validation retry | Accepted (amended) |
| [0005](ADR-0005-gold-by-construction.md) | Gold labels by construction from planner scripts | Accepted (amended) |
| [0006](ADR-0006-test-isolation.md) | Disjoint test pools, held-out templates, human challenge set, leakage check | Accepted |
| [0007](ADR-0007-trace-store.md) | Own trace store with OTel GenAI attribute names | Accepted |
| [0008](ADR-0008-hosting.md) | Streamlit Community Cloud + Neon Postgres | Accepted |
| [0009](ADR-0009-no-llm-guard.md) | No LLM-Guard dependency; injection neutralised structurally | Accepted |
| [0010](ADR-0010-invalid-synthetic-phones.md) | Synthetic phones in a provably invalid +91 range | Accepted |
| [0011](ADR-0011-plain-python-orchestration.md) | Plain Python orchestration and a DB approval queue | Accepted |
| [0012](ADR-0012-eval-slices.md) | Eval sliced by script and code-mix density | Accepted |
| [0013](ADR-0013-claude-code-guardrails.md) | Claude Code guardrails | Accepted |
| [0014](ADR-0014-zero-cost-openrouter.md) | Zero-cost operation with OpenRouter free models | Accepted |
