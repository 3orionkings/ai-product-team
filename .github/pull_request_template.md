## What changed and why

<!-- One or two sentences. Link the issue or run report if there is one. -->

## Checks

- [ ] I edited sources (`agents/`, `skills/`, `workflows/`, `entry/`, `registry/`), not `dist/`
- [ ] `python3 tools/check_authoring.py agents` and `... skills` pass
- [ ] I rebuilt `dist/` and `docs/directory/`
- [ ] `PYTHONPATH=src python3 -m unittest discover -s tests -t .` passes
- [ ] Any new claim in README or `docs/compatibility/` is backed by a recorded run
