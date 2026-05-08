"""Tag each word with the OG grapheme patterns it contains.

Uses the same matching logic as freq_stats pattern matching, but stores
results per-word in word_og_graphemes so they can be filtered/counted directly.

For graphemes already in word_graphemes (from g2p alignment), we use that data.
For graphemes NOT in word_graphemes (split digraphs, suffixes, welded sounds, etc.),
we use spelling+phoneme pattern matching.
"""

from sqlalchemy import select, func

from db.tables import (
    words, word_phonemes, word_graphemes, word_og_graphemes, og_graphemes,
)
from .mappings import COMPOUND_PHONEMES, PHONEME_ALIASES
from .phoneme_converter import arpabet_to_og_single


def _matches_phoneme(phoneme_id, phoneme_set):
    required = COMPOUND_PHONEMES.get(phoneme_id)
    if required:
        return required.issubset(phoneme_set)
    aliases = PHONEME_ALIASES.get(phoneme_id)
    if aliases:
        return bool(aliases & phoneme_set)
    return phoneme_id in phoneme_set


def _is_vce_match(word, vowel_part):
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


def load_og_grapheme_tags(conn):
    """Populate word_og_graphemes from word_graphemes + pattern matching."""
    print("Tagging words with OG grapheme patterns...")

    # Load all OG grapheme-phoneme pairs from reference
    og_pairs = conn.execute(
        select(og_graphemes.c.grapheme, og_graphemes.c.phoneme_id)
    ).fetchall()
    og_pair_set = {(r.grapheme, r.phoneme_id) for r in og_pairs}
    print(f"  {len(og_pair_set)} OG grapheme-phoneme pairs to match")

    # Step 1: Get pairs already in word_graphemes (from alignment)
    # These are authoritative — the g2p alignment confirmed these patterns
    alignment_pairs = set()
    for row in conn.execute(
        select(word_graphemes.c.grapheme, word_graphemes.c.og_phoneme_id)
        .distinct()
        .where(word_graphemes.c.is_silent == 0)
    ):
        if row.og_phoneme_id:
            alignment_pairs.add((row.grapheme, row.og_phoneme_id))

    # Which OG pairs are covered by alignment vs need pattern matching?
    covered = og_pair_set & alignment_pairs
    needs_pattern = og_pair_set - alignment_pairs
    print(f"  {len(covered)} pairs covered by alignment, {len(needs_pattern)} need pattern matching")

    # Step 2: For covered pairs, build word_og_graphemes from word_graphemes
    rows = []
    seen = set()  # (word_id, grapheme, phoneme_id) dedup

    for row in conn.execute(
        select(word_graphemes.c.word_id, word_graphemes.c.grapheme, word_graphemes.c.og_phoneme_id)
        .where(word_graphemes.c.is_silent == 0)
        .where(word_graphemes.c.og_phoneme_id != None)
    ):
        phoneme_id = row.og_phoneme_id
        pair = (row.grapheme, phoneme_id)
        if pair in og_pair_set:
            key = (row.word_id, row.grapheme, phoneme_id)
            if key not in seen:
                seen.add(key)
                rows.append({'word_id': row.word_id, 'grapheme': row.grapheme, 'phoneme_id': phoneme_id})
        elif '|' in phoneme_id:
            # Composite alignment (one grapheme mapped to multiple phonemes).
            # Try each component — the first match is the primary phoneme.
            for part in phoneme_id.split('|'):
                og_id = arpabet_to_og_single(part.upper())
                if (row.grapheme, og_id) in og_pair_set:
                    key = (row.word_id, row.grapheme, og_id)
                    if key not in seen:
                        seen.add(key)
                        rows.append({'word_id': row.word_id, 'grapheme': row.grapheme, 'phoneme_id': og_id})
                    break

    print(f"  {len(rows)} word-grapheme tags from alignment")

    # Step 3: For uncovered pairs, use pattern matching
    if needs_pattern:
        # Load word data for pattern matching
        words_data = {
            row.id: (row.word, row.frequency_zipf)
            for row in conn.execute(select(words.c.id, words.c.word, words.c.frequency_zipf))
        }
        word_phoneme_sets = {}
        for row in conn.execute(select(word_phonemes.c.word_id, word_phonemes.c.og_phoneme_id)):
            word_phoneme_sets.setdefault(row.word_id, set()).add(row.og_phoneme_id)

        pattern_count = 0
        for grapheme, phoneme_id in needs_pattern:
            # Split digraphs (a_e, i_e, etc.)
            if '_' in grapheme:
                vowel_part = grapheme.split('_')[0].lower()
                for wid, (word, zipf) in words_data.items():
                    if (wid in word_phoneme_sets
                            and phoneme_id in word_phoneme_sets[wid]
                            and _is_vce_match(word, vowel_part)):
                        key = (wid, grapheme, phoneme_id)
                        if key not in seen:
                            seen.add(key)
                            rows.append({'word_id': wid, 'grapheme': grapheme, 'phoneme_id': phoneme_id})
                            pattern_count += 1
            elif len(grapheme) >= 2:
                pattern = grapheme.lower()
                for wid, (word, zipf) in words_data.items():
                    if (pattern in word.lower()
                            and wid in word_phoneme_sets
                            and _matches_phoneme(phoneme_id, word_phoneme_sets[wid])):
                        key = (wid, grapheme, phoneme_id)
                        if key not in seen:
                            seen.add(key)
                            rows.append({'word_id': wid, 'grapheme': grapheme, 'phoneme_id': phoneme_id})
                            pattern_count += 1

        print(f"  {pattern_count} word-grapheme tags from pattern matching")

    # Step 4: Fill gaps — for words with incomplete tagging, use the raw
    # word_graphemes alignment to recover single-letter graphemes whose
    # og_phoneme_id was a composite (e.g. "b|ah") that step 2 couldn't
    # fully resolve, or that had no og_phoneme_id at all.
    tagged_words = {r['word_id'] for r in rows}
    all_word_ids = set(
        r.id for r in conn.execute(select(words.c.id))
    )
    untagged = all_word_ids - tagged_words

    if untagged:
        # For untagged words, try matching each letter in the word against
        # single-letter OG grapheme-phoneme pairs using the word's phoneme set
        word_phoneme_sets_local = {}
        for row in conn.execute(
            select(word_phonemes.c.word_id, word_phonemes.c.og_phoneme_id)
            .where(word_phonemes.c.word_id.in_(untagged))
        ):
            word_phoneme_sets_local.setdefault(row.word_id, set()).add(row.og_phoneme_id)

        single_og = {}  # letter -> set of phoneme_ids
        for g, ph in og_pair_set:
            if len(g) == 1:
                single_og.setdefault(g, set()).add(ph)

        words_text = {
            row.id: row.word
            for row in conn.execute(
                select(words.c.id, words.c.word).where(words.c.id.in_(untagged))
            )
        }

        gap_count = 0
        for wid, word in words_text.items():
            ph_set = word_phoneme_sets_local.get(wid, set())
            for ch in set(word.lower()):
                if ch in single_og:
                    for ph_id in single_og[ch]:
                        if _matches_phoneme(ph_id, ph_set):
                            key = (wid, ch, ph_id)
                            if key not in seen:
                                seen.add(key)
                                rows.append({'word_id': wid, 'grapheme': ch, 'phoneme_id': ph_id})
                                gap_count += 1
        print(f"  {gap_count} word-grapheme tags from gap fill ({len(untagged)} words)")

    print(f"  Inserting {len(rows)} total word-OG-grapheme tags...")
    conn.execute(word_og_graphemes.insert(), rows)
    conn.commit()
    return len(rows)
