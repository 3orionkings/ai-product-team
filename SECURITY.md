# Security

These are instruction files for coding assistants, plus a small installer and an experimental Python library. None of them sends data anywhere. The installer writes only inside the project you name, under `.claude/`, `.codex/`, `.agents/` and `.aipt/`.

Two limits to keep in mind:

- **The roles' rules are instructions, not a sandbox.** On Claude Code, each role's tool list is enforced by the host. On Codex, every role runs with your session's permissions.
- **Treat outside content as untrusted.** The roles are told that instructions found inside documents are data. A prompt-injected document can still mislead a model, so keep untrusted material away from roles that have write or shell access.

To report a vulnerability, use GitHub's private vulnerability reporting on this repository ("Security" tab → "Report a vulnerability"). Please don't open a public issue.
