# Generated Pack Contract

Defines the project-specific pack produced by the generator. `tools/validate_pack.py` enforces the mechanical parts.

## Files by profile

| File | Compact | Standard | Extended |
|---|---|---|---|
| root `AGENTS.md` section (between markers) | yes | yes | yes |
| `agent.md` | yes (also holds routes and increments) | yes | yes |
| `project-context.md` | yes | yes | yes |
| `validation-matrix.md` | yes | yes | yes |
| `session-handoff.md` | yes | yes | yes |
| `index.json` | yes | yes | yes |
| `README.md` | no | yes | yes |
| `development-workflow.md` | no | yes | yes |
| `contracts/*.md` | no | no | only relevant ones |
| `tools/packlib.py`, `validate_pack.py`, `suspects.py` | copied | copied | copied |

## Root `AGENTS.md`

Startup rules, scope, authority, invariants, routing, tool limits, validation honesty, completion requirements. Preserve existing instructions and nested scopes. Put the generated section between these markers (section at most 150 lines):

```text
<!-- ai-workflow:begin -->
...
<!-- ai-workflow:end -->
```

Point to supporting docs instead of duplicating them. If integration is unsafe or ambiguous, emit a proposed patch and mark activation pending.

## `README.md` (Standard, Extended)

What was generated; inspected snapshot and coverage limits; profile and why; file-to-purpose map; activation and merge instructions; copyable start and resume requests using real paths; host loading behavior when verified; `index.json` is navigation-only; validator result (executed or not) separate from game checks.

## `agent.md` (all profiles, at most 200 lines)

Real startup path, relevant systems, sources of truth, architecture policy, protected areas by `P-###`, operating loop, evidence and validation behavior. In Compact it also holds routes and increments.

## `project-context.md`

Facts only. Canonical sections, in this order:

1. provenance and coverage
2. pack profile and tier (with observed counts)
3. protected areas: `- [P-001] path or glob | reason: ...`
4. intended experience and design conflicts
5. stack and version evidence (cite claims)
6. entry and startup path
7. subsystem map
8. representative paths
9. scene, prefab, and config bindings and authored values
10. feature state split: source / wiring / execution
11. claims (all `C-###` lines live here)
12. detailed findings (at most 10), plus `12b` closed findings
13. overflow finding stubs (at most 20)
14. available tools and tests, and what they establish
15. **not inspected** (single home for this list)

Claim line: `- [C-012 | label | path#symbol | snapshot] Observation. | deps: C-003 | invalidates: source_changed | limit: ...`

Finding block:

```text
### F-001 Short title
Class: <verification gap | observed defect | source-supported risk | design conflict | missing integration/content | optional improvement> | Confidence: high|medium|low | Basis: runtime|static|uncertain
Evidence: C-###, C-###
Impact and trigger conditions:
Smallest follow-up and acceptance: V-### (and I-### if applicable)
```

Overflow stub: `F-011 | class | impact | C-### | reason deferred`. Closed finding: `- [F-005 | closed | V-003] short title`.

## `development-workflow.md` (Standard, Extended; in Compact these live in `agent.md`)

```text
### R-001 Route name
Start: real files/symbols (C-###)
State owner and scene/assets:
Invariants:
Protected areas: P-###
Required integration step:
Checks: V-###, V-###
```

Up to 8 routes, the project-specific operating loop, and up to 5 increments:

```text
### I-001 Outcome
Hard depends on: I-### or none
Soft depends on: I-### or none
Verification depends on: V-###
Exit check: V-###
Status: not_started | in_progress | done
```

`done` requires every named check to be `passed` in the matrix.

## `validation-matrix.md`

```text
### V-001 Short title
Covers: R-###, F-###
Mode: static | EditMode | PlayMode | editor-interactive | player-build | profiler
Preconditions and environment:
Runner or exact manual input path:
Expected observable result:
Status: not_run
Observed result and evidence location:
Remaining limit or next action:
```

`Status` is exactly one of `passed`, `failed`, `not_run`, `not_applicable`. `passed` or `failed` requires a real observed result and evidence location. Do not invent test names or treat test attributes as execution.

## `session-handoff.md`

Current state only. It must contain the phrase "see validation matrix" and must not restate outcomes.

```text
Date and source snapshot:
User goal and authorized scope:
Project root / selected entry path:
Pack profile:
Files created or updated:
Coverage: see project-context.md, "Not inspected"
Key facts (claim IDs):
Decisions made, proposed, unresolved:
Checks run this session (IDs only; see validation matrix):
Checks not run and why:
Blockers, missing access, pending integration:
Next executable increment and acceptance:
Resume instructions and isolated test data:
```

State explicitly when no game implementation changed.

## `index.json`

Navigation only. Valid JSON; no comments, trailing commas, or fake schema URL. All paths are repository-relative. Every object with `path` also has `path_state`: `existing`, `generated`, or `proposed` (a proposed path must not exist yet). No status, result, or pass/fail keys anywhere.

Top-level fields: `format`, `format_version` (`"1.2"`), `workflow_version`, `profile`, `project`, `snapshot`, `documents`, `entry_points`, `stack`, `task_routes`, `refresh_triggers`.

Entry shapes:

| Field | Required keys |
|---|---|
| `project` | `root`, `product_type`, `tier` (`small`/`medium`/`large`) |
| `snapshot` | `observed_date`, `source_kind`, `revision`, `dirty`, `completeness_limits` |
| `documents[]` | `id`, `path`, `path_state`, `purpose` |
| `entry_points[]` | `id`, `path`, `path_state`, `kind`, `certainty` (`confirmed`/`provisional`/`ambiguous`), `claim_ids` |
| `stack[]` | `name`, `version` (null needs a `note`), `claim_ids` |
| `task_routes[]` | `id` (an `R-###`), `title`, `document`, `check_ids` (`V-###`) |
| `refresh_triggers[]` | strings from the invalidation trigger list |

See `templates/index.example.json`. Its placeholder entries contain `REPLACE_ME`, which the validator rejects until every one is replaced.
