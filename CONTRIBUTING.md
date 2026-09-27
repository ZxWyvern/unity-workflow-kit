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

To add a validator rule: add the check in `tools/validate_pack.py`, add a mutation case to `CASES` in `tests/run_tests.py` or a regression in `tests/test_tools.py`, and confirm the clean fixture still passes with 0 errors and 0 warnings. The main runner executes both suites. Exercise context selection, dependency preservation, and oversized-output behavior for loading changes.

Keep defaults cheap to load: optional modules load by relevance; copied tool source does not need to enter model context. Measure any cost claim on named inputs and distinguish character counts from actual model tokens. Broader project coverage must be explicit, not inferred from repository size.

`tests/fixtures/good-pack` is fictional. Never copy its names into real guidance.

## Reporting results

The most valuable contribution is a real run. Use the *Run report* issue template: which AI tool, project size, profile chosen, validator output, and what the pack got wrong.

## Style

Python 3.9+, standard library only. Markdown: plain, no marketing language.
