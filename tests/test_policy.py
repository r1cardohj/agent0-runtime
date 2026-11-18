"""WorkspacePolicy: confine filesystem tools to one root, optionally read-only."""

import os
import tempfile
import unittest
from pathlib import Path

from agent0_runtime import (
    BuiltinToolsConfig,
    Shell,
    ToolCall,
    ToolContext,
    WorkspacePolicy,
    create_builtin_registry,
)
from agent0_runtime.filesystem import edit_file, read_file, write_file


class WorkspacePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "inside.txt").write_text("hello\n", encoding="utf-8")
        self.outside = Path(self.tmp.name).parent / "agent0-outside.txt"

    def tearDown(self):
        self.outside.unlink(missing_ok=True)

    def test_reads_and_writes_inside_the_root(self):
        policy = WorkspacePolicy(root=self.root)

        self.assertIn("1|hello", read_file(self.root, "inside.txt", policy=policy))
        self.assertIn("wrote", write_file(self.root, "new.txt", "data", policy=policy))
        self.assertEqual((self.root / "new.txt").read_text(encoding="utf-8"), "data")

    def test_relative_escape_is_refused(self):
        policy = WorkspacePolicy(root=self.root)

        result = write_file(self.root, "../agent0-outside.txt", "nope", policy=policy)

        self.assertEqual(result, "error: path escapes the workspace: ../agent0-outside.txt")
        self.assertFalse(self.outside.exists())

    def test_absolute_escape_is_refused(self):
        policy = WorkspacePolicy(root=self.root)

        self.assertTrue(read_file(self.root, "/etc/passwd", policy=policy).startswith("error:"))
        edited = edit_file(self.root, "/etc/passwd", [], policy=policy)
        self.assertIn("escapes the workspace", edited)

    def test_absolute_path_inside_the_root_is_allowed(self):
        policy = WorkspacePolicy(root=self.root)
        target = self.root / "nested" / "file.txt"

        result = write_file(self.root, str(target), "data", policy=policy)

        self.assertIn("wrote", result)
        self.assertEqual(target.read_text(encoding="utf-8"), "data")

    def test_symlink_cannot_escape_the_root(self):
        policy = WorkspacePolicy(root=self.root)
        link = self.root / "link.txt"
        os.symlink(self.outside, link)

        result = write_file(self.root, "link.txt", "nope", policy=policy)

        self.assertIn("escapes the workspace", result)
        self.assertFalse(self.outside.exists())

    def test_read_only_allows_reads_and_refuses_writes(self):
        policy = WorkspacePolicy(root=self.root, read_only=True)
        edit = [{"old_string": "hello", "new_string": "bye"}]

        self.assertIn("1|hello", read_file(self.root, "inside.txt", policy=policy))
        self.assertEqual(
            write_file(self.root, "new.txt", "data", policy=policy),
            "error: workspace policy is read-only",
        )
        self.assertEqual(
            edit_file(self.root, "inside.txt", edit, policy=policy),
            "error: workspace policy is read-only",
        )
        self.assertEqual((self.root / "inside.txt").read_text(encoding="utf-8"), "hello\n")

    def test_allow_outside_opts_back_in(self):
        policy = WorkspacePolicy(root=self.root, allow_outside=True)

        result = write_file(self.root, "../agent0-outside.txt", "ok", policy=policy)

        self.assertIn("wrote", result)
        self.assertEqual(self.outside.read_text(encoding="utf-8"), "ok")

    def test_policy_root_replaces_a_missing_cwd(self):
        policy = WorkspacePolicy(root=self.root)

        self.assertIn("1|hello", read_file(None, "inside.txt", policy=policy))
        self.assertEqual(write_file(None, "x.txt", "data", policy=policy).split()[0], "wrote")

    def test_builtin_registry_threads_the_policy_into_every_file_tool(self):
        registry = create_builtin_registry(
            BuiltinToolsConfig(
                shell=Shell("bash", ("/bin/bash", "-lc")),
                policy=WorkspacePolicy(root=self.root),
            )
        )
        context = ToolContext(cwd=self.root, call=ToolCall("call-1", "write", "{}"))

        write = registry.get("write")
        self.assertIsNotNone(write)
        result = write.handler(context, {"path": "../agent0-outside.txt", "content": "nope"})

        self.assertIn("escapes the workspace", result)
        self.assertFalse(self.outside.exists())

    def test_read_only_policy_disables_bash(self):
        registry = create_builtin_registry(
            BuiltinToolsConfig(
                shell=Shell("bash", ("/bin/bash", "-lc")),
                policy=WorkspacePolicy(root=self.root, read_only=True),
            )
        )
        context = ToolContext(cwd=self.root, call=ToolCall("call-1", "bash", "{}"))

        result = registry.get("bash").handler(context, {"command": "echo hi"})

        self.assertEqual(result, "error: workspace policy is read-only; bash is disabled")

    def test_no_policy_keeps_the_previous_permissive_behavior(self):
        # Hosts that have not adopted the policy keep today's semantics exactly.
        self.assertIn("wrote", write_file(self.root, "../agent0-outside.txt", "ok"))
        self.outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
