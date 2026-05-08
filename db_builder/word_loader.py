import json
import os

from config import WORDS_JSON_PATH, G2P_ALIGNED_PATH, USE_OG_SYLLABLE_DIVIDER
from db.tables import words, word_phonemes, word_graphemes, word_syllables, word_pos
from .phoneme_converter import convert_phoneme_sequence, merge_alignment_with_og
from .syllable_analyzer import analyze_syllables
from .definition_loader import build_pos_lookup, build_defined_words
from .og_syllable_divider import og_divide, map_phonemes_to_og_syllables
from build_word_data import split_syllables, W_WORD, W_PHONEMES, W_ZIPF, W_PER_MILLION, W_RANK


def _split_syllables_hyphenated(word, phonemes, alignment):
    if not alignment:
        return split_syllables(phonemes, word=word)

    # Extract segment words from alignment
    seg_words = []
    current_word = []
    for g, arp in alignment:
        if g == '-':
            seg_words.append(''.join(current_word))
            current_word = []
        else:
            current_word.append(g)
    seg_words.append(''.join(current_word))

    segments = []
    count = 0
    for g, arp in alignment:
        if g == '-':
            segments.append(count)
            count = 0
        elif arp:
            count += len(arp.split('|'))
    segments.append(count)

    result = []
    offset = 0
    for seg_idx, seg_len in enumerate(segments):
        seg_phonemes = phonemes[offset:offset + seg_len]
        seg_word = seg_words[seg_idx] if seg_idx < len(seg_words) else None
        result.extend(split_syllables(seg_phonemes, word=seg_word))
        offset += seg_len
    return result


def _load_g2p():
    """Load g2p_aligned.json (compact: {word: [[grapheme, phoneme], ...]})."""
    if not os.path.exists(G2P_ALIGNED_PATH):
        print(f"  WARNING: {G2P_ALIGNED_PATH} not found.")
        return {}
    with open(G2P_ALIGNED_PATH, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    return {
        word: [[g, p or None] for g, p in pairs]
        for word, pairs in raw.items()
    }


def _word_row(word_id, w, syllable_count):
    return {
        'id': word_id, 'word': w[W_WORD], 'syllable_count': syllable_count,
        'frequency_zipf': w[W_ZIPF],
        'frequency_per_million': w[W_PER_MILLION],
        'frequency_rank': w[W_RANK],
    }


def _phoneme_rows(word_id, phonemes_raw):
    og_phonemes = convert_phoneme_sequence(phonemes_raw)
    return [
        {'word_id': word_id, 'position': pos, 'arpabet': arp, 'og_phoneme_id': og_id}
        for pos, (arp, og_id) in enumerate(og_phonemes)
    ]


def _grapheme_rows(word_id, alignment_raw):
    if not alignment_raw:
        return []
    merged = merge_alignment_with_og(alignment_raw)
    return [
        {'word_id': word_id, 'position': pos,
         'grapheme': grapheme, 'arpabet': arpabet,
         'og_phoneme_id': og_id, 'is_silent': is_silent}
        for pos, (grapheme, arpabet, og_id, is_silent) in enumerate(merged)
    ]


def _syllable_rows(word_id, word_entry):
    return [
        {'word_id': word_id, 'position': pos,
         'cv_pattern': syl['cv_pattern'], 'og_type': syl['og_type']}
        for pos, syl in enumerate(analyze_syllables(word_entry))
    ]


def _pos_rows(word_id, word_text, pos_lookup):
    return [
        {'word_id': word_id, 'pos': p}
        for p in pos_lookup.get(word_text, set())
    ]


def _insert_batch(conn, table, rows, label):
    print(f"  Inserting {len(rows)} {label}...")
    conn.execute(table.insert(), rows)


def load_words(conn):
    print("Loading words.json...")
    with open(WORDS_JSON_PATH, 'r') as f:
        word_list = json.load(f)

    total = len(word_list)
    print(f"  {total} words to insert")

    print("Loading grapheme-phoneme alignments...")
    g2p = _load_g2p()
    print(f"  Loaded alignments for {len(g2p)} words")

    print("Building POS lookup...")
    pos_lookup = build_pos_lookup()

    print("Filtering to words with definitions...")
    defined = build_defined_words()
    word_list = [w for w in word_list if w[W_WORD] in defined]
    skipped = total - len(word_list)
    total = len(word_list)
    print(f"  Kept {total} words ({skipped} without definitions removed)")

    all_word_rows = []
    all_phoneme_rows = []
    all_grapheme_rows = []
    all_syllable_rows = []
    all_pos_rows = []

    if USE_OG_SYLLABLE_DIVIDER:
        print("  Using OG orthographic syllable divider")
    else:
        print("  Using phoneme-based syllable divider (Kondrak/MOP)")

    for i, w in enumerate(word_list):
        wid = i + 1
        word_text = w[W_WORD]
        phonemes = w[W_PHONEMES]
        alignment = g2p.get(word_text)

        if USE_OG_SYLLABLE_DIVIDER:
            og_syls = og_divide(word_text)
            align_pairs = [[g, p or None] for g, p in alignment] if alignment else None
            syllables_phonemes = map_phonemes_to_og_syllables(
                og_syls, phonemes, align_pairs)
            syl_entry = {
                'word': word_text,
                'syllables_phonemes': syllables_phonemes,
                'alignment': align_pairs or [],
                'og_syllables': og_syls,
            }
        else:
            if '-' in word_text and alignment:
                syllables_phonemes = _split_syllables_hyphenated(word_text, phonemes, alignment)
            else:
                syllables_phonemes = split_syllables(phonemes, word=word_text)
            syl_entry = {
                'word': word_text,
                'syllables_phonemes': syllables_phonemes,
                'alignment': alignment or [],
            }

        all_word_rows.append(_word_row(wid, w, len(syllables_phonemes)))
        all_phoneme_rows.extend(_phoneme_rows(wid, phonemes))
        all_grapheme_rows.extend(_grapheme_rows(wid, alignment))
        all_syllable_rows.extend(_syllable_rows(wid, syl_entry))
        all_pos_rows.extend(_pos_rows(wid, word_text, pos_lookup))

    _insert_batch(conn, words, all_word_rows, "words")
    _insert_batch(conn, word_phonemes, all_phoneme_rows, "word-phoneme links")
    _insert_batch(conn, word_graphemes, all_grapheme_rows, "word-grapheme links")
    _insert_batch(conn, word_syllables, all_syllable_rows, "syllable records")
    _insert_batch(conn, word_pos, all_pos_rows, "POS records")

    conn.commit()
    return total
