import json

from sqlalchemy import select, func, delete

from config import FREQ_STATS_EXAMPLE_COUNT
from db.tables import words, word_phonemes, word_graphemes, og_graphemes, freq_stats
from db.queries import group_rows
from .mappings import COMPOUND_PHONEMES, PHONEME_ALIASES


def _pct(part, whole):
    return round(100.0 * part / whole, 2) if whole else 0


def _build_stat_row(stat_type, key, word_freqs, total_words, total_weighted):
    """Build a single freq_stats row from a list of (word, zipf) pairs."""
    key1, key2 = key if isinstance(key, tuple) else (key, '')
    word_count = len(word_freqs)
    weighted = sum(f for _, f in word_freqs)
    word_freqs.sort(key=lambda x: x[1], reverse=True)
    return {
        'stat_type': stat_type, 'key1': key1, 'key2': key2,
        'word_count': word_count,
        'word_pct': _pct(word_count, total_words),
        'weighted_freq': weighted,
        'weighted_pct': _pct(weighted, total_weighted),
        'avg_zipf': round(weighted / word_count, 2) if word_count else 0,
        'example_words': json.dumps([w for w, _ in word_freqs[:FREQ_STATS_EXAMPLE_COUNT]]),
    }


def _matches_phoneme(phoneme_id, phoneme_set):
    """Check if a word's phoneme set matches a target (handling compounds and aliases)."""
    required = COMPOUND_PHONEMES.get(phoneme_id)
    if required:
        return required.issubset(phoneme_set)
    aliases = PHONEME_ALIASES.get(phoneme_id)
    if aliases:
        return bool(aliases & phoneme_set)
    return phoneme_id in phoneme_set


def _is_vce_match(word, vowel_part):
    """Check if word contains a vowel-consonant-e pattern with the given vowel."""
    w = word.lower()
    for i, ch in enumerate(w):
        if ch != vowel_part or i + 2 >= len(w):
            continue
        rest = w[i + 1:]
        if (len(rest) >= 2
                and rest[0] not in 'aeiou' and rest[0].isalpha()
                and rest[1] == 'e'
                and (len(rest) == 2 or not rest[2].isalpha() or rest[2] in 'sdr')):
            return True
    return False


def _find_og_pattern_matches(grapheme, phoneme_id, words_data, word_phoneme_sets):
    """Find words matching an OG grapheme-phoneme pattern via spelling scan."""
    if '_' in grapheme:
        vowel_part = grapheme.split('_')[0].lower()
        return [
            (word, zipf) for wid, (word, zipf) in words_data.items()
            if wid in word_phoneme_sets
            and phoneme_id in word_phoneme_sets[wid]
            and _is_vce_match(word, vowel_part)
        ]

    if len(grapheme) < 2:
        return []

    pattern = grapheme.lower()
    return [
        (word, zipf) for wid, (word, zipf) in words_data.items()
        if pattern in word.lower()
        and wid in word_phoneme_sets
        and _matches_phoneme(phoneme_id, word_phoneme_sets[wid])
    ]


def _load_word_phoneme_sets(conn):
    result = {}
    for row in conn.execute(select(word_phonemes.c.word_id, word_phonemes.c.og_phoneme_id)):
        result.setdefault(row.word_id, set()).add(row.og_phoneme_id)
    return result


def _compute_og_grapheme_stats(conn, total_words, total_weighted, stats_rows):
    """Fill in stats for OG grapheme-phoneme pairs missing from DB-level stats."""
    og_rows = conn.execute(
        select(og_graphemes.c.grapheme, og_graphemes.c.phoneme_id)
    ).fetchall()

    words_data = {
        row.id: (row.word, row.frequency_zipf)
        for row in conn.execute(select(words.c.id, words.c.word, words.c.frequency_zipf))
    }
    word_phoneme_sets = _load_word_phoneme_sets(conn)

    already_have = {
        (s['key1'], s['key2']) for s in stats_rows
        if s['stat_type'] == 'grapheme_phoneme' and s['word_count'] > 0
    }

    found = 0
    for og in og_rows:
        pair_key = (og.grapheme, og.phoneme_id)
        if pair_key in already_have:
            continue

        matches = _find_og_pattern_matches(og.grapheme, og.phoneme_id, words_data, word_phoneme_sets)
        if not matches:
            continue

        found += 1
        stats_rows[:] = [
            s for s in stats_rows
            if not (s['stat_type'] == 'grapheme_phoneme'
                    and s['key1'] == pair_key[0] and s['key2'] == pair_key[1])
        ]
        stats_rows.append(_build_stat_row('grapheme_phoneme', pair_key, matches, total_words, total_weighted))

    print(f"    Found {found} OG grapheme patterns via spelling scan")


def _aggregate_groups(conn, stat_type, query, key_fn, total_words, total_weighted):
    """Run a query, group by key, and return stat rows."""
    groups = group_rows(conn, query, key_fn, val_fn=lambda r: (r.word, r.frequency_zipf))
    return [
        _build_stat_row(stat_type, key, word_freqs, total_words, total_weighted)
        for key, word_freqs in groups.items()
    ]


def compute_freq_stats(conn, total_words):
    print("Computing frequency stats...")

    total_weighted = conn.execute(select(func.sum(words.c.frequency_zipf))).scalar()
    stats_rows = []

    print("  Phoneme stats...")
    stats_rows.extend(_aggregate_groups(
        conn, 'phoneme',
        select(word_phonemes.c.og_phoneme_id, words.c.word, words.c.frequency_zipf)
        .distinct()
        .join(words, words.c.id == word_phonemes.c.word_id),
        key_fn=lambda r: r.og_phoneme_id,
        total_words=total_words, total_weighted=total_weighted,
    ))

    print("  Grapheme stats...")
    stats_rows.extend(_aggregate_groups(
        conn, 'grapheme',
        select(word_graphemes.c.grapheme, words.c.word, words.c.frequency_zipf)
        .join(words, words.c.id == word_graphemes.c.word_id),
        key_fn=lambda r: r.grapheme,
        total_words=total_words, total_weighted=total_weighted,
    ))

    print("  Grapheme-phoneme pair stats...")
    stats_rows.extend(_aggregate_groups(
        conn, 'grapheme_phoneme',
        select(word_graphemes.c.grapheme, word_graphemes.c.og_phoneme_id, words.c.word, words.c.frequency_zipf)
        .join(words, words.c.id == word_graphemes.c.word_id)
        .where(word_graphemes.c.is_silent == 0),
        key_fn=lambda r: (r.grapheme, r.og_phoneme_id),
        total_words=total_words, total_weighted=total_weighted,
    ))

    print("  Silent grapheme stats...")
    stats_rows.extend(_aggregate_groups(
        conn, 'grapheme_silent',
        select(word_graphemes.c.grapheme, words.c.word, words.c.frequency_zipf)
        .join(words, words.c.id == word_graphemes.c.word_id)
        .where(word_graphemes.c.is_silent == 1),
        key_fn=lambda r: r.grapheme,
        total_words=total_words, total_weighted=total_weighted,
    ))

    print("  OG grapheme-phoneme stats (pattern matching)...")
    _compute_og_grapheme_stats(conn, total_words, total_weighted, stats_rows)

    print(f"  Inserting {len(stats_rows)} stat rows...")
    conn.execute(delete(freq_stats))
    conn.execute(freq_stats.insert(), stats_rows)
    conn.commit()
