# AGENTS.md — developing this package

This file guides agents working *on* the ai-product-team repository. It is not the AI Product Team's role catalog; that lives in `registry/`, `agents/` and `skills/`.

- Source of truth: `registry/*.json` for metadata; `agents/<id>.md` and `skills/<name>/SKILL.md` for bodies; `schemas/` for contracts. Generated files (`adapters/**/generated`, `docs/directory/`) are rebuilt by `aipt` commands and must not be hand-edited.
- Run `python -m pytest -q` (or `python -m unittest discover -s tests`) before claiming a change works. Record any check you did not run as unrun.
- Never add provider model ids, prices or host version facts to role or skill bodies; they belong in dated files under `policies/` and `docs/compatibility/`.
- Never add personal paths, private sources or run databases to the tree. `registry/sources.public.json` is the only provenance record allowed in the repo.
- Install into scratch targets only, with `--dry-run` first.
