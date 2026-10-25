# AGENTS-aware Hosts

When the repository/host demonstrably honors `AGENTS.md`:

1. read the existing root file fully;
2. discover relevant nested `AGENTS.md` files before editing inside their scope;
3. integrate a compact project workflow section rather than replacing unrelated instructions;
4. point to `docs/ai-workflow/` for detailed context;
5. keep host/tool-specific commands out unless verified in the current environment.

If activation semantics are uncertain, output a proposed patch and explain manual activation.

## MCP-capable hosts

When the host supports Model Context Protocol servers, prefer the native tools over manual shell paste:

```bash
python _ai-generator/tools/mcp_server.py --root .
```

Expose `uwk_get_context`, `uwk_find_suspects`, `uwk_validate`, and `uwk_save_handoff`. Verify the host's actual config filename, JSON shape, transport requirements, and start/restart behavior before editing configuration. Never invent server IDs or endpoints. If MCP is unavailable, keep the CLI fallback in `docs/USAGE.md`; the workflow must not depend on MCP.

Session state remains per actor even through MCP: `uwk_save_handoff` writes only `sessions/<branch-slug>__<actor-slug>.md` and refreshes `index.json`. Do not add a tool that overwrites another actor's session or hand-edits generated files.
