import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_cleanup():
    path = ROOT / "skills/workstation/safe-disk-cleanup/scripts/cleanup.py"
    spec = importlib.util.spec_from_file_location("safe_disk_cleanup", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_inventory():
    path = ROOT / "skills/workstation/safe-disk-cleanup/scripts/inventory.py"
    spec = importlib.util.spec_from_file_location("safe_disk_inventory", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_script(name):
    path = ROOT / f"skills/workstation/safe-disk-cleanup/scripts/{name}.py"
    spec = importlib.util.spec_from_file_location(f"safe_disk_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CleanupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.cleanup = load_cleanup()

    def test_unknown_action_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown action"):
            self.cleanup.select_actions(["delete-my-home"])

    def test_configurable_native_cleanup_is_not_allowlisted(self):
        for action_id in ("pnpm-store-prune", "homebrew-cleanup"):
            with (
                self.subTest(action_id=action_id),
                self.assertRaisesRegex(ValueError, "Unknown action"),
            ):
                self.cleanup.select_actions([action_id])

    def test_plan_token_is_bound_to_exact_action_set(self):
        home = Path("/tmp/example-home")
        expo = self.cleanup.select_actions(["expo-cache"])
        npm = self.cleanup.select_actions(["npm-cache"])
        self.assertNotEqual(
            self.cleanup.plan_token(expo, home),
            self.cleanup.plan_token(npm, home),
        )

    def test_npm_plan_names_every_deleted_path(self):
        home = Path("/tmp/example-home")
        action = self.cleanup.select_actions(["npm-cache"])[0]
        self.assertEqual(
            self.cleanup.expected_paths(action, home),
            [home / ".npm/_npx", home / ".npm/_cacache"],
        )

    def test_plan_token_changes_when_target_identity_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            target = home / ".expo/expo-go"
            target.mkdir(parents=True)
            actions = self.cleanup.select_actions(["expo-cache"])
            first = self.cleanup.plan_token(actions, home)
            target.rmdir()
            target.mkdir()
            second = self.cleanup.plan_token(actions, home)
            self.assertNotEqual(first, second)

    def test_plan_token_changes_when_nested_content_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            target = home / ".expo/expo-go"
            target.mkdir(parents=True)
            actions = self.cleanup.select_actions(["expo-cache"])
            first = self.cleanup.plan_token(actions, home)
            (target / "new-download.bin").write_bytes(b"download")
            second = self.cleanup.plan_token(actions, home)
            self.assertNotEqual(first, second)

    def test_dry_run_enumerates_without_modifying_files(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            target = home / ".expo/expo-go"
            target.mkdir(parents=True)
            download = target / "download.bin"
            download.write_bytes(b"cache")

            actions = self.cleanup.select_actions(["expo-cache"])
            plan = self.cleanup.build_plan(
                actions, home, include_entries=True, processes=[]
            )

            self.assertTrue(plan["dry_run"])
            self.assertFalse(plan["cleanup_mutations_performed"])
            self.assertTrue(download.is_file())
            entries = plan["actions"][0]["roots"][0]["entries"]
            self.assertEqual(entries[0]["full_path"], str(download))

    def test_symlink_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            outside = home / "outside"
            outside.mkdir()
            target = home / ".expo/expo-go"
            target.parent.mkdir(parents=True)
            target.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.cleanup.validate_target(target, home)

    def test_executor_only_removes_allowlisted_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            cache = home / ".expo/expo-go"
            cache.mkdir(parents=True)
            (cache / "download.bin").write_bytes(b"cache")
            personal = home / "Documents/important.txt"
            personal.parent.mkdir()
            personal.write_text("keep me", encoding="utf-8")

            action = self.cleanup.select_actions(["expo-cache"])
            results = self.cleanup.execute(action, home, processes=[])

            self.assertEqual(results[0]["status"], "ok")
            self.assertEqual(results[0]["deleted_paths"], [str(cache)])
            self.assertFalse(cache.exists())
            self.assertEqual(personal.read_text(encoding="utf-8"), "keep me")

    def test_all_targets_are_validated_before_any_deletion(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            expo_cache = home / ".expo/expo-go"
            expo_cache.mkdir(parents=True)
            outside = home / "outside"
            outside.mkdir()
            npm_cache = home / ".npm/_npx"
            npm_cache.parent.mkdir()
            npm_cache.symlink_to(outside, target_is_directory=True)

            actions = self.cleanup.select_actions(["expo-cache", "npm-cache"])
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.cleanup.execute(actions, home, processes=[])

            self.assertTrue(expo_cache.is_dir())

    def test_partial_execution_reports_completed_paths_and_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            expo_cache = home / ".expo/expo-go"
            expo_cache.mkdir(parents=True)
            npm_cache = home / ".npm/_npx"
            npm_cache.mkdir(parents=True)
            actions = self.cleanup.select_actions(["expo-cache", "npm-cache"])
            original = self.cleanup.delete_validated

            def fail_on_npm(path, validated_home, identity):
                if path == npm_cache:
                    raise OSError("simulated deletion failure")
                return original(path, validated_home, identity)

            with mock.patch.object(
                self.cleanup, "delete_validated", side_effect=fail_on_npm
            ):
                results = self.cleanup.execute(actions, home, processes=[])

            self.assertEqual(results[0]["status"], "ok")
            self.assertIn(str(expo_cache), results[0]["deleted_paths"])
            self.assertEqual(results[1]["status"], "failed")
            self.assertEqual(results[1]["deleted_paths"], [])
            self.assertTrue(npm_cache.is_dir())

    def test_active_tool_blocks_plan_and_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            cache = home / "Library/Caches/ms-playwright"
            cache.mkdir(parents=True)
            actions = self.cleanup.select_actions(["playwright-cache"])
            processes = [
                {
                    "pid": 4242,
                    "ppid": 1,
                    "executable": "node",
                    "arguments": "node project/node_modules/.bin/playwright test",
                }
            ]

            plan = self.cleanup.build_plan(actions, home, processes=processes)
            self.assertTrue(plan["execution_blocked_by_activity"])
            with self.assertRaisesRegex(ValueError, "active"):
                self.cleanup.execute(actions, home, processes=processes)
            self.assertTrue(cache.is_dir())

    def test_identity_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            cache = home / ".expo/expo-go"
            cache.mkdir(parents=True)
            validated = self.cleanup.validate_target(cache, home)
            assert validated
            path, identity = validated
            cache.rmdir()
            cache.mkdir()
            with self.assertRaisesRegex(ValueError, "changed"):
                self.cleanup.delete_validated(path, home, identity)


class InventorySafetyTests(unittest.TestCase):
    def setUp(self):
        self.inventory = load_inventory()

    def test_json_export_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "inventory.json"
            output.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                self.inventory.write_json_exclusive(output, {"safe": True})
            self.assertEqual(output.read_text(encoding="utf-8"), "keep")

    def test_deep_inventory_deduplicates_hardlinks(self):
        deep = load_script("deep_inventory")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first.bin"
            second = root / "second.bin"
            first.write_bytes(b"x" * 8192)
            second.hardlink_to(first)
            report = deep.scan_roots([root], 2, 1, 10)
            files = {row["path"] for row in report["large_files"]}
            self.assertEqual(len(files), 1)
            self.assertEqual(report["hardlink_deduplication"], "device-and-inode")

    def test_deep_inventory_marks_personal_directories_protected(self):
        deep = load_script("deep_inventory")
        home = Path("/Users/example")
        self.assertEqual(
            deep.risk_for_path(home / "Desktop/video.mov", home), "protected"
        )
        self.assertEqual(
            deep.risk_for_path(home / "Documents/taxes.pdf", home), "protected"
        )

    def test_worktree_parser_preserves_locks_and_detached_heads(self):
        audit = load_script("worktree_audit")
        rows = audit.parse_worktree_porcelain(
            "worktree /tmp/main\nHEAD abc\nbranch refs/heads/main\n\n"
            "worktree /tmp/review\nHEAD def\ndetached\nlocked agent session\n"
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["HEAD"], "def")
        self.assertTrue(rows[1]["locked"])
        self.assertNotIn("branch", rows[1])

    def test_worktree_decision_requires_recovery_and_owner_approval(self):
        audit = load_script("worktree_audit")
        facts = {
            "path": "/repo-worktrees/done",
            "branch": "feature/done",
            "head": "abc123",
            "main_ref": "origin/main",
            "exists": True,
            "clean": True,
            "merged_into_main_ref": True,
            "upstream": "origin/feature/done",
            "ahead_of_upstream": 0,
            "has_gitmodules": False,
            "locked": False,
            "prunable": False,
            "active_pids": [],
        }
        result = audit.decide_worktree(facts, "/repo")
        self.assertEqual(result["decision"], "review-ready")
        self.assertTrue(result["preconditions_met"])
        self.assertFalse(result["safe_to_remove_now"])
        self.assertTrue(result["owner_approval_required"])

    def test_worktree_decision_blocks_active_dirty_or_unpushed_work(self):
        audit = load_script("worktree_audit")
        facts = {
            "path": "/repo-worktrees/live",
            "branch": "feature/live",
            "head": "abc123",
            "main_ref": "origin/main",
            "exists": True,
            "clean": False,
            "merged_into_main_ref": False,
            "upstream": "origin/feature/live",
            "ahead_of_upstream": 2,
            "has_gitmodules": False,
            "locked": False,
            "prunable": False,
            "active_pids": [42],
        }
        result = audit.decide_worktree(facts, "/repo")
        self.assertEqual(result["decision"], "blocked")
        self.assertGreaterEqual(len(result["blockers"]), 3)

    def test_worktree_decision_protects_real_main_when_invoked_elsewhere(self):
        audit = load_script("worktree_audit")
        facts = {
            "path": "/repo/main",
            "branch": "main",
            "head": "abc123",
            "main_ref": "origin/main",
            "exists": True,
            "clean": True,
            "merged_into_main_ref": True,
            "upstream": "origin/main",
            "ahead_of_upstream": 0,
            "has_gitmodules": False,
            "locked": False,
            "prunable": False,
            "active_pids": [],
        }
        result = audit.decide_worktree(facts, "/repo/main")
        self.assertEqual(result["decision"], "protected")

    def test_docker_decisions_protect_volumes_and_block_active_build_cache(self):
        docker = load_script("docker_audit")
        report = docker.build_report(
            [
                {
                    "Type": "Build Cache",
                    "Reclaimable": "12GB",
                    "Size": "20GB",
                }
            ],
            [],
            [],
            [{"Name": "database", "Driver": "local"}],
            [{"pid": 42, "matched_activity": "docker buildx"}],
        )
        resources = {row["resource"]: row for row in report["resources"]}
        self.assertEqual(resources["docker-build-cache"]["decision"], "blocked")
        self.assertEqual(resources["volume:database"]["decision"], "protected")
        self.assertFalse(resources["docker-raw-vm-disk"]["safe_to_delete_now"])

    def test_docker_stopped_stateless_container_is_only_review_ready(self):
        docker = load_script("docker_audit")
        report = docker.build_report(
            [],
            [
                {
                    "ID": "abc123",
                    "Names": "one-shot",
                    "State": "exited",
                    "Mounts": "",
                    "Size": "10MB",
                }
            ],
            [],
            [],
            [],
        )
        container = next(
            row
            for row in report["resources"]
            if row["resource"] == "container:one-shot"
        )
        self.assertEqual(container["decision"], "review-ready")
        self.assertFalse(container["safe_to_delete_now"])

    def test_simulator_requires_state_evidence_and_fresh_approval(self):
        simulator = load_script("simulator_audit")
        payload = {
            "devices": {
                "runtime": [
                    {
                        "udid": "available",
                        "name": "iPhone",
                        "state": "Shutdown",
                        "isAvailable": True,
                        "dataPathSize": 1024,
                    },
                    {
                        "udid": "unavailable",
                        "name": "Old iPhone",
                        "state": "Shutdown",
                        "isAvailable": False,
                        "dataPathSize": 2048,
                    },
                ]
            }
        }
        report = simulator.build_report(payload, [])
        devices = {row["resource"]: row for row in report["devices"]}
        self.assertEqual(devices["simulator:available"]["decision"], "review")
        self.assertEqual(devices["simulator:unavailable"]["decision"], "review-ready")
        self.assertFalse(devices["simulator:unavailable"]["safe_to_delete_now"])

        blocked = simulator.build_report(
            payload, [{"pid": 42, "matched_activity": "xcodebuild"}]
        )
        self.assertTrue(all(row["decision"] == "blocked" for row in blocked["devices"]))

    def test_pnpm_store_requires_clean_status_no_activity_and_approval(self):
        pnpm = load_script("pnpm_audit")
        ready = pnpm.build_report(
            "/store", 1024, 0, "Packages in the store are untouched", []
        )
        self.assertEqual(ready["decision"], "review-ready")
        self.assertFalse(ready["safe_to_delete_now"])
        self.assertEqual(ready["recommended_action"], "pnpm store prune")

        blocked = pnpm.build_report(
            "/store",
            1024,
            1,
            "modified package",
            [{"pid": 42, "arguments": "pnpm install"}],
        )
        self.assertEqual(blocked["decision"], "blocked")
        self.assertGreaterEqual(len(blocked["blockers"]), 2)
        self.assertIsNone(blocked["recommended_action"])


if __name__ == "__main__":
    unittest.main()
