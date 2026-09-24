# 05 — Output Architecture and Canonical Homes

Use `templates/generated-pack-contract.md` for exact generated-pack requirements.

## Canonical homes

Every category has one authoritative home. Other files reference IDs instead of duplicating mutable state.

| Information | Canonical home |
|---|---|
| provenance, stack, claims, subsystem map, findings, protected areas (`P-###`), **not-inspected list** | `project-context.md` |
| task routes, operating loop, increments | `development-workflow.md`; in Compact, `agent.md` |
| validation check definitions **and statuses** | `validation-matrix.md` |
| current session state and next action | `session-handoff.md` (it points to the not-inspected list, never copies it) |
| navigation paths, entry points, routes | `index.json` |
| startup rules | root `AGENTS.md` (between markers) or verified host-native entry |
| portable agent role and behavior | `agent.md` |

Other files cite IDs (`C-###`, `F-###`, `V-###`, `R-###`, `I-###`, `P-###`) and never restate mutable content.

## Status single-source rule

Pass/fail/not-run/not-applicable status exists **only** in `validation-matrix.md`.

`session-handoff.md` may list check IDs run this session and must say “see validation matrix”; it may not duplicate the outcomes.

`index.json` contains no status/result/pass/fail fields.

## Existing instructions

If `AGENTS.md` or another authoritative instruction file already exists:

- read it fully;
- preserve unrelated instructions and scopes;
- integrate only a focused compatible section, wrapped in `<!-- ai-workflow:begin -->` and `<!-- ai-workflow:end -->` markers so the 150-line cap and ID scanning apply only to it;
- do not replace it from a template;
- when safe integration is ambiguous, output a **proposed integration patch** and mark activation pending.

## Host-native profiles

Generate host-specific config only when:

- the user selected that host or repository clearly uses it; and
- filename/location/schema/discovery behavior can be verified.

Never invent frontmatter, model identifiers, auto-discovery rules, or tool endpoints.
