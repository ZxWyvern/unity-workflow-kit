# Unity Workflow Agent Generator

Give your coding agent a small, project-specific guide to your Unity project. It records where a task starts, which files own the behavior, what must stay intact, and how to check the result.

[![Unity projects](https://img.shields.io/badge/Unity-181B23?style=for-the-badge&logo=unity&logoColor=FFFFFF)](https://unity.com/)
[![Python 3.9+ helpers](https://img.shields.io/badge/Python_3.9%2B-181B23?style=for-the-badge&logo=python&logoColor=FFD43B)](https://www.python.org/)
[![Markdown workflow documents](https://img.shields.io/badge/Markdown-181B23?style=for-the-badge&logo=markdown&logoColor=FFFFFF)](https://daringfireball.net/projects/markdown/)
[![Git change tracking](https://img.shields.io/badge/Git-181B23?style=for-the-badge&logo=git&logoColor=F05032)](https://git-scm.com/)
[![GitHub Actions CI](https://img.shields.io/badge/GitHub_Actions-181B23?style=for-the-badge&logo=githubactions&logoColor=58A6FF)](https://github.com/features/actions)

[Bahasa Indonesia](README.id.md) · [Usage guide](docs/USAGE.md) · [Contributing](CONTRIBUTING.md)

**v1.3.0 beta.** Local Python tools are tested; generation quality and token usage across real projects and AI hosts still need field reports. Not affiliated with Unity Technologies.

## Start with one prompt

1. Download the repository ZIP and extract it into your Unity project as `_ai-generator/`, outside `Assets/`. You can also use a sibling folder and adjust the path below.
2. Open your Unity project in a coding agent that can read local files.
3. Paste:

```text
Read _ai-generator/ENTRYPOINT.md and set up the workflow for this Unity project.
```

The agent discovers the project, creates a Compact pack, or refreshes the existing pack. It follows your existing architecture. Review the generated diff and commit the pack plus the marked `AGENTS.md` section.

Python 3.9+ runs the local helpers, using only the standard library. If Python is unavailable, the agent follows the documented manual procedure and reports that the validator was not run. Add `_ai-generator/` to your project's `.gitignore` if you do not want to commit the kit.

**Chat with uploads only:** attach a project export and the [full bundle](dist/Unity_Workflow_Agent_Generator_bundle.md), then ask it to set up the workflow. The bundle includes tool source and costs more input context. Directory mode is the recommended path for agents with filesystem access.

## What keeps context small

- Load a short entrypoint and three required references; other modules load when relevant.
- Start with a focused inspection: up to 2 subsystems, 1 end-to-end path, 3 findings, 3 routes, and 1 next increment. Expand when a real dependency requires it.
- Keep root startup instructions near 20 lines and the portable agent near 80 lines.
- Use `context.py` to select a route with its evidence dependencies, checks, and protected areas. It reads local pack files without sending the entire pack to the model.
- Refresh changed claims and dependent checks. Leave unaffected content alone.

These are context controls, not a guaranteed token saving. Actual cost depends on the agent, task, and project. Budgets never justify skipping applicable instructions or required verification.

## What gets generated

```text
AGENTS.md                       marked startup section; existing rules preserved
```

The default pack is:

```text
docs/ai-workflow/
  agent.md                      operating loop, task routes, next increment
  project-context.md            claims, protected areas, findings, coverage
  validation-matrix.md          checks and their outcomes
  session-handoff.md            current work and next action
  index.json                    navigation
  tools/                        four small Python helpers
```

Standard adds a README and separate workflow file when needed. Extended adds relevant specialist contracts. A focused task in a large repository can still use Compact.

Generation writes workflow documentation and helpers. Gameplay implementation requires a separate request. Source existence, scene wiring, and runtime verification remain separate claims.

## Daily use

```text
Read AGENTS.md and docs/ai-workflow/agent.md. Implement: <your task>.
Load only the relevant route and dependencies. Report checks run and not run.
```

The agent can list and select routes locally:

```bash
python docs/ai-workflow/tools/context.py .
python docs/ai-workflow/tools/context.py . --route R-001
```

Route IDs come from your generated pack. Repeat `--route` for a task spanning routes. The default output ceiling is 16,000 characters; oversized output fails explicitly instead of silently dropping evidence. Read the canonical blocks or raise `--max-chars` when needed.

## Large projects and teams

Give the agent a focus, such as:

```text
Focus: inventory save/load. Unity root: games/client.
```

It searches paths first, inspects that subsystem and its direct dependencies, and records everything else as not inspected. Generated caches and vendor dumps stay out of broad scans. Several Unity roots require an explicit or task-supported selection.

Optional controls:

| Setting | Use |
|---|---|
| `budget = lean` | Default focused investigation |
| `budget = balanced` | Broader system coverage |
| `budget = deep` | More verification of selected paths; widen coverage explicitly |
| `architecture_policy = toward: <target>` | Apply an explicit target to new/touched code |

After a merge or significant change:

```text
Read _ai-generator/ENTRYPOINT.md and refresh the existing workflow pack.
```

For team CI:

```bash
python docs/ai-workflow/tools/validate_pack.py . docs/ai-workflow
```

The validator checks structure and consistency. It does not prove gameplay correctness. Git-based refresh includes untracked, nonignored files; dirty snapshots and environment changes still need explicit review.

## Develop this kit

```bash
python tests/run_tests.py
python tools/bundle.py
```

CI is configured for Python 3.9 and 3.12 on Linux and Windows, and checks bundle freshness. See [CHANGELOG.md](CHANGELOG.md) for migration notes and [MIT license](LICENSE).
