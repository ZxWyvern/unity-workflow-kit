# 04 — Evidence, Claims, Dependencies, and Invalidation

## Evidence labels

| Label | Meaning |
|---|---|
| `source_verified` | confirmed in inspected source/config text |
| `serialized_verified` | confirmed in inspected scene/prefab/asset data |
| `execution_verified` | observed in a named test/editor/player/profiler run |
| `inferred` | reasoned from evidence but not directly established |
| `proposed` | recommendation/new design/new symbol/tuning value |
| `unknown` | not established with available access |

These labels are categories, not a quality ladder.

## Claim format

One line per important claim:

```text
- [C-012 | source_verified | Assets/Foo/Bar.cs#Baz | snapshot] Observation. | deps: C-003,C-008 | invalidates: source_changed,serialized_dependency_changed | limit: not checked in scene
```

Rules:

- IDs are unique three-digit `C-###`.
- repository-relative paths; prefer symbols/asset identifiers to drifting line numbers;
- snapshot revision/dirty state is canonical in `project-context.md`;
- `execution_verified` must reference at least one `V-###` check;
- do not create claims for trivial prose;
- `deps:` may be `none`;
- `invalidates:` is **required** for `source_verified`, `serialized_verified`, `execution_verified`, and `inferred` claims, and optional for `proposed` and `unknown` claims;
- an `invalidates:` token must be one of the defined triggers below or use the `project:` prefix (define it in `project-context.md`);
- `deps:` must not reference the claim itself and must not form a cycle;
- the validator checks that a `source_verified` claim's path exists and its symbol appears in the file. A path missing because of a partial export must say so in `limit:`.

## Invalidation triggers

Use the smallest applicable set:

- `source_changed`
- `serialized_dependency_changed`
- `package_or_unity_version_changed`
- `entry_path_changed`
- `design_authority_changed`
- `build_configuration_changed`
- `test_environment_changed`
- `runtime_dependency_changed`
- `save_schema_changed`
- `toolchain_changed`
- `manual_review_required`

Project-specific triggers use the `project:` prefix and are defined once in `project-context.md`.

## Dependency rule

A claim becomes **suspect** when:

- its own source path changed;
- any claim listed in `deps:` became invalidated;
- one of its named invalidation triggers occurred;
- the snapshot completeness changed materially.

In Refresh mode, suspect claims must be revalidated before being used as authority. Do not automatically delete them; update, downgrade, or replace based on evidence.

## Feature-state split

For any important feature, keep these separate:

1. **source state** — relevant code/config exists;
2. **wiring state** — real scene/prefab/config/registration connects it;
3. **execution state** — behavior observed in a named environment.

Never compress all three into “implemented” unless all required evidence exists and the workflow defines what “implemented” means for that feature.

## Finding format

```text
### F-001 Short title
Class: <class> | Confidence: high|medium|low | Basis: runtime|static|uncertain
Evidence: C-###, C-###
Impact and trigger conditions:
Smallest follow-up and acceptance: V-### (and I-### if applicable)
```

Do not use severity as a substitute for evidence.

Overflow findings (beyond the top 10) use one line each: `F-011 | class | impact | C-###[, C-###] | reason deferred`. A closed finding is one line: `[F-005 | closed | V-003] short title`. Both keep their IDs defined.

## Protected-area format

Protected areas have IDs so other files can reference them instead of restating them:

```text
- [P-001] <repo-relative path or glob> | reason: <why it is protected>
```

Define them once in `project-context.md`. Routes and `agent.md` cite `P-###` IDs.
