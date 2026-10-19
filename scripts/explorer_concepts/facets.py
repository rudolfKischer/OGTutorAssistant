import json
import sqlite3

from .catalog import SETTINGS, SQL, SoundNames, spelling_shape
from .models import ConceptRow

FACETS = SETTINGS["facets"]
PREFIX = FACETS["prefixes"]
KIND = FACETS["kinds"]


def grapheme_family(spelling: str) -> str:
    shape = spelling_shape(spelling)
    for rule in FACETS["grapheme_rules"]:
        if rule.get("shape", shape) != shape:
            continue
        if len(spelling) <= rule.get("max_length", len(spelling)):
            return rule["family"]
    return FACETS["grapheme_rules"][-1]["family"]


def grapheme_row(spelling: str, taught: set[str]) -> ConceptRow:
    return ConceptRow(PREFIX["grapheme"] + spelling, spelling, KIND["grapheme"], grapheme_family(spelling),
                      spelling, spelling, [], spelling not in taught)


def phoneme_row(sound: str, names: SoundNames, taught: set[str]) -> ConceptRow:
    family = FACETS["phoneme_families"].get(names.categories.get(sound), FACETS["default_phoneme_family"])
    return ConceptRow(PREFIX["phoneme"] + sound, names.label(sound), KIND["phoneme"], family,
                      names.label(sound), "", [sound], sound not in taught)


def write_facets(connection: sqlite3.Connection, names: SoundNames) -> int:
    connection.executemany("INSERT OR IGNORE INTO concept_sounds SELECT concept, value FROM concepts, json_each(concepts.sounds) WHERE kind IN (SELECT value FROM json_each(?))",
                           [(json.dumps(FACETS["source_kinds"]),)])
    graphemes = connection.execute((SQL / "facet-grapheme-counts.sql").read_text(), (json.dumps(FACETS["source_kinds"]),)).fetchall()
    phonemes = connection.execute((SQL / "facet-phoneme-counts.sql").read_text()).fetchall()
    taught_spellings = {row[0] for row in connection.execute((SQL / "taught-spellings.sql").read_text())}
    taught_sounds = {row[0] for row in connection.execute((SQL / "taught-sounds.sql").read_text())}
    rows = [(grapheme_row(spelling, taught_spellings), count) for spelling, count in graphemes if spelling]
    rows += [(phoneme_row(sound, names, taught_sounds), count) for sound, count in phonemes]
    connection.executemany("INSERT INTO concepts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        (row.concept, row.label, row.kind, row.family, row.sort_key, row.spelling, json.dumps(row.sounds), int(row.tail))
        for row, _ in rows])
    connection.executemany("INSERT INTO facet_counts VALUES (?, ?)", [(row.concept, count) for row, count in rows])
    return len(rows)
