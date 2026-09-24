#!/usr/bin/env python3
"""Self-tests for the v1.2.1 tools. Run from anywhere: python tests/run_tests.py

Copies tests/fixtures/good-pack to a temp dir, applies one mutation per case, and checks that
validate_pack.py reports the expected ERROR/WARN. Also exercises suspects.py and bundle.py.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
FIXTURE = KIT / "tests" / "fixtures" / "good-pack"
PACK = "docs/ai-workflow"
CTX, WF, MX = f"{PACK}/project-context.md", f"{PACK}/development-workflow.md", f"{PACK}/validation-matrix.md"
HO, AG, IDX, RD = f"{PACK}/session-handoff.md", f"{PACK}/agent.md", f"{PACK}/index.json", f"{PACK}/README.md"

# (name, edits, level, substring)   edit = (file, "replace"|"append"|"delete", a, b)
CASES = [
    ("stub bad class", [(CTX, "replace", "F-011 | design conflict", "F-011 | bogus class")], "ERROR", "stub F-011: invalid class"),
    ("self dependency", [(CTX, "replace", "initializes _player with 100. | deps: none", "initializes _player with 100. | deps: C-003")], "ERROR", "depends on itself"),
    ("claim cycle", [(CTX, "replace", "clamps Current at zero. | deps: none", "clamps Current at zero. | deps: C-005")], "ERROR", "dependency cycle"),
    ("increment done but check not passed", [(WF, "replace", "Status: not_started", "Status: done")], "ERROR", "Status 'done' but V-001"),
    ("increment hard cycle", [(WF, "append", "", "\n### I-002 Second\nHard depends on: I-001\nSoft depends on: none\nVerification depends on: V-002\nExit check: V-002\nStatus: not_started\n"),
                              (WF, "replace", "Hard depends on: none", "Hard depends on: I-002")], "ERROR", "hard-dependency cycle"),
    ("invalid check status", [(MX, "replace", "Status: not_run", "Status: maybe")], "ERROR", "invalid Status 'maybe'"),
    ("invalid mode", [(MX, "replace", "Mode: PlayMode", "Mode: vibes")], "ERROR", "invalid Mode"),
    ("passed without observation", [(MX, "replace", "Observed result and evidence location: Current was 0; illustrative fixture log at tests/fixtures/README.md", "Observed result and evidence location: none")], "ERROR", "requires an observed result"),
    ("duplicate id", [(CTX, "append", "", "\n- [C-001 | inferred | x | snapshot] dup | deps: none | invalidates: manual_review_required | limit: x\n")], "ERROR", "duplicate ID C-001"),
    ("undefined reference", [(AG, "append", "", "\nSee C-999.\n")], "ERROR", "undefined ID C-999"),
    ("execution claim without check", [(CTX, "replace", "an EditMode run, see V-002.", "an EditMode run.")], "ERROR", "must cite a V-###"),
    ("execution claim cites unpassed check", [(CTX, "replace", "an EditMode run, see V-002.", "an EditMode run, see V-001.")], "ERROR", "not 'passed'"),
    ("missing invalidates", [(CTX, "replace", "| deps: none | invalidates: source_changed | limit: none", "| deps: none | limit: none")], "ERROR", "needs an invalidates"),
    ("unknown invalidation token", [(CTX, "replace", "invalidates: package_or_unity_version_changed", "invalidates: made_up_trigger")], "ERROR", "unknown invalidation token"),
    ("no protected area", [(CTX, "replace", "- [P-001]", "- P-001"), (CTX, "replace", "- [P-002]", "- P-002")], "ERROR", "defines no protected area"),
    ("no not-inspected section", [(CTX, "replace", "## 15. Not inspected", "## 15. Leftovers")], "ERROR", "no 'not inspected' section"),
    ("finding bad class", [(CTX, "replace", "Class: verification gap", "Class: vibes")], "ERROR", "invalid Class"),
    ("route without checks", [(WF, "replace", "Checks: V-001", "Checks: none")], "ERROR", "route R-002"),
    ("closed finding with unpassed check", [(CTX, "replace", "[F-003 | closed | V-002]", "[F-003 | closed | V-001]")], "ERROR", "closed finding F-003"),
    ("handoff without deferral", [(HO, "replace", "see validation matrix", "consult the matrix")], "ERROR", "see validation matrix"),
    ("placeholder left", [(RD, "append", "", "\nREPLACE_ME\n")], "ERROR", "REPLACE_ME"),
    ("agents section too long", [("AGENTS.md", "replace", "<!-- ai-workflow:end -->", "\n".join(f"line {i}" for i in range(160)) + "\n<!-- ai-workflow:end -->")], "ERROR", "exceeds 150"),
    ("agent.md too long", [(AG, "append", "", "\n" + "\n".join(f"line {i}" for i in range(210)))], "ERROR", "exceeds 200"),
    ("missing agent.md", [(AG, "delete", "", "")], "ERROR", "missing required file: agent.md"),
    ("index parse error", [(IDX, "append", "", "}")], "ERROR", "does not parse"),
    ("index status key", [(IDX, "replace", '"profile": "standard",', '"profile": "standard", "status": "ok",')], "ERROR", "forbidden status"),
    ("index missing path_state", [(IDX, "replace", ', "path_state": "existing"', "")], "ERROR", "path_state"),
    ("index existing path missing", [(IDX, "replace", '"path": "Assets/Scenes/Dev.unity"', '"path": "Assets/Scenes/Nope.unity"')], "ERROR", "path not found"),
    ("index entry missing field", [(IDX, "replace", '"certainty": "provisional", "claim_ids": ["C-002"]}', '"certainty": "provisional"}')], "ERROR", "missing field: claim_ids"),
    ("index null version without note", [(IDX, "replace", '"version": "6000.0.0f1"', '"version": null')], "ERROR", "null version requires"),
    ("handoff mentions passed", [(HO, "append", "", "\nV-002 passed\n")], "WARN", "mentions passed/failed"),
    ("closed finding still listed", [(MX, "replace", "Status: not_run\nObserved result and evidence location: none yet\nRemaining limit or next action: schedule with the next Health change",
                                     "Status: passed\nObserved result and evidence location: fixture note\nRemaining limit or next action: none")], "WARN", "move it to closed findings"),
    ("claim symbol missing", [(CTX, "replace", "#Health.TakeDamage | snapshot] TakeDamage clamps", "#Health.Vanish | snapshot] TakeDamage clamps")], "WARN", "symbol 'Vanish' not found"),
    ("claim path missing", [(CTX, "replace", "Assets/Scripts/Game/Bootstrap.cs#Bootstrap", "Assets/Scripts/Game/Boot.cs#Bootstrap")], "WARN", "path not found"),
    ("tier null", [(IDX, "replace", '"tier": "small"', '"tier": null')], "WARN", "tier is null"),
]


def run(cmd):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def apply_edits(root, edits):
    for rel, kind, a, b in edits:
        p = root / rel
        if kind == "delete":
            p.unlink()
            continue
        text = p.read_text(encoding="utf-8")
        if kind == "append":
            text += b
        else:
            if a not in text:
                raise AssertionError(f"test bug: '{a[:40]}' not found in {rel}")
            text = text.replace(a, b, 1)
        p.write_text(text, encoding="utf-8")


def main():
    failures, total = [], 0

    def check(name, ok, detail=""):
        nonlocal total
        total += 1
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n      {detail}"))
        if not ok:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        code, out = run([str(KIT / "tools" / "validate_pack.py"), str(FIXTURE)])
        check("good-pack validates clean", code == 0 and "ERROR" not in out and "WARN" not in out, out)

        for i, (name, edits, level, needle) in enumerate(CASES):
            work = tmp / f"case{i}"
            shutil.copytree(FIXTURE, work)
            apply_edits(work, edits)
            code, out = run([str(KIT / "tools" / "validate_pack.py"), str(work)])
            hit = any(line.startswith(level) and needle in line for line in out.splitlines())
            want_code = 1 if level == "ERROR" else 0
            check(f"{level:5} {name}", hit and code == want_code, f"exit={code}\n{out}")

        # compact profile: routes and increments live in agent.md
        work = tmp / "compact"
        shutil.copytree(FIXTURE, work)
        pack = work / PACK
        wf = (pack / "development-workflow.md").read_text(encoding="utf-8")
        with open(pack / "agent.md", "a", encoding="utf-8") as fh:
            fh.write("\n" + wf)
        (pack / "development-workflow.md").unlink()
        (pack / "README.md").unlink()
        idx = json.loads((pack / "index.json").read_text(encoding="utf-8"))
        idx["profile"] = "compact"
        idx["documents"] = [d for d in idx["documents"] if d["id"] not in ("doc-readme", "doc-workflow")]
        for r in idx["task_routes"]:
            r["document"] = "agent.md"
        (pack / "index.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")
        code, out = run([str(KIT / "tools" / "validate_pack.py"), str(work)])
        check("compact profile validates clean", code == 0 and "ERROR" not in out and "WARN" not in out, out)

        # suspects.py
        code, out = run([str(KIT / "tools" / "suspects.py"), str(FIXTURE), "--changed", "./Assets/Scripts/Game/Bootstrap.cs"])
        check("suspects: direct + transitive", code == 0 and "C-003  direct" in out and "C-002  transitive" in out and "F-001" in out and "V-001" in out, out)
        code, out = run([str(KIT / "tools" / "suspects.py"), str(FIXTURE), "--changed", "x.txt", "--trigger", "package_or_unity_version_changed", "--json"])
        try:
            data = json.loads(out)
            ok = code == 0 and "C-001" in data["direct"] and "C-006" not in data["direct"]
        except json.JSONDecodeError:
            ok = False
        check("suspects: trigger, json, proposed claim ignored", ok, out)
        # git paths: use temp copies so results do not depend on the repository the kit lives in
        nogit = tmp / "nogit"
        shutil.copytree(FIXTURE, nogit)
        r = subprocess.run([sys.executable, str(KIT / "tools" / "suspects.py"), str(nogit), "--since", "HEAD"],
                           capture_output=True, text=True,
                           env={**os.environ, "GIT_CEILING_DIRECTORIES": str(tmp)})
        check("suspects: not a git repo exits 3", r.returncode == 3, r.stdout + r.stderr)
        if shutil.which("git"):
            gitrepo = tmp / "gitrepo"
            shutil.copytree(FIXTURE, gitrepo)
            g = ["git", "-C", str(gitrepo), "-c", "user.email=t@t", "-c", "user.name=t"]
            subprocess.run(g + ["init", "-q"], check=True)
            subprocess.run(g + ["add", "-A"], check=True)
            subprocess.run(g + ["commit", "-qm", "init"], check=True)
            hp = gitrepo / "Assets" / "Scripts" / "Game" / "Health.cs"
            hp.write_text(hp.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8")
            code, out = run([str(KIT / "tools" / "suspects.py"), str(gitrepo), "--since", "HEAD"])
            check("suspects: --since HEAD finds the edited file", code == 0 and "C-004  direct" in out, out)

        # index example must fail until placeholders are replaced
        ex = (KIT / "templates" / "index.example.json").read_text(encoding="utf-8")
        try:
            json.loads(ex)
            check("index.example.json parses and carries REPLACE_ME", "REPLACE_ME" in ex)
        except json.JSONDecodeError as e:
            check("index.example.json parses and carries REPLACE_ME", False, str(e))

        # bundle.py
        bundle = tmp / "bundle.md"
        code, out = run([str(KIT / "tools" / "bundle.py"), str(bundle)])
        text = bundle.read_text(encoding="utf-8") if bundle.exists() else ""
        needed = ["BEGIN file: ENTRYPOINT.md", "BEGIN file: core/09-conditional-contracts.md",
                  "BEGIN file: tools/validate_pack.py", "BEGIN file: tools/packlib.py"]
        check("bundle contains kit files, no tests", code == 0 and all(n in text for n in needed) and "BEGIN file: tests/" not in text, out)

    print(f"\n{total - len(failures)}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
