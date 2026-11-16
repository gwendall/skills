"""Read plain or zstd session logs without restoring archives to disk."""
import subprocess
from contextlib import contextmanager
from tempfile import TemporaryFile
from pathlib import Path


def transcripts(root):
    """Return (original path, readable file), preferring native plain logs.

    The central store mirrors canonical HOME-relative paths. Resolving the
    requested root also handles ~/.claude/projects pointing into ~/.denshin.
    """
    root = Path(root)
    home = Path.home().resolve()
    store = home / ".local/state/machine/transcript-archive/store"
    files = {p: p for p in root.rglob("*.jsonl") if p.is_file()}
    for archive in root.rglob("*.jsonl.zst"):
        if archive.is_file() and store not in archive.resolve().parents:
            files.setdefault(Path(str(archive)[:-4]), archive)
    try:
        central = store / root.resolve().relative_to(home)
    except ValueError:
        central = None  # An unrelated --root never inherits this home's data.
    if central is not None:
        for archive in central.rglob("*.jsonl.zst"):
            if archive.is_file():
                original = root / str(archive.relative_to(central))[:-4]
                files.setdefault(original, archive)
    return [(original, files[original]) for original in sorted(files)]


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
