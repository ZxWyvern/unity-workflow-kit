# Usage guide

## Setup

Extract the kit to `_ai-generator/` in your Unity project, outside `Assets/`, or to a sibling directory. Give the agent the actual path:

```text
Read _ai-generator/ENTRYPOINT.md and set up the workflow for this Unity project.
```

`mode = auto` generates a missing pack or refreshes an existing one. Defaults are `budget = lean`, `profile = compact`, and `architecture_policy = conform`. Existing packs keep their profile and paths. Optional preferences are discovered from the project where possible; there is no mandatory questionnaire.

Python 3.9+ runs the tools with no additional packages. Without Python, use the manual loading and validation instructions in the generated pack. The agent must report unexecuted validation.

For team automation, install the versioned hooks once per clone:

```bash
python _ai-generator/tools/install_hooks.py .
```

This installs `pre-commit`, `post-merge`, and `post-checkout`, enables the `merge=ours` driver, and appends missing `.gitattributes` rules for the generated `index.json` (and the bundle when it lives in the repository). Pass `--pack <dir>` for a non-default pack path; the installed hooks remember it. Existing non-kit hooks are never overwritten unless you pass `--force`. Set `UWK_KIT_ROOT` when the kit is outside the repository.

## Chat-only use

Upload the full bundle from `dist/` and a project export. Exclude `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/`, and `Builds/`. Keep relevant `Assets/` with `.meta` files, `Packages/`, and `ProjectSettings/`. Identify omitted assets and local packages. Ask for the generated files as downloadable artifacts or complete file contents.

The full bundle contains all reference modules and tool source, so it uses more input context than directory mode. Chat without project file access cannot produce a grounded pack.

## Everyday tasks

```text
Read AGENTS.md and docs/ai-workflow/agent.md. Implement: <task>.
Load the relevant route and dependencies. Report checks run and not run.
```

Read all applicable repository instructions. When resuming, read `docs/ai-workflow/sessions/<branch-slug>__<actor-slug>.md`; never create a shared `session-handoff.md`. Then:

```bash
python docs/ai-workflow/tools/context.py .
python docs/ai-workflow/tools/context.py . --route R-001
```

The first command lists routes. The second prints the selected route, its claim dependencies, related detailed findings, checks, and all protected areas. It also loads the active branch's session file in full and other branches as five-line headers. Repeat `--route` when needed. It does not read project source, replace repository instructions, verify freshness, or include every increment/contract. Follow additional references in their canonical files. The session branch comes from `UWK_BRANCH` or Git; the actor comes from `UWK_ACTOR`, `git config user.name`, the OS user, or `agent`. Set `UWK_ACTOR` when several agents share one machine user.

The default ceiling is 16,000 characters, not an exact token budget. If exceeded, the tool prints no partial excerpt and exits 2. Select fewer routes, read the canonical blocks, or use `--max-chars 24000`. A task without a matching route starts with a source trace; add a grounded route afterward.

Without Python, use `index.json` to locate the route, follow its claim IDs and `deps:` transitively, read protected areas and the referenced validation checks. Load relevant contracts separately.

## Source inspection without raw files

Read a C# file as a skeleton instead of the whole body:

```bash
python docs/ai-workflow/tools/context.py . --file Assets/Scripts/Game/Health.cs
python docs/ai-workflow/tools/context.py . --file Assets/Scripts/Game/Health.cs --method TakeDamage
```

The skeleton keeps `using`, namespaces/types, attributes, serialized/public fields, signatures, and XML docs. The second command returns only `TakeDamage` (all overloads named `TakeDamage`). Scene and prefab files are condensed to a GameObject hierarchy:

```bash
python docs/ai-workflow/tools/context.py . --file Assets/Scenes/Dev.unity
```

You still need canonical source or the editor before claiming body, serialization, or runtime behavior. Use `--no-sessions` for a pure source excerpt.

## Budget and large-project scope

| Budget | Subsystems | End-to-end paths | Detailed findings | Routes | Increments |
|---|---:|---:|---:|---:|---:|
| lean | 2 | 1 | 3 | 3 | 1 |
| balanced / deep | 6 | 2 + 1 per explicit focus | 10 | 8 | 5 |

These are ceilings, not quotas. Deep means more verification of selected paths, with wider coverage only when requested. Any budget may expand to follow necessary dependencies; record the reason and remaining limits. Never skip applicable instructions or safety-critical evidence to meet a budget.

For a large repository, specify a focus and root:

```text
Focus: inventory save/load. Unity root: games/client. budget = lean
```

Search filenames first and read a bounded set of candidates. Avoid broad scans of caches, generated files, or vendor dumps; inspect a specific excluded dependency when it matters. Record uninspected areas. Select one task-supported Unity root before writing; ambiguous roots require clarification.

Compact is suitable for a focused scope in a large project. Use Standard when routes/procedures need their own file; Extended adds only relevant contracts. To direct new/touched implementation, use `architecture_policy = toward: <target>`. Otherwise local conventions apply.

## Refresh and evidence

```text
Read _ai-generator/ENTRYPOINT.md and refresh the existing workflow pack.
```

For a known clean Git snapshot:

```bash
python docs/ai-workflow/tools/suspects.py . --since <recorded-revision> --json
```

By default the tool also scans files that mention C# types declared in changed files and adds them as suspects. Pass `--no-references` to skip that scan.

Without Git:

```bash
python docs/ai-workflow/tools/suspects.py . --changed Assets/Scripts/Player.cs
```

Add `--trigger package_or_unity_version_changed` for a known environment change; repeat the flag for other triggers. Git comparison includes tracked changes and untracked, nonignored files. It does not reconstruct a previous dirty working tree, inspect ignored files, or detect external environment changes. Review dirty/incomplete snapshots explicitly and broaden revalidation as needed.

The tool computes suspect claims and dependent checks; it does not reset statuses or rewrite files. Revalidate the active session's next action even when the suspect set is empty. Leave unaffected content unchanged. Routine implementation only updates affected facts, checks, and your own session file; it does not need to reload the generator kit. Regenerate navigation after structural changes:

```bash
python docs/ai-workflow/tools/packlib.py index . --pack docs/ai-workflow
```

Generation permits documentation and helper updates. Runtime tests/builds require user authorization or an established project workflow that permits them with isolated test data. Source, serialized integration, and execution are separate evidence classes.

## Review and CI

Review the diff, preserved `AGENTS.md` instructions, coverage limits, and matrix. Compact has no pack README; its startup instructions are in `agent.md` and current limits in the handoff/context.

```bash
python docs/ai-workflow/tools/validate_pack.py . docs/ai-workflow
python docs/ai-workflow/tools/validate_pack.py . docs/ai-workflow --compile
```

Use the first command in your team's CI. It checks structure, IDs, cited paths/symbols, status consistency, session filenames, Unity `.meta` coverage, duplicate/broken GUIDs, and documented paths; it cannot prove interpretation or gameplay behavior. `--compile` also runs a filtered `dotnet build` through `verify_compile.py`. For a standalone compiler check:

```bash
python docs/ai-workflow/tools/verify_compile.py . --project MyGame.sln
```

It prints only `CS####` diagnostics plus `COMPILE_STATUS`. Missing dotnet/project is `NOT_RUN`, never a pass. No Unity Editor run is implied by pack validation or `dotnet build`.

## MCP server for AI IDEs

The kit can expose its tools natively over the Model Context Protocol. Start from the directory-mode kit:

```bash
python _ai-generator/tools/mcp_server.py --root .
```

Example client configuration (adjust the absolute paths for your host):

```json
{
  "mcpServers": {
    "unity-workflow-kit": {
      "command": "python",
      "args": ["D:/Project/_ai-generator/tools/mcp_server.py", "--root", "D:/Project"]
    }
  }
}
```

Tools: `uwk_get_context`, `uwk_find_suspects`, `uwk_validate`, `uwk_save_handoff`. The transport is newline-delimited JSON-RPC 2.0 over stdio, with no third-party packages. Verify your host's MCP schema and config location before relying on it.

## Upgrades and troubleshooting

For v1.4, copy all six pack tools plus `scripts/hooks/` from the newer kit, read its entrypoint, and refresh. Move the shared handoff to `sessions/<branch-slug>__<actor-slug>.md`, run `packlib.py index`, and install hooks once per clone. Legacy `session-handoff.md` still reads with a warning. Existing index format `1.2` remains compatible. Keep established IDs and file paths. Never delete existing instructions or downgrade a useful Standard/Extended pack just to shrink it.

| Situation | Action |
|---|---|
| No project access | Supply a repository/export; an ungrounded scaffold is not a finished pack |
| Missing path warning | Explain a partial export in the claim's `limit:` or correct the path |
| Context exceeds budget | Split routes, read canonical blocks, or raise `--max-chars` |
| Pack lacks an important subsystem | Supply a focus or request broader coverage |
| Agent ran out of context | Resume from `sessions/<branch-slug>__<actor-slug>.md`, selecting only the next route |
| Two developers/agents conflict in the pack | Use `sessions/<branch-slug>__<actor-slug>.md`; never edit another actor's file; regenerate `index.json` |
| Generated bundle/index conflicts | Merge driver `ours` is configured by `install_hooks.py`; regenerate instead of resolving by hand |
| C# changes but no proof of compilation | Run `verify_compile.py` or `validate_pack.py --compile`; report `NOT_RUN` when dotnet/project is unavailable |
| Binary assets or missing `.meta` | Record serialization/reference limits; do not invent bindings |
| Existing pack cannot validate | Repair the reported mechanical issues before using it as authority |
