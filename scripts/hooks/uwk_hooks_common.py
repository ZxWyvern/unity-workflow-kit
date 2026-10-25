# UWK_HOOK managed by unity-workflow-kit tools/install_hooks.py
"""Shared helpers for installed unity-workflow-kit Git hooks (standard library only)."""
import os
import subprocess
import sys
from pathlib import Path


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, errors="replace")


def repo_root(start):
    r = git(start, "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()).resolve() if r.returncode == 0 else Path(start).resolve()


def find_kit(repo):
    candidates = []
    env = os.environ.get("UWK_KIT_ROOT")
    if env:
        candidates.append(Path(env))
    candidates += [repo, repo / "_ai-generator", repo / "tools/unity-workflow-kit"]
    for path in candidates:
        try:
            path = path.resolve()
        except OSError:
            continue
        if (path / "tools/bundle.py").is_file() or (
                (path / "ENTRYPOINT.md").is_file() and (path / "tools/packlib.py").is_file()):
            return path
    return None


def is_ignored(repo, path):
    try:
        rel = Path(path).resolve().relative_to(Path(repo).resolve())
    except ValueError:
        return True
    r = git(repo, "check-ignore", "-q", "--", rel.as_posix())
    return r.returncode == 0


def find_tool(repo, kit, name):
    candidates = []
    configured = configured_pack(repo)
    if configured:
        candidates.append(configured / "tools" / name)
    candidates += [repo / "docs/ai-workflow/tools" / name,
                   repo / "tools" / name]
    if kit:
        candidates += [kit / "tools" / name, kit / "docs/ai-workflow/tools" / name]
    for path in candidates:
        if path.is_file():
            return path
    return None


def configured_pack(repo):
    marker = Path(__file__).resolve().parent / "uwk_pack_path"
    if not marker.is_file():
        return None
    try:
        value = marker.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not value:
        return None
    path = Path(value)
    return (Path(repo) / path).resolve() if not path.is_absolute() else path.resolve()


def pack_dir(repo):
    configured = configured_pack(repo)
    if configured and (configured / "index.json").is_file():
        return configured
    pack = Path(repo) / "docs/ai-workflow"
    return pack if (pack / "index.json").is_file() else None


def staged(repo):
    r = git(repo, "diff", "--cached", "--name-only", "-z", "--no-renames")
    if r.returncode != 0:
        return []
    return [p for p in r.stdout.split("\0") if p]


def run_python(tool, *args):
    return subprocess.run([sys.executable, str(tool)] + [str(a) for a in args],
                          capture_output=True, text=True, errors="replace")


def emit(result):
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
