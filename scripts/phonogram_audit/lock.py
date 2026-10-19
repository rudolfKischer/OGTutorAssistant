import json
from pathlib import Path

from .models import BaselineLock, BaselineReport, SourceFile


def validate_lock(report: BaselineReport, path: Path) -> None:
    values = json.loads(path.read_text())
    values["sources"] = [SourceFile(**source) for source in values["sources"]]
    lock = BaselineLock(**values)
    sources = {source.path: source.sha256 for source in report.sources}
    changed = [source.path for source in lock.sources if sources.get(source.path) != source.sha256]
    if changed:
        raise ValueError(f"Frozen source input changed: {changed}")
    expected = (lock.tags_sha256, lock.local_words, lock.shared_words, lock.deployed_words)
    actual = (report.tags.tags_sha256, report.tags.local_words, report.tags.shared_words,
              report.tags.deployed_words)
    if actual != expected:
        raise ValueError("Detector output differs from the frozen Phase 0 baseline")
