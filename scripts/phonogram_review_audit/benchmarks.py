import json
import hashlib
import sqlite3
from collections import Counter
from contextlib import closing
from importlib.metadata import version
from pathlib import Path

import cmudict

from scripts.phonogram_base.storage import sql


SQL_DIRECTORY = Path(__file__).with_name("sql")


def bases(phones: list[str]) -> tuple[str, ...]:
    return tuple(phone.rstrip("012") for phone in phones)


def syllabified(path: Path) -> dict[str, set[tuple[str, ...]]]:
    result = {}
    with path.open() as stream:
        for line in stream:
            if line.startswith("##") or "  " not in line:
                continue
            word, pronunciation = line.strip().split("  ", 1)
            word = word.lower().split("(")[0]
            phones = [phone for phone in pronunciation.split() if phone != "-"]
            result.setdefault(word, set()).add(bases(phones))
    return result


def pronunciation_check(word: str, selected: list[str], alignment: list[list[str]], variants: dict) -> str:
    if not alignment:
        return "missing_alignment"
    raw = bases([phone for _, token in alignment if token for phone in token.split("|")])
    if raw == bases(selected):
        return "matches_selected"
    if raw in {bases(option) for option in variants.get(word, [])}:
        return "matches_other_cmu_variant"
    return "unresolved_pronunciation"


def benchmark(repository: Path, database: Path) -> dict:
    selected = {row[0]: row[1] for row in json.loads((repository / "data/words.json").read_text())}
    alignments = json.loads((repository / "data/g2p_aligned.json").read_text())
    variants = cmudict.dict()
    syllables = syllabified(repository / "data/cmudict_syllabified.rep")
    counts, examples = Counter(), {}
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        rows = connection.execute((SQL_DIRECTORY / "words.sql").read_text()).fetchall()
        bundle = json.loads(connection.execute(sql("summary.sql")).fetchone()[0])["bundle_version"]
    for word, status, reasons, _, _ in rows:
        outcome = pronunciation_check(word, selected[word], alignments.get(word, []), variants)
        counts[outcome] += 1
        examples.setdefault(outcome, []).append(word)
        if bases(selected[word]) in syllables.get(word, set()):
            counts["syllabified_matches_selected"] += 1
            if status == "excluded":
                counts["excluded_with_matching_phonetic_syllables"] += 1
        if outcome == "matches_other_cmu_variant" and set(json.loads(reasons)) <= {
                "pronunciation_mismatch", "incomplete_coverage"}:
            counts["variant_conflict_without_other_recorded_reasons"] += 1
    return {"bundle_version": bundle, "sources": source_checksums(repository),
            "cmudict_package_version": version("cmudict"), "counts": dict(counts),
            "examples": {key: words[:12] for key, words in examples.items()},
            "limit": "Phonetic syllables are not orthographic OG syllable divisions. Counts are comparison coverage, not repair guarantees."}


def source_checksums(repository: Path) -> dict[str, str]:
    result = {}
    for name in ["words.json", "g2p_aligned.json", "cmudict_syllabified.rep"]:
        with (repository / "data" / name).open("rb") as stream:
            result[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result
