import os

from sqlalchemy import select, func

from config import DB_PATH
from db.connection import get_engine, create_tables
from db.tables import (
    words, word_phonemes, word_graphemes, word_syllables,
    word_pos, word_morphemes, word_concepts, sight_words,
    og_phonemes, og_graphemes, word_og_graphemes,
)
from db_builder.word_loader import load_words
from db_builder.og_reference_loader import load_og_reference
from db_builder.morpheme_loader import load_morphemes
from db_builder.concept_loader import load_concepts
from db_builder.definition_loader import load_definitions
from db_builder.sight_word_loader import load_sight_words, compute_irregularity_reasons
from db_builder.og_grapheme_tagger import load_og_grapheme_tags

SUMMARY_TABLES = [
    words, word_phonemes, word_graphemes, word_syllables,
    word_pos, word_morphemes, word_concepts, sight_words,
    og_phonemes, og_graphemes, word_og_graphemes,
]


def print_summary(conn):
    print("\n=== Database Summary ===")
    for table in SUMMARY_TABLES:
        count = conn.execute(select(func.count()).select_from(table)).scalar()
        print(f"  {table.name}: {count:,} rows")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    engine = get_engine(DB_PATH, wal=True)
    create_tables(engine)

    with engine.connect() as conn:
        total = load_words(conn)
        load_og_reference(conn)
        load_morphemes(conn)
        load_concepts(conn)
        load_definitions(conn)
        print("Loading sight words...")
        load_sight_words(conn)
        print("Computing irregularity reasons...")
        compute_irregularity_reasons(conn)
        load_og_grapheme_tags(conn)
        print_summary(conn)

    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\nDatabase: {DB_PATH} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
