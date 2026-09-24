# 03 — Investigation Passes

Prefer targeted search (`rg` or host equivalent) to directory dumps. Batch independent reads; sequence dependent decisions and writes.

## Pass A — Workspace, instructions, and preserved work

- Read root and relevant nested instruction files fully before working in their scope.
- Inspect existing workflow documents before replacing their role.
- Establish the actual Unity root(s); distinguish full checkout, partial export, package repository, sample, or monorepo.
- Observe Git revision/dirty state only when available; never invent a commit.
- Inspect archives before extraction and reject traversal paths.
- Detect missing submodules, Git LFS pointer files, omitted packages/assets, and export-to-checkout mapping limits.
- Never create guessed parallel `Assets` trees to make paths appear valid.
- Record unrelated dirty work and protected areas.

## Pass B — Stack and execution environment

Inspect what exists:

- `ProjectSettings/ProjectVersion.txt`;
- `Packages/manifest.json`, lockfile, embedded packages;
- asmdefs/references and scripting defines;
- render-pipeline configuration;
- input system;
- UI technology;
- 2D/3D physics usage;
- Addressables/resources/custom asset loading;
- persistence/save storage;
- networking/ECS when present;
- CI/build tooling;
- test assemblies;
- editor tooling.

Distinguish declared, locked/resolved, and observed-running versions.

### Unity validity checks

Run these before relying on serialized or runtime claims. Each check states what to record and what to do when it fails.

1. **Serialization mode and meta files.** Read `ProjectSettings/EditorSettings.asset` (typically `m_SerializationMode`, where 2 is Force Text, and `m_ExternalVersionControlSupport` for Visible Meta Files; confirm the key names in the file). If assets are Mixed or Binary, or `.meta` files are hidden or uncommitted, serialized inspection is unreliable or impossible for the affected assets. Record that limit **before** any `serialized_verified` claim, and make no such claim for those assets.
2. **API drift.** Check the exact installed Unity and package versions against installed package source or the official documentation for that version. Do not rely on memory. Unity 6 examples to verify, not assume: `Object.FindObjectOfType` replaced by `FindFirstObjectByType`/`FindAnyObjectByType`; `Rigidbody.velocity` replaced by `linearVelocity`.
3. **Project lock.** Before proposing or running any batch-mode test or build, check whether an editor has the project open (for example `Temp/UnityLockfile` or a running Unity process). If it is open, use the editor connection or report the check as blocked; do not force it.
4. **Domain reload.** Read Enter Play Mode Options (`EditorSettings.asset`, typically `m_EnterPlayModeOptionsEnabled` and its flags). With domain reload disabled, static state persists between Play sessions, which changes what "fresh start" means and which tests are trustworthy.
5. **Build identity.** Any build claim names target platform, development vs release, scripting backend (Mono or IL2CPP), managed stripping level, and `link.xml` if present.
6. **Test mode.** Every test claim names EditMode or PlayMode. One does not substitute for the other.

Configured tools/connections do not prove availability. Record what was actually exercised.

## Pass C — Entry points and serialized wiring

- Locate candidate scenes, build profiles/lists, bootstrap/runtime initialize hooks, scene loading, tests, and editor entry points.
- Respect a user-selected development scene.
- Distinguish development scene, bootstrap scene, first built scene, and additive scene sets.
- If ambiguous, record evidence-backed candidates; use a provisional choice only when justified.
- Trace startup into GameObjects/components, prefab variants/overrides, config assets, DI/registration mechanisms, ScriptableObjects, and services.
- Resolve GUIDs through `.meta` files when possible.
- Distinguish missing references from unresolved references in incomplete exports.
- Keep source defaults, serialized authored values, test fixtures, runtime overrides, and save-restored values separate.
- Report binary/unsupported assets as limits rather than fabricating hierarchy or bindings.

A class existing in source does not prove registration, enablement, instantiation, or use.

## Pass D — Implemented architecture

For each selected subsystem record:

- files/symbols;
- responsibility;
- state owner;
- callers;
- dependencies;
- composition/registration path;
- lifetime/teardown;
- tests/checks.

Trace representative paths end-to-end:

`entry/input -> request -> validation -> authoritative state change -> notification/result -> presentation/effect -> completion/cancellation/persistence/teardown`

Inspect initialization order, subscribers, async ownership, cleanup, failure paths, and scene registration. Follow definitions and usages.

Adapt to evidence. Do not force Clean Architecture onto a prototype or MonoBehaviour pattern onto an ECS/package/tool project.

## Pass E — Intended experience and constraints

Read relevant GDD/TDD/README/acceptance notes. Identify:

- primary user/player;
- primary loop or tool workflow;
- current project stage;
- stated constraints and budgets;
- explicitly approved decisions.

Translate vague qualities into observable outcomes without pretending subjective goals are automatically testable. Keep recommendations separate from approved intent.

## Pass F — Findings and next increment

Record only substantiated findings. Classes:

- observed defect;
- source-supported risk;
- design conflict;
- missing integration/content;
- verification gap;
- optional improvement.

Missing test execution is not automatically a gameplay defect. Unresolved export references are not automatically broken references. Check the caller and state path that would make a defect relevant before prescribing a fix.

For an explicit task, prioritize that task and real prerequisites. For broad continuation, choose one high-value increment with a complete observable outcome.

Finish by recording coverage in `project-context.md` (its single home for the not-inspected list): read, sampled, omitted, not inspected. Say "relevant-path review" when that is what was done; never claim an exhaustive audit.
