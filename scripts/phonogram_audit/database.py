import sqlite3
from collections import defaultdict
from pathlib import Path

from .models import Word, WordInputs


SQL_DIRECTORY = Path(__file__).resolve().parents[1] / "sql"


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.execute((SQL_DIRECTORY / "audit_readonly.sql").read_text())
    return connection


def query(connection: sqlite3.Connection, name: str) -> list[tuple]:
    return connection.execute((SQL_DIRECTORY / name).read_text()).fetchall()


def grouped(connection: sqlite3.Connection, name: str) -> dict[int, list]:
    rows = defaultdict(list)
    for key, *values in query(connection, name):
        rows[key].append(tuple(values))
    return dict(rows)


def load_inputs(path: Path) -> WordInputs:
    with connect_readonly(path) as connection:
        words = [Word(*row) for row in query(connection, "audit_words.sql")]
        graphemes = grouped(connection, "audit_graphemes.sql")
        morphemes = grouped(connection, "audit_morphemes.sql")
        phonemes = grouped(connection, "audit_phonemes.sql")
        syllables = grouped(connection, "audit_syllables.sql")
        pos = grouped(connection, "audit_pos.sql")
    return WordInputs(
        words, graphemes, {key: [row[0] for row in rows] for key, rows in phonemes.items()},
        {key: [dict(cv_pattern=row[0], og_type=row[1]) for row in rows]
         for key, rows in syllables.items()}, morphemes,
        {key: [row[0] for row in rows] for key, rows in pos.items()},
    )
