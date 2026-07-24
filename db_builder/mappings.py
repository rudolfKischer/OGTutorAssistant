import json
import os

from config import MAPPINGS_DIR


def _load_json(filename):
    with open(os.path.join(MAPPINGS_DIR, filename), 'r') as f:
        return json.load(f)


_arpabet = _load_json('arpabet_to_og.json')
ARPABET_TO_OG = _arpabet['arpabet_to_og']
R_CONTROLLED_COMBOS = {
    tuple(k.split(',')): v for k, v in _arpabet['r_controlled_combos'].items()
}
ARPABET_VOWELS = set(_arpabet['arpabet_vowels'])
ARPABET_CONSONANTS = set(_arpabet['arpabet_consonants'])
SHORT_VOWEL_ARPABET = set(_arpabet['short_vowel_arpabet'])
LONG_VOWEL_ARPABET = set(_arpabet['long_vowel_arpabet'])
VOWEL_LETTERS = set(_arpabet['vowel_letters'])
CONSONANT_LETTERS = set(_arpabet['consonant_letters'])

_concepts = _load_json('og_concepts.json')
INITIAL_BLENDS = set(_concepts['initial_blends'])
FINAL_BLENDS = set(_concepts['final_blends'])
VOWEL_TEAMS_MAP = _concepts['vowel_teams']
SYLLABLE_VOWEL_TEAMS = _concepts['syllable_vowel_teams']
MAGIC_E_VOWEL_MAP = _concepts['magic_e_vowel_map']
FLOSS_VOWELS = set(_concepts['floss_vowels'])
FLOSS_DOUBLES = set(_concepts['floss_doubles'])
SHORT_VOWEL_PHONEMES = set(_concepts['short_vowel_phonemes'])
OG_VOWEL_PHONEMES = set(_concepts['og_vowel_phonemes'])
CV_PATTERNS = set(_concepts['cv_patterns'])

_contractions = _load_json('contractions.json')
CONTRACTION_SUFFIXES = tuple(_contractions['suffixes'])
VALID_S_CONTRACTIONS = set(_contractions['valid_s_contractions'])
VALID_APOSTROPHE_WORDS = set(_contractions['valid_apostrophe_words'])

INFLECTIONAL_SUFFIXES = _load_json('inflectional_suffixes.json')

_irreg = _load_json('irregularity_detection.json')
COMPOUND_PHONEMES = {k: set(v) for k, v in _irreg['compound_phonemes'].items()}
PHONEME_ALIASES = {k: set(v) for k, v in _irreg['phoneme_aliases'].items()}
PRIMARY_SOUND = _irreg['primary_sound']
