#!/usr/bin/env python3
"""Fast, token-lean C# compile check through `dotnet build`.

Usage:
    python verify_compile.py <repo_root> [--project PATH] [--timeout SECONDS] [--json]

Finds a .sln/.csproj (prefer .sln at the shallowest depth), runs
`dotnet build --no-restore -v q`, and prints only C# diagnostics. A successful
build prints exactly `COMPILE_STATUS: OK (0 errors)` instead of the full log.
This is a source-level compiler check; it does not replace a Unity import or a
real scene/build verification.

Exit codes: 0 = ok, 1 = compile errors, 2 = no/ambiguous project,
3 = dotnet unavailable, 4 = timeout.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", "Library", "Temp", "Obj", "Logs", "Builds", "UserSettings",
             "node_modules", ".idea", ".vs", ".vscode", "PackageCache"}
DIAGNOSTIC = re.compile(r"\b(error|warning)\s+(CS\d{4})\b")
MAX_ERRORS = 40
MAX_WARNINGS = 10


def find_projects(root):
    root = Path(root).resolve()
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            if name.endswith((".sln", ".csproj")):
                path = Path(base) / name
                try:
                    rel = path.relative_to(root).as_posix()
                except ValueError:
                    continue
                found.append((len(Path(rel).parts), rel, path))
    found.sort(key=lambda item: (item[0], item[1]))
    return found


def _dedupe(lines):
    seen, out = set(), []
    for line in lines:
        key = line.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def run_compile(root, project=None, timeout=300):
    root = Path(root).resolve()
    result = {"status": "ok", "command": None, "project": None,
              "errors": [], "warnings": [], "note": ""}
    if not shutil.which("dotnet"):
        result["status"] = "dotnet_missing"
        result["note"] = "dotnet was not found on PATH"
        return result
    if project:
        path = Path(project)
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_file():
            result["status"] = "no_project"
            result["note"] = f"project not found: {project}"
            return result
    else:
        projects = find_projects(root)
        solutions = [p for p in projects if p[1].endswith(".sln")]
        pick = solutions[0] if solutions else (projects[0] if projects else None)
        if not pick:
            result["status"] = "no_project"
            result["note"] = "no .sln or .csproj found outside generated directories"
            return result
        if len(solutions) > 1 and solutions[1][0] == solutions[0][0]:
            result["status"] = "ambiguous"
            result["note"] = "multiple solutions at the same depth; pass --project"
            result["candidates"] = [p[1] for p in solutions[:10]]
            return result
        path = pick[2]
    try:
        result["project"] = path.relative_to(root).as_posix()
    except ValueError:
        result["status"] = "no_project"
        result["note"] = "project must live under the repository root"
        return result
    command = ["dotnet", "build", str(path), "--no-restore", "-v", "q", "--nologo"]
    result["command"] = " ".join(command)
    try:
        proc = subprocess.run(command, cwd=str(root), capture_output=True,
                              text=True, errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["note"] = f"dotnet build exceeded {timeout}s"
        return result
    except OSError as exc:
        result["status"] = "error"
        result["note"] = str(exc)
        return result
    stream = (proc.stdout or "") + "\n" + (proc.stderr or "")
    for line in stream.splitlines():
        match = DIAGNOSTIC.search(line)
        if not match:
            continue
        stripped = line.strip()
        if match.group(1) == "error":
            result["errors"].append(stripped)
        else:
            result["warnings"].append(stripped)
    result["errors"] = _dedupe(result["errors"])
    result["warnings"] = _dedupe(result["warnings"])
    result["error_count"] = len(result["errors"])
    result["warning_count"] = len(result["warnings"])
    result["errors"] = result["errors"][:MAX_ERRORS]
    result["warnings"] = result["warnings"][:MAX_WARNINGS]
    if proc.returncode != 0:
        result["status"] = "failed"
        if not result["errors"]:
            tail = [line.strip() for line in stream.splitlines()
                    if line.strip() and ("error" in line.lower() or "failed" in line.lower())]
            result["errors"] = _dedupe(tail)[:5] or ["build failed without C# diagnostics"]
    return result


def summarize(result):
    status = result["status"]
    if status == "ok":
        return ["COMPILE_STATUS: OK (0 errors)"]
    if status == "failed":
        lines = [f"COMPILE_STATUS: FAILED ({result.get('error_count', len(result['errors']))} errors, "
                 f"{result.get('warning_count', len(result['warnings']))} warnings)"]
        if result.get("error_count", 0) > MAX_ERRORS or result.get("warning_count", 0) > MAX_WARNINGS:
            lines.append(f"COMPILE_DIAGNOSTICS_TRUNCATED: showing at most {MAX_ERRORS} errors "
                         f"and {MAX_WARNINGS} warnings")
        lines += result["errors"][:MAX_ERRORS]
        lines += result["warnings"][:MAX_WARNINGS]
        return lines
    if status == "dotnet_missing":
        return ["COMPILE_STATUS: NOT_RUN (dotnet not found on PATH)"]
    if status == "no_project":
        return ["COMPILE_STATUS: NOT_RUN (no .sln/.csproj found; pass --project)"]
    if status == "ambiguous":
        lines = ["COMPILE_STATUS: NOT_RUN (multiple solutions; pass --project)"]
        lines += result.get("candidates", [])
        return lines
    if status == "timeout":
        return ["COMPILE_STATUS: NOT_RUN (dotnet build timed out)"]
    return [f"COMPILE_STATUS: NOT_RUN ({result.get('note') or status})"]


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Filtered dotnet build check")
    ap.add_argument("root")
    ap.add_argument("--project", help="explicit .sln/.csproj path")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv[1:])
    if args.timeout < 1:
        ap.error("--timeout must be positive")
    result = run_compile(args.root, args.project, args.timeout)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n".join(summarize(result)))
    return {"ok": 0, "failed": 1, "no_project": 2, "ambiguous": 2,
            "dotnet_missing": 3, "timeout": 4}.get(result["status"], 4)


if __name__ == "__main__":
    sys.exit(main())
