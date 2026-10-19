import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from functools import cache

from .models import BaseSummary, Pattern, PatternKind, PatternSummary, Section, WordAnalysis


SQL_DIRECTORY = Path(__file__).with_name("sql")


@cache
def sql(name: str) -> str:
    return (SQL_DIRECTORY / name).read_text()


class BaseWriter:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.execute(sql("foreign-keys.sql"))
        self.connection.executescript(sql("schema.sql"))
        self.saved_patterns: set[str] = set()

    def add_pattern(self, pattern: Pattern) -> None:
        if pattern.id in self.saved_patterns:
            return
        self.connection.execute(sql("save-pattern.sql"), (pattern.id, json.dumps(asdict(pattern))))
        self.saved_patterns.add(pattern.id)

    def add(self, analysis: WordAnalysis) -> None:
        self.connection.execute(sql("save-analysis.sql"), (
            analysis.word, analysis.status, json.dumps(analysis.reasons), analysis.frequency_rank,
            analysis.frequency_weight, json.dumps(asdict(analysis)),
        ))
        for occurrence in analysis.occurrences:
            self.add_pattern(occurrence.pattern)
        self.connection.executemany(sql("save-occurrence.sql"), [
            (analysis.word, index, occurrence.pattern.id, occurrence.layer)
            for index, occurrence in enumerate(analysis.occurrences)
        ])

    def add_pronunciations(self, word: str, options: list) -> None:
        self.connection.executemany(sql("save-pronunciation.sql"), [
            (word, option.ordinal, option.source, json.dumps(option.phones), json.dumps(option.senses),
             option.analysis.status, json.dumps(option.analysis.reasons),
             json.dumps(asdict(option.analysis)) if option.ordinal else "{}")
            for option in options])

    def summarize(self, version: str, sources: dict[str, str], settings: dict) -> BaseSummary:
        counts = {status: (count, weight) for status, count, weight in self.connection.execute(sql("word-counts.sql"))}
        patterns = [pattern_summary(row, settings["rare_word_threshold"])
                    for row in self.connection.execute(sql("pattern-counts.sql"))]
        total = sum(count for count, _ in counts.values())
        weight = sum(value for _, value in counts.values())
        consistent, _ = counts.get("consistent", (0, 0))
        excluded, excluded_weight = counts.get("excluded", (0, 0))
        reasons = dict(self.connection.execute(sql("reason-counts.sql")))
        return BaseSummary(version, total, consistent, excluded, excluded_weight / weight if weight else 0,
                           reasons, sources, settings["rare_word_threshold"], patterns)

    def finish(self, summary: BaseSummary) -> None:
        self.connection.execute(sql("save-metadata.sql"), ("summary", json.dumps(asdict(summary))))
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


def pattern_summary(row: tuple, threshold: int) -> PatternSummary:
    _, document, count, excluded, occurrences = row
    record = json.loads(document)
    pattern = Pattern(**record)
    flags = []
    if not pattern.definition_ids:
        flags.append("unmapped")
    if count < threshold:
        flags.append("rare")
    if not count and excluded:
        flags.append("excluded_only")
    section = Section.Review if flags else Section.Teaching
    if pattern.kind in (PatternKind.Silent, PatternKind.Punctuation):
        section = Section.Silent
    return PatternSummary(pattern, count, excluded, occurrences, section, flags)


def read_query(path: Path, name: str, parameters: tuple = ()) -> list[tuple]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        connection.execute(sql("readonly.sql"))
        return connection.execute(sql(name), parameters).fetchall()
