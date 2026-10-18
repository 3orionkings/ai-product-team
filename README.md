# AI Product Team

A set of 64 specialist agents, 28 shared method skills and 12 workflows that you install into a project and use from Claude Code or Codex. Together they investigate, design, build, evaluate and improve an AI feature, and they keep a record of what each conclusion rests on.

You ask in plain language: "Turn these documents into a feature proposal", "Is this ready for a pilot?", "This test contradicts our isolation assumption; what must we revisit?" Your current session picks the smallest route that answers it. It tells you which roles it will run and which it will skip, runs only those, and writes every artifact and record into a case folder in your project. A summary request might use two roles. A disputed architecture decision might use ten.

## Status

**v0.1, October 2026: the definitions are complete; none has been evaluated on a live model.**

| Part | State |
|---|---|
| 64 role definitions, each with a positive and a negative scenario | written; pass the authoring checks in `tools/check_authoring.py` |
| 28 shared method skills | written; 11 adapted from the author's earlier drafts, 17 new; pass the same checks |
| 12 workflow recipes and their entry skills, plus `aipt-start` | written |
| Claude Code files (`dist/claude/`) | generated; match the documented format (static tests); live discovery not yet verified |
| Codex files (`dist/codex/`) | generated from the documentation only; live validation blocked (no working Codex CLI on the build machine) |
| Installer (`install.py`) | working; tested for dry run, conflicts, symlinks, upgrade and uninstall |
| Record-keeping controller (`src/ai_product_team/`) | **experimental**; see below |
| Role, workflow or cross-host evaluation | **not done** |

What has not been shown yet: that the roles produce better results than an assistant without them, that both hosts load and run them as intended, or that any workflow completes end to end. The per-host records are in `docs/compatibility/`.

## Install

You need Python 3.11 or later, and Claude Code, Codex or both. Nothing else is installed.

```bash
git clone https://github.com/<owner>/ai-product-team.git
cd ai-product-team
python3 install.py --target ~/code/my-app --host claude --dry-run   # shows what would change
python3 install.py --target ~/code/my-app --host claude             # or --host codex, or --host both
```

The installer writes only under `.claude/`, `.codex/` and `.agents/` in that project, and records what it wrote in `.aipt/install-manifest.json`. It never edits your `CLAUDE.md`, `AGENTS.md`, settings or anything global. If a file it would write already exists and it did not write it, or you have edited one it wrote, it stops and changes nothing. Run `--status` to inspect an installation and `--uninstall` to remove it. Uninstall removes only files that are unchanged since install and keeps any you edited.

To check that Claude Code sees the roles, open the project and type `/agents`. You should see 64 entries named `aipt-…`.

## Use

In Claude Code, type `/aipt-start` followed by your request, or call a workflow directly, for example `/aipt-shape-feature`. In Codex, use `$aipt-start` or `$aipt-shape-feature`. Plain language also works: when a request fits, the host can pick up `aipt-start` from its description.

| You want to… | Entry skill |
|---|---|
| decide whether AI belongs in a workflow at all | `aipt-assess-opportunity` |
| turn documents into a feature proposal with requirements and acceptance checks | `aipt-shape-feature` |
| design how an AI feature should work | `aipt-design-system` |
| build a bounded version that can be tested | `aipt-build-prototype` |
| evaluate a feature against its real task | `aipt-evaluate-feature` |
| find out why a feature is failing | `aipt-investigate-failure` |
| know whether another model would do better | `aipt-compare-models` |
| cut cost or waiting without losing required quality | `aipt-optimize-cost-latency` |
| know whether a feature is ready for a proposed release | `aipt-review-release` |
| know what to revisit after something changed | `aipt-process-change` |
| challenge a proposal and settle a disagreement | `aipt-resolve-decision` |
| improve a method from verified outcomes | `aipt-learn-from-outcomes` |

`examples/support-copilot/` is a small synthetic case (a fictional help desk's reply-drafting feature) with a deliberate conflict between two documents and a protected isolation requirement. It is the quickest way to see what a workflow is supposed to do: point `aipt-shape-feature` at it.

## How it works

**One dispatcher.** Your current session is the only one that starts roles. On Claude Code, no role is given the tool to start another. On Codex, each role is told not to. Directors and managers return work orders and verdicts; they do not run other roles.

**Selective routing.** Each workflow is a short list of stages, some conditional. A stage is skipped when a current, accepted artifact already covers it. Review stages are never skipped. A budget mode caps the number of role calls: focused 4, standard 12, deep 24.

**A case ledger.** Every source, claim, requirement, decision, review, check and approval becomes one line in `aipt-cases/<case>/ledger.jsonl`, bound to a content hash. Lines are never edited; a change is a new version. The rules are in the `aipt-start` skill:

- A test result stays true as history, even after its target changes.
- A contradiction marks a claim as contested; it does not mark it false.
- A protected requirement survives a failed implementation.
- An approval covers exactly the version it was given for.

**Separated authority.** Roles propose. Managers review. Challengers attack a premise and must name the test that would settle it. Judges rule on evidence and are allowed to say "unresolved". A Decision Authority role accepts only what you have delegated. Releasing, publishing, sending, paying and deleting are never done by a role. The workflow stops and asks you.

**Evidence over self-report.** A check counts only if the session actually ran the command and recorded its exit status. A role saying "tests pass" is recorded as a claim.

These rules are instructions that the agents follow. In this release nothing enforces them in code. Claude Code does enforce one thing: the per-role tool lists in the generated files. Codex does not support per-role permissions, so there every role runs with your session's permissions.

## The organization

Three directors (Product, Engineering, Assurance), one workflow orchestrator, and ten teams of six:

| Team | Director | Examples |
|---|---|---|
| Discovery and strategy | Product | Context Analyst, Discovery Interviewer, Opportunity Analyst |
| Research and evidence | Product | Source Researcher, Claim Checker, Evidence Linker |
| Product and experience | Product | Journey Designer, Requirements Writer, Acceptance Designer |
| AI systems design | Engineering | Workflow Architect, Retrieval Designer, Safety Boundary Designer |
| Engineering and integration | Engineering | Repository Mapper, Prototype Engineer, Refactoring Engineer |
| Evaluation and quality | Engineering | Evaluation Designer, Test Engineer, Failure Analyst |
| Operations and economics | Engineering | Cost Analyst, Latency Analyst, Rollout Planner |
| Adversarial challenge | Assurance | Assumption Challenger, Alternative Advocate, Red-Team Tester |
| Decision and convergence | Assurance | Evidence Judge, Convergence Judge, Decision Authority |
| Assurance and improvement | Assurance | Independent Auditor, Security Reviewer, Learning Steward |

The full catalog is in `docs/directory/`. `index.html` there is searchable and works offline.

## Where the methods came from

Eleven of the 28 method skills adapt the author's own unpublished drafts from early 2026: seven reasoning skills and four delivery runbooks (plan, implement, audit, status handoff). The adaptations keep each draft's method, conditions, output contract and guardrails, and add typed inputs, examples and links to the shared record rules. Each adapted skill has a `references/adaptation-notes.md` listing what was preserved, changed and omitted. The other 17 skills and all 64 role bodies are new, written for this package. `registry/sources.public.json` lists every source by content hash. No third-party skill text is included.

## The experimental controller

`src/ai_product_team/` is a small Python library, standard library only. It was meant to enforce the ledger rules in code: immutable versions in SQLite, impact tracing over declared dependencies, version-bound approvals, review-independence checks, budget admission and command receipts. Eight of its modules are implemented and unit-tested (528 tests in the suite, which also covers the installer and generator). The run controller itself is incomplete, there is no command-line interface, and nothing connects the library to either host. The agents do not need it. `docs/architecture/controller-contracts.md` describes the intended design and marks what exists.

## Repository layout

```
agents/          64 role bodies (source)
skills/          28 shared method skills (source)
workflows/       12 workflow recipes (source)
entry/           the aipt-start entry skill (source)
registry/        agents, skills, workflows and public provenance (source of truth)
dist/            generated host files: dist/claude/, dist/codex/ (do not edit)
install.py       installer
tools/           build_adapters.py, build_directory.py, check_authoring.py
evals/           role and workflow scenarios (all unrun)
examples/        synthetic support-copilot case
docs/            directory, compatibility records, architecture, original design package
src/, tests/     experimental controller library and the test suite
```

## Development

```bash
python3 tools/check_authoring.py agents && python3 tools/check_authoring.py skills
python3 tools/build_adapters.py && python3 tools/build_directory.py
PYTHONPATH=src python3 -m unittest discover -s tests -t .
```

Edit the sources, never `dist/`. A test fails if `dist/` is stale.

## License

Pending. See `LICENSE_PENDING.md`. Until a license is applied, no part of this repository is offered under an open-source license.
