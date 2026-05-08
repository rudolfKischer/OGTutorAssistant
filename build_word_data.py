"""
Build the master word dataset: phonemes, syllables, frequency.

Outputs data/words.json — array of [word, [phonemes], zipf, per_million, rank].

Sources:
- CMU Pronouncing Dictionary via cmudict package (phonemes + syllable structure)
- wordfreq (frequency data from multiple corpora)
"""

import json
import os

import cmudict
from wordfreq import zipf_frequency, word_frequency

from config import WORDS_JSON_PATH, DATA_DIR
from db_builder.mappings import (
    CONTRACTION_SUFFIXES, VALID_S_CONTRACTIONS,
    VALID_APOSTROPHE_WORDS, ARPABET_TO_OG,
)

VALID_ARPABET = set(ARPABET_TO_OG.keys())

# words.json column indices
W_WORD, W_PHONEMES, W_ZIPF, W_PER_MILLION, W_RANK = range(5)


def _is_keepable_apostrophe(word):
    """Return True if an apostrophe word should be kept in the dataset."""
    if word.startswith("'") or word.endswith("'"):
        return False
    if word in VALID_APOSTROPHE_WORDS:
        return True
    if word.endswith("'s"):
        return word in VALID_S_CONTRACTIONS
    return any(word.endswith(s) for s in CONTRACTION_SUFFIXES if s != "'s")


def _is_valid_word(word):
    """Check if a word passes all CMU dict filters."""
    if '.' in word:
        return False
    if not all(c.isalpha() or c in "-'" for c in word):
        return False
    if "'" in word and not _is_keepable_apostrophe(word):
        return False
    return True


def _has_valid_phonemes(phonemes):
    return all(p.rstrip('012') in VALID_ARPABET for p in phonemes)


def _load_cmu_dict():
    """Load CMU dict via cmudict package, filtering to valid words."""
    raw = cmudict.dict()
    result = {}
    skipped = 0
    for word, pronunciations in raw.items():
        if not _is_valid_word(word) or not _has_valid_phonemes(pronunciations[0]):
            skipped += 1
            continue
        result[word] = pronunciations[0]
    print(f"  Skipped {skipped} entries (abbreviations, foreign words, etc.)")
    return result


def is_vowel_phoneme(phoneme):
    return any(c.isdigit() for c in phoneme)


def _load_syllabified_cmudict():
    """Load the Kondrak syllabified CMU dict (phoneme-level syllable boundaries)."""
    path = os.path.join(DATA_DIR, 'cmudict_syllabified.rep')
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('##'):
                continue
            parts = line.split('  ', 1)
            if len(parts) != 2:
                continue
            word = parts[0].strip().lower()
            if '(' in word:
                continue
            phoneme_str = parts[1].strip()
            syllables = [s.strip().split() for s in phoneme_str.split(' - ')]
            result[word] = syllables
    return result


_SYLLABIFIED = None


def _get_syllabified():
    global _SYLLABIFIED
    if _SYLLABIFIED is None:
        _SYLLABIFIED = _load_syllabified_cmudict()
    return _SYLLABIFIED


# Legal English onset clusters in ARPABET (Maximum Onset Principle).
# Any single consonant is a legal onset. Multi-consonant onsets listed here.
_LEGAL_ONSETS = {
    # Stop + liquid/glide
    ('P', 'L'), ('P', 'R'), ('B', 'L'), ('B', 'R'),
    ('T', 'R'), ('T', 'W'), ('D', 'R'), ('D', 'W'),
    ('K', 'L'), ('K', 'R'), ('K', 'W'), ('G', 'L'), ('G', 'R'),
    # Fricative + liquid/glide
    ('F', 'L'), ('F', 'R'), ('TH', 'R'), ('TH', 'W'),
    ('SH', 'R'), ('HH', 'Y'), ('HH', 'W'),
    # S + stop
    ('S', 'P'), ('S', 'T'), ('S', 'K'),
    # S + nasal/liquid/glide
    ('S', 'M'), ('S', 'N'), ('S', 'L'), ('S', 'W'), ('S', 'F'),
    # S + stop + liquid/glide (3-consonant onsets)
    ('S', 'P', 'L'), ('S', 'P', 'R'), ('S', 'T', 'R'),
    ('S', 'K', 'R'), ('S', 'K', 'W'),
    # SH clusters
    ('SH', 'M'), ('SH', 'N'), ('SH', 'L'), ('SH', 'W'),
    ('SH', 'T'), ('SH', 'P'), ('SH', 'R'),  # loanwords (schm-, schn-, etc.)
    ('SH', 'T', 'R'), ('SH', 'P', 'R'),
}


def _is_legal_onset(consonants):
    """Check if a consonant sequence is a legal English syllable onset."""
    if len(consonants) <= 1:
        return True
    bases = tuple(c.rstrip('012') for c in consonants)
    return bases in _LEGAL_ONSETS


def _mop_split(phonemes):
    """Split phonemes into syllables using the Maximum Onset Principle.

    Each syllable has exactly one vowel nucleus. Consonants between vowels
    are assigned to the following syllable's onset as much as possible,
    subject to English phonotactic constraints.
    """
    # Find vowel positions
    vowel_indices = [i for i, ph in enumerate(phonemes) if is_vowel_phoneme(ph)]
    if not vowel_indices:
        return [list(phonemes)] if phonemes else []
    if len(vowel_indices) == 1:
        return [list(phonemes)]

    syllables = []
    prev_end = 0  # start of current syllable

    for vi in range(len(vowel_indices) - 1):
        v_pos = vowel_indices[vi]
        next_v_pos = vowel_indices[vi + 1]

        # Consonants between this vowel and the next
        consonants = phonemes[v_pos + 1:next_v_pos]

        if len(consonants) == 0:
            # Adjacent vowels — split between them
            syllables.append(list(phonemes[prev_end:v_pos + 1]))
            prev_end = v_pos + 1
        else:
            # Find the maximal legal onset for the next syllable
            # Try giving all consonants to onset, then reduce
            split_at = v_pos + 1  # default: all consonants go to coda
            for onset_start in range(len(consonants)):
                candidate_onset = consonants[onset_start:]
                if _is_legal_onset(candidate_onset):
                    split_at = v_pos + 1 + onset_start
                    break

            syllables.append(list(phonemes[prev_end:split_at]))
            prev_end = split_at

    # Last syllable gets everything remaining
    syllables.append(list(phonemes[prev_end:]))
    return syllables


def _try_compound_split(word, phonemes, syl_db):
    """Try splitting a word into two known sub-words in the syllabified dict.

    Only returns a result when BOTH parts are found and phoneme counts match.
    """
    for split_pos in range(2, len(word) - 1):
        left_syls = syl_db.get(word[:split_pos])
        if not left_syls:
            continue
        left_count = sum(len(s) for s in left_syls)
        if left_count >= len(phonemes):
            continue
        right_syls = syl_db.get(word[split_pos:])
        if right_syls and left_count + sum(len(s) for s in right_syls) == len(phonemes):
            return [list(s) for s in left_syls] + [list(s) for s in right_syls]
    return None


def split_syllables(phonemes, word=None):
    """Split phonemes into syllables.

    1. Kondrak syllabified CMU dict lookup (94.5% of words)
    2. Compound decomposition — both parts must be in dict (covers compounds)
    3. Maximum Onset Principle fallback (linguistically principled)
    """
    if word:
        syl_db = _get_syllabified()
        clean = word.lower().replace('-', '').replace("'", '')
        lookup = syl_db.get(clean)
        if lookup:
            flat = [ph for syl in lookup for ph in syl]
            if len(flat) == len(phonemes):
                return [list(syl) for syl in lookup]

        result = _try_compound_split(clean, phonemes, syl_db)
        if result:
            return result

    return _mop_split(phonemes)


def _print_stats(dataset):
    size_mb = os.path.getsize(WORDS_JSON_PATH) / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")

    print(f"\nStats:")
    print(f"  Total words: {len(dataset)}")
    for n in (1, 2, 3):
        count = sum(1 for w in dataset if len(split_syllables(w[W_PHONEMES])) == n)
        print(f"  {n}-syllable: {count}")
    count4 = sum(1 for w in dataset if len(split_syllables(w[W_PHONEMES])) >= 4)
    print(f"  4+ syllable: {count4}")


def build_dataset():
    print("Loading CMU dict...")
    cmu = _load_cmu_dict()
    print(f"Loaded {len(cmu)} words from CMU dict")

    print("Computing word frequencies...")
    word_entries = [
        (word, phonemes, zipf_frequency(word, 'en'), round(word_frequency(word, 'en') * 1e6, 2))
        for word, phonemes in cmu.items()
    ]
    word_entries.sort(key=lambda x: x[2], reverse=True)

    print("Building final dataset...")
    dataset = [
        [word, phonemes, round(freq, 2), per_million, rank]
        for rank, (word, phonemes, freq, per_million) in enumerate(word_entries, 1)
    ]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(WORDS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=None, separators=(',', ':'))

    print(f"Wrote {len(dataset)} words to {WORDS_JSON_PATH}")
    _print_stats(dataset)


if __name__ == '__main__':
    build_dataset()
