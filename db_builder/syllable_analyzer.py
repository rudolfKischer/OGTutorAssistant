from .mappings import (
    ARPABET_VOWELS, ARPABET_CONSONANTS, LONG_VOWEL_ARPABET,
    VOWEL_LETTERS, SYLLABLE_VOWEL_TEAMS,
)


def cv_pattern(syllable_graphemes, syllable_phonemes=None, syllable_alignment=None):
    """Build CV pattern from spelling — each letter gets C or V.

    Uses alignment data to resolve ambiguous letters:
    - y: vowel if its phoneme is a vowel sound, else consonant
    - u: consonant if its phoneme is /w/ (u-after-q)
    Falls back to positional/counting heuristics when no alignment is available.
    """
    spelling = ''.join(syllable_graphemes).lower()
    alpha = [ch for ch in spelling if ch.isalpha()]
    if not alpha:
        return 'C'

    # Build a per-letter phoneme lookup from alignment
    letter_phonemes = _map_letters_to_phonemes(syllable_alignment) if syllable_alignment else {}

    # Count vowel phonemes for Y heuristic fallback
    phoneme_vowels = 0
    if syllable_phonemes:
        phoneme_vowels = sum(1 for p in syllable_phonemes if p.rstrip('012') in ARPABET_VOWELS)

    result = []
    for i, ch in enumerate(alpha):
        ph = letter_phonemes.get(i)
        if ch == 'y':
            if ph is not None:
                # Y: use its actual phoneme
                result.append('V' if ph in ARPABET_VOWELS else 'C')
            elif syllable_phonemes:
                definite_vowels = sum(1 for c in alpha if c in VOWEL_LETTERS)
                result.append('V' if phoneme_vowels > definite_vowels else 'C')
            else:
                result.append('C' if i == 0 else 'V')
        elif ch == 'u' and ph is not None and ph not in ARPABET_VOWELS:
            # u acting as consonant (e.g. u-after-q = /w/)
            result.append('C')
        elif ch in VOWEL_LETTERS:
            result.append('V')
        else:
            result.append('C')

    return ''.join(result)


def _map_letters_to_phonemes(syl_alignment):
    """Map ambiguous letters (y, u) to their phoneme using alignment data.

    Only returns entries for letters that need phoneme-based classification:
    - y: could be vowel or consonant
    - u: consonant only when it IS the grapheme mapped to /w/ (e.g. 'u' → W in 'qu')
    Returns {letter_index: base_phoneme}.
    """
    result = {}
    letter_idx = 0
    for grapheme, arpabet in syl_alignment:
        if grapheme == '-':
            continue
        letters = [ch for ch in grapheme.lower() if ch.isalpha()]
        base = arpabet.split('|')[0].rstrip('012') if arpabet else None
        for ch in letters:
            if ch == 'y' and base is not None:
                result[letter_idx] = base
            elif ch == 'u' and grapheme.lower() == 'u' and base == 'W':
                # Only override u when it's a standalone 'u' grapheme mapping to /w/
                result[letter_idx] = base
            letter_idx += 1
    return result


def _syl_spelling(syllable_graphemes):
    return ''.join(syllable_graphemes).lower()


def _is_r_controlled(bases):
    for i, b in enumerate(bases):
        if b == 'ER':
            return True
        if b in ARPABET_VOWELS and i + 1 < len(bases) and bases[i + 1] == 'R':
            return True
    return False


def _is_cle(syl_spell):
    """C+le: last syllable ending in consonant-le."""
    return (len(syl_spell) >= 3
            and syl_spell.endswith('le')
            and syl_spell[-3].isalpha()
            and syl_spell[-3] not in 'aeiou')


def _is_vce(syl_spell, vowel_bases):
    """Vowel-consonant-e with a long vowel sound."""
    if len(syl_spell) < 3 or syl_spell[-1] != 'e':
        return False
    before_e = syl_spell[-2]
    if not before_e.isalpha() or before_e in 'aeiou':
        return False
    return any(b in LONG_VOWEL_ARPABET for b in vowel_bases)


def _has_vowel_team(syl_spell):
    return any(vt in syl_spell for vt in SYLLABLE_VOWEL_TEAMS)


def classify_og_syllable_type(syllable_phonemes, syllable_graphemes,
                               is_last_syllable, word_spelling):
    bases = [ph.rstrip('012') for ph in syllable_phonemes]
    vowel_bases = [b for b in bases if b in ARPABET_VOWELS]

    if not vowel_bases:
        return 'closed'

    if _is_r_controlled(bases):
        return 'r_controlled'

    syl_spell = _syl_spelling(syllable_graphemes) if syllable_graphemes else ''

    if is_last_syllable and _is_cle(syl_spell):
        return 'cle'

    if _is_vce(syl_spell, vowel_bases):
        return 'vce'

    if _has_vowel_team(syl_spell):
        return 'vowel_team'

    ends_consonant = bases[-1] in ARPABET_CONSONANTS if bases else False
    return 'closed' if ends_consonant else 'open'


def _build_syl_assignments(syllables_phonemes):
    """Map each phoneme index to its syllable index."""
    assignments = []
    for syl_idx, syl_phs in enumerate(syllables_phonemes):
        assignments.extend([syl_idx] * len(syl_phs))
    return assignments


def _count_align_phonemes(alignment):
    """Count total phonemes in alignment (pipe-separated entries)."""
    return sum(len(p.split('|')) for _, p in alignment if p is not None)


def _alignment_matches_phonemes(alignment, flat_phonemes):
    """Check if alignment phoneme count matches actual phonemes, accounting for vowel+R → ER."""
    align_count = _count_align_phonemes(alignment)
    flat_count = len(flat_phonemes)
    if align_count == flat_count:
        return True
    # Check if mismatch is explainable by vowel+R vs ER merging
    align_phs = []
    for _, p in alignment:
        if p is not None:
            align_phs.extend(p.split('|'))
    vr_merges = 0
    for i in range(len(align_phs) - 1):
        if (align_phs[i].rstrip('012') in ARPABET_VOWELS
                and align_phs[i + 1].rstrip('012') == 'R'):
            vr_merges += 1
    return align_count - vr_merges == flat_count


def _proportional_grapheme_assignment(alignment, syllables_phonemes):
    """Fallback: assign graphemes proportionally by syllable phoneme counts."""
    num_syls = len(syllables_phonemes)
    total_phonemes = sum(len(s) for s in syllables_phonemes)
    grapheme_result = [[] for _ in range(num_syls)]
    alignment_result = [[] for _ in range(num_syls)]

    # Build cumulative phoneme boundaries as fractions
    boundaries = []
    running = 0
    for syl in syllables_phonemes:
        running += len(syl)
        boundaries.append(running / total_phonemes if total_phonemes else 1.0)

    # Count non-hyphen graphemes for proportional mapping
    entries = [(g, a) for g, a in alignment if g != '-']
    total_g = len(entries)

    for idx, (grapheme, arpabet) in enumerate(entries):
        frac = (idx + 0.5) / total_g if total_g else 0
        syl_idx = 0
        for bi, b in enumerate(boundaries):
            if frac <= b:
                syl_idx = bi
                break
        grapheme_result[syl_idx].append(grapheme)
        alignment_result[syl_idx].append((grapheme, arpabet))

    return grapheme_result, alignment_result


def get_syllable_graphemes(syllables_phonemes, alignment, word):
    """Returns (syl_graphemes, syl_alignments) — grapheme lists and alignment pairs per syllable."""
    if not alignment:
        return [[] for _ in syllables_phonemes], [[] for _ in syllables_phonemes]

    flat_phonemes = [ph for syl in syllables_phonemes for ph in syl]

    # If alignment phoneme count doesn't match actual phonemes, the alignment
    # data is unreliable — fall back to proportional assignment
    if not _alignment_matches_phonemes(alignment, flat_phonemes):
        return _proportional_grapheme_assignment(alignment, syllables_phonemes)

    assignments = _build_syl_assignments(syllables_phonemes)
    grapheme_result = [[] for _ in syllables_phonemes]
    alignment_result = [[] for _ in syllables_phonemes]
    ph_idx = 0
    prev_syl = 0
    for grapheme, arpabet in alignment:
        if arpabet is not None:
            syl_idx = assignments[min(ph_idx, len(assignments) - 1)] if assignments else 0
            prev_syl = syl_idx
            # Match alignment phonemes against actual sequence — only advance
            # for phonemes that actually exist.
            # Handles: w→HH|W when only W is present (multi-phoneme grapheme)
            # Handles: vowel→AO + next grapheme R→R when flat has ER (r-colored vowel merge)
            align_phs = arpabet.split('|')
            advance = 0
            absorbed = False
            for aph in align_phs:
                check_idx = ph_idx + advance
                if check_idx < len(flat_phonemes):
                    aph_base = aph.rstrip('012')
                    flat_base = flat_phonemes[check_idx].rstrip('012')
                    if flat_base == aph_base:
                        advance += 1
                    elif flat_base == 'ER' and aph_base in ARPABET_VOWELS:
                        # Vowel absorbed into ER — don't advance, R grapheme will consume it
                        absorbed = True
                    elif flat_base == 'ER' and aph_base == 'R':
                        # R part of merged ER — consume it
                        advance += 1
            if absorbed:
                ph_idx += advance  # may be 0, vowel is part of ER
            else:
                ph_idx += max(advance, 1)
        else:
            # Silent grapheme: stays with the previous syllable
            syl_idx = prev_syl
        grapheme_result[syl_idx].append(grapheme)
        alignment_result[syl_idx].append((grapheme, arpabet))
    return grapheme_result, alignment_result


def _fallback_graphemes(word, num_syls):
    """Approximate syllable graphemes when no alignment is available."""
    if num_syls == 1:
        return [[word]]
    chunk = max(1, len(word) // num_syls)
    return [
        [word[i * chunk: (i + 1) * chunk if i < num_syls - 1 else len(word)]]
        for i in range(num_syls)
    ]


def analyze_syllables(word_entry):
    syllables_phonemes = word_entry.get('syllables_phonemes', [])
    alignment = word_entry.get('alignment', [])
    word = word_entry['word']
    num_syls = len(syllables_phonemes)
    og_syllables = word_entry.get('og_syllables')

    if og_syllables:
        # OG divider provides orthographic syllables directly
        syl_graphemes = [[s] for s in og_syllables]
        # Build alignment per syllable from character positions
        syl_alignments = _og_syl_alignments(og_syllables, alignment)
    else:
        syl_graphemes, syl_alignments = get_syllable_graphemes(syllables_phonemes, alignment, word)
        if not alignment:
            syl_graphemes = _fallback_graphemes(word, num_syls)
            syl_alignments = [None] * num_syls

    return [
        {
            'cv_pattern': cv_pattern(
                syl_graphemes[i] if i < len(syl_graphemes) else [word],
                syl_phs,
                syl_alignments[i] if i < len(syl_alignments) else None,
            ),
            'og_type': classify_og_syllable_type(syl_phs, syl_graphemes[i], i == num_syls - 1, word),
        }
        for i, syl_phs in enumerate(syllables_phonemes)
    ]


def _og_syl_alignments(og_syllables, alignment):
    """Build per-syllable alignment pairs from OG character boundaries."""
    if not alignment:
        return [None] * len(og_syllables)

    # Map character positions to syllable indices
    char_to_syl = {}
    pos = 0
    for i, syl in enumerate(og_syllables):
        for j in range(len(syl)):
            char_to_syl[pos + j] = i
        pos += len(syl)

    result = [[] for _ in og_syllables]
    char_pos = 0
    for grapheme, arpabet in alignment:
        if grapheme == '-':
            char_pos += 1
            continue
        syl_idx = char_to_syl.get(char_pos, len(og_syllables) - 1)
        result[syl_idx].append((grapheme, arpabet))
        char_pos += len(grapheme)

    return result
