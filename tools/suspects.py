#!/usr/bin/env python3
"""Compute suspect claims for Refresh mode (generator v1.2.1).

Usage:
    python suspects.py <repo_root> [--pack DIR] (--since REV | --changed PATH [PATH ...])
                       [--trigger TOKEN ...] [--json]

--since REV     changed files = `git diff --name-only REV` (working tree vs REV)
--changed ...   explicit repository-relative paths (use when git is unavailable)
--trigger TOKEN also mark every claim whose invalidates: list contains TOKEN
                (e.g. package_or_unity_version_changed)

A claim is suspect when its path changed (or its .meta changed, or a file under
its directory changed, or the path no longer exists), when it carries a fired
trigger, or when it depends (transitively) on a suspect claim.
This tool only reads. It never edits the pack or resets check statuses;
the agent decides what to reset after reviewing the output.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib as P  # noqa: E402


def git_changed(root, rev):
    r = subprocess.run(["git", "-C", str(root), "diff", "--name-only", rev],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()
    return [x.strip() for x in r.stdout.splitlines() if x.strip()], ""


def main(argv):
    ap = argparse.ArgumentParser(description="Suspect-claim calculator for Refresh mode")
    ap.add_argument("root")
    ap.add_argument("--pack", default="docs/ai-workflow")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since")
    g.add_argument("--changed", nargs="+")
    ap.add_argument("--trigger", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv[1:])

    root = Path(a.root).resolve()
    pack = root / a.pack
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
        elif any(f.startswith(p + "/") for f in changed):
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
