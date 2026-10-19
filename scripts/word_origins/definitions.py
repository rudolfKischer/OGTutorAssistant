import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .settings import SETTINGS

DEFINITIONS = SETTINGS["definitions"]
PATTERNS = {kind: re.compile(pattern, 0 if kind in DEFINITIONS["case_sensitive_kinds"] else re.I)
            for kind, pattern in DEFINITIONS["patterns"].items()}


ORIGINS = [re.compile(pattern) for pattern in DEFINITIONS["origin_patterns"]]
ORIGIN_SKIP = set(DEFINITIONS["origin_skip"])
ABBREVIATION_START = re.compile(DEFINITIONS["abbreviation_start"], re.I)
ABBREVIATION_LIKE = re.compile(DEFINITIONS["abbreviation_like"], re.I)
ACRONYM_WORDS = re.compile(DEFINITIONS["acronym_words"], re.I)


def sense_kind(text: str) -> str:
    for kind, pattern in PATTERNS.items():
        if pattern.search(text):
            return kind
    return ""


def profile(senses: list[str]) -> tuple[list[str], bool]:
    kinds = [sense_kind(text) for text in senses]
    return sorted({kind for kind in kinds if kind}), any(not kind for kind in kinds)


def name_kinds(senses: list[str]) -> list[str]:
    kinds, ordinary = profile(senses)
    return [] if ordinary else kinds


def sense_profiles(repository: Path) -> dict[str, tuple[list[str], bool]]:
    return {word: profile(senses) for word, senses in read_senses(repository).items()}


def read_senses(repository: Path) -> dict[str, list[str]]:
    path = repository / DEFINITIONS["database"]
    query = "SELECT w.word, d.definition FROM word_definitions d JOIN words w ON w.id = d.word_id ORDER BY w.id, d.position"
    senses: dict[str, list[str]] = {}
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        for word, definition in connection.execute(query):
            senses.setdefault(word, []).append(definition)
    return senses


def acronym_senses(text: str) -> bool:
    return bool(ACRONYM_WORDS.search(text) or ABBREVIATION_LIKE.search(text))


def abbreviation_flags(repository: Path) -> tuple[set[str], dict[str, tuple[list[str], bool]]]:
    abbreviations: set[str] = set()
    profiles: dict[str, tuple[list[str], bool]] = {}
    for word, senses in read_senses(repository).items():
        if any(ABBREVIATION_START.search(text) for text in senses) and all(ABBREVIATION_LIKE.search(text) for text in senses):
            abbreviations.add(word)
        found = {match.group(1).lower() for text in senses for match in [ACRONYM_WORDS.search(text)] if match}
        profiles[word] = (sorted(found), not all(acronym_senses(text) for text in senses))
    return abbreviations, profiles


def name_origins(senses: list[str]) -> list[str]:
    found = {match.group(1) for text in senses if sense_kind(text) for pattern in ORIGINS for match in [pattern.search(text)] if match}
    return sorted(found - ORIGIN_SKIP)
