import os
import platform
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/workstation/mac-for-agents/scripts/mac-for-agents.sh"
HEADER = "label,epoch,load1,mds_cpu,mds_mb,fseventsd_cpu,fseventsd_mb,mdworkers,agents_cli\n"


def run(*args, cwd=None, env=None):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)


class MacForAgentsTests(unittest.TestCase):
    def test_compare_averages_each_run_and_keeps_the_spotlight_peak(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "before.csv").write_text(HEADER
                + "before,1,20.0,10.0,1000,100.0,19000,4,18\n"
                + "before,2,30.0,350.0,2000,110.0,19100,9,18\n")
            Path(tmp, "after.csv").write_text(HEADER + "after,3,12.0,2.0,500,90.0,19000,1,17\n")
            result = run("compare", cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        before, after = result.stdout.strip().splitlines()
        self.assertIn("before    2 samples", before)
        self.assertIn("load  25.0", before)
        self.assertIn("Spotlight CPU  180% (peak  350%)", before)
        self.assertIn("fseventsd CPU  105%", before)
        self.assertIn("after     1 samples", after)

    def test_compare_names_a_missing_run_instead_of_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run("compare", cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("before.csv: missing", result.stdout)
        self.assertIn("after.csv: missing", result.stdout)

    def test_unknown_command_prints_usage(self):
        result = run("help")
        self.assertIn("measure before", result.stdout)

    @unittest.skipUnless(platform.system() == "Darwin", "Spotlight is macOS only")
    def test_report_reads_an_unindexed_folder_as_not_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "CODE_DIRS": tmp}
            result = run("report", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"{tmp}: not indexed (good)", result.stdout)
        self.assertIn("== Cost right now", result.stdout)

    @unittest.skipUnless(platform.system() == "Darwin", "Spotlight is macOS only")
    def test_report_finds_the_default_folders_and_names_each_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("code", "project", "repo"):
                Path(tmp, name).mkdir()
            env = {k: v for k, v in os.environ.items() if k != "CODE_DIRS"} | {"HOME": tmp}
            result = run("report", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = [line for line in result.stdout.splitlines() if line.startswith(f"  {tmp}/")]
        names = sorted(line[len(f"  {tmp}/"):].split(":")[0].lower() for line in listed)
        # A case-insensitive disk (the macOS default) answers ~/Code for ~/code: still one folder.
        self.assertEqual(names, ["code", "project", "repo"], result.stdout)


if __name__ == "__main__":
    unittest.main()
