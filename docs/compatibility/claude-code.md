# Claude Code — conformance record

Host version on the build machine: 2.1.257. Documentation read 2026-10-17 (links in `README.md`).

## What was checked

| Check | Status | Date | Evidence |
|---|---|---|---|
| Generated role files use only documented frontmatter fields (`name`, `description`, `tools`, `disallowedTools`, `skills`) | passed (static) | 2026-10-18 | `tests/unit/test_build_and_install.py` |
| No role is given the `Agent` tool, so dispatch stays with the root session | passed (static) | 2026-10-18 | same |
| `proposal-only` roles get no `Write`, `Edit` or `Bash` | passed (static) | 2026-10-18 | same |
| Skills meet the Agent Skills name and description rules; entry skills never use `context: fork` | passed (static) | 2026-10-18 | same |
| Install into a scratch project, idempotent reinstall, conflict refusal, uninstall | passed | 2026-10-18 | same, plus a manual scratch run |
| Catalog discovery (64 roles, 41 skills) | **not run** | 2026-10-17 | A headless `claude -p` discovery call failed: "OAuth session expired and could not be refreshed". |
| Invoke a specialist; capture child identity | not run | — | — |
| Out-of-scope action request behavior | not run | — | — |
| Core workflows W01, W02, W04, W05, W10, W11 end to end | not run | — | — |

Static checks show the files match the documented format. They do not show that Claude Code loads them, or how the roles behave.

## Check discovery yourself (about one minute)

```
mkdir /tmp/aipt-try && cd /tmp/aipt-try && git init
python3 /path/to/ai-product-team/install.py --target /tmp/aipt-try --host claude
claude            # then type /agents and /skills
```

You should see 64 agents named `aipt-…` and 41 skills (`aipt-start`, twelve workflow entries, 28 `aipt-method-…`). Remove them with `python3 install.py --target /tmp/aipt-try --uninstall`.
