import json
import os
from collections import defaultdict

from sqlalchemy import select

from config import WIKTIONARY_PATH, MAX_DEFINITIONS_PER_WORD
from db.tables import words, word_definitions

# wiktionary_parsed.json column indices: [pos, definition, example]
_POS, _DEF, _EX = 0, 1, 2


def _load_wiktionary():
    """Load wiktionary data, returning (definitions_dict, pos_lookup)."""
    if not os.path.exists(WIKTIONARY_PATH):
        print(f"  WARNING: {WIKTIONARY_PATH} not found. Run the Wiktionary parser first.")
        return {}, {}

    with open(WIKTIONARY_PATH, 'r') as f:
        wikt = json.load(f)
    print(f"  Wiktionary has {len(wikt):,} words")

    pos_lookup = defaultdict(set)
    for word_text, defs in wikt.items():
        for d in defs:
            if d[_POS]:
                pos_lookup[word_text].add(d[_POS])

    return wikt, pos_lookup


def build_pos_lookup():
    """Build POS lookup from Wiktionary data."""
    _, pos_lookup = _load_wiktionary()
    print(f"  POS lookup: {len(pos_lookup)} words from Wiktionary")
    return pos_lookup


_NAME_ONLY_PREFIXES = (
    'a surname', 'a female given name', 'a male given name',
    'a given name', 'a place name',
)


def _is_name_only(defs):
    """True if all definitions are just name/surname entries."""
    texts = [d[_DEF].strip().lower().rstrip('.') for d in defs if d[_DEF]]
    if not texts:
        return True
    return all(any(t.startswith(p) for p in _NAME_ONLY_PREFIXES) for t in texts)


def build_defined_words():
    """Return the set of words that have at least one real (non-name-only) definition."""
    wikt, _ = _load_wiktionary()
    return {word for word, defs in wikt.items() if not _is_name_only(defs)}


def load_definitions(conn):
    all_words = conn.execute(select(words.c.id, words.c.word)).fetchall()
    word_lookup = {r.word: r.id for r in all_words}

    wikt, _ = _load_wiktionary()

    batch = []
    defined = set()

    for word_text, defs in wikt.items():
        word_id = word_lookup.get(word_text)
        if not word_id or not defs:
            continue
        defined.add(word_text)
        for i, d in enumerate(defs[:MAX_DEFINITIONS_PER_WORD]):
            batch.append({
                'word_id': word_id, 'position': i,
                'pos': d[_POS] or None, 'definition': d[_DEF],
                'example': d[_EX] or None,
            })

    print(f"  Wiktionary: {len(defined):,} words ({len(defined) * 100 // len(word_lookup)}%)")

    conn.execute(word_definitions.insert(), batch)
    conn.commit()
    print(f"  Total: {len(batch):,} definitions for {len(defined):,} words ({len(defined) * 100 // len(word_lookup)}% coverage)")
