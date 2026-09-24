# Changelog

## v1.2.1

Fixes and hardening after review of v1.2. Verified by `tests/run_tests.py`.

Fixed:

- Validator rejected packs that followed the spec: overflow finding stubs (`F-011 | ...`) were not recognized as definitions.
- Self-dependencies and dependency cycles among claims were not detected.
- An increment could be `done` while its exit check was `not_run`. Now an error.
- `invalidates:` was only a warning and fired on `proposed`/`unknown` claims. Now required for verified/inferred claims, optional for the others, and tokens are validated.

Restored from v1.1 (lost in the v1.2 split): `EditorSettings.asset` serialization-mode check with a failure rule, API-drift examples, project-lock detection, domain-reload settings, verification rules (pre-existing errors separate, no mirror tests, verify commands exist), and the nested shapes of `index.json` entries.

Changed:

- One home for the not-inspected list (`project-context.md`). Protected areas get `P-###` IDs and are referenced, not restated.
- Compact profile now includes a short `agent.md` (procedure) so `project-context.md` stays facts only.
- Tier definitions have approximate counts.
- AGENTS.md section is delimited by `ai-workflow` markers so the 150-line cap is enforceable.

Added:

- `tools/suspects.py` (suspect claims from changed files plus dependency closure, for Refresh).
- `tools/bundle.py` and `dist/` single-file bundle for paste-only use.
- `tools/packlib.py` shared parser; the three pack tools are copied into every generated pack.
- Validator checks: cited paths and symbols exist, `execution_verified` cites a `passed` check, `passed`/`failed` requires observed evidence, finding/stub/route/increment formats and caps, closed-finding lines, index entry shapes, `REPLACE_ME` placeholders.
- `tests/`: fictional fixture pack and a runner with clean and broken cases.

Packaging:

- Public `README.md` and `README.id.md`, `docs/USAGE.md`, `CONTRIBUTING.md`, MIT `LICENSE`, CI (self-tests plus bundle-freshness check) and tag-triggered release workflows, issue templates.

Removed:

- `REFERENCE-v1.1.md` (41 KB of non-authoritative duplicate; use version control for history).

Migration from v1.2 packs: add `P-###` IDs to protected areas, move any not-inspected list into `project-context.md`, add `ai-workflow` markers to the `AGENTS.md` section, and give `index.json` entries the required keys. `format_version` stays `"1.2"`.

## v1.2

Structural rewrite of v1.1 into a modular generator kit: ordered authoritative modules, Compact/Standard/Extended profiles, protected map, overflow finding stubs, claim dependency graph and invalidation triggers, targeted Refresh, hard/soft/verification increment dependencies, and a mechanical validator.
