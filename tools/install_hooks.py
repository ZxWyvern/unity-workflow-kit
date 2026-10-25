#!/usr/bin/env python3
"""Install the versioned Git hooks for this workflow kit.

Usage:
    python tools/install_hooks.py [repo_root] [--force] [--no-merge-driver] [--pack DIR]

Copies scripts/hooks/pre-commit, post-merge, post-checkout, and the helper
module into the repository's actual hooks directory (worktrees included).
It also records the pack path for the hooks, enables the `merge=ours` driver,
and appends idempotent .gitattributes rules for the generated index and (when
inside the repo) dist bundle.
Existing non-kit hooks are never overwritten unless --force is passed.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SOURCE = KIT / "scripts/hooks"
HOOKS = ("pre-commit", "post-merge", "post-checkout", "uwk_hooks_common.py")
MARKER = "UWK_HOOK managed by unity-workflow-kit"
PACK_CONFIG = "uwk_pack_path"


def hooks_dir(root):
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-path", "hooks"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise ValueError(r.stderr.strip() or "not a git repository")
    path = Path(r.stdout.strip())
    return path.resolve() if path.is_absolute() else (Path(root) / path).resolve()


def configure_merge_driver(root):
    r = subprocess.run(["git", "-C", str(root), "config", "--get", "merge.ours.driver"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode == 0 and r.stdout.strip():
        return False
    run = subprocess.run(["git", "-C", str(root), "config", "merge.ours.driver", "true"],
                         capture_output=True, text=True, errors="replace")
    if run.returncode != 0:
        raise ValueError(run.stderr.strip() or "could not configure merge.ours.driver")
    return True


def configure_attributes(root, pack="docs/ai-workflow"):
    """Append merge=ours rules for generated files without rewriting existing lines."""
    root = Path(root).resolve()
    path = root / ".gitattributes"
    existing = path.read_bytes() if path.is_file() else b""
    text = existing.decode("utf-8", errors="replace")
    lines = text.splitlines()
    pack_path = Path(pack)
    if not pack_path.is_absolute():
        pack_path = root / pack_path
    try:
        pack_rel = pack_path.resolve().relative_to(root).as_posix()
    except ValueError:
        raise ValueError("pack directory must be inside the repository")
    wanted = [f"{pack_rel}/index.json merge=ours"]
    try:
        bundle = (KIT / "dist/Unity_Workflow_Agent_Generator_bundle.md").resolve().relative_to(root)
    except ValueError:
        bundle = None
    if bundle is not None:
        wanted.append(f"{bundle.as_posix()} merge=ours")
    missing = []
    for rule in wanted:
        attr_path = rule.split()[0].lstrip("/")
        if not any(line.split() and line.lstrip("/").split()[0] == attr_path
                   and "merge=ours" in line.split()[1:] for line in lines):
            missing.append(rule)
    if not missing:
        return False
    prefix = "\n" if existing and not existing.endswith(b"\n") else ""
    path.write_bytes(existing + (prefix + "\n".join(missing) + "\n").encode("utf-8"))
    return True


def record_pack(target_dir, repo_root, pack):
    path = Path(pack)
    if not path.is_absolute():
        path = Path(repo_root) / path
    path = path.resolve()
    try:
        value = path.relative_to(Path(repo_root).resolve()).as_posix()
    except ValueError:
        value = str(path)
    (target_dir / PACK_CONFIG).write_text(value + "\n", encoding="utf-8")


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Install unity-workflow-kit Git hooks")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--force", action="store_true", help="overwrite existing hooks")
    ap.add_argument("--no-merge-driver", action="store_true",
                    help="do not configure merge.ours.driver or .gitattributes")
    ap.add_argument("--pack", default="docs/ai-workflow",
                    help="pack directory used by hooks and the .gitattributes rule")
    args = ap.parse_args(argv[1:])
    root = Path(args.root).resolve()
    if not SOURCE.is_dir():
        print(f"hook sources not found: {SOURCE}", file=sys.stderr)
        return 1
    try:
        target_dir = hooks_dir(root)
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, errors="replace")
        attributes_root = Path(top.stdout.strip()).resolve() if top.returncode == 0 else root
        if not args.no_merge_driver:
            configured = configure_merge_driver(root)
            attributes_changed = configure_attributes(attributes_root, args.pack)
        else:
            configured, attributes_changed = False, False
    except (OSError, ValueError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1
    target_dir.mkdir(parents=True, exist_ok=True)
    skipped = []
    for name in HOOKS:
        source = SOURCE / name
        target = target_dir / name
        if not source.is_file():
            print(f"missing hook source: {source}", file=sys.stderr)
            return 1
        if target.exists() and not args.force:
            try:
                if MARKER not in target.read_text(encoding="utf-8", errors="replace"):
                    skipped.append(target)
                    continue
            except OSError:
                skipped.append(target)
                continue
        data = source.read_bytes().replace(b"\r\n", b"\n")
        target.write_bytes(data)
        if os.name != "nt":
            target.chmod(0o755)
    record_pack(target_dir, attributes_root, args.pack)
    for path in skipped:
        print(f"SKIP existing non-kit hook: {path} (use --force to replace)", file=sys.stderr)
    print(f"installed {len(HOOKS) - len(skipped)} hook file(s) in {target_dir}")
    if not args.no_merge_driver:
        print("merge.ours.driver " + ("configured" if configured else "already configured"))
        print(".gitattributes " + ("updated" if attributes_changed else "already configured"))
    if skipped:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
