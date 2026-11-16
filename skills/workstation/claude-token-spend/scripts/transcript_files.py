"""Read plain or zstd session logs without restoring archives to disk."""
import subprocess
from contextlib import contextmanager
from tempfile import TemporaryFile


def transcripts(root):
    """A restored plain log wins over its archive, including without message IDs."""
    files = {str(p): p for p in root.rglob("*.jsonl") if p.is_file()}
    for archive in root.rglob("*.jsonl.zst"):
        if archive.is_file():
            files.setdefault(str(archive)[:-4], archive)
    return [files[key] for key in sorted(files)]


@contextmanager
def open_transcript(path):
    if not str(path).endswith(".jsonl.zst"):
        with open(path, encoding="utf-8", errors="replace") as stream:
            yield stream
        return
    # A file avoids an unread stderr pipe blocking decompression. Never buffer a
    # whole transcript: old logs can be larger than the available RAM.
    with TemporaryFile() as errors:
        proc = subprocess.Popen(
            ["zstd", "-q", "-d", "-c", "--", str(path)],
            stdout=subprocess.PIPE, stderr=errors, text=True,
            encoding="utf-8", errors="replace",
        )
        failed = False
        try:
            with proc.stdout as stream:
                yield stream
        except BaseException:
            failed = True
            raise
        finally:
            if failed and proc.poll() is None:
                proc.terminate()
            try:
                status = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                status = proc.wait()
            if status and not failed:
                raise RuntimeError("zstd could not read transcript: %s (exit %d)" % (path, status))
