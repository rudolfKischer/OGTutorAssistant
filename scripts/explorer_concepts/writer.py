import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from .catalog import SETTINGS, SQL
from .models import AnalysisRow, ConceptRow
from .origins import origin_rows


def create(path: Path) -> sqlite3.Connection:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    connection.executescript((SQL / "schema.sql").read_text())
    return connection


def write_families(connection: sqlite3.Connection) -> None:
    connection.executemany("INSERT INTO families VALUES (?, ?, ?, ?, ?, ?)", [
        (family["id"], family["label"], family["group"], index, int(family["collapsed"]), family["lens"])
        for index, family in enumerate(SETTINGS["families"])])


def write_concepts(connection: sqlite3.Connection, rows: list[ConceptRow]) -> None:
    connection.executemany("INSERT INTO concepts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        (row.concept, row.label, row.kind, row.family, row.sort_key, row.spelling, json.dumps(row.sounds), int(row.tail))
        for row in rows])


def write_sounds(connection: sqlite3.Connection, sounds: list[tuple]) -> None:
    connection.executemany("INSERT INTO sounds VALUES (?, ?, ?, ?, ?)", sounds)


def write_words(connection: sqlite3.Connection, word_ids: dict[str, int], analyses: list[AnalysisRow],
                tags: dict[str, set[str]]) -> None:
    for analysis in analyses:
        word_id = word_ids.get(analysis.word)
        if word_id is None:
            continue
        connection.execute("INSERT INTO word_analysis VALUES (?, ?, ?, ?, ?, ?)",
                           (word_id, analysis.status, json.dumps(analysis.reasons), json.dumps(analysis.syllables),
                            json.dumps(analysis.written), json.dumps(analysis.warnings)))
        connection.executemany("INSERT INTO word_phonograms VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            (word_id, item.ordinal, item.concept, item.layer, item.syllable, item.spelling, json.dumps(item.sounds),
             json.dumps(item.spans), json.dumps(item.phones)) for item in analysis.phonograms])
    connection.executemany("INSERT INTO word_concepts VALUES (?, ?)", [
        (word_ids[word], tag) for word, word_tags in tags.items() if word in word_ids for tag in sorted(word_tags)])


def write_rarity(connection: sqlite3.Connection) -> None:
    connection.execute((SQL / "word-rarity.sql").read_text(), (json.dumps(SETTINGS["rarity_kinds"]),))


def finish(connection: sqlite3.Connection, path: Path, meta: dict[str, str]) -> None:
    connection.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
    connection.commit()
    connection.close()
    os.replace(path.with_suffix(path.suffix + ".tmp"), path)


def write_origins(connection: sqlite3.Connection, word_ids: dict[str, int], origins: dict[str, dict]) -> None:
    rows = [row for word, flags in origins.items() if word in word_ids for row in origin_rows(word_ids[word], flags)]
    connection.executemany("INSERT INTO word_origin_flags VALUES (?, ?, ?)", rows)


def write_pronunciations(connection: sqlite3.Connection, word_ids: dict[str, int], pronunciations: dict[str, list[dict]],
                         heteronyms: dict[str, dict], link) -> None:
    for word, items in pronunciations.items():
        if word not in word_ids:
            continue
        connection.executemany("INSERT INTO pronunciations VALUES (?, ?, ?, ?, ?, ?)", [
            (word_ids[word], item["ordinal"], item["source"], json.dumps(item["sounds"]), json.dumps(item["senses"]),
             json.dumps(item["analysis"])) for item in items])
    confidence = SETTINGS["heteronym_confidence"]
    connection.executemany("INSERT INTO heteronyms VALUES (?, ?, ?, ?, ?)", [
        (word_ids[word], json.dumps(entry["sources"]), json.dumps(entry["senses"]), link(word),
         confidence["confirmed"] if entry["senses"] else confidence["listed"])
        for word, entry in heteronyms.items() if word in word_ids])
