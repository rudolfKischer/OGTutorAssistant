import json

from sqlalchemy import select

from config import MORPHOLEX_JSON_PATH
from db.tables import words, word_morphemes
from .mappings import INFLECTIONAL_SUFFIXES

# morpholex_parsed.json column indices: [[prefixes], [roots], [suffixes]]
M_PREFIXES, M_ROOTS, M_SUFFIXES = 0, 1, 2

STRIP_ENDINGS = [
    ('ing', ''), ('ing', 'e'), ('ed', ''), ('ed', 'e'),
    ('er', ''), ('er', 'e'), ('est', ''), ('est', 'e'),
    ('s', ''), ('es', ''), ('ies', 'y'),
    ('ly', ''), ('ily', 'y'), ('ness', ''), ('iness', 'y'),
]


def load_morpholex():
    with open(MORPHOLEX_JSON_PATH, 'r') as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} words from MorphoLex")
    return data


def _matches_spelling_change(word, base_form, word_ending, root_ending):
    """Check if a spelling change rule matches word -> base_form."""
    if not word_ending or not word.endswith(word_ending):
        return False
    candidate = word[:-len(word_ending)] + root_ending
    if candidate == base_form:
        return True
    # Handle doubled consonant: "running" -> "runn" matches "run"
    return (len(candidate) >= 2
            and candidate[-1] == candidate[-2]
            and candidate[:-1] == base_form)


def detect_inflectional_suffix(word, base_form):
    if not base_form or word == base_form or len(word) <= len(base_form):
        return None

    for entry in INFLECTIONAL_SUFFIXES:
        if not word.endswith(entry['suffix']):
            continue
        if any(_matches_spelling_change(word, base_form, we, re_)
               for we, re_ in entry['spelling_changes']):
            return entry['suffix']
    return None


def _find_base_candidates(word, morph, morpholex):
    """Find possible base forms for inflection detection."""
    base_form = ''.join(morph[M_PREFIXES]) + ''.join(morph[M_ROOTS]) + ''.join(morph[M_SUFFIXES])
    candidates = [base_form]
    if morph[M_ROOTS]:
        candidates.append(morph[M_ROOTS][-1])

    for ending, replacement in STRIP_ENDINGS:
        if not word.endswith(ending) or len(word) <= len(ending):
            continue
        stem = word[:-len(ending)] + replacement
        if stem != word and stem in morpholex:
            candidates.append(stem)
        if not replacement and len(stem) >= 2 and stem[-1] == stem[-2]:
            short_stem = stem[:-1]
            if short_stem in morpholex:
                candidates.append(short_stem)

    return candidates


def _find_inflection(word, candidates):
    """Try each candidate base form to detect an inflectional suffix."""
    for candidate in candidates:
        if candidate == word:
            continue
        infl = detect_inflectional_suffix(word, candidate)
        if infl:
            return infl
    return None


def _morph_to_parts(morph):
    """Convert a morpholex entry into a list of (morpheme, type) tuples."""
    return ([(p, 'prefix') for p in morph[M_PREFIXES]]
            + [(r, 'root') for r in morph[M_ROOTS]]
            + [(s, 'suffix') for s in morph[M_SUFFIXES]])


def decompose_word(word, morpholex):
    morph = morpholex.get(word)
    if not morph:
        return None

    parts = _morph_to_parts(morph)

    if morph[M_ROOTS]:
        candidates = _find_base_candidates(word, morph, morpholex)
        infl = _find_inflection(word, candidates)
        if infl:
            parts.append((infl, 'suffix'))

    return parts


def _decompose_with_hyphen_fallback(word, morpholex):
    """Try decomposing word; for hyphenated words, decompose each segment."""
    parts = decompose_word(word, morpholex)
    if parts is not None:
        return parts
    if '-' not in word:
        return None

    combined = []
    for seg in word.split('-'):
        seg_parts = decompose_word(seg, morpholex)
        combined.extend(seg_parts if seg_parts else [(seg, 'root')])
    return combined


def _has_affixes(parts):
    return len(parts) > 1 or any(t != 'root' for _, t in parts)


def load_morphemes(conn):
    print("Loading morphology data...")
    morpholex = load_morpholex()
    if not morpholex:
        return

    all_words = conn.execute(select(words.c.id, words.c.word)).fetchall()

    morpheme_rows = []
    matched = 0
    affix_count = 0

    for w in all_words:
        parts = _decompose_with_hyphen_fallback(w.word, morpholex)
        if parts is None:
            continue

        matched += 1
        if _has_affixes(parts):
            affix_count += 1

        for pos, (morpheme, mtype) in enumerate(parts):
            morpheme_rows.append({
                'word_id': w.id, 'position': pos,
                'morpheme': morpheme, 'morpheme_type': mtype,
            })

    print(f"  Matched {matched}/{len(all_words)} words in MorphoLex")
    print(f"  Words with affixes: {affix_count}")
    print(f"  Inserting {len(morpheme_rows)} morpheme records...")
    conn.execute(word_morphemes.insert(), morpheme_rows)
    conn.commit()
