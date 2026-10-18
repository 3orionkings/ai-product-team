# Contributing

Thanks for looking. The most useful contributions right now are reports from actually running the agents, because no role or workflow has been evaluated on a live model yet.

## Most wanted

1. **Run reports.** Install into a scratch project, run a workflow (the synthetic case in `examples/support-copilot/` is a good start), and open a *Run report* issue: host and version, the request, which roles ran, what the case ledger shows, and where the behavior matched or missed the recipe.
2. **Codex conformance.** Codex support was generated from the documentation and never run. If you use Codex, check discovery (`/subagents`, `$aipt-start`) and report what works.
3. **Role and method improvements** backed by a concrete failure: the input, the output you got, and the output the role's own Negative case or Review rubric says it should give.

## Ground rules for changes

- **Edit the sources, never `dist/`.** Role bodies live in `agents/`, methods in `skills/`, workflow recipes in `workflows/`, the root entry skill in `entry/aipt-start/`, metadata in `registry/`. Rebuild with `python3 tools/build_adapters.py` and `python3 tools/build_directory.py`.
- **Follow the authoring contract** in `docs/architecture/authoring-contract.md`:
  - a role body has twelve sections in a fixed order, and a skill has ten;
  - nothing in a body names a model, vendor, price or host version;
  - every "must not" says what to do instead.
- **Reference a method; don't restate it.** If two roles need the same paragraph, it belongs in a skill.
- **Keep claims within the evidence.** A README or compatibility change that says something works needs a recorded run behind it, in `docs/compatibility/`.
- **No private or real-world data in examples.** Use synthetic cases.

## Before you open a pull request

```bash
python3 tools/check_authoring.py agents
python3 tools/check_authoring.py skills
python3 tools/build_adapters.py && python3 tools/build_directory.py
PYTHONPATH=src python3 -m unittest discover -s tests -t .
```

CI runs the same checks. A pull request that leaves `dist/` stale fails.

## Adding a role or a method

See `docs/customizing.md`. It covers the registry entry, the body, the fixtures and the rebuild.

## Conduct

Be direct and kind. Critique the work, not the person. Assume good faith, and say what evidence would change your mind.

By contributing you agree that your contribution is released under the repository's MIT License.
