# Unity Workflow Agent Generator v1.4.0

Create a project-specific workflow pack from inspected Unity project files. Deliver the pack, validate it, and report the next executable action. Generation changes documentation and copied workflow tools only. Implementation is a separate request.

## Start without a questionnaire

Read applicable repository instructions and preserve dirty work. Locate the Unity root (or package consumer). Use the user's focus and selected scene when supplied. Otherwise inspect startup and choose one evidence-supported next action; do not invent product intent.

Defaults: `mode = auto`, `budget = lean`, `profile = compact`, `architecture_policy = conform`, output `docs/ai-workflow/`. Auto refreshes an existing pack and generates when none exists. Keep an existing pack's profile and paths during refresh. Ask only when a missing choice blocks safe, grounded work.

Read `core/01-authority-and-scope.md`, `core/04-evidence-claims-and-invalidation.md`, and `templates/generated-pack-contract.md`. Load other guidance only when the situation below applies. Do not read this kit's `tests/`, `dist/`, or `docs/` during generation. Copy tools as files; do not load their source into model context just to copy or execute them.

## Read only what the task needs

| Situation | Additional reading |
|---|---|
| Profile/budget overrides or unclear project size | `core/02-inputs-budget-and-profiles.md` |
| Investigating source/architecture | Relevant passes in `core/03-investigation-passes.md` |
| Before serialized or runtime claims | Passes B and C in `core/03-investigation-passes.md` |
| Existing instructions or conflicting document ownership | `core/05-output-architecture.md` |
| Resuming work, parallel developers/agents, or handoff format | Session rules below and `core/06-operating-loop.md` |
| Writing the generated agent's implementation procedure | `core/06-operating-loop.md` |
| Refreshing an existing pack | `core/07-refresh-policy.md` |
| Validation warnings, incomplete exports, or completion uncertainty | `core/08-validation-and-completion.md` |
| Relevant networking, narrative, editor tooling, or performance systems | Matching section of `core/09-conditional-contracts.md` |
| Requested/detected host integration | Matching `hosts/` file; verify behavior before generating native config |
| Large C#/scene inspection or MCP host | `tools/context.py --file`; MCP notes in `hosts/AGENTS-aware.md` |

## Lean investigation

1. Search filenames before contents. Exclude `Library`, `Temp`, `Obj`, `Logs`, `Builds`, `.git`, generated code, and vendor dumps from broad scans. Inspect an excluded dependency directly only when the task requires it.
2. Start with metadata, entry candidates, and the focus path. Initially read at most 12 source/config/asset candidates, then expand only for callers, state ownership, integration, or verification needed by the selected task. Repository instructions are never subject to this budget. Record missing coverage instead of pretending inspection is complete.
3. Map up to 2 subsystems, 1 end-to-end path, 3 detailed findings, 3 routes, and 1 next increment. These are ceilings, not quotas. Record other findings as brief stubs. Expand with a stated reason when necessary for correctness; `budget = balanced` or `deep` is an optional user override.
4. On a large project, inspect the focus and its dependencies. A large repository does not require a large pack. For multiple roots, select the root supported by the task; if ambiguous, list candidates and ask before writing a pack.
5. Write evidence once and cite IDs. Keep the generated root instruction section near 20 lines and `agent.md` near 80 lines; hard limits remain 150 and 200. Do not fill optional sections with generic advice.

## Generate, check, deliver

Use the contract's formats and canonical files. Never conflate source existence, serialized wiring, and runtime execution. Unknowns remain unknown. Follow existing architecture unless the user explicitly supplies `toward: <target>`.

Copy `packlib.py`, `validate_pack.py`, `suspects.py`, `context.py`, `verify_compile.py`, and `mcp_server.py` from `tools/` into `<pack_dir>/tools/`. Run `python <pack_dir>/tools/validate_pack.py <repo_root> <pack_dir>` when a shell and Python exist. Resolve errors and explain remaining warnings. If unavailable, say validation was not executed and check the contract manually.

Teach future sessions to read applicable instructions and `agent.md`, list routes with `context.py`, then load only the selected route and dependency closure. Session state is sharded: `sessions/<branch-slug>__<actor-slug>.md` per branch and actor; never write a shared `session-handoff.md`. Load the active branch in full and other branches as bounded headers. `context.py --file` prints a C# skeleton or a condensed `.unity`/`.prefab` hierarchy unless `--method` asks for a full body. Check freshness; the excerpt is navigation, not proof. Never truncate required evidence or safety instructions to meet a token budget.

Finish with pack location, grounding sources, pack validation, game checks run/not run, remaining limits, and one copyable next request. No gameplay changes are implied by generating a pack.

Run `python <pack_dir>/tools/verify_compile.py <repo_root>` for a filtered C# check when a solution/project exists; report dotnet failure or unavailability separately from Unity execution. `index.json` and `dist/` are generated artifacts: regenerate `index.json` with `packlib.py index` and never hand-edit it. Optional project automation lives in the kit's `tools/install_hooks.py` and `tools/mcp_server.py`.

In a pasted full bundle, references mean sections marked `BEGIN file: ...`. Use the full bundle only for first-time initialization or a chat-only host that cannot read repository files; for ongoing work, load the selected core/template/host files only. Directory mode avoids loading tool source entirely.
