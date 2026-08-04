"""Extracts the two "hot path" lookups (concept -> words, sight-word
membership) out of the full authoring database into a small standalone
JSON artifact production can load straight into memory, without needing
words.db (and its phoneme/grapheme/syllable/morpheme tables) at runtime.

Run this whenever build_word_db.py is re-run and the change should reach
production - it's a separate, deliberate step, not wired into build_word_db.py
itself, since production shouldn't silently pick up an in-progress rebuild.
"""
import json
import os

from sqlalchemy import select

from config import DB_PATH, PRODUCTION_CACHE_PATH
from db.connection import get_engine
from db.tables import words, word_concepts, sight_words


def build_cache():
    engine = get_engine(DB_PATH)
    with engine.connect() as conn:
        concept_to_words = {}
        for row in conn.execute(
            select(word_concepts.c.concept, words.c.word)
            .select_from(word_concepts.join(words, words.c.id == word_concepts.c.word_id))
            .order_by(word_concepts.c.concept, words.c.word)
        ):
            concept_to_words.setdefault(row.concept, []).append(row.word)

        sight_word_list = sorted({
            row.word for row in conn.execute(select(sight_words.c.word).distinct())
        })

    cache = {
        'concept_to_words': concept_to_words,
        'sight_words': sight_word_list,
    }

    with open(PRODUCTION_CACHE_PATH, 'w') as f:
        json.dump(cache, f)

    size_kb = os.path.getsize(PRODUCTION_CACHE_PATH) / 1024
    print(f"  {len(concept_to_words)} concepts, {sum(len(v) for v in concept_to_words.values()):,} concept-word pairs")
    print(f"  {len(sight_word_list)} sight words")
    print(f"Production cache: {PRODUCTION_CACHE_PATH} ({size_kb:.1f} KB)")


if __name__ == '__main__':
    build_cache()
