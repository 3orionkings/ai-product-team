# Changelog

## 0.1.0 — 18 October 2026

First public release.

- 64 role definitions in ten teams of six, plus three directors and a workflow orchestrator. Each role has a positive and a negative scenario.
- 28 shared method skills: 11 adapted from the author's earlier drafts, 17 new.
- 12 workflow recipes, each with an entry skill, plus the root entry skill `aipt-start` and its case-ledger rules.
- Generated host files for Claude Code (`dist/claude/`) and Codex (`dist/codex/`), and `install.py` for repository-scoped install, upgrade, status and uninstall.
- An offline, searchable agent directory (`docs/directory/`) and a synthetic example case (`examples/support-copilot/`).
- An experimental record-keeping library in `src/`, partly built and not connected to either host.

Not verified in this release: live discovery and execution on either host, and any evaluation of role or workflow behavior. See `docs/compatibility/`.
