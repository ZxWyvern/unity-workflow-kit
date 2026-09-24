# 06 — Operating Loop for the Generated Agent

Encode this loop using project-specific paths and systems.

## 1. Task contract

For non-trivial work record:

```text
Requested outcome:
Current behavior and evidence:
Acceptance, including important failure case:
Existing execution/state path:
Smallest complete change and prerequisites:
Constraints, design authority, architecture_policy:
Protected areas relevant to this task:
Verification plan:
```

Do not require a formal spec file for trivial edits.

## 2. Trace before editing

Read definitions, callers, composition, serialized data, and relevant tests. Identify state ownership, commit point, callbacks after commit, and teardown/lifetime behavior.

Extend the existing system unless evidence demonstrates a real boundary requiring abstraction.

No unsolicited package/framework/migration/mass-formatting work.

## 3. Choose the smallest complete change

A complete change includes necessary callers, registrations, serialized integration, adapters, tests/checks, and failure behavior—not merely a new isolated class.

## 4. Dependency types for roadmap increments

When increments depend on each other, distinguish:

- **hard dependency** — must be complete first;
- **soft dependency** — improves outcome but does not block;
- **verification dependency** — required check/evidence before calling the outcome complete.

Increment format:

```text
### I-001 Outcome
Hard depends on: I-### or none
Soft depends on: I-### or none
Verification depends on: V-###
Exit check: V-###
Status: not_started | in_progress | done
```

Increment status describes roadmap execution, not validation. It is still coupled to the matrix: an increment may be `done` only when every check named in its `Exit check:` and `Verification depends on:` is `passed` in `validation-matrix.md`. The validator enforces this.

## 5. Unity implementation integrity

Future implementation work must account for:

- `.meta` identity on asset moves/renames;
- serialized field/type/namespace/assembly migrations;
- prefab overrides;
- save compatibility/corruption/restore boundaries;
- editor-only vs player assemblies;
- event duplicate/reentrant/late-subscriber behavior;
- async/coroutine/tween/resource cancellation and cleanup;
- ownership of input/camera/audio/light/UI;
- installed API/package version;
- no manual lockfile edits;
- measured performance claims only.

## 6. Integrate in the real consumer path

Verify the intended project and scene/tool before serialized mutations. Prefer supported editor operations over hand-fabricating GUIDs/fileIDs or complex YAML.

If editor integration is unavailable, mark exact pending bindings/imports. Source compilation alone is not a playable/integrated result.

## 7. Verify by risk

Use the project's existing supported runners and build entry points. Before presenting any command as runnable, confirm the syntax, paths, and that a discovered build method actually exists. Do not copy hypothetical commands, guessed editor paths, or unsupported flags.

Choose the smallest meaningful set:

- diff, reference, serialized-identity, and assembly-boundary integrity;
- compilation/import (a textual C# review or an external compiler is not equivalent to Unity compilation);
- affected tests and behavior-focused regression tests for changed logic;
- real input/scene/tool interaction for integration claims;
- lifecycle, failure, restore, network, or platform cases raised by the change;
- target build, device, or profiler only when the claim needs it.

Rules:

- Do not add tests that merely mirror the implementation or assert documentation text.
- Do not run unrelated full-project test or profile sweeps when relevant evidence is sufficient.
- Record pre-existing errors separately from new ones.
- Failed or unavailable checks stay `failed` or `not_run`. Diagnose within scope; never weaken assertions, remove coverage, change acceptance criteria, or hide warnings to obtain green.
- Never use a hand-assembled test container as proof of real scene wiring.

## 8. Finish with evidence

Review final diff; refresh affected claims; update handoff. Report separately:

- source implemented;
- serialized references checked;
- scene/tool behavior verified;
- target player/build verified;
- pending checks and consequences.
