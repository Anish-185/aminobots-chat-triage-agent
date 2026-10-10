Phase 0 — project initialisation. Set up a new repository "aminobots-chat-triage-agent" locally and on GitHub with the planning files. Do NOT write application code, run `uv init`, install dependencies or create hooks; later phases do that.

## 1. Preconditions — check and report first
- Confirm `git config user.name` / `user.email` are set, `gh` is installed, and `gh auth status` shows I'm logged in. If anything is missing, stop and give me the exact commands to fix it. Don't authenticate for me.
- Find `claude-code-pack.zip` in ~/Downloads (else search ~ to depth 3). If it's missing or there are several copies, stop and ask.
- Confirm ~/aminobots-chat-triage-agent doesn't exist. If it does, stop and ask.

## 2. Create the project
1. `mkdir ~/aminobots-chat-triage-agent && cd ~/aminobots-chat-triage-agent && git init -b main`
2. Unzip into a temp dir (`mktemp -d`), then `cp -a <tmp>/claude-code-pack/repo/. .` so hidden folders (.claude/) come too. Delete the temp dir.
3. Read CLAUDE.md fully; it governs all future phases.
4. Save this prompt verbatim to `docs/build-prompts/phase-00-init.md`, as CLAUDE.md requires.
5. Add `.gitignore`: Python caches, `.venv/`, `.env` and `.env.*` (but keep `.env.example`), `*.db`, `*.sqlite`, `.DS_Store`, `eval/tmp/`, `.streamlit/secrets.toml`.
6. Add a short `README.md`:
   - a one-line description: "Finds, attributes and grades requests in code-mixed Telugu–English partner group chats under a written autonomy policy; all actions simulated."
   - status: "Phase 0 — planning docs in place."
   - links to docs/functional.md, docs/SPEC.md and CLAUDE.md
   - the line "Synthetic data only. No action is ever executed."

## 3. Verify
- Print the file tree (excluding .git). Expected:
  - CLAUDE.md, README.md, .gitignore
  - docs/SPEC.md, docs/functional.md
  - docs/build-prompts/README.md and phase-00-init.md
  - .claude/agents/ (3 files) and .claude/commands/ (4 files)
- List Markdown links in README.md and docs/functional.md whose targets don't exist yet. Don't remove them.
- Secret scan: `grep -rIE "(sk-ant-|api[_-]?key\s*=\s*\S+)" . --exclude-dir=.git` must find nothing.

## 4. Commit and publish
1. Make one commit: `chore: phase 0 — planning docs, spec, functional overview, Claude Code setup`
2. Ask me whether the repo should be public or private (recommend public: assessors need access). Wait for my answer.
3. `gh repo create aminobots-chat-triage-agent --<public|private> --source=. --remote=origin --push --description "Bounded-autonomy triage agent for code-mixed Telugu–English partner group chats (simulated actions only)"`
4. Confirm with `git remote -v`, `git log --oneline -1`, and print the repo URL.

## 5. Finish
End with the phase report defined in CLAUDE.md (all six sections). Then stop.
