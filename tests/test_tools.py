"""Regression and bounded-context tests; standard library, no Unity installation."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))
import context as task_context
import install_hooks
import mcp_server
import packlib as P
import suspects
import validate_pack
import verify_compile


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


class TokenDietTests(Fixture):
    def _text(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def test_csharp_skeleton_hides_bodies_and_keeps_contract(self):
        skeleton = task_context.csharp_skeleton(
            self._text("Assets/Scripts/Game/Health.cs"))
        self.assertIn("public sealed class Health", skeleton)
        self.assertIn("public void TakeDamage(int amount) { ... }", skeleton)
        self.assertIn("public int Current { get; private set; }", skeleton)
        self.assertNotIn("Mathf.Max", skeleton)

    def test_csharp_skeleton_keeps_serialized_fields_and_docs(self):
        text = ('namespace N {\n    public class C {\n'
                '        /// <summary>Speed.</summary>\n'
                '        [SerializeField, Range(0, 10)] private float _speed;\n'
                '        private float _hidden;\n'
                '        public float Speed => _speed;\n    }\n}\n')
        skeleton = task_context.csharp_skeleton(text)
        self.assertIn("/// <summary>Speed.</summary>", skeleton)
        self.assertIn("[SerializeField, Range(0, 10)] private float _speed;", skeleton)
        self.assertNotIn("_hidden", skeleton)
        self.assertIn("public float Speed => _speed;", skeleton)

    def test_csharp_skeleton_keeps_interface_members(self):
        skeleton = task_context.csharp_skeleton(
            "public interface IHit { void Apply(int amount); int Value { get; } }")
        self.assertIn("void Apply(int amount);", skeleton)
        self.assertIn("int Value { get; }", skeleton)

    def test_raw_and_verbatim_strings_do_not_break_skeletons(self):
        text = ('public class C {\n'
                '    public string Raw = """{ not a brace } """;\n'
                '    public string Path = @"C:\\tmp";\n'
                '    public void Run() { }\n}')
        skeleton = task_context.csharp_skeleton(text)
        self.assertIn("public void Run() { ... }", skeleton)
        self.assertIn('"""', skeleton)

    def test_full_method_returns_the_body(self):
        text = self._text("Assets/Scripts/Game/Health.cs")
        method = task_context.csharp_methods(text, ["Health.TakeDamage"])
        self.assertIn("Current = Mathf.Max(0, Current - amount);", method)
        with self.assertRaisesRegex(ValueError, "method\\(s\\) not found"):
            task_context.csharp_methods(text, ["Vanish"])

    def test_unity_scene_condenser_builds_hierarchy(self):
        out = task_context.file_context(self.root, "Assets/Scenes/Dev.unity")
        self.assertIn("[Scene: Assets/Scenes/Dev.unity]", out)
        self.assertIn("GameObject: Bootstrap", out)
        self.assertIn("GameObject: Player", out)
        self.assertIn("MonoBehaviour: Health.cs", out)
        self.assertIn("_maxHealth: 100", out)
        self.assertIn("_player: -> Player", out)
        self.assertNotIn("%YAML", out)
        self.assertNotIn("m_ObjectHideFlags", out)

    def test_prefab_uses_the_same_condensed_hierarchy(self):
        source = self.root / "Assets/Scenes/Dev.unity"
        target = self.root / "Assets/Scenes/Dev.prefab"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        out = task_context.file_context(self.root, "Assets/Scenes/Dev.prefab")
        self.assertIn("[Prefab: Assets/Scenes/Dev.prefab]", out)
        self.assertIn("GameObject: Player", out)
        self.assertIn("MonoBehaviour: Health.cs", out)

    def test_file_outside_repository_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            task_context.file_context(self.root, "../outside.cs")

    def test_context_cli_file_mode_obeys_budget(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = task_context.main(["context.py", str(self.root), "--file",
                                      "Assets/Scripts/Game/Health.cs",
                                      "--max-chars", "10"])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Nothing was truncated", err.getvalue())


class SessionTests(Fixture):
    def write_session(self, name, lines):
        path = self.pack / "sessions" / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_active_branch_full_and_other_branch_header_only(self):
        self.write_session("feat-combat__dev-andi.md", [
            "# Session feat-combat__dev-andi",
            "Date: 2026-10-01",
            "Goal: combat",
            "Next: V-004",
            "Blockers: none",
            "Coverage: see validation matrix",
            "Long detail that must not leak from another branch.",
        ])
        texts = P.read_pack(self.root, self.pack)
        out = P.session_context(texts, "feat/combat", "dev-andi")
        self.assertIn("active session: sessions/feat-combat__dev-andi.md", out)
        self.assertIn("Long detail that must not leak", out)
        self.assertIn("main__fixture.md", out)
        self.assertNotIn("Resume instructions and isolated test data", out)

    def test_legacy_handoff_is_loaded_when_sessions_are_absent(self):
        legacy = self.pack / "session-handoff.md"
        legacy.write_text("# Legacy\nDate: now\nCoverage: see validation matrix\n",
                          encoding="utf-8")
        shutil.rmtree(self.pack / "sessions")
        texts = P.read_pack(self.root, self.pack)
        out = P.session_context(texts, "main", "fixture")
        self.assertIn("legacy session-handoff.md", out)
        self.assertIn("Coverage: see validation matrix", out)

    def test_save_handoff_creates_isolated_file_and_refreshes_index(self):
        content = ("# Session work\nDate: 2026-10-01\nBranch: feat/combat\n"
                   "Next: implement damage\nCoverage: see validation matrix\n")
        with mock.patch.dict(os.environ, {"UWK_BRANCH": "feat/combat",
                                          "UWK_ACTOR": "dev-andi"}):
            path, index_path, changed = P.save_handoff(self.root, self.pack, content)
        self.assertEqual(path.name, "feat-combat__dev-andi.md")
        self.assertTrue(path.is_file())
        self.assertTrue(index_path.is_file())
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertIn("doc-sessions", {d["id"] for d in index["documents"]})
        self.assertFalse(P.refresh_index(self.root, self.pack)[1])
        self.assertFalse(changed)

    def test_save_handoff_requires_the_handoff_phrase(self):
        with self.assertRaisesRegex(ValueError, "see validation matrix"):
            P.save_handoff(self.root, self.pack, "# no phrase", "a", "main")

    def test_validator_rejects_nested_session_files(self):
        nested = self.pack / "sessions/team/main__fixture.md"
        nested.parent.mkdir(parents=True)
        shutil.copyfile(self.pack / "sessions/main__fixture.md", nested)
        code, out = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("must live directly under sessions/", out)

    def test_index_rebuild_lists_new_documents_deterministically(self):
        contracts = self.pack / "contracts"
        contracts.mkdir()
        (contracts / "network.md").write_text("# Network contract\n", encoding="utf-8")
        path, changed = P.refresh_index(self.root, self.pack)
        self.assertTrue(changed)
        index = json.loads(path.read_text(encoding="utf-8"))
        paths = {d["path"] for d in index["documents"]}
        self.assertIn("docs/ai-workflow/contracts/network.md", paths)
        self.assertIn("docs/ai-workflow/sessions", paths)
        self.assertFalse(P.refresh_index(self.root, self.pack)[1])

    def test_packlib_index_check_reports_current(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = P.main(["packlib.py", "index", str(self.root),
                           "--pack", "docs/ai-workflow", "--check"])
        self.assertEqual(code, 0)
        self.assertIn("is current", out.getvalue())


@unittest.skipUnless(shutil.which("git"), "Git is unavailable")
class HookInstallTests(Fixture):
    def setUp(self):
        super().setUp()
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)

    def install(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = install_hooks.main(["install_hooks.py", str(self.root)] + list(args))
        return code, out.getvalue(), err.getvalue()

    def test_installer_copies_hooks_and_configures_merge_driver(self):
        code, out, err = self.install()
        self.assertEqual(code, 0, err)
        hooks = self.root / ".git/hooks"
        for name in install_hooks.HOOKS:
            self.assertTrue((hooks / name).is_file(), name)
            self.assertIn(install_hooks.MARKER, (hooks / name).read_text(encoding="utf-8"))
            self.assertNotIn(b"\r\n", (hooks / name).read_bytes(), name)
            if os.name == "posix":
                self.assertTrue(os.access(hooks / name, os.X_OK), name)
        driver = subprocess.run(["git", "-C", str(self.root), "config", "--get",
                                 "merge.ours.driver"], capture_output=True, text=True)
        self.assertEqual(driver.stdout.strip(), "true")
        attributes = (self.root / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("docs/ai-workflow/index.json merge=ours", attributes)
        code, out, err = self.install()
        self.assertEqual(code, 0, err)
        self.assertEqual((self.root / ".gitattributes").read_text(encoding="utf-8"), attributes)

    def test_installer_refuses_to_clobber_a_user_hook(self):
        hooks = self.root / ".git/hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        user = hooks / "pre-commit"
        user.write_text("#!/bin/sh\necho user\n", encoding="utf-8")
        code, out, err = self.install()
        self.assertEqual(code, 1)
        self.assertIn("SKIP existing non-kit hook", err)
        self.assertEqual(user.read_text(encoding="utf-8"), "#!/bin/sh\necho user\n")
        self.assertTrue((hooks / "post-merge").is_file())

    def test_custom_pack_path_is_recorded_for_hooks(self):
        code, out, err = self.install("--pack", "custom/workflow", "--no-merge-driver")
        self.assertEqual(code, 0, err)
        marker = self.root / ".git/hooks/uwk_pack_path"
        self.assertEqual(marker.read_text(encoding="utf-8").strip(), "custom/workflow")


class CompileTests(unittest.TestCase):
    def test_success_summary_is_one_line(self):
        self.assertEqual(verify_compile.summarize({"status": "ok", "errors": [], "warnings": []}),
                         ["COMPILE_STATUS: OK (0 errors)"])

    def test_filtered_run_keeps_only_cs_diagnostics(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="Build started\nAssets/A.cs(1,2): error CS0103: missing name\n"
                   "noise line\nAssets/A.cs(9,9): warning CS0168: unused\n",
            stderr="")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "Game.csproj"
            project.write_text("<Project />", encoding="utf-8")
            with mock.patch.object(verify_compile.shutil, "which", return_value="dotnet"), \
                    mock.patch.object(verify_compile.subprocess, "run", return_value=fake):
                result = verify_compile.run_compile(root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("CS0103", result["errors"][0])
        self.assertEqual(len(result["warnings"]), 1)
        self.assertNotIn("noise line", "\n".join(result["errors"] + result["warnings"]))

    def test_truncated_diagnostics_are_announced(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="\n".join(f"Assets/A.cs({i},1): error CS0103: missing {i}"
                             for i in range(45)), stderr="")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Game.csproj").write_text("<Project />", encoding="utf-8")
            with mock.patch.object(verify_compile.shutil, "which", return_value="dotnet"), \
                    mock.patch.object(verify_compile.subprocess, "run", return_value=fake):
                result = verify_compile.run_compile(root)
        summary = verify_compile.summarize(result)
        self.assertEqual(result["error_count"], 45)
        self.assertTrue(any("TRUNCATED" in line for line in summary))

    def test_project_outside_the_repository_is_not_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            outside = Path(tmp) / "Outside.csproj"
            outside.write_text("<Project />", encoding="utf-8")
            with mock.patch.object(verify_compile.shutil, "which", return_value="dotnet"):
                result = verify_compile.run_compile(root, outside)
        self.assertEqual(result["status"], "no_project")

    def test_generated_directories_are_not_project_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Library").mkdir()
            (root / "Library/Ignored.csproj").write_text("", encoding="utf-8")
            (root / "Game.sln").write_text("", encoding="utf-8")
            projects = verify_compile.find_projects(root)
        self.assertEqual([p[1] for p in projects], ["Game.sln"])


class McpTests(Fixture):
    def call(self, name, arguments):
        return mcp_server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}})

    def test_initialize_and_tool_list(self):
        response = mcp_server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}})
        self.assertEqual(response["result"]["protocolVersion"], "2024-11-05")
        tools = mcp_server.handle({
            "jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        self.assertEqual({t["name"] for t in tools},
                         {"uwk_get_context", "uwk_find_suspects",
                          "uwk_validate", "uwk_save_handoff"})
        self.assertIsNone(mcp_server.handle({"jsonrpc": "2.0",
                                             "method": "notifications/initialized"}))

    def test_get_context_route_and_skeleton(self):
        response = self.call("uwk_get_context", {"root": str(self.root), "route": "R-002"})
        text = response["result"]["content"][0]["text"]
        self.assertFalse(response["result"]["isError"])
        self.assertIn("### R-002", text)
        self.assertIn("Session state", text)
        response = self.call("uwk_get_context", {
            "root": str(self.root), "file": "Assets/Scripts/Game/Health.cs"})
        text = response["result"]["content"][0]["text"]
        self.assertIn("TakeDamage(int amount) { ... }", text)
        self.assertNotIn("Mathf.Max", text)

    def test_find_suspects_and_validate(self):
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.root.parent)}):
            response = self.call("uwk_find_suspects", {
                "root": str(self.root), "changed": ["Assets/Scripts/Game/Health.cs"]})
        text = response["result"]["content"][0]["text"]
        self.assertIn('"C-004"', text)
        response = self.call("uwk_validate", {"root": str(self.root)})
        self.assertFalse(response["result"]["isError"])
        self.assertIn("0 error(s)", response["result"]["content"][0]["text"])

    def test_save_handoff_tool(self):
        content = ("# Session MCP\nDate: 2026-10-01\nBranch: feat/x\n"
                   "Coverage: see validation matrix\n")
        response = self.call("uwk_save_handoff", {
            "root": str(self.root), "content": content, "branch": "feat/x", "actor": "agent"})
        self.assertFalse(response["result"]["isError"])
        self.assertTrue((self.pack / "sessions/feat-x__agent.md").is_file())

    def test_unknown_tool_is_an_error(self):
        response = mcp_server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "nope", "arguments": {}}})
        self.assertEqual(response["error"]["code"], -32602)


    def test_stdio_transport_is_utf8_and_newline_delimited(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "uwk_get_context",
                        "arguments": {"root": str(self.root),
                                      "file": "Assets/Scenes/Dev.unity",
                                      "sessions": False}}},
        ]
        proc = subprocess.run(
            [sys.executable, str(KIT / "tools/mcp_server.py"), "--root", str(self.root)],
            input="\n".join(json.dumps(m) for m in messages) + "\n",
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual([r["id"] for r in responses], [1, 2])
        self.assertIn("GameObject: Player", responses[1]["result"]["content"][0]["text"])


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
