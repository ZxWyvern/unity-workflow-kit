# Usage guide

Human-facing documentation. The AI does not read this folder while generating a pack.

## 1. Pick your path

| Your setup | What to do |
|---|---|
| **A. Agentic tool or IDE assistant that opens your project folder** (best) | Put the kit where the tool can read it (see section 2), then paste the Generate prompt. The tool can inspect files, run the validator, and write the pack directly. |
| **B. Chat AI with file upload** | Zip your project (see section 3), upload it together with `dist/Unity_Workflow_Agent_Generator_bundle.md`, and paste the Generate prompt with the bundle wording. Ask it to output each file in full; you then save them into your project yourself. |
| **C. Chat AI without any file access** | Not enough. The generator refuses to invent project facts and will report that grounding is blocked. |

## 2. Where to put the kit

The kit must be readable by the AI but should not pollute your game.

- **Never inside `Assets/`.** Unity would import every file and create `.meta` files for them.
- Good options:
  - a sibling folder: `../unity-workflow-agent-generator` (tell the AI the path);
  - the project root under `_ai-generator/` (add it to `.gitignore` if you do not want to commit it);
  - a git submodule at the project root if your team wants a pinned version.
- After generation the pack carries its own copy of the three tools, so the kit is only needed again for **Refresh** or to upgrade the generator.

## 3. What to exclude when zipping a project

Exclude generated and machine-specific folders: `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/`, `Builds/`, and large third-party asset dumps you do not want analyzed. Keep `Assets/`, `Packages/`, and `ProjectSettings/` (the AI needs `ProjectSettings/EditorSettings.asset` to tell whether scenes are readable as text).

If assets are serialized as binary or `.meta` files are hidden, the AI will report that serialized inspection is limited and will avoid claiming things it cannot read. Switching to Force Text and Visible Meta Files in Unity gives much better results.

## 4. Prompt library

**Generate (first run)**

```text
Read ENTRYPOINT.md in the generator kit and every module it references. Use Generate mode.
Inspect this Unity project, create the project-specific workflow pack, run the validator,
and report what you verified, what you could not verify, and the next executable increment.
```

**Bundle wording** (paste or attach the single file): replace the first sentence with
`The generator is the attached bundle; read the ENTRYPOINT.md section and every module it references.`

**Steering** (add lines as needed):

```text
Focus: <the outcome you care about>. Development scene: <path>.
Target: <platform, frame budget, memory budget>.
Design references: <paths to GDD/TDD>.
architecture_policy = conform
```
```text
architecture_policy = toward: <your target, e.g. DI framework, layering, singleton rules>
```
With `toward:`, new and touched code follows your target; legacy code is migrated only when a task touches it.

**Small project**

```text
This is a small prototype/tool. Use the Compact profile if it fits.
```

**Work with the pack**

```text
Read AGENTS.md and docs/ai-workflow/agent.md. Then implement: <task>.
Follow the operating loop. At the end, list checks run vs not run.
```

**Allow runtime checks** (off by default)

```text
You may run EditMode tests and open the Dev scene in the editor, using an isolated save slot.
```

**Refresh**

```text
Read ENTRYPOINT.md and use Refresh mode. Use docs/ai-workflow/tools/suspects.py against the
revision recorded in the pack, revalidate only suspect claims plus the handoff target,
and update the pack without rewriting unaffected sections.
```

## 5. What the AI will and will not do

By default it will: read files, write `docs/ai-workflow/*`, copy the tools, add a marked section to `AGENTS.md`, run the validator.

By default it will not: edit gameplay code, scenes, or prefabs; upgrade packages; convert saves; enter Play Mode; run builds; or touch protected areas it lists in the pack. If your `AGENTS.md` already exists, it preserves your rules and adds only its marked section (or a proposed patch if merging is ambiguous).

## 6. Reading the result

1. `git diff`: review `AGENTS.md` (only the section between `<!-- ai-workflow:begin -->` and `<!-- ai-workflow:end -->` should be new) and the new files.
2. `docs/ai-workflow/README.md`: profile, coverage, and what was and was not verified.
3. `project-context.md`, section *Not inspected*: the honest list of what the AI did not look at.
4. `validation-matrix.md`: every check starts as `not_run`. Only a real observed result may make it `passed`.

Vocabulary: `C-###` claim, `F-###` finding, `V-###` check, `R-###` task route, `I-###` increment, `P-###` protected area.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| "Project grounding is blocked" | The AI cannot read your files. Use path A or B. |
| Validator prints errors | Paste the output back: `Fix these validator errors without inventing facts.` |
| Validator warns "path not found" | Fine for a partial export if the claim's `limit:` says so; otherwise the claim is wrong. |
| Pack is thin or misses your systems | Large projects are capped on purpose. Rerun with `Focus:` naming the systems, or ask to raise a specific cap. |
| AI ran out of context mid-run | Start a new session with the Refresh prompt; it resumes from `session-handoff.md`. |
| No Python available | The validator is skipped. The AI does the same checks by reading and must say the script was not executed. |
| Files appeared under `Assets/` | Move them out and delete their `.meta` files. The pack belongs in `docs/ai-workflow/`. |

## 8. Teams and CI

Commit `docs/ai-workflow/` and the `AGENTS.md` section. Run Refresh after large merges. To keep the pack from rotting, add a step to your own CI:

```yaml
- name: Validate AI workflow pack
  run: python docs/ai-workflow/tools/validate_pack.py . docs/ai-workflow
```

This checks mechanics only (IDs, formats, cited paths and symbols, status consistency).

## 9. Upgrading the generator

Replace the kit with the new release, read its `CHANGELOG.md` for migration notes, then run Refresh. Copy the newer `tools/` into `docs/ai-workflow/tools/`.
