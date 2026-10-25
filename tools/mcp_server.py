#!/usr/bin/env python3
"""Minimal MCP stdio server for the unity-workflow-kit tools.

Usage:
    python tools/mcp_server.py [--root REPO]

Transport: newline-delimited JSON-RPC 2.0 (MCP stdio). No third-party packages.
Tools:
    uwk_get_context     route context, C# skeleton, or condensed Unity YAML
    uwk_find_suspects   git diff + changed-type references -> suspect claims
    uwk_validate        pack validation and optional filtered dotnet build
    uwk_save_handoff    write sessions/<branch-slug>__<actor-slug>.md and refresh index.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import context as task_context  # noqa: E402
import packlib as P  # noqa: E402

VERSION = "1.4.0"
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_ROOT = Path.cwd()


def _schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required),
            "additionalProperties": False}


TOOLS = [
    {
        "name": "uwk_get_context",
        "description": "Load a selected task route plus dependencies/session state, or a "
                       "C# skeleton, or a condensed .unity/.prefab hierarchy. Never returns "
                       "raw serialization YAML.",
        "inputSchema": _schema({
            "root": {"type": "string", "description": "repository root (default: server root)"},
            "pack": {"type": "string", "description": "pack directory", "default": "docs/ai-workflow"},
            "route": {"type": "string", "description": "one R-### route"},
            "routes": {"type": "array", "items": {"type": "string"}},
            "file": {"type": "string", "description": ".cs, .unity, or .prefab path"},
            "method": {"type": ["string", "array"], "items": {"type": "string"},
                       "description": "full C# method body/bodies instead of the skeleton"},
            "sessions": {"type": "boolean", "default": True},
            "max_chars": {"type": "integer", "default": 16000},
            "branch": {"type": "string"},
            "actor": {"type": "string"},
        }),
    },
    {
        "name": "uwk_find_suspects",
        "description": "Compute suspect claims from git changes, changed C# type references, "
                       "and invalidation triggers. Returns compact JSON, not source files.",
        "inputSchema": _schema({
            "root": {"type": "string"},
            "pack": {"type": "string", "default": "docs/ai-workflow"},
            "since": {"type": "string", "description": "git revision (default HEAD)"},
            "changed": {"type": "array", "items": {"type": "string"},
                        "description": "explicit paths; overrides since"},
            "triggers": {"type": "array", "items": {"type": "string"}},
            "references": {"type": "boolean", "default": True},
        }),
    },
    {
        "name": "uwk_validate",
        "description": "Validate pack structure, IDs, .meta/GUID integrity, documented paths, "
                       "and optionally run a filtered dotnet build.",
        "inputSchema": _schema({
            "root": {"type": "string"},
            "pack": {"type": "string", "default": "docs/ai-workflow"},
            "compile": {"type": "boolean", "default": False},
        }),
    },
    {
        "name": "uwk_save_handoff",
        "description": "Write this actor's session file at sessions/<branch-slug>__<actor-slug>.md and "
                       "regenerate index.json. Content must say 'see validation matrix'.",
        "inputSchema": _schema({
            "root": {"type": "string"},
            "pack": {"type": "string", "default": "docs/ai-workflow"},
            "content": {"type": "string"},
            "actor": {"type": "string"},
            "branch": {"type": "string"},
            "require_phrase": {"type": "boolean", "default": True},
        }, ("content",)),
    },
]


def _resolve_root(value):
    root = Path(value) if value else SERVER_ROOT
    return (root if root.is_absolute() else SERVER_ROOT / root).resolve()


def _text(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


def _run_tool(script, args):
    proc = subprocess.run([sys.executable, str(TOOLS_DIR / script)] + [str(a) for a in args],
                          capture_output=True, text=True, errors="replace")
    output = (proc.stdout or "") + (proc.stderr or "")
    return _text(output.rstrip() or f"{script} exited {proc.returncode}",
                 proc.returncode != 0)


def call_tool(name, args):
    args = args if isinstance(args, dict) else {}
    root = _resolve_root(args.get("root"))
    pack = args.get("pack") or "docs/ai-workflow"
    if name == "uwk_get_context":
        routes = list(args.get("routes") or [])
        if args.get("route"):
            routes.append(args["route"])
        methods = args.get("method") or []
        if isinstance(methods, str):
            methods = [methods]
        try:
            max_chars = int(args.get("max_chars") or 16000)
        except (TypeError, ValueError):
            return _text("max_chars must be an integer", True)
        try:
            text = task_context.build_output(
                root, pack, routes, args.get("file"), methods,
                bool(args.get("sessions", True)), args.get("branch"), args.get("actor"))
        except (ValueError, OSError) as exc:
            return _text(str(exc), True)
        if len(text) > max_chars:
            return _text(f"Context needs {len(text)} characters; limit is {max_chars}. "
                         "Select fewer routes or raise max_chars. Nothing was truncated.", True)
        return _text(text)
    if name == "uwk_find_suspects":
        cmd = ["--pack", pack, "--json"]
        changed = args.get("changed") or []
        if changed:
            cmd += ["--changed"] + list(changed)
        else:
            cmd += ["--since", str(args.get("since") or "HEAD")]
        for trigger in args.get("triggers") or []:
            cmd += ["--trigger", trigger]
        if args.get("references") is False:
            cmd += ["--no-references"]
        return _run_tool("suspects.py", [root] + cmd)
    if name == "uwk_validate":
        cmd = [root, pack]
        if args.get("compile"):
            cmd.append("--compile")
        return _run_tool("validate_pack.py", cmd)
    if name == "uwk_save_handoff":
        try:
            path, index_path, changed = P.save_handoff(
                root, root / pack, args.get("content", ""), args.get("actor"),
                args.get("branch"), bool(args.get("require_phrase", True)))
        except (ValueError, OSError) as exc:
            return _text(str(exc), True)
        return _text(f"wrote {path.relative_to(root).as_posix()}\n"
                     f"index.json {'updated' if changed else 'already current'} "
                     f"({index_path.relative_to(root).as_posix()})")
    return None


def handle(message):
    """Return a JSON-RPC response dict, or None for notifications."""
    if not isinstance(message, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    is_notification = "id" not in message
    if not isinstance(method, str):
        return None if is_notification else {
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32600, "message": "invalid request"}}
    if method == "initialize":
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        protocol = requested if requested in PROTOCOLS else PROTOCOLS[0]
        result = {
            "protocolVersion": protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "unity-workflow-kit", "version": VERSION},
            "instructions": "Use uwk_get_context before reading source; use uwk_validate "
                            "before claiming completion; save progress with uwk_save_handoff.",
        }
        return None if is_notification else {"jsonrpc": "2.0", "id": msg_id, "result": result}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return None if is_notification else {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return None if is_notification else {
            "jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        if not isinstance(params, dict) or not isinstance(params.get("name"), str):
            return None if is_notification else {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32602, "message": "tools/call requires params.name"}}
        result = call_tool(params["name"], params.get("arguments"))
        if result is None:
            return None if is_notification else {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32602, "message": f"unknown tool: {params['name']}"}}
        return None if is_notification else {"jsonrpc": "2.0", "id": msg_id, "result": result}
    if is_notification:
        return None
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32601, "message": f"method not found: {method}"}}


def serve(instream, outstream):
    for raw in instream:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": f"parse error: {exc}"}}
        else:
            response = handle(message)
        if response is not None:
            outstream.write(json.dumps(response, ensure_ascii=False) + "\n")
            outstream.flush()


def main(argv=None):
    global SERVER_ROOT
    argv = list(sys.argv if argv is None else argv)
    ap = argparse.ArgumentParser(description="MCP stdio server for unity-workflow-kit")
    ap.add_argument("--root", default=".", help="default repository root")
    args = ap.parse_args(argv[1:])
    SERVER_ROOT = Path(args.root).resolve()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print(f"unity-workflow-kit MCP server {VERSION} (root: {SERVER_ROOT})", file=sys.stderr)
    serve(sys.stdin.buffer, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
