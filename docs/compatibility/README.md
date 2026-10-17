# Host compatibility

The neutral role, skill and workflow contracts are authoritative. Each host adapter translates them into that host's registration format and declares, in `adapters/<host>/capabilities.json`, what the host supports, what it does not, and what has actually been tested. Nothing in this directory is a compatibility claim until the corresponding row says so from a recorded run.

## Matrix (as of 2026-10-17)

| Capability | Claude Code | Codex |
|---|---|---|
| Role registration format | `.claude/agents/<name>.md`, Markdown + YAML frontmatter | `.codex/agents/<name>.toml`, one TOML file per agent |
| Required fields | `name`, `description` | `name`, `description`, `developer_instructions` |
| Skills location | `.claude/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` |
| Per-role tool restriction | yes (`tools` / `disallowedTools`) | no (`features.*` flags only) |
| Per-role sandbox or approval policy | partial (`permissionMode`; adapter never sets it) | **no** — inherited from the parent by documentation |
| Isolation claim the adapter makes | `tool_allowlist_only` | `inherited_from_parent` |
| Native dispatch | yes; adapter withholds `Agent` from every role to keep it flat | yes by documentation; nesting undocumented |
| Child identity observable | yes (agent id returned; transcript path) | unknown (not stated in docs) |
| Usage / cost observable | no → unknown | no → unknown |
| Human input attested | no | no |
| Installed version observed | 2.1.257 | none (binary missing) |
| Live validation status | not run | **blocked** |

## The three execution labels

- `native` — a real host child executed the assigned role and its identity was recorded by the controller (`task attach` with the observed child id).
- `sequential` — the current assistant followed a role's instructions without independent delegation. Weaker isolation; labelled as such.
- `manual_handoff` — a person moved the packet into a new session. Origin and independence remain unverified unless observable.

A fourth label, `fixture_replay`, marks software tests that drive the controller with predetermined responses. It is never reported as any of the three above.

## What this directory does not establish

Behavior of either host for AIPT roles, actual permission enforcement, child identity capture on Codex, nesting behavior, or cancellation. Each is an M6 conformance item recorded per host in `claude-code.md` and `codex.md` from actual runs, with host version, settings, observed results and unavailable fields.

## Documentation consulted

Claude Code: https://code.claude.com/docs/en/sub-agents and https://code.claude.com/docs/en/skills. Codex: https://learn.chatgpt.com/docs/agent-configuration/subagents, https://learn.chatgpt.com/docs/build-skills, https://learn.chatgpt.com/docs/config-file/config-reference. Shared skill format: https://agentskills.io/specification. All read on 17 October 2026; recheck before any release.
