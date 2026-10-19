import hashlib
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from scripts.phonogram_audit.database import connect_readonly
from scripts.phonogram_cache.exporter import build as build_cache
from .analyses import read_analyses
from .facets import write_facets
from .models import AnalysisRow
from .catalog import SQL, SoundNames, concept_row, defined_patterns, notation_rows
from .origins import read_origins
from .pronunciations import heteronym_link, read_heteronyms, read_pronunciations
from .writer import create, finish, write_concepts, write_families, write_origins, write_pronunciations, write_rarity, write_sounds, write_words


def word_ids(repository: Path) -> dict[str, int]:
    with closing(connect_readonly(repository / "data/words.db")) as connection:
        return dict(connection.execute((SQL / "word-ids.sql").read_text()))


def word_tags(cache: dict, analyses: list[AnalysisRow]) -> dict[str, set[str]]:
    tags: dict[str, set[str]] = defaultdict(set)
    for concept, words in cache["concept_to_words"].items():
        for word in words:
            tags[word].add(concept)
    for analysis in analyses:
        tags[analysis.word].update(item.concept for item in analysis.phonograms if item.concept)
    return tags


def fingerprint(database: Path) -> str:
    with database.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(repository: Path, database: Path, output: Path, workspace: Path | None = None) -> dict[str, int]:
    cache = build_cache(workspace or repository.parent, database)
    analyses = read_analyses(database)
    tags = word_tags(cache, analyses)
    names, definitions = SoundNames(repository), defined_patterns(database)
    rows = [row for tag in sorted({tag for item in tags.values() for tag in item}) if (row := concept_row(tag, definitions, names))]
    connection = create(output)
    write_families(connection)
    write_concepts(connection, rows)
    write_sounds(connection, notation_rows(workspace or repository.parent))
    ids = word_ids(repository)
    write_words(connection, ids, analyses, tags)
    write_origins(connection, ids, read_origins(repository))
    write_rarity(connection)
    write_pronunciations(connection, ids, read_pronunciations(database), read_heteronyms(repository), heteronym_link)
    facets = write_facets(connection, names)
    meta = {"cache_format": cache["format_version"], "observation_sha256": fingerprint(database)}
    finish(connection, output, meta)
    return {"concepts": len(rows), "facets": facets, "words": len(tags)}
