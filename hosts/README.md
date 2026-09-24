# Host Integration

These notes are advisory until verified against the current host's documentation/repository conventions.

Typical entry points:

| Host | Typical entry |
|---|---|
| Codex / OpenCode / AGENTS-aware tools | root `AGENTS.md` |
| Claude Code | `CLAUDE.md` (may reference/import project rules) |
| Cursor | `.cursor/rules/` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Unknown | root `AGENTS.md` + portable `agent.md` + README loading instructions |

Before generating host-native configuration, verify actual filename, path, supported schema, precedence, and discovery behavior. Never invent model IDs/frontmatter/tool endpoints.
