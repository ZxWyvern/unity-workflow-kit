# 08 — Validation and Completion

## Pack validation

Before delivery, validate the generated workflow pack itself. This is separate from testing the game.

If shell access exists, run:

```bash
python <pack_dir>/tools/validate_pack.py <repo_root> <pack_dir>
```

Copy `tools/packlib.py`, `tools/validate_pack.py`, and `tools/suspects.py` into `<pack_dir>/tools/` first (the validator imports `packlib.py`). Fix every validator error. Warnings require review and either correction or an explicit reason in the README. If no shell is available, perform the same checks by reading and say the validator was not executed.

The validator checks mechanics: IDs, formats, status vocabulary, increment-to-matrix coupling, cited paths and symbols, size limits, placeholder leftovers. It cannot prove that claims are true.

## Manual validation

Confirm:

- every claimed project path/symbol/package/scene/test/tool traces to inspected evidence;
- unknown/proposed items are labeled;
- source, serialized wiring, and execution evidence are not conflated;
- explicit user decisions are not contradicted;
- findings distinguish defect/risk/conflict/missing integration/verification gap/improvement;
- no other project's paths/names/mechanics/tool settings leaked in;
- no credentials/secrets/filler/invented API signatures/guarantees;
- protected areas are defined once with `P-###` IDs and referenced, not restated;
- the not-inspected list has exactly one home (`project-context.md`);
- claim dependencies and invalidation triggers are syntactically coherent;
- selected pack profile is justified by project complexity, not by prestige.

## Edge-case reasoning

Reason explicitly about applicable cases:

- partial export;
- no editor connection;
- dirty repository;
- several roots/scenes;
- stale docs;
- missing design authority;
- existing nested instructions;
- package/editor-tool/non-game Unity project;
- missing `.meta` or non-text serialization;
- Git LFS/submodule gaps.

Reasoning is not an executed test.

## Completion response

The final response must state:

1. where the generated pack is and how to load it;
2. the most important grounding sources/paths;
3. pack validation performed;
4. game/editor/build checks performed, separately;
5. unresolved limits/blockers;
6. one concise starting/resume request using real generated paths.

Never promise zero bugs, flawless code, exhaustive inspection, or a quality score.
