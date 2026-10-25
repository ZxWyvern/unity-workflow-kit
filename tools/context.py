#!/usr/bin/env python3
"""Print a route list, a bounded task context, or a token-lean source excerpt.

Usage:
    python context.py ROOT [--pack DIR] [--route R-001] [--max-chars 16000]
    python context.py ROOT --file Assets/Scripts/Game/Health.cs [--skeleton]
    python context.py ROOT --file Assets/Scripts/Game/Health.cs --method TakeDamage
    python context.py ROOT --file Assets/Scenes/Dev.unity

Repeat --route to select multiple routes. C# files print a skeleton (using,
types, serialized/public fields, signatures, XML docs); --method prints full
bodies. Unity .unity/.prefab files print a condensed GameObject hierarchy.
Sessions load from sessions/<branch-slug>__<actor-slug>.md: the active branch in full,
other branches as five-line headers. No files are modified.
Read applicable AGENTS.md instructions and agent.md before using this excerpt.
Exit 0 = success, 1 = invalid selection/pack, 2 = context exceeds the output budget.
"""
import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packlib as P


# ---------------------------------------------------------------------------
# C# skeleton extraction (standard library only)
# ---------------------------------------------------------------------------

TYPE_DECL = re.compile(r"\b(class|struct|interface|enum|record)\s+([A-Za-z_]\w*)")
CONTROL = {"if", "for", "foreach", "while", "switch", "using", "lock", "catch",
           "fixed", "checked", "unchecked", "do", "else", "try"}


def _mask_csharp(text):
    """Blank comments and string literals while preserving offsets and newlines."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == "/" and nxt == "*":
            out[i] = out[i + 1] = " "
            i += 2
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            if i < n:
                out[i] = " "
                if i + 1 < n:
                    out[i + 1] = " "
                i += 2
            continue
        if text.startswith('"""', i):
            q = 0
            while i + q < n and text[i + q] == '"':
                q += 1
            for k in range(q):
                out[i + k] = " "
            i += q
            while i < n:
                if text.startswith('"' * q, i):
                    for k in range(q):
                        out[i + k] = " "
                    i += q
                    break
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            continue
        if c == '"':
            verbatim = i > 0 and text[i - 1] == "@"
            out[i] = " "
            i += 1
            while i < n:
                if verbatim and text[i] == '"' and i + 1 < n and text[i + 1] == '"':
                    out[i] = out[i + 1] = " "
                    i += 2
                    continue
                if not verbatim and text[i] == "\\" and i + 1 < n:
                    out[i] = out[i + 1] = " "
                    i += 2
                    continue
                if text[i] == '"':
                    out[i] = " "
                    i += 1
                    break
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            continue
        if c == "'":
            out[i] = " "
            i += 1
            while i < n:
                if text[i] == "\\" and i + 1 < n:
                    out[i] = out[i + 1] = " "
                    i += 2
                    continue
                if text[i] == "'":
                    out[i] = " "
                    i += 1
                    break
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def _line_start(text, index):
    return text.rfind("\n", 0, index) + 1


def _doc_start(text, index, floor=0):
    """Start of the contiguous /// block immediately above a declaration."""
    start = _line_start(text, index)
    if start < floor:
        return index
    while start > 0:
        prev_end = start - 1
        prev_start = _line_start(text, prev_end)
        line = text[prev_start:prev_end].strip()
        if line.startswith("///"):
            start = prev_start
        else:
            break
    return start


def _skip_ws(masked, i):
    n = len(masked)
    while i < n and masked[i].isspace():
        i += 1
    return i


def _match_brace(masked, open_index):
    depth = 0
    for i in range(open_index, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _visibility(header):
    h = re.sub(r"\[[^\]]*\]", " ", header)
    for word in ("public", "protected", "internal", "private"):
        if re.search(r"\b" + word + r"\b", h):
            return word
    return "private"


def _is_serialized(header):
    return bool(re.search(r"\[\s*(?:field:\s*)?(?:SerializeField|SerializeReference)\b", header))


def _method_name(header):
    m = re.search(r"([A-Za-z_]\w*)\s*(?:<[^>{}()]*>)?\s*\(", header)
    if m:
        return m.group(1)
    return "(anonymous)"


def _field_name(header):
    m = re.search(r"([A-Za-z_]\w*)\s*(?:=[^;]*)?;\s*$", header)
    return m.group(1) if m else "?"


def _accessors(text, open_index, close_index):
    body = _mask_csharp(text[open_index + 1:close_index])
    names = []
    for m in re.finditer(r"((?:(?:public|protected|internal|private)\s+)?(?:get|set|init))\b", body):
        names.append(m.group(1).strip())
    return "{ " + " ".join(n + ";" for n in names) + " }" if names else "{ ... }"


def _scan_csharp(text):
    masked = _mask_csharp(text)
    records = []

    def scan(start, end, mode, in_interface=False):
        out = []
        i = start
        while i < end:
            i = _skip_ws(masked, i)
            if i >= end:
                break
            if masked[i] == "#":
                nl = masked.find("\n", i)
                i = end if nl == -1 else nl + 1
                continue
            seg_start = i
            j = i
            paren = bracket = 0
            term, open_index = None, None
            while j < end:
                c = masked[j]
                if c == "(":
                    paren += 1
                elif c == ")":
                    paren = max(0, paren - 1)
                elif c == "[":
                    bracket += 1
                elif c == "]":
                    bracket = max(0, bracket - 1)
                elif paren == 0 and bracket == 0 and c == ";":
                    term = ";"
                    break
                elif paren == 0 and bracket == 0 and c == "{":
                    open_index = j
                    break
                j += 1

            if term == ";":
                header = text[seg_start:j + 1]
                h = masked[seg_start:j].strip()
                if re.match(r"(?:global\s+)?using\b", h):
                    kind, name = "using", ""
                elif re.match(r"\[assembly:", h):
                    kind, name = "assembly", ""
                elif re.search(r"\bnamespace\b", h):
                    kind, name = "namespace-file", ""
                elif re.match(r"delegate\b|.*\bdelegate\b", h):
                    kind = "delegate"
                    name = _method_name(h)
                elif "=>" in h and _method_name(h) != "(anonymous)":
                    kind = "method-expression"
                    name = _method_name(h)
                elif "=>" in h:
                    kind, name = "property-expression", ""
                elif "(" in h:
                    kind = "method-decl"
                    name = _method_name(h)
                else:
                    kind, name = "field", _field_name(h)
                out.append({"kind": kind, "name": name, "doc_start": _doc_start(text, seg_start, start),
                            "decl_start": seg_start, "sig_end": j + 1, "body_open": None,
                            "body_close": None, "header": header, "children": [],
                            "interface": in_interface})
                i = j + 1
                continue

            if open_index is None:
                break
            close = _match_brace(masked, open_index)
            if close is None or close > end:
                close = end - 1
            header = masked[seg_start:open_index]
            h = header.strip()
            type_match = TYPE_DECL.search(header)
            if type_match:
                kind = "enum" if type_match.group(1) == "enum" else "type"
                rec = {"kind": kind, "name": type_match.group(2),
                       "doc_start": _doc_start(text, seg_start, start), "decl_start": seg_start,
                       "sig_end": open_index, "body_open": open_index, "body_close": close,
                       "header": header, "children": [], "interface": in_interface}
                if kind != "enum":
                    rec["children"] = scan(open_index + 1, close, "type",
                                             type_match.group(1) == "interface")
                out.append(rec)
            elif re.search(r"\bnamespace\b", h):
                rec = {"kind": "namespace", "name": "", "doc_start": _doc_start(text, seg_start, start),
                       "decl_start": seg_start, "sig_end": open_index, "body_open": open_index,
                       "body_close": close, "header": header, "children": [],
                       "interface": in_interface}
                rec["children"] = scan(open_index + 1, close, "namespace", in_interface)
                out.append(rec)
            elif "(" in h and not re.match(r"(?:" + "|".join(CONTROL) + r")\b", h):
                out.append({"kind": "method", "name": _method_name(h),
                            "doc_start": _doc_start(text, seg_start, start), "decl_start": seg_start,
                            "sig_end": open_index, "body_open": open_index, "body_close": close,
                            "header": header, "children": [], "interface": in_interface})
            elif "=>" in h:
                out.append({"kind": "property-expression", "name": "",
                            "doc_start": _doc_start(text, seg_start, start), "decl_start": seg_start,
                            "sig_end": open_index, "body_open": open_index, "body_close": close,
                            "header": header, "children": [], "interface": in_interface})
            else:
                out.append({"kind": "property", "name": "",
                            "doc_start": _doc_start(text, seg_start, start), "decl_start": seg_start,
                            "sig_end": open_index, "body_open": open_index, "body_close": close,
                            "header": header, "children": [], "interface": in_interface})
            i = close + 1
        return out

    records = scan(0, len(text), "file")
    return text, masked, records


def _include_record(rec):
    if rec["kind"] in ("using", "namespace-file", "namespace", "type", "enum",
                       "method", "method-decl", "method-expression"):
        return True
    if rec.get("interface"):
        return True
    visibility = _visibility(rec["header"])
    return visibility in ("public", "protected") or _is_serialized(rec["header"])


def _render_csharp(rec, text):
    start = rec["doc_start"]
    if rec["kind"] in ("enum",):
        return text[start:rec["body_close"] + 1].rstrip()
    if rec["kind"] in ("type", "namespace"):
        head = text[start:rec["body_open"]].rstrip()
        indent = " " * (rec["decl_start"] - _line_start(text, rec["decl_start"]))
        inner = [_render_csharp(child, text) for child in rec["children"] if _include_record(child)]
        body = "\n".join(part for part in inner if part)
        return head + " {\n" + body + "\n" + indent + "}" if body else head + " { }"
    if rec["kind"] == "method":
        return text[start:rec["body_open"]].rstrip() + " { ... }"
    if rec["kind"] == "property":
        return (text[start:rec["body_open"]].rstrip() + " "
                + _accessors(text, rec["body_open"], rec["body_close"]))
    return text[start:rec["sig_end"]].rstrip()


def csharp_skeleton(text):
    """Signatures, fields, attributes, and XML docs; implementation bodies omitted."""
    _, _, records = _scan_csharp(text)
    return "\n".join(part for part in (_render_csharp(r, text) for r in records
                                       if _include_record(r)) if part)


def _method_slice(rec, text):
    if rec.get("body_close") is not None:
        return text[rec["doc_start"]:rec["body_close"] + 1].rstrip()
    return text[rec["doc_start"]:rec["sig_end"]].rstrip()


def csharp_methods(text, methods):
    """Full implementation slices for the requested method names (overloads included)."""
    _, _, records = _scan_csharp(text)
    wanted = {m.rsplit(".", 1)[-1] for m in methods}
    found, names = [], set()

    def walk(items):
        for rec in items:
            if rec["kind"] in ("method", "method-decl", "method-expression") and rec["name"] in wanted:
                found.append(_method_slice(rec, text))
                names.add(rec["name"])
            walk(rec["children"])

    walk(records)
    missing = sorted(wanted - names)
    if missing:
        raise ValueError("method(s) not found: " + ", ".join(missing))
    return "\n\n".join(found)


# ---------------------------------------------------------------------------
# Unity YAML condenser (.unity / .prefab)
# ---------------------------------------------------------------------------

UNITY_DOC = re.compile(r"^--- !u!(\d+) &(-?\d+)(?: stripped)?\s*$", re.M)


def _yaml_key(body, key):
    m = re.search(r"^  " + re.escape(key) + r":\s*(.*)$", body, re.M)
    return m.group(1).strip() if m else None


def _yaml_file_ids(body, key):
    m = re.search(r"^  " + re.escape(key) + r":\s*\n((?:  - .*\n?)*)", body, re.M)
    return re.findall(r"fileID:\s*(-?\d+)", m.group(1)) if m else []


def _yaml_vec(value, keys):
    if not value:
        return None
    if value.startswith("{"):
        out = []
        for k in keys:
            m = re.search(r"\b" + k + r":\s*(-?[\d.eE+]+)", value)
            out.append(m.group(1).rstrip(".") if m else "0")
        return ", ".join(out)
    return value


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _quat_euler(value):
    if not value:
        return "0, 0, 0"
    parts = {}
    for k in ("x", "y", "z", "w"):
        m = re.search(r"\b" + k + r":\s*(-?[\d.eE+-]+)", value)
        parts[k] = _num(m.group(1)) if m else 0.0
    x, y, z, w = parts["x"], parts["y"], parts["z"], parts["w"]
    sinr = 2 * (w * x + y * z)
    cosr = 1 - 2 * (x * x + y * y)
    roll = math.degrees(math.atan2(sinr, cosr))
    sinp = 2 * (w * y - z * x)
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, sinp))))
    siny = 2 * (w * z + x * y)
    cosy = 1 - 2 * (y * y + z * z)
    yaw = math.degrees(math.atan2(siny, cosy))
    def fmt(v):
        return f"{round(v, 1):g}"
    return ", ".join(fmt(v) for v in (pitch, yaw, roll))


def _script_guids(root):
    mapping = {}
    for base in (Path(root) / "Assets", Path(root) / "Packages"):
        if not base.is_dir():
            continue
        for meta in base.rglob("*.cs.meta"):
            try:
                text = meta.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            m = re.search(r"^guid:\s*([0-9a-fA-F]{32})\s*$", text, re.M)
            if m:
                mapping[m.group(1).lower()] = meta.name[:-5]
    return mapping


def _parse_unity_docs(text):
    matches = list(UNITY_DOC.finditer(text))
    docs = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end]
        first = next((line for line in body.splitlines() if line.strip()), "")
        type_name = first.split(":", 1)[0].strip() if ":" in first else ""
        docs.append({"class_id": match.group(1), "anchor": match.group(2),
                     "type": type_name, "body": body})
    return docs


def _script_name(script_guids, value):
    if not value:
        return None, None
    m = re.search(r"guid:\s*([0-9a-fA-F]{32})", value)
    guid = m.group(1).lower() if m else None
    return (script_guids.get(guid) if guid else None), guid


def _field_lines(body):
    """Serialized (non-m_) scalar fields for a MonoBehaviour document."""
    fields = []
    for m in re.finditer(r"^  ([A-Za-z_]\w*):[ \t]*(.*)$", body, re.M):
        key, value = m.group(1), m.group(2).strip()
        if key.startswith("m_") or not value or value in ("[]", "{}"):
            continue
        if value.startswith("["):
            continue
        fields.append((key, value))
    return fields


def unity_summary(root, path):
    """Compact GameObject/Transform/MonoBehaviour hierarchy for a scene or prefab."""
    root = Path(root)
    text = path.read_text(encoding="utf-8", errors="replace")
    docs = _parse_unity_docs(text)
    if not docs:
        return f"[Unity YAML without documents: {path.name}]"
    script_guids = _script_guids(root)

    gameobjects, transforms, behaviours, by_anchor = {}, {}, {}, {}
    for doc in docs:
        anchor, body = doc["anchor"], doc["body"]
        by_anchor[anchor] = doc
        if doc["type"] == "GameObject":
            gameobjects[anchor] = {
                "name": (_yaml_key(body, "m_Name") or "").strip("'\"") or "(unnamed)",
                "active": _yaml_key(body, "m_IsActive") != "0",
                "tag": (_yaml_key(body, "m_TagString") or "Untagged").strip("'\""),
                "components": _yaml_file_ids(body, "m_Component"),
            }
        elif doc["type"] == "Transform":
            parent = _yaml_key(body, "m_Father") or ""
            pm = re.search(r"fileID:\s*(-?\d+)", parent)
            transforms[anchor] = {
                "go": (re.search(r"fileID:\s*(-?\d+)", _yaml_key(body, "m_GameObject") or "") or [None, None])[1],
                "parent": pm.group(1) if pm else "0",
                "children": _yaml_file_ids(body, "m_Children"),
                "pos": _yaml_vec(_yaml_key(body, "m_LocalPosition"), ("x", "y", "z")),
                "rot": _quat_euler(_yaml_key(body, "m_LocalRotation")),
                "scale": _yaml_vec(_yaml_key(body, "m_LocalScale"), ("x", "y", "z")),
            }
        elif doc["type"] == "MonoBehaviour":
            go = re.search(r"fileID:\s*(-?\d+)", _yaml_key(body, "m_GameObject") or "")
            script, guid = _script_name(script_guids, _yaml_key(body, "m_Script"))
            behaviours.setdefault(go.group(1) if go else None, []).append({
                "script": script, "guid": guid, "fields": _field_lines(body)})

    def name_of_fileid(file_id):
        doc = by_anchor.get(file_id)
        if not doc:
            return None
        if doc["type"] == "GameObject":
            return gameobjects.get(file_id, {}).get("name")
        if doc["type"] in ("Transform", "MonoBehaviour"):
            go = re.search(r"fileID:\s*(-?\d+)", _yaml_key(doc["body"], "m_GameObject") or "")
            return gameobjects.get(go.group(1), {}).get("name") if go else None
        return None

    go_transform = {t["go"]: a for a, t in transforms.items() if t["go"]}
    roots = []
    for anchor, t in transforms.items():
        if t["parent"] in ("0", "") or t["parent"] not in transforms:
            if t["go"] in gameobjects:
                roots.append(t["go"])
    for go in gameobjects:
        if go not in roots and go not in go_transform:
            roots.append(go)

    def render_field(value):
        m = re.fullmatch(r"\{fileID:\s*(-?\d+)\}", value)
        if m:
            target = name_of_fileid(m.group(1))
            return f"-> {target}" if target else f"-> #{m.group(1)}"
        if len(value) > 60:
            return value[:57] + "..."
        return value

    def render_component(go, transform_anchor):
        entries = []
        t = transforms.get(transform_anchor) if transform_anchor else None
        if t:
            entries.append(f"Transform (Pos: {t['pos'] or '?'} | Rot: {t['rot']} "
                           f"| Scale: {t['scale'] or '?'})")
        for mono in behaviours.get(go, []):
            label = mono["script"] or f"<script {mono['guid'][:8] + '…' if mono['guid'] else '?'}>"
            details = []
            if mono["guid"]:
                details.append("guid: " + mono["guid"][:8])
            fields = mono["fields"][:8]
            details += [f"{k}: {render_field(v)}" for k, v in fields]
            if len(mono["fields"]) > len(fields):
                details.append(f"... +{len(mono['fields']) - len(fields)} fields")
            suffix = " (" + ", ".join(details) + ")" if details else ""
            entries.append(f"MonoBehaviour: {label}{suffix}")
        return entries

    def render_go(go, prefix, last):
        g = gameobjects[go]
        branch = "└──" if last else "├──"
        pad = "    " if last else "│   "
        lines = [f"{prefix}{branch} GameObject: {g['name']} "
                 f"(Active: {'true' if g['active'] else 'false'}, Tag: {g['tag']})"]
        transform_anchor = go_transform.get(go)
        children = transforms[transform_anchor]["children"] if transform_anchor else []
        child_gos = [transforms[c]["go"] for c in children if c in transforms and transforms[c]["go"]]
        entries = render_component(go, transform_anchor)
        for i, entry in enumerate(entries):
            tail = "└──" if i == len(entries) - 1 and not child_gos else "├──"
            lines.append(f"{prefix}{pad}{tail} {entry}")
        for i, child in enumerate(child_gos):
            lines += render_go(child, prefix + pad, i == len(child_gos) - 1)
        return lines

    label = "Scene" if path.suffix == ".unity" else "Prefab"
    seen = set()
    lines = [f"[{label}: {path.relative_to(root.resolve()).as_posix()}]"]
    ordered = [go for go in roots if go in gameobjects]
    for i, go in enumerate(ordered):
        if go in seen:
            continue
        seen.add(go)
        lines += render_go(go, "", i == len(ordered) - 1)
    if len(lines) == 1:
        lines.append("(no GameObject hierarchy found)")
    return "\n".join(lines)


def project_file(root, name):
    root = Path(root).resolve()
    path = Path(name)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"file is outside the repository: {name}") from exc
    if not path.is_file():
        raise ValueError(f"file not found: {name}")
    return path


def file_context(root, name, methods=None):
    path = project_file(root, name)
    rel = path.relative_to(Path(root).resolve()).as_posix()
    if path.suffix == ".cs":
        text = path.read_text(encoding="utf-8", errors="replace")
        if methods:
            return f"# Full method context: {rel}\n\n" + csharp_methods(text, methods)
        return f"# C# skeleton: {rel}\n\n" + csharp_skeleton(text)
    if path.suffix in (".unity", ".prefab"):
        return unity_summary(root, path)
    raise ValueError("--file supports .cs, .unity, and .prefab files")


def select(texts, route_ids, session_branch=None, session_actor=None, include_sessions=True):
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
        "Read applicable AGENTS.md and agent.md first; resume work also reads the active "
        "sessions/<branch-slug>__<actor-slug>.md file.\n"
        "This is an excerpt, not a new source of truth. Check freshness before relying on claims.\n"
        "Other routes, increments, contracts, and uninspected source are not included.\n"
        "Follow referenced IDs outside this excerpt in their canonical files when needed.\n"
    )
    sessions = ""
    if include_sessions:
        state = P.session_context(texts, session_branch, session_actor)
        if state:
            sessions = "\n## Session state\n\n" + state + "\n"
    return intro + sessions + "".join(f"\n<!-- {name} -->\n{body}\n" for _, name, body in selected)


def build_output(root, pack="docs/ai-workflow", routes=None, file=None, methods=None,
                 include_sessions=True, branch=None, actor=None):
    """Shared by the CLI and the MCP server; returns the bounded-context text."""
    root = Path(root).resolve()
    pack_path = (root / pack).resolve() if not Path(pack).is_absolute() else Path(pack).resolve()
    try:
        pack_path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"pack directory must be inside the repository: {pack}") from exc
    texts = P.read_pack(root, pack_path)
    parts = []
    routes = [routes] if isinstance(routes, str) else list(routes or [])
    methods = [methods] if isinstance(methods, str) else list(methods or [])
    if routes or not file:
        parts.append(select(texts, routes,
                            session_branch=branch or P.current_branch(root),
                            session_actor=actor or P.current_actor(root),
                            include_sessions=include_sessions))
    if file:
        file_text = file_context(root, file, methods)
        if include_sessions:
            state = P.session_context(texts, branch or P.current_branch(root),
                                      actor or P.current_actor(root))
            if state:
                file_text = "## Session state\n\n" + state + "\n\n" + file_text
        if parts:
            parts.append("")
        parts.append(file_text)
    return "\n".join(parts).lstrip("\n")


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--pack", default="docs/ai-workflow")
    ap.add_argument("--route", action="append", default=[])
    ap.add_argument("--file", help=".cs skeleton, or condensed .unity/.prefab hierarchy")
    ap.add_argument("--method", action="append", default=[],
                    help="with --file .cs: print these method bodies instead of the skeleton")
    ap.add_argument("--skeleton", action="store_true",
                    help="explicitly request skeleton mode (the default for .cs)")
    ap.add_argument("--no-sessions", action="store_true", help="omit session state")
    ap.add_argument("--branch", help="override branch detection for session selection")
    ap.add_argument("--actor", help="override actor detection for session selection")
    ap.add_argument("--max-chars", type=int, default=16000)
    args = ap.parse_args(argv[1:])
    if args.max_chars < 1:
        ap.error("--max-chars must be positive")
    if args.method and not args.file:
        ap.error("--method requires --file")
    if args.skeleton and not args.file:
        ap.error("--skeleton requires --file")
    if args.skeleton and Path(args.file).suffix != ".cs":
        ap.error("--skeleton only applies to .cs files")
    root = Path(args.root).resolve()
    try:
        output = build_output(root, args.pack, args.route, args.file, args.method,
                              not args.no_sessions, args.branch, args.actor)
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
