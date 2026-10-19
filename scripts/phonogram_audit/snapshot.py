import hashlib
import subprocess
from pathlib import Path

from .models import RepoState, SourceFile


def file_snapshot(path: Path, workspace: Path, chunk_size: int) -> SourceFile:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return SourceFile(str(path.relative_to(workspace)), digest.hexdigest(), path.stat().st_size)


def repository_snapshot(workspace: Path, name: str) -> RepoState:
    def git(*arguments: str) -> str:
        return subprocess.check_output(
            ["git", "--no-optional-locks", "-C", str(workspace / name), *arguments], text=True,
        ).strip()
    return RepoState(name, git("rev-parse", "HEAD"), git("branch", "--show-current"))
