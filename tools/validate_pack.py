#!/usr/bin/env python3
"""Validate a generated Unity AI workflow pack (generator v1.2.1).

Usage:
    python validate_pack.py <repo_root> [pack_dir]

pack_dir is relative to repo_root and defaults to docs/ai-workflow.
Checks mechanical consistency only. It cannot prove that claims are true,
but it does check that cited paths and symbols exist.
Exit code: 0 = no errors, 1 = errors, 2 = usage.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib as P  # noqa: E402


def check_index(index, root, defs, profile, err, warn):
    if not isinstance(index, dict):
        err.append("index.json must be a JSON object")
        return
    for key in ["format", "format_version", "workflow_version", "profile", "project",
                "snapshot", "documents", "entry_points", "stack", "task_routes",
                "refresh_triggers"]:
        if key not in index:
            err.append(f"index.json missing top-level field: {key}")
    if index.get("format_version") not in (None, "1.2"):
        err.append(f"index.json format_version must be '1.2', got {index.get('format_version')!r}")
    proj = index.get("project")
    if isinstance(proj, dict):
        for k in ("root", "product_type", "tier"):
            if k not in proj:
                err.append(f"index.json project missing field: {k}")
        tier = proj.get("tier")
        if tier is None:
            warn.append("index.json project.tier is null; record the depth tier")
        elif tier not in P.TIERS:
            err.append(f"index.json project.tier must be one of {sorted(P.TIERS)}")
    snap = index.get("snapshot")
    if isinstance(snap, dict):
        for k in ("observed_date", "source_kind", "revision", "dirty", "completeness_limits"):
            if k not in snap:
                err.append(f"index.json snapshot missing field: {k}")

    def walk(obj, trail=""):
        if isinstance(obj, dict):
            yield trail, obj
            for k, v in obj.items():
                yield from walk(v, f"{trail}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield from walk(v, f"{trail}[{i}]")

    for trail, d in walk(index):
        for key in d:
            if key.lower() in {"status", "result", "results", "passed", "failed"}:
                err.append(f"index.json{trail}: forbidden status/result key '{key}' "
                           "(status lives only in validation-matrix.md)")
        if "path" in d:
            state = d.get("path_state")
            if state not in P.PATH_STATES:
                err.append(f"index.json{trail}: path '{d['path']}' has invalid or missing path_state")
            elif isinstance(d["path"], str):
                exists = (root / d["path"]).exists()
                if state in ("existing", "generated") and not exists:
                    err.append(f"index.json{trail}: {state} path not found: {d['path']}")
                if state == "proposed" and exists:
                    warn.append(f"index.json{trail}: proposed path already exists: {d['path']}")

    def entries(key, required):
        arr = index.get(key)
        if not isinstance(arr, list):
            return []
        for i, e in enumerate(arr):
            if not isinstance(e, dict):
                err.append(f"index.json {key}[{i}] must be an object")
                continue
            for r in required:
                if r not in e:
                    err.append(f"index.json {key}[{i}] missing field: {r}")
        return [e for e in arr if isinstance(e, dict)]

    docs = entries("documents", ["id", "path", "path_state", "purpose"])
    eps = entries("entry_points", ["id", "path", "path_state", "kind", "certainty", "claim_ids"])
    stack = entries("stack", ["name", "version", "claim_ids"])
    routes = entries("task_routes", ["id", "title", "document", "check_ids"])

    for e in eps:
        if e.get("certainty") not in P.CERTAINTY:
            err.append(f"index.json entry_point {e.get('id')}: certainty must be one of {sorted(P.CERTAINTY)}")
    for e in stack:
        if e.get("version") is None and not e.get("note"):
            err.append(f"index.json stack '{e.get('name')}': null version requires a 'note'")
    for key, arr in (("entry_points", eps), ("stack", stack)):
        for e in arr:
            for cid in e.get("claim_ids") or []:
                if cid not in defs:
                    err.append(f"index.json {key}: claim_id {cid} is not defined")
    for e in routes:
        rid = e.get("id")
        if rid not in defs:
            err.append(f"index.json task_routes: route {rid} is not defined in the pack")
        for vid in e.get("check_ids") or []:
            if vid not in defs:
                err.append(f"index.json task_routes {rid}: check {vid} is not defined")

    listed = {d.get("path", "").split("/")[-1] for d in docs}
    needed = ["agent.md", "project-context.md", "validation-matrix.md", "session-handoff.md"]
    if profile in ("standard", "extended"):
        needed += ["README.md", "development-workflow.md"]
    for n in needed:
        if n not in listed:
            warn.append(f"index.json documents does not list {n}")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = Path(argv[1]).resolve()
    pack = (root / argv[2]).resolve() if len(argv) > 2 else root / "docs" / "ai-workflow"
    err, warn = [], []
    texts = P.read_pack(root, pack)

    # ---- index and profile -------------------------------------------------
    index, profile = None, None
    if "index.json" not in texts:
        err.append("missing required file: index.json")
    else:
        try:
            index = json.loads(texts["index.json"])
        except json.JSONDecodeError as e:
            err.append(f"index.json does not parse: {e}")
    if isinstance(index, dict):
        profile = str(index.get("profile", "")).lower()
        if profile not in P.PROFILES:
            err.append(f"index.json profile must be one of {sorted(P.PROFILES)}")

    required = ["agent.md", "project-context.md", "validation-matrix.md", "session-handoff.md"]
    if profile in ("standard", "extended"):
        required += ["README.md", "development-workflow.md"]
    for n in required:
        if n not in texts:
            err.append(f"missing required file: {n} (profile '{profile}')")

    for name, text in texts.items():
        if "REPLACE_ME" in text:
            err.append(f"{name}: unresolved REPLACE_ME placeholder")

    # ---- size limits and AGENTS.md section ----------------------------------
    if "agent.md" in texts and len(texts["agent.md"].splitlines()) > P.AGENT_MD_LIMIT:
        err.append(f"agent.md exceeds {P.AGENT_MD_LIMIT} lines")
    if "AGENTS.md" in texts:
        sec = P.agents_section(texts["AGENTS.md"])
        if sec is None:
            warn.append("AGENTS.md has no ai-workflow begin/end markers; the 150-line cap "
                        "and ID scanning cannot be enforced")
        elif len(sec.strip().splitlines()) > P.AGENTS_SECTION_LIMIT:
            err.append(f"AGENTS.md workflow section exceeds {P.AGENTS_SECTION_LIMIT} lines")
    else:
        warn.append("root AGENTS.md not found; acceptable only with another verified entry mechanism")

    # ---- IDs ---------------------------------------------------------------
    defs = P.collect_defs(texts)
    for i, where in sorted(defs.items()):
        if len(where) > 1:
            err.append(f"duplicate ID {i} defined in: {', '.join(where)}")
    for name, text in texts.items():
        for i in sorted(set(P.ANY_ID.findall(P.scan_text(name, text)))):
            if i not in defs:
                err.append(f"{name}: references undefined ID {i}")

    matrix_text = texts.get("validation-matrix.md", "")
    matrix = P.matrix_status(matrix_text)

    # ---- claims ------------------------------------------------------------
    claims = P.parse_claims(texts)
    graph = {}
    for cid, c in sorted(claims.items()):
        label = c["label"]
        if label not in P.LABELS:
            err.append(f"claim {cid}: invalid label '{label}'")
        if c["deps_raw"] is None:
            warn.append(f"claim {cid}: no deps: field (use 'deps: none')")
        for d in c["deps"]:
            if not re.fullmatch(r"C-\d{3}", d):
                err.append(f"claim {cid}: invalid dependency token '{d}'")
            elif d == cid:
                err.append(f"claim {cid}: depends on itself")
        graph[cid] = [d for d in c["deps"] if d != cid]
        if label in P.NEEDS_INVALIDATION:
            if not c["inval"]:
                err.append(f"claim {cid}: '{label}' claim needs an invalidates: field")
        for tok in c["inval"] or []:
            if tok not in P.INVALIDATION and not tok.startswith("project:"):
                err.append(f"claim {cid}: unknown invalidation token '{tok}' "
                           "(define it as 'project:<name>' in project-context.md)")
        if label == "execution_verified":
            vs = P.V_ID.findall(c["line"])
            if not vs:
                err.append(f"claim {cid}: execution_verified must cite a V-### check")
            for v in vs:
                if v in matrix and matrix[v] != "passed":
                    err.append(f"claim {cid}: cites {v} whose Status is '{matrix[v]}', not 'passed'")
        if label in ("source_verified", "serialized_verified") and c["path"] and "*" not in c["path"]:
            target = root / c["path"]
            if not target.exists():
                warn.append(f"claim {cid}: path not found: {c['path']} "
                            "(acceptable only for a partial export; say so in limit:)")
            elif label == "source_verified" and c["symbol"] and target.is_file():
                try:
                    body = target.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    body = None
                if body is not None:
                    for part in [x for x in re.split(r"[.:()<>\s]+", c["symbol"]) if x]:
                        if not re.search(r"\b" + re.escape(part) + r"\b", body):
                            warn.append(f"claim {cid}: symbol '{part}' not found in {c['path']}")
                            break
    for cyc in P.find_cycles(graph):
        err.append("claim dependency cycle: " + " -> ".join(cyc))

    # ---- protected areas, not-inspected ------------------------------------
    ctx = texts.get("project-context.md", "")
    if not any(w == "project-context.md" for i, ws in defs.items() if i.startswith("P-") for w in ws):
        err.append("project-context.md defines no protected area (P-###)")
    if not re.search(r"^#{1,4}[ \t]+.*not[- ]inspected", ctx, re.I | re.M):
        err.append("project-context.md has no 'not inspected' section (canonical home)")

    # ---- findings ----------------------------------------------------------
    findings = P.all_blocks(texts, "F")
    if len(findings) > P.CAPS["findings"]:
        warn.append(f"{len(findings)} detailed findings exceed the cap of {P.CAPS['findings']}")
    for fid, body, name in findings:
        cls = (P.field(body, "Class") or "")
        parts = [x.strip() for x in cls.split("|")]
        if not parts or parts[0] not in P.FINDING_CLASSES:
            err.append(f"finding {fid}: invalid Class '{parts[0] if parts else ''}'")
        for p in parts[1:]:
            k, _, v = p.partition(":")
            k, v = k.strip().lower(), v.strip().lower()
            if k == "confidence" and v not in P.CONFIDENCE:
                err.append(f"finding {fid}: invalid Confidence '{v}'")
            if k == "basis" and v not in P.BASIS:
                err.append(f"finding {fid}: invalid Basis '{v}'")
        if not P.C_ID.search(P.field(body, "Evidence") or ""):
            err.append(f"finding {fid}: Evidence must cite at least one C-###")
        acc = P.field(body, "Smallest follow-up and acceptance") or ""
        vids = P.V_ID.findall(acc)
        if not vids:
            err.append(f"finding {fid}: acceptance must cite a V-### check")
        elif all(matrix.get(v) == "passed" for v in vids):
            warn.append(f"finding {fid}: acceptance check(s) passed; move it to closed findings")
    stubs = P.all_stubs(texts)
    if len(stubs) > P.CAPS["stubs"]:
        warn.append(f"{len(stubs)} overflow stubs exceed the cap of {P.CAPS['stubs']}")
    for sid, rest, name in stubs:
        cols = [x.strip() for x in rest.split("|")]
        if len(cols) < 4:
            err.append(f"stub {sid}: expected 'ID | class | impact | evidence IDs | reason deferred'")
            continue
        if cols[0] not in P.FINDING_CLASSES:
            err.append(f"stub {sid}: invalid class '{cols[0]}'")
        if not P.C_ID.search(cols[2]):
            err.append(f"stub {sid}: evidence column must cite a C-###")

    for fid, vid, name in P.all_closed(texts):
        if matrix.get(vid) != "passed":
            err.append(f"closed finding {fid}: closing check {vid} is '{matrix.get(vid)}', not 'passed'")

    # ---- routes ------------------------------------------------------------
    routes = P.all_blocks(texts, "R")
    if len(routes) > P.CAPS["routes"]:
        warn.append(f"{len(routes)} routes exceed the cap of {P.CAPS['routes']}")
    for rid, body, name in routes:
        if not (P.field(body, "Start") or "").strip():
            err.append(f"route {rid}: missing Start:")
        if not P.V_ID.search(P.field(body, "Checks") or ""):
            err.append(f"route {rid}: Checks: must cite at least one V-###")

    # ---- increments --------------------------------------------------------
    incs = P.all_blocks(texts, "I")
    if len(incs) > P.CAPS["increments"]:
        warn.append(f"{len(incs)} increments exceed the cap of {P.CAPS['increments']}")
    hard = {}
    for iid, body, name in incs:
        st = (P.field(body, "Status") or "").strip()
        if st not in P.INC_STATUSES:
            err.append(f"increment {iid}: invalid Status '{st}'")
        exit_ids = P.V_ID.findall(P.field(body, "Exit check") or "")
        if not exit_ids:
            err.append(f"increment {iid}: Exit check must cite a V-###")
        hard[iid] = P.I_ID.findall(P.field(body, "Hard depends on") or "")
        if st == "done":
            need = set(exit_ids) | set(P.V_ID.findall(P.field(body, "Verification depends on") or ""))
            for v in sorted(need):
                if matrix.get(v) != "passed":
                    err.append(f"increment {iid}: Status 'done' but {v} is '{matrix.get(v)}', not 'passed'")
    for cyc in P.find_cycles(hard):
        err.append("increment hard-dependency cycle: " + " -> ".join(cyc))

    # ---- validation matrix -------------------------------------------------
    vblocks = P.blocks(matrix_text, "V")
    for vid, body in vblocks:
        stat = (P.field(body, "Status") or "").strip("`* ")
        if len(re.findall(r"^[ \t]*Status:", body, re.M)) != 1:
            err.append(f"check {vid}: must have exactly one Status: line")
        if stat not in P.STATUSES:
            err.append(f"check {vid}: invalid Status '{stat}'")
        mode = (P.field(body, "Mode") or "").strip("`* ")
        if mode not in P.MODES:
            err.append(f"check {vid}: invalid Mode '{mode}'")
        obs = (P.field(body, "Observed result and evidence location") or "").strip().lower()
        if stat in ("passed", "failed") and obs in ("", "none", "n/a", "none yet", "-"):
            err.append(f"check {vid}: Status '{stat}' requires an observed result and evidence location")

    # ---- handoff -----------------------------------------------------------
    ho = texts.get("session-handoff.md", "")
    if "see validation matrix" not in ho.lower():
        err.append("session-handoff.md must say 'see validation matrix' instead of restating outcomes")
    elif re.search(r"\b(passed|failed)\b", ho, re.I):
        warn.append("session-handoff.md mentions passed/failed; outcomes belong only in the matrix")

    # ---- index -------------------------------------------------------------
    if isinstance(index, dict):
        check_index(index, root, defs, profile, err, warn)

    for w in warn:
        print(f"WARN  {w}")
    for e in err:
        print(f"ERROR {e}")
    print(f"\n{len(err)} error(s), {len(warn)} warning(s)")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
