import json
import os
from collections import defaultdict

from sqlalchemy import select, update

from config import SIGHT_WORDS_PATH, SIGHT_WORD_SOURCES_NO_GRADE, SIGHT_WORD_SOURCES_WITH_GRADE
from db.tables import words, word_graphemes, sight_words, og_phonemes, og_graphemes
from db.queries import batch_fetch
from .mappings import PRIMARY_SOUND


def load_sight_words(conn):
    if not os.path.exists(SIGHT_WORDS_PATH):
        print("  No sight_words.json found, skipping")
        return

    with open(SIGHT_WORDS_PATH, 'r') as f:
        data = json.load(f)

    rows = []
    for word, sources in data['words'].items():
        for src_key, src_val in sources.items():
            if src_key in SIGHT_WORD_SOURCES_NO_GRADE:
                rows.append({'word': word, 'source': src_key, 'grade_level': None})
            elif src_key in SIGHT_WORD_SOURCES_WITH_GRADE:
                rows.append({'word': word, 'source': src_key, 'grade_level': src_val})

    conn.execute(sight_words.insert().prefix_with('OR IGNORE'), rows)
    conn.commit()

    unique_words = len(data['words'])
    src_counts = {}
    for s in data['words'].values():
        for k in s:
            src_counts[k] = src_counts.get(k, 0) + 1
    parts = ', '.join(f"{v} {k}" for k, v in sorted(src_counts.items(), key=lambda x: -x[1]))
    print(f"  Loaded {unique_words} sight words ({parts})")


def _load_sound_data(conn):
    """Load expected grapheme->phoneme mappings and phoneme display names from DB."""
    phoneme_names = {
        r.id: r.sound
        for r in conn.execute(select(og_phonemes))
    }
    expected = defaultdict(set)
    for r in conn.execute(select(og_graphemes.c.grapheme, og_graphemes.c.phoneme_id)):
        expected[r.grapheme].add(r.phoneme_id)
    return expected, phoneme_names


def _classify_grapheme(grapheme, og_id, is_silent, expected, phoneme_names):
    """Return an irregularity reason string for one grapheme, or None if regular."""
    g = grapheme.lower()
    sname = lambda oid: phoneme_names.get(oid, oid)

    if is_silent:
        return f'"{grapheme}" is silent'
    if og_id is None:
        return None

    primary = PRIMARY_SOUND.get(g)
    expected_sounds = expected.get(g, set())

    if og_id in expected_sounds:
        if primary and og_id != primary:
            return f'"{grapheme}" makes /{sname(og_id)}/ (usually /{sname(primary)}/)'
        return None

    if primary:
        return f'"{grapheme}" makes /{sname(og_id)}/ instead of /{sname(primary)}/'
    return f'"{grapheme}" making /{sname(og_id)}/ is an unusual pattern'


def _compute_word_reasons(alignment_rows, expected, phoneme_names):
    """Compute irregularity reasons for one word's alignment."""
    reasons = [
        _classify_grapheme(a.grapheme, a.og_phoneme_id, a.is_silent, expected, phoneme_names)
        for a in alignment_rows
    ]
    return [r for r in reasons if r]


def compute_irregularity_reasons(conn):
    expected, phoneme_names = _load_sound_data(conn)

    sight_word_texts = [
        r.word for r in conn.execute(
            select(sight_words.c.word).distinct()
            .join(words, words.c.word == sight_words.c.word)
        )
    ]
    if not sight_word_texts:
        return

    word_id_map = {
        r.word: r.id for r in conn.execute(
            select(words.c.id, words.c.word).where(words.c.word.in_(sight_word_texts))
        )
    }
    word_ids = list(word_id_map.values())

    alignment_map = batch_fetch(
        conn, word_graphemes, word_ids,
        order_by=(word_graphemes.c.word_id, word_graphemes.c.position),
    )

    reasons_data = {}
    for word_text in sight_word_texts:
        wid = word_id_map.get(word_text)
        if not wid:
            continue
        alignment = alignment_map.get(wid, [])
        if not alignment:
            continue
        reasons = _compute_word_reasons(alignment, expected, phoneme_names)
        if reasons:
            reasons_data[word_text] = reasons

    for word_text, reasons in reasons_data.items():
        conn.execute(
            update(sight_words).where(sight_words.c.word == word_text)
            .values(irregularity_reason=json.dumps(reasons))
        )
    conn.commit()
    print(f"  Computed irregularity reasons for {len(reasons_data)} words")
