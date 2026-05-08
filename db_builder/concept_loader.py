from collections import defaultdict

from sqlalchemy import select

from db.tables import words, word_graphemes, word_phonemes, word_syllables, word_morphemes, word_concepts
from db.queries import group_rows
from .concept_detector import detect_concepts


def _load_all_word_data(conn):
    """Load all per-word data needed for concept detection, grouped by word_id."""
    graphemes = group_rows(
        conn,
        select(word_graphemes.c.word_id, word_graphemes.c.grapheme,
               word_graphemes.c.arpabet, word_graphemes.c.og_phoneme_id,
               word_graphemes.c.is_silent)
        .order_by(word_graphemes.c.word_id, word_graphemes.c.position),
        key_fn=lambda r: r.word_id,
        val_fn=lambda r: (r.grapheme, r.arpabet, r.og_phoneme_id, r.is_silent),
    )

    phonemes = group_rows(
        conn,
        select(word_phonemes.c.word_id, word_phonemes.c.og_phoneme_id)
        .order_by(word_phonemes.c.word_id, word_phonemes.c.position),
        key_fn=lambda r: r.word_id,
        val_fn=lambda r: r.og_phoneme_id,
    )

    syllables = group_rows(
        conn,
        select(word_syllables.c.word_id, word_syllables.c.cv_pattern, word_syllables.c.og_type)
        .order_by(word_syllables.c.word_id, word_syllables.c.position),
        key_fn=lambda r: r.word_id,
        val_fn=lambda r: {'cv_pattern': r.cv_pattern, 'og_type': r.og_type},
    )

    morphemes = group_rows(
        conn,
        select(word_morphemes.c.word_id, word_morphemes.c.morpheme, word_morphemes.c.morpheme_type)
        .order_by(word_morphemes.c.word_id, word_morphemes.c.position),
        key_fn=lambda r: r.word_id,
        val_fn=lambda r: (r.morpheme, r.morpheme_type),
    )

    return graphemes, phonemes, syllables, morphemes


def load_concepts(conn):
    print("Detecting OG concepts...")

    all_words = conn.execute(select(words.c.id, words.c.word, words.c.syllable_count)).fetchall()
    all_graphemes, all_phonemes, all_syllables, all_morphemes = _load_all_word_data(conn)

    concept_rows = []
    concept_counts = defaultdict(int)

    for w in all_words:
        wid = w.id
        syllables_phonemes = [[] for _ in range(w.syllable_count)]

        concepts = detect_concepts(
            w.word,
            all_graphemes.get(wid, []),
            all_phonemes.get(wid, []),
            syllables_phonemes,
            all_syllables.get(wid, []),
            all_morphemes.get(wid, []),
        )

        for c in concepts:
            concept_rows.append({'word_id': wid, 'concept': c})
            concept_counts[c] += 1

    print(f"  Inserting {len(concept_rows)} concept tags...")
    conn.execute(word_concepts.insert(), concept_rows)
    conn.commit()

    print(f"  {len(concept_counts)} unique concepts detected")
    for c, cnt in sorted(concept_counts.items(), key=lambda x: -x[1])[:25]:
        print(f"    {c:30s} {cnt:,} words")
