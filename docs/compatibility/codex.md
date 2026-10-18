# Codex — conformance record

**Live validation: blocked.** The Codex CLI on the build machine does not start (its vendored executable is missing), and the owner chose to leave it blocked for v0.1. The Codex files were generated from the official documentation only (links in `README.md`).

| Check | Status | Evidence |
|---|---|---|
| Each role is one TOML file with exactly `name`, `description`, `developer_instructions`, and it parses | passed (static) | `tests/unit/test_build_and_install.py` |
| No role uses a reserved built-in name (`default`, `worker`, `explorer`) | passed (static) | same |
| Skills are placed under `.agents/skills/`, a documented scan path | passed (static) | same |
| Install, idempotent reinstall, conflict refusal, uninstall | passed | same |
| Discovery, dispatch, child identity, permissions, workflows | **blocked** | Codex CLI unavailable |

Codex documentation says a custom agent cannot narrow its own sandbox or approval policy, so on Codex every role runs with the parent session's permissions. The write-scope rules are instructions in each role's text, not an enforced boundary.
