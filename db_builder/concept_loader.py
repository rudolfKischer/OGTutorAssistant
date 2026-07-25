from collections import defaultdict

from sqlalchemy import select

from db.tables import words, word_graphemes, word_phonemes, word_syllables, word_morphemes, word_pos, word_concepts
from db.queries import group_rows
from .concept_detector import detect_concepts, is_111_doubling_base, is_final_e_base


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


def _load_pos(conn):
    return group_rows(
        conn,
        select(word_pos.c.word_id, word_pos.c.pos),
        key_fn=lambda r: r.word_id,
        val_fn=lambda r: r.pos,
    )


# These suffixing rules (1-1-1 doubling, Final E) only make sense for words
# that actually take the suffix (verbs take -ing/-ed, adjectives take
# -er/-est). Without this, the word list's many noun fragments/abbreviations
# and loanwords (e.g. "cal", "tel", "wil", "karate", "recipe") would falsely
# match as the reconstructed base of unrelated words - see each
# `_compute_*_base_words` docstring for a concrete example.
BASE_POS = {'verb', 'adj'}

# Below this, a "base word" is either too obscure/dialectal to be a sane
# example (e.g. "ane", "gae", "germane" - all under 2.7) or, worse, coincides
# with a completely unrelated common word (germany -> "german" + e =
# "germane", by -> "b" + e = "be"). Reconstructed bases must clear this to be
# usable, even though it costs some legitimate but rare vocabulary (e.g.
# "deplete", "finagle") - for a tutoring tool, a missed rare word is far
# better than a common word wrongly flagged as demonstrating a rule it
# doesn't follow.
MIN_BASE_FREQUENCY_ZIPF = 3.0


def _compute_111_base_words(all_words, all_phonemes, all_pos):
    """Spellings that independently satisfy the 1-1-1 doubling-base checklist.

    Used to recognize words that SHOW the rule applied (running, sitting) by
    reconstructing their base (run, sit) and checking it against this set -
    see `_detect_doubled_word` in concept_detector.py.
    """
    bases = set()
    for w in all_words:
        if w.frequency_zipf < MIN_BASE_FREQUENCY_ZIPF:
            continue
        if not BASE_POS.intersection(all_pos.get(w.id, ())):
            continue
        spelling = w.word.lower()
        if is_111_doubling_base(spelling, all_phonemes.get(w.id, []), w.syllable_count):
            bases.add(spelling)
    return bases


def _compute_final_e_base_words(all_words, all_pos):
    """Spellings that independently satisfy the Final E rule's base checklist.

    Used to recognize words that SHOW the rule applied (basing) by
    reconstructing their base (base) and checking it against this set - see
    `_detect_final_e_word` in concept_detector.py. Same POS/frequency
    rationale as `_compute_111_base_words`.
    """
    bases = set()
    for w in all_words:
        if w.frequency_zipf < MIN_BASE_FREQUENCY_ZIPF:
            continue
        if not BASE_POS.intersection(all_pos.get(w.id, ())):
            continue
        spelling = w.word.lower()
        if is_final_e_base(spelling):
            bases.add(spelling)
    return bases


def load_concepts(conn):
    print("Detecting OG concepts...")

    all_words = conn.execute(
        select(words.c.id, words.c.word, words.c.syllable_count, words.c.frequency_zipf)
    ).fetchall()
    all_graphemes, all_phonemes, all_syllables, all_morphemes = _load_all_word_data(conn)
    all_pos = _load_pos(conn)
    base_words_111 = _compute_111_base_words(all_words, all_phonemes, all_pos)
    base_words_final_e = _compute_final_e_base_words(all_words, all_pos)

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
            base_words_111,
            base_words_final_e,
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
