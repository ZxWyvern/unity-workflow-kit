#!/usr/bin/env python3
"""Compute suspect claims for Refresh mode (generator v1.4.0).

Usage:
    python suspects.py <repo_root> [--pack DIR] (--since REV | --changed PATH [PATH ...])
                       [--trigger TOKEN ...] [--json] [--no-references]

--since REV     tracked changes against REV plus untracked, nonignored files
--changed ...   explicit repository-relative paths (use when git is unavailable)
--trigger TOKEN also mark every claim whose invalidates: list contains TOKEN
                (e.g. package_or_unity_version_changed)
--no-references skip the changed-type -> referencing-file scan

A claim is suspect when its path changed (or its .meta changed, or a file under
its directory changed, or the path no longer exists), when it carries a fired
trigger, or when it depends (transitively) on a suspect claim. Changed C# type
definitions also pull in files that reference those types, so the agent sees
likely call sites without a whole-repository search.
This tool only reads. It never edits the pack or resets check statuses;
the agent decides what to reset after reviewing the output.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib as P  # noqa: E402

SKIP_DIRS = {".git", "Library", "Temp", "Obj", "Logs", "Builds", "UserSettings",
             "node_modules", ".idea", ".vs", ".vscode", "PackageCache"}
TYPE_DEF = re.compile(r"\b(?:class|struct|interface|enum|record)\s+([A-Za-z_]\w*)")
MAX_REFERENCE_FILES = 4000
MAX_REFERENCE_BYTES = 512 * 1024


def cs_symbols(path):
    """Type names declared by one C# file (empty when unreadable)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {name for name in TYPE_DEF.findall(text) if len(name) >= 3}


def reference_scan(root, changed):
    """Map files that mention types declared in changed C# files to those types."""
    root = Path(root)
    changed = set(changed)
    types, origins = set(), {}
    for rel in sorted(changed):
        if not rel.endswith(".cs"):
            continue
        path = root / rel
        if not path.is_file():
            continue
        names = cs_symbols(path)
        types.update(names)
        for name in names:
            origins.setdefault(name, rel)
    notes = {"capped": False, "skipped_large": 0}
    if not types:
        return {}, set(), origins, notes
    pattern = re.compile(r"\b(?:" + "|".join(sorted(map(re.escape, types))) + r")\b")
    hits, scanned = {}, 0
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            if not name.endswith(".cs"):
                continue
            path = Path(base) / name
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if rel in changed:
                continue
            try:
                if path.stat().st_size > MAX_REFERENCE_BYTES:
                    notes["skipped_large"] += 1
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            scanned += 1
            if scanned > MAX_REFERENCE_FILES:
                notes["capped"] = True
                break
            found = sorted(set(pattern.findall(text)) & types)
            if found:
                hits[rel] = found
        if scanned > MAX_REFERENCE_FILES:
            notes["capped"] = True
            break
    return hits, set(hits), origins, notes


def git_changed(root, rev):
    changed = set()
    # NUL delimiters preserve spaces, newlines, and non-ASCII filenames.
    # Disable rename detection so both old and new paths invalidate claims.
    for args in (["diff", "--name-only", "--no-renames", "-z", rev, "--"],
                 ["ls-files", "--others", "--exclude-standard", "-z"]):
        try:
            r = subprocess.run(["git", "-C", str(root)] + args, capture_output=True)
        except OSError as exc:
            return None, str(exc)
        if r.returncode != 0:
            return None, r.stderr.decode("utf-8", errors="replace").strip()
        changed.update(p.decode("utf-8", errors="surrogateescape")
                       for p in r.stdout.split(b"\0") if p)
    return sorted(changed), ""


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Suspect-claim calculator for Refresh mode")
    ap.add_argument("root")
    ap.add_argument("--pack", default="docs/ai-workflow")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since")
    g.add_argument("--changed", nargs="+")
    ap.add_argument("--trigger", action="append", default=[])
    ap.add_argument("--no-references", action="store_true",
                    help="skip the changed-type referencing-file scan")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv[1:])

    root = Path(a.root).resolve()
    pack = (root / a.pack).resolve() if not Path(a.pack).is_absolute() else Path(a.pack).resolve()
    try:
        pack.relative_to(root)
    except ValueError:
        print(f"pack directory must be inside the repository: {pack}", file=sys.stderr)
        return 2
    texts = P.read_pack(root, pack)
    claims = P.parse_claims(texts)
    if not claims:
        print("no claims found; nothing to compute", file=sys.stderr)
        return 2

    if a.since:
        changed, msg = git_changed(root, a.since)
        if changed is None:
            print(f"git diff failed: {msg}", file=sys.stderr)
            return 3
    else:
        changed = a.changed
    def norm(c):
        c = c.replace("\\", "/")
        while c.startswith("./"):
            c = c[2:]
        return c
    changed = {norm(c) for c in changed}
    references, reference_files, origins = {}, set(), {}
    reference_notes = {"capped": False, "skipped_large": 0}
    if not a.no_references:
        references, reference_files, origins, reference_notes = reference_scan(root, changed)
        changed |= reference_files
    # Index ancestors once instead of scanning every changed path for every claim.
    ancestors = set()
    for path in changed:
        parts = path.split("/")
        ancestors.update("/".join(parts[:i]) for i in range(1, len(parts)))

    direct = {}
    for cid, c in claims.items():
        p = c["path"].replace("\\", "/").rstrip("/")
        if not p or "*" in p:
            continue
        why = None
        if p in changed:
            why = "path_changed"
        elif p + ".meta" in changed:
            why = "meta_changed"
        elif p in ancestors:
            why = "file_under_path_changed"
        elif c["label"] not in ("proposed", "unknown") and not (root / p).exists():
            why = "path_missing"
        if why:
            direct[cid] = why
    for tok in a.trigger:
        for cid, c in claims.items():
            if tok in (c["inval"] or []):
                direct.setdefault(cid, f"trigger:{tok}")

    rev = {}
    for cid, c in claims.items():
        for d in c["deps"]:
            rev.setdefault(d, []).append(cid)
    transitive, queue = {}, list(direct)
    while queue:
        cur = queue.pop()
        for dep in rev.get(cur, []):
            if dep not in direct and dep not in transitive:
                transitive[dep] = cur
                queue.append(dep)
    suspect = set(direct) | set(transitive)

    findings = []
    for fid, body, _ in P.all_blocks(texts, "F"):
        ev = set(P.C_ID.findall(P.field(body, "Evidence") or ""))
        if ev & suspect:
            findings.append(fid)
    exec_checks = sorted({v for cid in suspect if claims[cid]["label"] == "execution_verified"
                          for v in P.V_ID.findall(claims[cid]["line"])})
    finding_checks = set()
    for fid, body, _ in P.all_blocks(texts, "F"):
        if fid in findings:
            finding_checks |= set(P.V_ID.findall(P.field(body, "Smallest follow-up and acceptance") or ""))
    covers_checks = set()
    for vid, body in P.blocks(texts.get("validation-matrix.md", ""), "V"):
        if set(P.ANY_ID.findall(P.field(body, "Covers") or "")) & set(findings):
            covers_checks.add(vid)
    review = sorted(set(exec_checks) | finding_checks | covers_checks)

    result = {
        "changed_files": sorted(changed),
        "symbol_references": {k: references[k] for k in sorted(references)},
        "reference_types": {k: origins[k] for k in sorted(origins)},
        "reference_scan": reference_notes,
        "direct": {k: direct[k] for k in sorted(direct)},
        "transitive": {k: f"depends on {transitive[k]}" for k in sorted(transitive)},
        "findings_to_recheck": sorted(findings),
        "checks_to_review": review,
        "note": "Review each check; reset to not_run only if its observation no longer supports the current snapshot. "
                "Always revalidate the handoff's next executable action.",
    }
    if a.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"changed files: {len(changed)}")
    if references:
        print(f"symbol references: {len(references)} file(s) mention changed types: "
              + ", ".join(sorted(origins)))
    print(f"suspect claims: {len(suspect)} ({len(direct)} direct, {len(transitive)} via deps)")
    for k in sorted(direct):
        print(f"  {k}  direct     {direct[k]}  [{claims[k]['label']}]  {claims[k]['path']}")
    for k in sorted(transitive):
        print(f"  {k}  transitive depends on {transitive[k]}  [{claims[k]['label']}]  {claims[k]['path']}")
    print("findings to recheck:", ", ".join(result["findings_to_recheck"]) or "none")
    print("checks to review:   ", ", ".join(review) or "none")
    print(result["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
