"""Extracts the two "hot path" lookups (concept -> words, sight-word
membership) out of the full authoring database into a small standalone
JSON artifact production can load straight into memory, without needing
words.db (and its phoneme/grapheme/syllable/morpheme tables) at runtime.

Run this whenever build_word_db.py is re-run and the change should reach
production - it's a separate, deliberate step, not wired into build_word_db.py
itself, since production shouldn't silently pick up an in-progress rebuild.
"""
import csv
import json
import os

from sqlalchemy import select

from config import DB_PATH, PRODUCTION_CACHE_PATH, PRODUCTION_CACHE_KEYS_PATH, UI_CONFIG_PATH
from db.connection import get_engine
from db.tables import words, word_concepts, sight_words


def _concept_name(concept_id, labels):
    if concept_id in labels:
        return labels[concept_id]
    if concept_id.startswith('pattern_'):
        return concept_id[len('pattern_'):]
    if concept_id.startswith('blend_initial_'):
        return concept_id[len('blend_initial_'):] + '- blend'
    return ''


# Concept groups, in addition to the "Irregular Words" group applied to the
# separate sight-word list. Everything defaults to "Other Phonograms"; only
# the families below are carved out into the other named groups.
SYLLABLE_TYPE_IDS = {
    'closed_syllable', 'open_syllable', 'vce_syllable',
    'vowel_team_syllable', 'r_controlled_syllable', 'cle_syllable',
}
SPELLING_RULE_IDS = {
    'doubling_rule_111', 'doubling_rule_211', 'final_e_rule', 'final_y_rule',
    'cle_rule_double', 'cle_rule_single', 'floss',
}
SPELLING_RULE_PREFIXES = ('magic_e_',)
MORPHOLOGY_BASE_PREFIXES = ('morph_root_',)
MORPHOLOGY_AFFIX_PREFIXES = ('morph_prefix_', 'morph_suffix_')
SYLLABLE_DIVISION_PREFIX = 'syllable_div_'

# The initial single-letter sounds taught first in an OG scope and sequence.
BASIC_PHONOGRAM_IDS = {
    'phoneme_short_a', 'phoneme_m', 'phoneme_s', 'phoneme_n', 'phoneme_f',
    'phoneme_short_i', 'phoneme_t', 'phoneme_l', 'phoneme_h', 'phoneme_p',
    'phoneme_short_o', 'hard_c', 'phoneme_r', 'phoneme_d', 'phoneme_short_u',
    'phoneme_g', 'phoneme_w', 'phoneme_b', 'phoneme_v', 'phoneme_short_e',
    'phoneme_j', 'phoneme_k', 'x_as_ks', 'phoneme_y', 'phoneme_z',
}
BLEND_PHONOGRAM_PREFIXES = ('blend_initial_', 'blend_final_')
# "-ild/-ind/-old/-oll/-ost" endings carry a long vowel sound, same family as
# the ng/nk endings below.
ENDING_PHONOGRAM_IDS = {'ild_as_i', 'ind_as_i', 'old_as_o', 'oll_as_o', 'ost_as_o'}
ENDING_PHONOGRAM_PREFIXES = ('ng_ending_', 'nk_ending_')
LONG_VOWEL_PHONOGRAM_IDS = {'u_as_long_oo', 'y_as_long_e', 'y_as_long_i', 'y_as_short_i'}
LONG_VOWEL_PHONOGRAM_PREFIX = 'phoneme_long_'
# R-controlled and diphthong-ish phonemes join the vowel-team concepts
# proper; 'r_controlled_syllable' is excluded by the earlier syllable-type
# check, so it still lands in Syllables rather than here.
VOWEL_TEAM_PHONOGRAM_IDS = {
    'bossy_r_ir', 'bossy_r_ur',
    'phoneme_air', 'phoneme_ar', 'phoneme_aw', 'phoneme_ear', 'phoneme_er',
    'phoneme_or', 'phoneme_ow', 'phoneme_oy', 'phoneme_short_oo',
    'r_controlled_air', 'r_controlled_ar', 'r_controlled_ear',
    'r_controlled_er', 'r_controlled_or',
}
VOWEL_TEAM_PHONOGRAM_PREFIX = 'vowel_team_'


def _concept_group(concept_id):
    if concept_id in SYLLABLE_TYPE_IDS:
        return 'Syllables'
    if concept_id.startswith('pattern_'):
        return 'Consonant-Vowel Word Structure Patterns'
    if concept_id.startswith(SYLLABLE_DIVISION_PREFIX):
        return 'Syllable Division Rules'
    if concept_id in SPELLING_RULE_IDS or concept_id.startswith(SPELLING_RULE_PREFIXES):
        return 'Spelling Rules'
    if concept_id.startswith(MORPHOLOGY_BASE_PREFIXES):
        return 'Morphology - Base Words'
    if concept_id.startswith(MORPHOLOGY_AFFIX_PREFIXES):
        return 'Morphology - Prefixes/Suffixes'
    if concept_id in BASIC_PHONOGRAM_IDS:
        return 'Basic Phonograms'
    if concept_id.startswith(BLEND_PHONOGRAM_PREFIXES):
        return 'Blends'
    if concept_id in ENDING_PHONOGRAM_IDS or concept_id.startswith(ENDING_PHONOGRAM_PREFIXES):
        return 'Endings'
    if concept_id in LONG_VOWEL_PHONOGRAM_IDS or concept_id.startswith(LONG_VOWEL_PHONOGRAM_PREFIX):
        return 'Long Vowels'
    if concept_id in VOWEL_TEAM_PHONOGRAM_IDS or concept_id.startswith(VOWEL_TEAM_PHONOGRAM_PREFIX):
        return 'Vowel Teams'
    return 'Other Phonograms'


def _write_keys_csv(concept_ids, sight_word_list):
    with open(UI_CONFIG_PATH) as f:
        labels = json.load(f)['concepts']['labels']

    with open(PRODUCTION_CACHE_KEYS_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['concept_id', 'concept_name', 'group'])
        for concept_id in sorted(concept_ids):
            writer.writerow([concept_id, _concept_name(concept_id, labels), _concept_group(concept_id)])
        for word in sight_word_list:
            writer.writerow([word, word, 'Irregular Words'])

    print(f"Production cache keys: {PRODUCTION_CACHE_KEYS_PATH}")


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

        cache_words = {word for words_list in concept_to_words.values() for word in words_list}
        cache_words.update(sight_word_list)

        word_frequency_rank = {
            row.word: row.frequency_rank
            for row in conn.execute(
                select(words.c.word, words.c.frequency_rank)
                .where(words.c.word.in_(cache_words))
            )
        }

    cache = {
        'concept_to_words': concept_to_words,
        'sight_words': sight_word_list,
        'word_frequency_rank': word_frequency_rank,
    }

    with open(PRODUCTION_CACHE_PATH, 'w') as f:
        json.dump(cache, f)

    size_kb = os.path.getsize(PRODUCTION_CACHE_PATH) / 1024
    print(f"  {len(concept_to_words)} concepts, {sum(len(v) for v in concept_to_words.values()):,} concept-word pairs")
    print(f"  {len(sight_word_list)} sight words")
    print(f"  {len(word_frequency_rank)} word frequency ranks")
    print(f"Production cache: {PRODUCTION_CACHE_PATH} ({size_kb:.1f} KB)")

    _write_keys_csv(concept_to_words.keys(), sight_word_list)


if __name__ == '__main__':
    build_cache()
