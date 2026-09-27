#!/usr/bin/env python3
"""Print a route list or a bounded task context from a generated workflow pack.

Usage: python context.py ROOT [--pack DIR] [--route R-001] [--max-chars 16000]
Repeat --route to select multiple routes. No source files are read or modified.
Read applicable AGENTS.md instructions and agent.md before using this excerpt.
Exit 0 = success, 1 = invalid selection/pack, 2 = context exceeds the output budget.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib as P


def select(texts, route_ids):
    def block(identifier, name, body):
        heading = re.search(r"^#{2,4}[ \t]+" + re.escape(identifier) + r"\b[^\n]*",
                            P.scan_text(name, texts[name]), re.M)
        return (identifier, name, heading.group(0) + "\n" + body.strip())

    routes = {rid: (body, name) for rid, body, name in P.all_blocks(texts, "R")}
    if not routes:
        raise ValueError("no routes found; generate a pack first")
    if not route_ids:
        lines = ["Routes (choose --route R-###; repeat for a task spanning routes):"]
        for rid, (body, name) in sorted(routes.items()):
            lines.append(f"{rid} [{name}] Start: {P.field(body, 'Start') or 'unspecified'}")
        return "\n".join(lines) + "\n"
    missing = set(route_ids) - routes.keys()
    if missing:
        raise ValueError("undefined routes: " + ", ".join(sorted(missing)))

    claims = P.parse_claims(texts)
    needed, selected, finding_ids = set(), [], set()
    for rid in sorted(set(route_ids)):
        body, name = routes[rid]
        selected.append(block(rid, name, body))
        needed.update(P.ANY_ID.findall(body))

    def expand_claims():
        queue = [i for i in needed if i.startswith("C-")]
        seen = set()
        while queue:
            cid = queue.pop()
            if cid in seen:
                continue
            seen.add(cid)
            if cid not in claims:
                raise ValueError(f"undefined claim: {cid}; run validate_pack.py")
            refs = set(claims[cid]["deps"]) | set(P.V_ID.findall(claims[cid]["line"]))
            needed.update(refs)
            queue.extend(i for i in refs if i.startswith("C-"))

    expand_claims()
    findings = P.all_blocks(texts, "F")
    while True:
        added = False
        for fid, body, name in findings:
            if fid not in finding_ids and (fid in needed or
                    set(P.C_ID.findall(P.field(body, "Evidence") or "")) & needed):
                selected.append(block(fid, name, body))
                finding_ids.add(fid)
                needed.update(P.ANY_ID.findall(body))
                added = True
        if not added:
            break
        expand_claims()
    for cid in sorted(needed):
        if cid in claims:
            c = claims[cid]
            selected.append((cid, c["file"], c["line"]))

    matrix = texts.get("validation-matrix.md", "")
    for vid, body in P.blocks(matrix, "V"):
        covers = set(P.ANY_ID.findall(P.field(body, "Covers") or ""))
        if vid in needed or covers & (set(route_ids) | finding_ids):
            selected.append(block(vid, "validation-matrix.md", body))
            needed.add(vid)

    # All protected areas are small and safety-relevant, including those a route forgot to cite.
    for match in P.PROT_DEF.finditer(texts.get("project-context.md", "")):
        selected.append((match.group(1), "project-context.md", match.group(0).strip()))
    provided = {sid for sid, _, _ in selected}
    missing = {i for i in needed if i.startswith(("C-", "V-", "P-"))} - provided
    if missing:
        raise ValueError("undefined context IDs: " + ", ".join(sorted(missing)))

    intro = (
        "# Selected task context\n\n"
        "Read applicable AGENTS.md and agent.md first; resume work also reads session-handoff.md.\n"
        "This is an excerpt, not a new source of truth. Check freshness before relying on claims.\n"
        "Other routes, increments, contracts, and uninspected source are not included.\n"
        "Follow referenced IDs outside this excerpt in their canonical files when needed.\n"
    )
    return intro + "".join(f"\n<!-- {name} -->\n{body}\n" for _, name, body in selected)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--pack", default="docs/ai-workflow")
    ap.add_argument("--route", action="append", default=[])
    ap.add_argument("--max-chars", type=int, default=16000)
    args = ap.parse_args(argv[1:])
    if args.max_chars < 1:
        ap.error("--max-chars must be positive")
    root = Path(args.root).resolve()
    try:
        output = select(P.read_pack(root, root / args.pack), args.route)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if len(output) > args.max_chars:
        print(f"Context needs {len(output)} characters; limit is {args.max_chars}. "
              "Select fewer routes, read their canonical blocks directly, or raise --max-chars. "
              "Nothing was truncated.", file=sys.stderr)
        return 2
    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
