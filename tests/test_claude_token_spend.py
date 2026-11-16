"""Synthetic transcripts prove that archives preserve usage and fail visibly."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/workstation/claude-token-spend/scripts"
sys.path.insert(0, str(SCRIPTS))
import token_spend as spend
import transcript_files as files


def message(mid=None, value=7):
    rec = {
        "type": "assistant", "timestamp": "2026-01-01T00:00:00Z",
        "message": {"model": "synthetic-model", "usage": {"input_tokens": value}},
    }
    if mid:
        rec.update(requestId="request-" + mid)
        rec["message"]["id"] = mid
    return json.dumps(rec) + "\n"


@unittest.skipUnless(shutil.which("zstd"), "zstd is needed to prove archive reads")
class TokenSpendArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "synthetic-project"
        self.project.mkdir()

    def archive(self, path, content):
        proc = subprocess.run(["zstd", "-q", "-3", "-c"], input=content.encode(),
                              capture_output=True, check=True)
        path.write_bytes(proc.stdout)

    def test_archive_and_plain_return_identical_counts(self):
        path = self.project / "session.jsonl"
        content = message("one") + "invalid JSON\n" + message("two", 11) + message("one")
        path.write_text(content)
        before = spend.scan(self.root)
        path.unlink()
        self.archive(Path(str(path) + ".zst"), content)
        after = spend.scan(self.root)
        self.assertEqual(before, after)
        by_model, _, counted, duplicates = after
        self.assertEqual((counted, duplicates), (2, 1))
        self.assertEqual(by_model["synthetic-model"]["all"]["input"], 18)

    def test_plain_wins_without_message_id_and_includes_new_events(self):
        path = self.project / "session.jsonl"
        self.archive(Path(str(path) + ".zst"), message(value=3))
        path.write_text(message(value=5) + message(value=9))
        by_model, _, counted, duplicates = spend.scan(self.root)
        self.assertEqual((counted, duplicates), (2, 0))
        self.assertEqual(by_model["synthetic-model"]["all"]["input"], 14)
        self.assertEqual(files.transcripts(self.root), [path])

    def test_corruption_fails_instead_of_returning_partial_totals(self):
        path = self.project / "broken.jsonl.zst"
        self.archive(path, message("one"))
        path.write_bytes(path.read_bytes()[:-3])
        with self.assertRaisesRegex(RuntimeError, "zstd could not read transcript"):
            spend.scan(self.root)
        result = subprocess.run([sys.executable, str(SCRIPTS / "token_spend.py"),
                                 "--root", str(self.root), "--json"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_missing_zstd_fails_visibly(self):
        path = self.project / "session.jsonl.zst"
        self.archive(path, message("one"))
        with patch.dict("os.environ", {"PATH": ""}):
            with self.assertRaises(FileNotFoundError):
                spend.scan(self.root)

    def test_exception_closes_and_reaps_decompressor(self):
        path = self.project / "session.jsonl.zst"
        self.archive(path, message("one") * 100000)
        real_popen = files.subprocess.Popen
        processes = []

        def capture(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            processes.append(proc)
            return proc

        with patch.object(files.subprocess, "Popen", side_effect=capture):
            with self.assertRaisesRegex(ValueError, "stop early"):
                with files.open_transcript(path) as stream:
                    self.assertIn("synthetic-model", next(stream))
                    raise ValueError("stop early")
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed)


if __name__ == "__main__":
    unittest.main()
