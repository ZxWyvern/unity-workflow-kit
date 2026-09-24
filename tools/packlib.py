"""Shared helpers for the workflow-pack tools (v1.2.1). Standard library only."""
import re
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
