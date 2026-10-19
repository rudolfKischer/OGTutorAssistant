import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
RELATED_KINDS = ("phonogram", "unmodeled")


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def load() -> dict:
    overlay = connect(REPOSITORY / "data/explorer-concepts.sqlite")
    with closing(connect(REPOSITORY / "data/words.db")) as words, closing(overlay):
        base = {row[0]: row[1:] for row in words.execute("SELECT id, word, frequency_rank, frequency_per_million FROM words")}
        flags: dict[int, set[str]] = defaultdict(set)
        for word_id, flag in overlay.execute("SELECT word_id, flag FROM word_origin_flags"):
            flags[word_id].add(flag)
        kinds = dict(overlay.execute("SELECT concept, kind FROM concepts"))
        concepts: dict[int, set[str]] = defaultdict(set)
        for word_id, concept in overlay.execute("SELECT word_id, concept FROM word_concepts"):
            if kinds.get(concept) in RELATED_KINDS:
                concepts[word_id].add(concept)
        sight = {row[0] for row in words.execute("SELECT DISTINCT w.id FROM words w JOIN sight_words s ON s.word = w.word")}
        status = dict(overlay.execute("SELECT word_id, status FROM word_analysis"))
    return {"words": base, "flags": flags, "concepts": concepts, "kinds": kinds, "status": status, "sight": sight}
