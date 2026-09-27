# 02 — Inputs, Budget, and Pack Profiles

## Inputs

Read from the user request when supplied; otherwise discover:

- mode: `auto` (default: refresh an existing pack, otherwise generate), `generate`, or `refresh`;
- budget: `lean` (default), `balanced`, or `deep`;
- repository/project location;
- focus/outcome;
- development/bootstrap scene;
- target platform(s), hardware, frame/memory/loading budgets;
- design references;
- host/tool preference;
- output location/conventions;
- `architecture_policy`.

Never infer genre, render pipeline, DI framework, networking model, production stage, or project conventions from another project.

## Project depth tier

After workspace discovery classify the inspected scope:

Record the tier and the observed counts behind it (scripts, scenes, asmdefs, Unity roots). Counts are approximate guides, not thresholds to game:

- **small** — one Unity root, roughly up to 150 C# scripts and 10 scenes, or a focused tool/package;
- **medium** — one root, roughly 150 to 1500 scripts, multiple systems;
- **large** — more than roughly 1500 scripts, several Unity roots, a monorepo, extensive local packages, or many independent systems.

For large projects, deep-inspect only the requested focus, startup path, and direct dependencies. Record the rest as not inspected.

## Investigation caps

Select a budget independently of repository size and output profile. Defaults are ceilings, not quotas; expand only for necessary dependencies or an explicit request. Record the reason and remaining coverage. `deep` still uses the balanced caps unless the user requests wider coverage; it spends effort verifying selected paths rather than collecting more prose.

| Budget | Subsystems | End-to-end paths | Detailed findings | Routes | Increments |
|---|---:|---:|---:|---:|---:|
| lean (default) | 2 | 1 | 3 | 3 | 1 |
| balanced / deep | 6 | 2 + 1 per focus | 10 | 8 | 5 |

Overall limits, independent of lean targets:

| Item | Default cap |
|---|---:|
| deeply mapped subsystems | 6 |
| representative end-to-end paths | 2 + 1 per explicit focus |
| detailed findings | 10 |
| overflow finding stubs | 20 |
| task routes | 8 |
| roadmap increments | 5 |
| root `AGENTS.md` generated section (between markers) | 150 lines |
| portable `agent.md` | 200 lines |

### Overflow findings

When more than 10 substantiated findings exist, do not silently drop them. Keep the top 10 in full format and record up to 20 additional stubs containing only:

`ID | class | impact | evidence IDs | reason deferred`

Do not prescribe fixes for overflow stubs unless promoted into detailed findings.

## Pack profiles

Choose the smallest profile that preserves safe navigation and verification. Every profile ends with the same evidence rules; only document count changes.

All profiles copy `tools/packlib.py`, `tools/validate_pack.py`, `tools/suspects.py`, and `tools/context.py` into `<pack_dir>/tools/`. Copy files directly without printing source into model context.

### Compact (default)

Use for a prototype, package, editor tool, focused vertical slice, or focused scope inside a large repository. Repository size alone does not promote the profile.

Required generated files:

- root `AGENTS.md` integration (between the `ai-workflow` markers) or proposed patch;
- `agent.md` (short): role, operating loop, task routes, and increments. Compact keeps **procedure** here so `project-context.md` stays facts only;
- `project-context.md`;
- `validation-matrix.md`;
- `session-handoff.md`;
- `index.json`.

### Standard

Compact plus `README.md` and `development-workflow.md`. Use when procedures no longer fit a short agent file or several task routes need separate navigation. Routes and increments live in `development-workflow.md`; `agent.md` keeps the role and loop and points to it.

### Extended

Standard plus only the relevant specialized files, for example:

- `contracts/narrative.md`;
- `contracts/networking.md`;
- `contracts/performance.md`;
- `contracts/editor-tooling.md`.

Do not select Extended merely because the repository is large.

## Write order

Write incrementally:

- **W1 after workspace/stack/entry:** startup rules skeleton, context/provenance, handoff stub.
- **W2 after architecture/intent:** subsystem and representative-path context.
- **W3 after findings:** routes/increments/checks.
- **W4:** agent profile, README if profile requires it, index, validation, final handoff.

## Stop rule

If roughly 70% of available context/time is consumed before W3, stop investigating. Finish W3–W4 using known evidence and mark remaining areas `unknown`/`not inspected`.
