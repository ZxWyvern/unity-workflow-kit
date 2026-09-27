"""Regression and bounded-context tests; standard library, no Unity installation."""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))
import context as task_context
import packlib as P
import suspects
import validate_pack


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        shutil.copytree(KIT / "tests/fixtures/good-pack", self.root)
        self.pack = self.root / "docs/ai-workflow"

    def validate(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate_pack.main(["validate_pack.py", str(self.root)])
        return code, out.getvalue()


class PackTests(Fixture):
    def test_nonobject_index_rejected(self):
        for value in ([], None, "index", 1):
            with self.subTest(value=value):
                (self.pack / "index.json").write_text(json.dumps(value))
                code, out = self.validate()
                self.assertEqual(code, 1)
                self.assertIn("must be a JSON object", out)

    def test_null_containers_rejected(self):
        path = self.pack / "index.json"
        index = json.loads(path.read_text())
        for key in ("project", "snapshot", "documents", "entry_points", "stack",
                    "task_routes", "refresh_triggers"):
            with self.subTest(key=key):
                path.write_text(json.dumps({**index, key: None}))
                self.assertEqual(self.validate()[0], 1)

    def test_invalid_index_values_do_not_crash(self):
        path = self.pack / "index.json"
        original = path.read_text()
        for section, key, value in (("documents", "path", None),
                                    ("documents", "path_state", []),
                                    ("entry_points", "certainty", []),
                                    ("entry_points", "claim_ids", "C-002"),
                                    ("task_routes", "id", []),
                                    ("task_routes", "check_ids", [None])):
            with self.subTest(section=section, key=key):
                index = json.loads(original)
                index[section][0][key] = value
                path.write_text(json.dumps(index))
                self.assertEqual(self.validate()[0], 1)

    def test_execution_check_outside_matrix_rejected(self):
        path = self.pack / "validation-matrix.md"
        text = path.read_text()
        start, end = text.index("### V-002"), text.index("### V-003")
        agent = self.pack / "agent.md"
        agent.write_text(agent.read_text() + "\n" + text[start:end])
        path.write_text(text[:start] + text[end:])
        code, out = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("definitions belong only in validation-matrix.md", out)
        self.assertIn("claim C-005: cites V-002", out)

    def test_check_requires_runnable_procedure(self):
        path = self.pack / "validation-matrix.md"
        path.write_text("\n".join(line for line in path.read_text().splitlines()
                                  if not line.startswith("Runner or exact manual input path:")))
        self.assertIn("missing Runner or exact manual input path", self.validate()[1])

    def test_context_list_does_not_dump_claims(self):
        out = task_context.select(P.read_pack(self.root, self.pack), [])
        self.assertIn("R-001", out)
        self.assertIn("R-002", out)
        self.assertNotIn("[C-", out)

    def test_context_preserves_dependencies_checks_and_protection(self):
        out = task_context.select(P.read_pack(self.root, self.pack), ["R-002"])
        for item in ("[C-002 |", "[C-003 |", "[P-001]", "[P-002]", "### V-001", "### F-001"):
            self.assertIn(item, out)
        for item in ("[C-004 |", "[C-006 |", "### R-001"):
            self.assertNotIn(item, out)

    def test_context_with_multiple_routes(self):
        out = task_context.select(P.read_pack(self.root, self.pack), ["R-001", "R-002", "R-002"])
        self.assertEqual(out.count("### R-002"), 1)
        self.assertEqual(out.count("[P-001]"), 1)
        self.assertIn("[C-004 |", out)

    def test_context_keeps_check_titles(self):
        out = task_context.select(P.read_pack(self.root, self.pack), ["R-001"])
        self.assertIn("### V-002 Health clamps at zero", out)

    def test_context_related_findings_are_order_independent(self):
        texts = P.read_pack(self.root, self.pack)
        context = texts["project-context.md"]
        context = context.replace("Evidence: C-002, C-003", "Evidence: C-002, C-003, C-004")
        start, mid = context.index("### F-001"), context.index("### F-002")
        end = context.index("## 12b.")
        texts["project-context.md"] = context[:start] + context[mid:end] + context[start:mid] + context[end:]
        out = task_context.select(texts, ["R-002"])
        self.assertIn("### F-002", out)
        self.assertIn("### V-003", out)

    def test_context_unknown_route_rejected(self):
        with self.assertRaisesRegex(ValueError, "undefined routes"):
            task_context.select(P.read_pack(self.root, self.pack), ["R-999"])

    def test_context_missing_dependency_rejected(self):
        texts = P.read_pack(self.root, self.pack)
        texts["project-context.md"] = texts["project-context.md"].replace("deps: C-003", "deps: C-999")
        with self.assertRaisesRegex(ValueError, "undefined claim"):
            task_context.select(texts, ["R-002"])

    def test_context_budget_never_silently_truncates(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = task_context.main(["context.py", str(self.root), "--route", "R-001", "--max-chars", "100"])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Nothing was truncated", err.getvalue())

    def test_context_supports_compact_profile(self):
        texts = P.read_pack(self.root, self.pack)
        texts["agent.md"] += texts.pop("development-workflow.md")
        out = task_context.select(texts, ["R-002"])
        self.assertIn("<!-- agent.md -->", out)
        self.assertIn("[C-003 |", out)

    def test_unrelated_pack_growth_does_not_grow_context(self):
        texts = P.read_pack(self.root, self.pack)
        before = task_context.select(texts, ["R-002"])
        for number in range(100, 900):
            texts["project-context.md"] += (
                f"\n- [C-{number:03} | proposed | Assets/Other.cs | snapshot] unrelated "
                + "detail " * 50 + "| deps: none | limit: not adopted\n")
        self.assertEqual(before, task_context.select(texts, ["R-002"]))


@unittest.skipUnless(shutil.which("git"), "Git is unavailable")
class GitTests(Fixture):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test",
                               "-c", "user.email=test@example.test", "-c", "core.autocrlf=false"]
                              + list(args), check=True, capture_output=True)

    def test_untracked_files_invalidate_directory_claims(self):
        new = self.root / "Assets/Scripts/Game/NewSystem.cs"
        new.write_text("class NewSystem {}")
        path = self.pack / "project-context.md"
        path.write_text(path.read_text() + "\n- [C-008 | source_verified | Assets/Scripts/Game | snapshot] Files. | deps: none | invalidates: source_changed\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = suspects.main(["suspects.py", str(self.root), "--since", "HEAD", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["direct"]["C-008"], "file_under_path_changed")
        self.assertIn("Assets/Scripts/Game/NewSystem.cs", data["changed_files"])

    def test_nonascii_and_space_paths_roundtrip(self):
        relative = "Assets/Scripts/Game/Caf\u00e9 script .cs"
        path = self.root / relative
        path.write_text("before")
        self.git("add", "-A")
        self.git("commit", "-qm", "unicode")
        path.write_text("after")
        changed, error = suspects.git_changed(self.root, "HEAD")
        self.assertEqual(error, "")
        self.assertEqual(changed, [relative])

    def test_ignored_files_are_excluded(self):
        (self.root / ".gitignore").write_text("Library/\n")
        (self.root / "Library").mkdir()
        (self.root / "Library/cache.txt").write_text("generated")
        changed, error = suspects.git_changed(self.root, "HEAD")
        self.assertEqual(error, "")
        self.assertNotIn("Library/cache.txt", changed)

    def test_rename_includes_both_paths(self):
        old = "Assets/Scripts/Game/Health.cs"
        new = "Assets/Scripts/Game/Renamed.cs"
        self.git("mv", old, new)
        changed, error = suspects.git_changed(self.root, "HEAD")
        self.assertEqual(error, "")
        self.assertEqual(set(changed), {old, new})


if __name__ == "__main__":
    unittest.main()
