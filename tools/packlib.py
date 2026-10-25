"""Shared helpers for the workflow-pack tools (v1.4.0). Standard library only."""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

LABELS = {"source_verified", "serialized_verified", "execution_verified",
          "inferred", "proposed", "unknown"}
NEEDS_INVALIDATION = LABELS - {"proposed", "unknown"}
STATUSES = {"passed", "failed", "not_run", "not_applicable"}
MODES = {"static", "EditMode", "PlayMode", "editor-interactive", "player-build", "profiler"}
INC_STATUSES = {"not_started", "in_progress", "done"}
PATH_STATES = {"existing", "generated", "proposed"}
PROFILES = {"compact", "standard", "extended"}
TIERS = {"small", "medium", "large"}
CERTAINTY = {"confirmed", "provisional", "ambiguous"}
CONFIDENCE = {"high", "medium", "low"}
BASIS = {"runtime", "static", "uncertain"}
FINDING_CLASSES = {"observed defect", "source-supported risk", "design conflict",
                   "missing integration/content", "verification gap", "optional improvement"}
INVALIDATION = {
    "source_changed", "serialized_dependency_changed", "package_or_unity_version_changed",
    "entry_path_changed", "design_authority_changed", "build_configuration_changed",
    "test_environment_changed", "runtime_dependency_changed", "save_schema_changed",
    "toolchain_changed", "manual_review_required",
}
CAPS = {"findings": 10, "stubs": 20, "routes": 8, "increments": 5}
AGENTS_BEGIN = "<!-- ai-workflow:begin -->"
AGENTS_END = "<!-- ai-workflow:end -->"
AGENTS_SECTION_LIMIT = 150
AGENT_MD_LIMIT = 200
SESSION_DIR = "sessions"
LEGACY_HANDOFF = "session-handoff.md"
SESSION_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*__[a-z0-9][a-z0-9._-]*\.md$")
HANDOFF_PHRASE = "see validation matrix"
SESSION_HEADER_LINES = 5
DOC_PURPOSES = {
    "agent.md": "portable agent profile",
    "project-context.md": "canonical facts",
    "development-workflow.md": "routes and increments",
    "validation-matrix.md": "checks and status",
    "README.md": "install and use",
    LEGACY_HANDOFF: "legacy current session state (deprecated)",
}
DOC_IDS = {
    "agent.md": "doc-agent",
    "project-context.md": "doc-context",
    "development-workflow.md": "doc-workflow",
    "validation-matrix.md": "doc-matrix",
    "README.md": "doc-readme",
    LEGACY_HANDOFF: "doc-handoff",
}

CLAIM_DEF = re.compile(r"^[ \t]*(?:[-*][ \t]*)?\[(C-\d{3})[ \t]*\|[ \t]*([a-z_]+)[ \t]*\|([^\]\n]+)\][^\n]*", re.M)
PROT_DEF = re.compile(r"^[ \t]*(?:[-*][ \t]*)?\[(P-\d{3})\][^\n]*", re.M)
CLOSED_DEF = re.compile(r"^[ \t]*(?:[-*][ \t]*)?\[(F-\d{3})[ \t]*\|[ \t]*closed[ \t]*\|[ \t]*(V-\d{3})[ \t]*\][^\n]*", re.M)
STUB_DEF = re.compile(r"^[ \t]*(?:[-*][ \t]*)?(F-\d{3})[ \t]*\|([^\n]*)", re.M)
ANY_ID = re.compile(r"\b([CFVRIP]-\d{3})\b")
V_ID = re.compile(r"\bV-\d{3}\b")
C_ID = re.compile(r"\bC-\d{3}\b")
I_ID = re.compile(r"\bI-\d{3}\b")
DEPS = re.compile(r"\|\s*deps:\s*([^|\n]+)", re.I)
INVAL = re.compile(r"\|\s*invalidates:\s*([^|\n]+)", re.I)
ANY_HEAD = re.compile(r"^#{1,4}[ \t]+\S", re.M)


def _head_rx(prefix):
    return re.compile(r"^#{2,4}[ \t]+(%s-\d{3})\b[^\n]*$" % prefix, re.M)


def read_pack(root, pack):
    """Return {name: text}. Root AGENTS.md is keyed 'AGENTS.md'; pack files by pack-relative path."""
    texts = {}
    agents = Path(root) / "AGENTS.md"
    if agents.is_file():
        texts["AGENTS.md"] = agents.read_text(encoding="utf-8", errors="replace")
    pack = Path(pack)
    if pack.is_dir():
        for p in sorted(pack.rglob("*")):
            rel = p.relative_to(pack)
            if p.is_file() and p.suffix in (".md", ".json") and "tools" not in rel.parts:
                texts[rel.as_posix()] = p.read_text(encoding="utf-8", errors="replace")
    return texts


def agents_section(text):
    """Marked workflow section of AGENTS.md, or None if markers are absent."""
    a, b = text.find(AGENTS_BEGIN), text.find(AGENTS_END)
    if a == -1 or b == -1 or b < a:
        return None
    return text[a + len(AGENTS_BEGIN):b]


def scan_text(name, text):
    """Text that participates in ID scanning (AGENTS.md: marked section only)."""
    if name == "AGENTS.md":
        return agents_section(text) or ""
    return text


def field(body, label):
    m = re.search(r"^[ \t]*%s:[ \t]*(.*?)[ \t]*$" % re.escape(label), body, re.M | re.I)
    return m.group(1) if m else None


def blocks(text, prefix):
    out = []
    for m in _head_rx(prefix).finditer(text):
        nxt = ANY_HEAD.search(text, m.end())
        out.append((m.group(1), text[m.end(): nxt.start() if nxt else len(text)]))
    return out


def all_blocks(texts, prefix):
    res = []
    for name, text in texts.items():
        if name.endswith(".json"):
            continue
        for bid, body in blocks(scan_text(name, text), prefix):
            res.append((bid, body, name))
    return res


def all_stubs(texts):
    res = []
    for name, text in texts.items():
        if name.endswith(".json"):
            continue
        for m in STUB_DEF.finditer(scan_text(name, text)):
            res.append((m.group(1), m.group(2), name))
    return res


def all_closed(texts):
    res = []
    for name, text in texts.items():
        if name.endswith(".json"):
            continue
        for m in CLOSED_DEF.finditer(scan_text(name, text)):
            res.append((m.group(1), m.group(2), name))
    return res


def git_output(root, *args):
    """Run git without a shell; return stdout or None when unavailable/failed."""
    try:
        r = subprocess.run(["git", "-C", str(root)] + list(args),
                           capture_output=True, text=True, errors="replace", timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def slug(value, fallback="unknown"):
    """Filesystem- and git-safe lowercase token for branch/actor names."""
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip())
    value = re.sub(r"-{2,}", "-", value).strip("-._")
    return value.lower()[:64] or fallback


def current_branch(root):
    """Active branch name; UWK_BRANCH wins, then git, then 'detached'/None."""
    env = os.environ.get("UWK_BRANCH")
    if env:
        return env
    out = git_output(root, "rev-parse", "--abbrev-ref", "HEAD")
    if out and out != "HEAD":
        return out
    out = git_output(root, "symbolic-ref", "--short", "HEAD")
    if out:
        return out
    return "detached" if git_output(root, "rev-parse", "--git-dir") else None


def current_actor(root):
    """Actor name; UWK_ACTOR wins, then git config user.name, then USER, then 'agent'."""
    env = os.environ.get("UWK_ACTOR")
    if env:
        return env
    out = git_output(root, "config", "user.name")
    if out:
        return out
    return os.environ.get("USERNAME") or os.environ.get("USER") or "agent"


def session_relpath(branch, actor):
    return f"{SESSION_DIR}/{slug(branch)}__{slug(actor)}.md"


def session_names(texts):
    return sorted(n for n in texts
                  if n.startswith(SESSION_DIR + "/") and n.endswith(".md"))


def session_summary(text, limit=SESSION_HEADER_LINES):
    """Bounded header/summary for a session owned by another branch."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max(1, limit)])


def session_context(texts, branch=None, actor=None, header_lines=SESSION_HEADER_LINES):
    """Active-branch sessions in full, other branches as short headers.

    Returns plain text without a leading heading; an empty string when the pack
    has no session state at all.
    """
    names = session_names(texts)
    if names:
        prefix = slug(branch) + "__" if branch else None
        active = [n for n in names if prefix and n.rsplit("/", 1)[-1].startswith(prefix)]
        if not active and len(names) == 1:
            active = names
        others = [n for n in names if n not in active]
        parts = []
        if branch:
            who = actor or "unknown actor"
            parts.append(f"Active branch: {branch} (actor: {who})")
        for name in active:
            parts.append(f"<!-- active session: {name} -->\n{texts[name].strip()}")
        if others:
            parts.append("Other branches (headers only; do not edit their sessions):")
            for name in others:
                parts.append(f"<!-- {name} -->\n{session_summary(texts[name], header_lines)}")
        return "\n\n".join(parts)
    if LEGACY_HANDOFF in texts:
        return ("<!-- legacy session-handoff.md; migrate to sessions/<branch-slug>__<actor-slug>.md -->\n"
                + texts[LEGACY_HANDOFF].strip())
    return ""


def session_problems(text):
    problems = []
    if HANDOFF_PHRASE not in text.lower():
        problems.append(f"must say '{HANDOFF_PHRASE}' instead of restating outcomes")
    return problems


def _pack_relpath(root, pack):
    root = Path(root).resolve()
    pack = Path(pack).resolve()
    try:
        return pack.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"pack directory must be inside the repository: {pack}") from exc


def _document_id(rel):
    name = rel.rsplit("/", 1)[-1]
    if name in DOC_IDS:
        return DOC_IDS[name]
    stem = re.sub(r"[^a-z0-9]+", "-", name.rsplit(".", 1)[0].lower()).strip("-")
    prefix = "" if "/" not in rel else re.sub(r"[^a-z0-9]+", "-", rel.rsplit("/", 1)[0].lower()) + "-"
    return "doc-" + prefix + (stem or "document")


def build_documents(root, pack):
    """Deterministically list every pack document plus the sharded session store."""
    pack = Path(pack)
    pack_rel = _pack_relpath(root, pack)
    docs = []
    for path in sorted(pack.rglob("*.md")):
        rel = path.relative_to(pack)
        if "tools" in rel.parts or rel.parts[0] == SESSION_DIR:
            continue
        rel_posix = rel.as_posix()
        docs.append({
            "id": _document_id(rel_posix),
            "path": f"{pack_rel}/{rel_posix}" if pack_rel != "." else rel_posix,
            "path_state": "generated",
            "purpose": DOC_PURPOSES.get(rel.name, "workflow document"),
        })
    sessions = pack / SESSION_DIR
    if sessions.is_dir():
        docs.append({
            "id": "doc-sessions",
            "path": f"{pack_rel}/{SESSION_DIR}" if pack_rel != "." else SESSION_DIR,
            "path_state": "generated",
            "purpose": "sharded session handoffs (one file per branch and actor)",
        })
    docs.sort(key=lambda d: d["path"])
    return docs


def render_index(index):
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def refresh_index(root, pack, update_snapshot=False, today=None):
    """Rebuild index.json documents from the pack scan. Returns (path, changed)."""
    pack = Path(pack)
    index_path = pack / "index.json"
    if not index_path.is_file():
        raise ValueError(f"index.json not found at {index_path}; create the pack first")
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"index.json cannot be refreshed: {exc}") from exc
    if not isinstance(index, dict):
        raise ValueError("index.json must be a JSON object")
    index.setdefault("format", "unity-project-workflow-index")
    index.setdefault("format_version", "1.2")
    index.setdefault("workflow_version", "1")
    index.setdefault("profile", "compact")
    index["documents"] = build_documents(root, pack)
    if update_snapshot:
        snap = index.get("snapshot")
        if not isinstance(snap, dict):
            snap = {}
        snap["observed_date"] = today or date.today().isoformat()
        revision = git_output(root, "rev-parse", "HEAD")
        if revision is not None:
            snap["revision"] = revision
            dirty = git_output(root, "status", "--porcelain")
            snap["dirty"] = bool(dirty)
        index["snapshot"] = snap
    text = render_index(index)
    current = index_path.read_text(encoding="utf-8")
    changed = current != text
    if changed:
        tmp = index_path.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(index_path)
    return index_path, changed


def save_handoff(root, pack, content, actor=None, branch=None, require_phrase=True):
    """Write the active actor's sharded session file and refresh index.json."""
    if not isinstance(content, str):
        raise ValueError("session content must be a string")
    content = content.strip()
    if not content:
        raise ValueError("session content is empty")
    if require_phrase and HANDOFF_PHRASE not in content.lower():
        raise ValueError(f"session content must contain '{HANDOFF_PHRASE}'")
    branch = branch or current_branch(root) or "detached"
    actor = actor or current_actor(root)
    root = Path(root).resolve()
    pack = Path(pack)
    pack = (root / pack).resolve() if not pack.is_absolute() else pack.resolve()
    try:
        pack.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"pack directory must be inside the repository: {pack}") from exc
    if not (pack / "index.json").is_file():
        raise ValueError(f"index.json not found at {pack / 'index.json'}; create the pack first")
    rel = session_relpath(branch, actor)
    path = pack / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)
    index_path, changed = refresh_index(root, pack)
    return path, index_path, changed


def collect_defs(texts):
    """ID -> list of files that define it (claims, F/V/R/I headings, F stubs, P protected areas)."""
    defs = {}
    for name, text in texts.items():
        if name.endswith(".json"):
            continue
        scan = scan_text(name, text)
        for m in CLAIM_DEF.finditer(scan):
            defs.setdefault(m.group(1), []).append(name)
        for m in PROT_DEF.finditer(scan):
            defs.setdefault(m.group(1), []).append(name)
        for pref in "FVRI":
            for m in _head_rx(pref).finditer(scan):
                defs.setdefault(m.group(1), []).append(name)
        for m in STUB_DEF.finditer(scan):
            defs.setdefault(m.group(1), []).append(name)
        for m in CLOSED_DEF.finditer(scan):
            defs.setdefault(m.group(1), []).append(name)
    return defs


def parse_claims(texts):
    claims = {}
    for name, text in texts.items():
        if name.endswith(".json"):
            continue
        for m in CLAIM_DEF.finditer(scan_text(name, text)):
            cid, label, rest, line = m.group(1), m.group(2), m.group(3), m.group(0)
            parts = [x.strip() for x in rest.split("|")]
            path = parts[0] if parts else ""
            dm, im = DEPS.search(line), INVAL.search(line)
            claims.setdefault(cid, {
                "file": name, "label": label, "line": line.strip(),
                "path": path.split("#", 1)[0].strip(),
                "symbol": path.split("#", 1)[1].strip() if "#" in path else "",
                "deps_raw": dm.group(1).strip() if dm else None,
                "deps": [] if (not dm or dm.group(1).strip().lower() == "none")
                        else [x.strip() for x in dm.group(1).split(",") if x.strip()],
                "inval": None if not im else [x.strip() for x in im.group(1).split(",") if x.strip()],
            })
    return claims


def matrix_status(matrix_text):
    return {bid: field(body, "Status") for bid, body in blocks(matrix_text, "V")}


def find_cycles(graph):
    """graph: node -> iterable of nodes. Returns a list of cycles (each a list of nodes)."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    stack, cycles = [], []

    def visit(n):
        color[n] = GREY
        stack.append(n)
        for d in graph.get(n, ()):
            if d not in color:
                continue
            if color[d] == GREY:
                cycles.append(stack[stack.index(d):] + [d])
            elif color[d] == WHITE:
                visit(d)
        stack.pop()
        color[n] = BLACK

    for n in list(graph):
        if color[n] == WHITE:
            visit(n)
    return cycles


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Session and index helpers for a workflow pack.")
    sub = ap.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("root", nargs="?", default=".")
        p.add_argument("--pack", default="docs/ai-workflow")

    idx = sub.add_parser("index", help="rebuild index.json deterministically")
    common(idx)
    idx.add_argument("--check", action="store_true", help="exit 1 instead of writing when stale")
    idx.add_argument("--snapshot", action="store_true", help="also refresh date/revision/dirty")

    ses = sub.add_parser("session", help="print the active session file path")
    common(ses)
    ses.add_argument("--branch")
    ses.add_argument("--actor")

    save = sub.add_parser("save-handoff", help="write the active session file from stdin or a file")
    common(save)
    save.add_argument("--actor")
    save.add_argument("--branch")
    save.add_argument("--content-file", default="-")
    save.add_argument("--no-phrase-check", action="store_true")

    a = ap.parse_args(argv[1:])
    root = Path(a.root).resolve()
    pack = root / a.pack
    try:
        if a.command == "session":
            print(pack / session_relpath(a.branch or current_branch(root) or "detached",
                                         a.actor or current_actor(root)))
            return 0
        if a.command == "save-handoff":
            if a.content_file == "-":
                try:
                    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
                except (AttributeError, ValueError):
                    pass
                content = sys.stdin.read()
            else:
                content = Path(a.content_file).read_text(encoding="utf-8")
            path, index_path, changed = save_handoff(
                root, pack, content, a.actor, a.branch, not a.no_phrase_check)
            print(f"wrote {path.relative_to(root).as_posix()}")
            print(f"index.json {'updated' if changed else 'already current'} ({index_path.relative_to(root).as_posix()})")
            return 0
        if a.check:
            index_path = pack / "index.json"
            if not index_path.is_file():
                print("index.json not found", file=sys.stderr)
                return 1
            before = index_path.read_text(encoding="utf-8")
            index = json.loads(before)
            if not isinstance(index, dict):
                print("index.json must be a JSON object", file=sys.stderr)
                return 1
            try:
                index["documents"] = build_documents(root, pack)
                text = render_index(index)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            if text != before:
                print("index.json is stale; run: python tools/packlib.py index . --pack <pack>")
                return 1
            print("index.json is current")
            return 0
        index_path, changed = refresh_index(root, pack, a.snapshot)
        rel = index_path.relative_to(root).as_posix()
        print(f"{rel} {'updated' if changed else 'already current'}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
