# Unity Workflow Agent Generator

**Let your AI coding agent write a project-specific, evidence-based workflow for *your* Unity project, from your real files.**

Instead of a generic "be a senior Unity developer" prompt, this kit makes an AI inspect your actual project (scenes, prefabs, packages, source, tests) and produce a small **workflow pack** in `docs/ai-workflow/`. Future AI sessions read that pack and know your real entry scene, your subsystems, what is protected, what has been verified, and what has not.

🇮🇩 [Baca dalam Bahasa Indonesia](README.id.md)

> Not affiliated with or endorsed by Unity Technologies. "Unity" is a trademark of its owner.

**Status: v1.2.1, beta.** The tools are covered by self-tests, but the generator has not yet been validated on many real projects. Feedback from real runs is the most useful contribution (see the *Run report* issue template).

## Why use it

- **Grounded, not generic.** Every important claim carries an evidence label (`source_verified`, `serialized_verified`, `execution_verified`, `inferred`, `proposed`, `unknown`) and a path to the code or asset it came from.
- **Honest about verification.** "It compiles", "the scene is wired", and "I played it and it works" are separate claims. The pack never merges them.
- **Safe by default.** Generation writes documentation only. It does not change gameplay, upgrade packages, or touch your saves.
- **Stays fresh.** A Refresh mode recomputes which claims went stale after your code changed, instead of rewriting everything.
- **Checked by a script.** A validator catches broken IDs, fake paths, missing evidence, and status contradictions.

## What you get

```
AGENTS.md                      <- a short section is added (between markers)
docs/ai-workflow/
  agent.md                     role + operating loop for future AI sessions
  project-context.md           facts: stack, entry path, subsystems, findings, protected areas
  development-workflow.md      task routes + next increments
  validation-matrix.md         checks and their status (the only place status lives)
  session-handoff.md           where things stand right now
  index.json                   navigation index
  README.md                    how to use the pack
  tools/                       validate_pack.py, suspects.py, packlib.py
```

Small projects get the **Compact** profile (fewer files); the AI picks the smallest profile that fits.

## Quick start (about 5 minutes)

**You need:** an AI that can read your Unity project folder (an agentic coding tool or IDE assistant), or the ability to upload your project as a zip.

**1. Get the kit.** Pick one:

- Easiest: download the latest **bundle** from [Releases](../../releases) (or open [`dist/Unity_Workflow_Agent_Generator_bundle.md`](dist/Unity_Workflow_Agent_Generator_bundle.md) and click *Copy raw file*). It is one file containing everything.
- Or download the repository ZIP (*Code → Download ZIP*) and unzip it **next to** your project, not inside `Assets/` (Unity would import it).

**2. Give the AI your project.**

- Agentic tool in your project folder: open the folder, and make the kit readable (place it outside `Assets/`, e.g. `../unity-workflow-agent-generator`, or in the project root under `_ai-generator/`).
- Chat-only AI: zip your project **without** `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/`, and `Builds/`, then upload the zip and the bundle.

**3. Paste this prompt:**

```text
Read ENTRYPOINT.md in the generator kit and every module it references. Use Generate mode.
Inspect this Unity project, create the project-specific workflow pack, run the validator,
and report what you verified, what you could not verify, and the next executable increment.
```

(Bundle mode: attach or paste the bundle file and say "The generator is the attached bundle" instead of naming `ENTRYPOINT.md`.)

**4. Review the result.** Check the diff, especially the section added to `AGENTS.md`, then commit `docs/ai-workflow/`.

## Optional prompt add-ons

Add any of these lines to the prompt above.

```text
Focus: finish the playable demo. Development scene: Assets/Scenes/Dev.unity.
```
```text
Target: Android mid-range, 60 FPS, 2 GB memory budget.
```
```text
architecture_policy = toward: Clean Architecture with VContainer, no singletons, asmdef layers Domain/Application/Infrastructure/Presentation.
```

Without `architecture_policy`, the pack **conforms** to whatever conventions your project already uses and will not propose rewrites.

## Using the pack day to day

Start each task with:

```text
Read AGENTS.md and docs/ai-workflow/agent.md. Then implement: <your task>.
Follow the operating loop. At the end, list checks run vs not run.
```

The agent traces the existing code path first, makes the smallest complete change, integrates it in the real scene, verifies by risk, and reports honestly. It never marks a check `passed` without evidence.

## Keeping the pack fresh

After significant changes:

```text
Read ENTRYPOINT.md and use Refresh mode. Use docs/ai-workflow/tools/suspects.py against the
revision recorded in the pack, revalidate only suspect claims plus the handoff target,
and update the pack without rewriting unaffected sections.
```

You can also run the tools yourself (Python 3.9+, no dependencies):

```bash
python docs/ai-workflow/tools/validate_pack.py . docs/ai-workflow
python docs/ai-workflow/tools/suspects.py . --pack docs/ai-workflow --since HEAD~5
```

## FAQ

**Does it change my game?** No. By default it only writes documentation and copies the three small tools into `docs/ai-workflow/tools/`. Implementation is a separate, explicit request.

**Which AI does it work with?** It is tool-agnostic: any AI that can read your project files. It has not been benchmarked across tools yet; please [open an issue](../../issues) with your results.

**Is the pack guaranteed correct?** No. The validator checks mechanics (IDs, formats, that cited paths and symbols exist). It cannot prove an interpretation is right. Unverified things are labeled `unknown`, not guessed.

**Large projects?** The AI caps its depth (6 subsystems, 10 findings, 8 routes, 5 increments by default) and lists everything else as *not inspected*. Ask for a `Focus:` to steer it.

**Editor tools, packages, non-game projects?** Yes. The Compact profile and the editor-tooling contract cover them.

**Language?** The kit and pack are English because the validator relies on English field names. You can talk to your AI in any language.

More detail: [docs/USAGE.md](docs/USAGE.md).

## Repository layout

| Path | Purpose |
|---|---|
| `ENTRYPOINT.md`, `core/` | The generator rules (authoritative) |
| `templates/` | Output contract and index example |
| `hosts/` | Notes on where each AI tool loads instructions (verify before use) |
| `tools/` | `validate_pack.py`, `suspects.py`, `packlib.py`, `bundle.py` |
| `dist/` | Single-file bundle for paste or upload |
| `tests/` | Self-tests and a fictional fixture (never loaded during generation) |
| `docs/` | Human documentation |

## Development

```bash
python tests/run_tests.py     # run the self-tests
python tools/bundle.py        # rebuild dist/ after editing ENTRYPOINT, core/, templates/, hosts/, or tools/
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes to `core/` should come with a fixture or test case.

## License

[MIT](LICENSE)
