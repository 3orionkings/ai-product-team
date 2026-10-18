# Fork and customize

The package is meant to be adapted. Everything a host loads is generated from a few source folders. Change the sources, rebuild, and reinstall into your project.

## Start your own copy

- **Fork** on GitHub to keep a link to upstream and send changes back.
- **Use this template** for a clean copy without history.
- Or just clone and install. You don't need your own copy to use the agents as they are.

## Use only part of the team

Install everything, then use the parts you need. Roles that are never dispatched cost nothing: a host loads only names and descriptions until a role is used. To keep a project lean, install with `--host claude` or `--host codex` rather than `both`.

If you want a smaller catalog in your fork, remove roles from the registry (next sections) rather than deleting installed files. The installer restores files it owns on the next install.

## Change what a role does

1. Edit `agents/<role-id>.md`. Keep the twelve sections from `docs/architecture/authoring-contract.md`. If you change the role's rule or negative case, also change its `distinctive_rule` or `negative_test` in `registry/agents.json`, because the checker compares them verbatim.
2. Update `evals/roles/<role-id>/positive.json` and `negative.json` if the expected behavior changed.
3. Run `python3 tools/check_authoring.py agents`.
4. Run `python3 tools/build_adapters.py`, then reinstall: `python3 install.py --target <project> --host claude`. Files you have not edited in the project are updated in place.

## Change a shared method

Edit `skills/aipt-method-<name>/SKILL.md`. Every role that lists the method picks up the change, so check which ones do first: the "Methods" line in `docs/directory/` shows this, as does `skill_ids` in `registry/agents.json`. Then run `python3 tools/check_authoring.py skills` and rebuild.

## Add a role

1. Add an entry to `registry/agents.json` with the same fields as its neighbors:
   - `id`, `native_name` (`aipt-<id>`), `name`, `type`, `team`;
   - `reports_to` and `reviewed_by`;
   - `description`, `input_contract`, `output_contract`, `distinctive_rule`, `negative_test`;
   - `skill_ids`, `write_scope`, `may_dispatch: false`, `acceptance_authority`, `status`, `dispatch_condition`.
2. Write `agents/<id>.md` from the template in the authoring contract.
3. Add `evals/roles/<id>/positive.json`, `negative.json` and `readiness.json`.
4. If a workflow should use it, add it to that workflow's stages or `conditional_specialists` in `registry/workflows.json`, and to the recipe in `workflows/`.
5. Run the checks and rebuild.

The registry validator in `src/ai_product_team/registry.py` expects ten teams of six plus four leadership roles. If you change the shape of the organization, update its counts and the matching test in `tests/unit/test_registry.py`.

## Add a method

Add an entry to `registry/skills.json` (`id`, `name`, `title`, `summary`, `provenance`). Then create `skills/aipt-method-<name>/SKILL.md` from the skill template, with a frontmatter `name` that matches the folder exactly, and list its id in the `skill_ids` of the roles that should use it.

## Add a workflow

Add an entry to `registry/workflows.json` (copy the shape of an existing one) and a recipe in `workflows/<name>.md` with the same section headings as the others. Add a fixture in `evals/workflows/<name>/fixture.json`. The generator creates the entry skill `aipt-<name>` from the registry entry and bundles the recipe as its reference.

## Change the `aipt-` prefix

The prefix appears in `native_name` in `registry/agents.json`, in the skill folder names under `skills/`, in `entry/aipt-start/`, and in the `aipt-…` names inside role and recipe text. A global rename across those files, followed by a rebuild, works. Run the full checks afterwards.

## Keep your fork current

```bash
git remote add upstream https://github.com/3orionkings/ai-product-team.git
git fetch upstream && git merge upstream/main
python3 tools/build_adapters.py && python3 tools/build_directory.py
```

Conflicts land in the source files, never in `dist/`. Rebuild after resolving them.
