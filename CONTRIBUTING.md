# Contributing

Thanks for helping improve the generator.

## Ground rules

- `ENTRYPOINT.md` and `core/` are the authoritative rules. Keep them short, specific, and free of any single project's names or paths.
- Every rule about a mechanical property (IDs, formats, statuses, limits) should be enforced by `tools/validate_pack.py` and covered by a test case.
- Do not add framework opinions (DI, ECS, layering) as defaults. Opinions belong behind `architecture_policy`.

## Workflow

```bash
python tests/run_tests.py      # must pass
python tools/bundle.py         # rebuild dist/ if you touched ENTRYPOINT.md, core/, templates/, hosts/, or tools/
```

CI fails if `dist/` is out of date.

To add a validator rule: add the check in `tools/validate_pack.py`, add a mutation case to `CASES` in `tests/run_tests.py` (a small edit to the fixture that must trigger it), and confirm the clean fixture still passes with 0 errors and 0 warnings.

`tests/fixtures/good-pack` is fictional. Never copy its names into real guidance.

## Reporting results

The most valuable contribution is a real run. Use the *Run report* issue template: which AI tool, project size, profile chosen, validator output, and what the pack got wrong.

## Style

Python 3.9+, standard library only. Markdown: plain, no marketing language.
