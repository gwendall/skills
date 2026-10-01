import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_manager():
    path = ROOT / "skills/workstation/safe-memory-manager/scripts/memory_manager.py"
    spec = importlib.util.spec_from_file_location("safe_memory_manager", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SafeMemoryManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = load_manager()

    def identity(self, **overrides):
        value = {
            "pid": 4242,
            "uid": 501,
            "ppid": 100,
            "state": "S",
            "family": "developer-runtime",
            "tty": "??",
            "started": "Mon Sep 7 12:00:00 2026",
            "command": "node",
            "cwd": "/tmp/project",
            "ports": ["*:3000"],
            "arguments_sha256": "abc",
            "protected_marker": None,
            "protected_descendant": None,
        }
        value.update(overrides)
        return value

    def test_memory_size_parser(self):
        self.assertEqual(self.manager.parse_memory_size("1.5G"), 1610612736)
        self.assertEqual(self.manager.parse_memory_size("512M"), 536870912)
        self.assertIsNone(self.manager.parse_memory_size("unknown"))

    def test_elapsed_parser(self):
        self.assertEqual(self.manager.elapsed_seconds("01-02:03:04"), 93784)
        self.assertEqual(self.manager.elapsed_seconds("12:34"), 754)

    def test_process_family_protects_agents_and_gui_apps(self):
        self.assertEqual(self.manager.process_family("/usr/local/bin/codex"), "agent")
        self.assertEqual(
            self.manager.process_family(
                "/Applications/Example.app/Contents/MacOS/Example"
            ),
            "gui-app",
        )

    def test_lifecycle_states_do_not_call_live_processes_dead(self):
        self.assertEqual(
            self.manager.lifecycle_state(self.identity(state="Z")), "zombie-exited"
        )
        self.assertEqual(
            self.manager.lifecycle_state(self.identity(ppid=1)),
            "orphan-or-launchd-owned-live",
        )
        self.assertEqual(
            self.manager.lifecycle_state(self.identity(tty="ttys001")),
            "attached-terminal-live",
        )
        self.assertEqual(
            self.manager.lifecycle_state(self.identity()), "detached-sleeping-live"
        )
        self.assertEqual(
            self.manager.lifecycle_state(self.identity(state="R")),
            "detached-active-live",
        )

    def test_process_inspection_never_authorizes_generic_termination(self):
        with (
            mock.patch.object(
                self.manager, "process_identity", return_value=self.identity()
            ),
            mock.patch.object(
                self.manager, "protected_descendant_marker", return_value=None
            ),
            mock.patch.object(
                self.manager, "read_process_footprint", return_value=1024
            ),
        ):
            report = self.manager.build_process_inspection(4242)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertFalse(report["automatic_termination_supported"])
        self.assertNotIn("confirmation_token", report)


if __name__ == "__main__":
    unittest.main()
