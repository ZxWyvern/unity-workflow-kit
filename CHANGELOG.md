# Changelog

## v1.4.0

Multi-user, multi-agent, and token-diet release:

- Sharded session state at `sessions/<branch-slug>__<actor-slug>.md`. The active branch loads in full; other branches appear as five-line headers. Legacy `session-handoff.md` still validates with a deprecation warning.
- `index.json` is regenerated deterministically by `tools/packlib.py` from the pack scan; sessions are one directory entry so branch work does not churn navigation.
- `.gitattributes` marks generated `index.json` and the dist bundle as `merge=ours`; `install_hooks.py` configures the driver, appends missing rules for consumer repositories, and records a custom pack path for the hooks.
- Versioned Git hooks (`pre-commit`, `post-merge`, `post-checkout`) rebuild the bundle/index and block commits on pack validation failure.
- `context.py --file` emits a C# skeleton (types, attributes, serialized/public fields, signatures, XML docs) and `--method` returns only the requested implementation. `.unity`/`.prefab` files condense to a GameObject/Transform/MonoBehaviour hierarchy with script names and authored values.
- `suspects.py` adds changed C# type definitions to a reference scan, so likely call sites become suspects without a repository-wide search.
- `validate_pack.py` checks Unity `.meta` coverage, duplicate/invalid GUIDs, orphan metas, broken script GUIDs, documented project paths, and sharded session filenames.
- `verify_compile.py` runs a filtered `dotnet build --no-restore -v q`; success is one `COMPILE_STATUS: OK (0 errors)` line. `validate_pack.py --compile` integrates it.
- `mcp_server.py` exposes `uwk_get_context`, `uwk_find_suspects`, `uwk_validate`, and `uwk_save_handoff` over newline-delimited MCP stdio with no third-party packages.
- Tests cover skeleton/YAML condensation, multi-session isolation, index determinism, hooks, `.meta`/GUID checks, filtered compiler output, and MCP dispatch.

Migration: copy all six pack tools plus `scripts/hooks/`, replace the shared handoff with at least one `sessions/<branch-slug>__<actor-slug>.md`, run `packlib.py index` once, install hooks, and resolve new validator errors (missing `.meta`, duplicate GUIDs, missing documented paths). Keep index `format_version` at `1.2`. Existing pack profiles and IDs remain compatible. Token and compile claims still need measurement on named projects and hosts.

## v1.3.0

Focused setup and task context:

- One setup prompt; auto mode generates or refreshes while preserving existing pack paths/profile.
- Lean investigation and Compact output by default, including focused scopes in large repositories.
- Conditional module loading, filenames before contents, short startup instructions, and no tool-source reads just to copy tools.
- `context.py` lists routes or emits a selected route with claim dependencies, relevant detailed findings/checks, and protected areas. A character ceiling fails explicitly instead of truncating evidence.
- No-change refresh leaves the pack untouched; dirty snapshots and external environment changes require explicit review.
- English and Indonesian onboarding rewritten around the shorter workflow.

Correctness:

- Reject non-object indexes, invalid container/reference types, and misplaced check definitions.
- Execution claims require passed checks in the canonical matrix. Checks require an environment, runner, and expected result.
- Git refresh includes untracked nonignored files, preserves quoted/non-ASCII paths, and invalidates both sides of a rename.
- Changed-path ancestor indexing avoids scanning every changed filename for every claim.
- Added regression/context tests, including 800 unrelated claims with unchanged selected output. CI now includes Windows and Linux; releases check bundle freshness before packaging.

Migration: keep index `format_version` at `1.2`. Copy the four tools (including `context.py`) into the existing pack, refresh its loading instructions, and resolve stricter validator errors. Do not renumber IDs or convert an existing Standard/Extended pack without a reason. Actual token cost and real-project generation quality remain unbenchmarked.

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
