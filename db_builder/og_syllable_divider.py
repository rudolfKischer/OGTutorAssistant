"""
OG (Orton-Gillingham) orthographic syllable divider.

Splits English words into syllables using OG syllable division rules,
working from spelling patterns rather than phonemes.

Rules applied in order:
1. Hyphens: split at hyphens
2. C+le: consonant+le at end is its own syllable
3. Silent suffixes: -ed (after non t/d), -gue, -que endings
4. VCCV (Rabbit): split between consonants
5. VCV (Tiger): split before consonant (open syllable default)
6. VCCCV: keep onset blends/digraphs together
7. VV: known vowel teams stay together, others split (hiatus)
"""

VOWEL_LETTERS = set('aeiou')

# Vowel teams that stay together as one vowel unit
VOWEL_TEAMS = frozenset({
    'ai', 'ay', 'au', 'aw', 'ea', 'ee', 'ei', 'ew', 'ey',
    'ie', 'oa', 'oi', 'oo', 'ou', 'ow', 'oy', 'ue',
})

# Consonant units (digraphs/trigraphs) that cannot be split
C_UNITS = frozenset({
    'th', 'sh', 'ch', 'wh', 'ph', 'ck', 'ng', 'nk', 'gh',
    'wr', 'kn', 'gn',
    'tch', 'dge',
})

# Consonant units that only appear in codas (never valid word onsets)
CODA_ONLY = frozenset({'tch', 'dge', 'ck', 'ng', 'nk'})

# Valid onset clusters (consonant groups that can start a syllable)
ONSETS = frozenset({
    'bl', 'br', 'cl', 'cr', 'dr', 'dw', 'fl', 'fr', 'gl', 'gr',
    'pl', 'pr', 'sc', 'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'sw',
    'tr', 'tw', 'qu', 'squ',
    'scr', 'spl', 'spr', 'str', 'shr', 'thr', 'sch',
    # Digraphs that can be onsets
    'th', 'sh', 'ch', 'wh', 'ph',
})


def _is_vowel(ch, pos, word):
    """Is this character a vowel in this position?"""
    if ch in VOWEL_LETTERS:
        return True
    if ch == 'y' and pos > 0:
        if pos + 1 < len(word) and word[pos + 1] in VOWEL_LETTERS:
            return False
        return True
    return False


def _strip_silent_suffix(word):
    """Remove silent suffix from word for syllable counting purposes.

    Returns (base_word, suffix) where suffix is the silent part, or (word, '').
    """
    w = word.lower()
    n = len(w)

    # -gue / -que endings: the 'ue' is silent (league, unique, plaque)
    if n >= 4 and (w.endswith('gue') or w.endswith('que')):
        return w[:-2], w[-2:]

    # Note: -ed is NOT stripped. Distinguishing silent -ed (walked, jumped)
    # from pronounced -ed (wicked, hundred, sacred) requires morphological
    # knowledge we don't have. Both cases are handled naturally:
    # - "walked" → 2 nuclei (a, e) but silent-e detection may merge
    # - "wicked" → 2 nuclei (i, e) → correctly 2 syllables

    return w, ''


def _find_nuclei(word, vc):
    """Find vowel nuclei, keeping vowel teams together as single units."""
    nuclei = []
    i = 0
    n = len(word)
    while i < n:
        if vc[i] == 'V':
            start = i
            while i + 1 < n and vc[i + 1] == 'V':
                if word[i:i + 2] in VOWEL_TEAMS:
                    i += 1
                else:
                    break
            nuclei.append((start, i + 1))
            i += 1
        else:
            i += 1
    return nuclei


def _split_cluster(cluster, offset):
    """Find the best split position in a consonant cluster between two vowels."""
    n = len(cluster)

    # If entire cluster is a consonant unit, decide by onset/coda status
    if cluster in C_UNITS:
        if cluster in CODA_ONLY:
            return offset + n  # coda: split after
        return offset  # onset-capable: split before

    # If entire cluster is a valid onset, split before it (open first syllable)
    # EXCEPT for s-blends (sc, sk, sl, sm, sn, sp, st, sw) where VCCV splits between
    if cluster in ONSETS:
        if not (len(cluster) == 2 and cluster[0] == 's' and cluster not in C_UNITS):
            return offset

    # Try each possible split, preferring longest valid onset for next syllable
    for onset_len in range(min(n - 1, 3), 0, -1):
        split_pos = n - onset_len
        onset = cluster[split_pos:]

        # Check onset is valid
        if not (len(onset) == 1 or onset in ONSETS or onset in C_UNITS):
            continue

        # Check we're not splitting a consonant unit at the boundary
        split_ok = True
        # Check 2-letter units straddling the split
        if split_pos > 0 and split_pos < n:
            if cluster[split_pos - 1:split_pos + 1] in C_UNITS:
                split_ok = False
        # Check 3-letter units straddling the split
        for start in range(max(0, split_pos - 2), split_pos):
            end = start + 3
            if end <= n and cluster[start:end] in C_UNITS:
                if start < split_pos < end:
                    split_ok = False

        if split_ok:
            return offset + split_pos

    # Fallback: find any valid split that doesn't break a unit
    for split_pos in range(1, n):
        ok = True
        if split_pos > 0 and split_pos < n:
            if cluster[split_pos - 1:split_pos + 1] in C_UNITS:
                ok = False
        if ok:
            return offset + split_pos

    return offset + 1


def og_divide(word):
    """Divide a word into orthographic syllables using OG rules.

    Returns a list of syllable strings.
    """
    w = word.lower()
    n = len(w)

    if n <= 2:
        return [w]

    # Handle hyphens: split at hyphens, divide each part
    if '-' in w:
        result = []
        for part in w.split('-'):
            if part:
                result.extend(og_divide(part))
        return result

    # Handle C+le: consonant+le at end is its own syllable
    if (n >= 4 and w.endswith('le')
            and w[-3].isalpha() and not _is_vowel(w[-3], n - 3, w)):
        remainder = w[:-3]
        cle = w[-3:]
        if len(remainder) >= 2:
            return og_divide(remainder) + [cle]

    # Strip silent suffixes before counting nuclei
    base, suffix = _strip_silent_suffix(w)

    # Classify each letter in the base
    base_n = len(base)
    vc = ['V' if _is_vowel(base[i], i, base) else 'C' for i in range(base_n)]

    # Find vowel nuclei in the base
    nuclei = _find_nuclei(base, vc)

    # Handle silent final e in base: remove last nucleus if it's lone 'e'
    # preceded by consonant
    if len(nuclei) > 1:
        last_s, last_e = nuclei[-1]
        if last_e == base_n and last_s == base_n - 1 and base[-1] == 'e':
            if base_n >= 2 and not _is_vowel(base[-2], base_n - 2, base):
                nuclei.pop()

    if len(nuclei) <= 1:
        # Whole word is one syllable (re-attach suffix)
        return [w]

    # Find split points between consecutive nuclei
    splits = []
    for k in range(len(nuclei) - 1):
        v1_end = nuclei[k][1]
        v2_start = nuclei[k + 1][0]
        cluster = base[v1_end:v2_start]

        if len(cluster) == 0:
            splits.append(v2_start)
        elif len(cluster) == 1:
            # VCV: split before consonant (open syllable default)
            splits.append(v1_end)
        else:
            splits.append(_split_cluster(cluster, v1_end))

    # Build syllables from base, then re-attach suffix to last syllable
    result = []
    prev = 0
    for sp in splits:
        if sp > prev:
            result.append(base[prev:sp])
        prev = sp
    # Last syllable: rest of base + suffix
    last = base[prev:] + suffix
    if last:
        result.append(last)

    return result


def map_phonemes_to_og_syllables(og_syllables, phonemes, alignment):
    """Map CMU phonemes to orthographic syllables using g2p alignment.

    Returns list of phoneme lists, one per syllable.
    """
    if not alignment:
        # No alignment data — distribute phonemes evenly
        total = len(phonemes)
        n_syls = len(og_syllables)
        chunk = max(1, total // n_syls)
        result = []
        idx = 0
        for i in range(n_syls):
            end = idx + chunk if i < n_syls - 1 else total
            result.append(phonemes[idx:end])
            idx = end
        return result

    # Build character→syllable mapping
    char_to_syl = {}
    pos = 0
    for i, syl in enumerate(og_syllables):
        for j in range(len(syl)):
            char_to_syl[pos + j] = i
        pos += len(syl)

    # Walk alignment, assign actual CMU phonemes based on grapheme positions
    from db_builder.mappings import ARPABET_VOWELS
    syl_phonemes = [[] for _ in og_syllables]
    char_pos = 0
    ph_idx = 0
    flat = list(phonemes)

    for g, arp in alignment:
        if g == '-':
            char_pos += 1
            continue

        syl_idx = char_to_syl.get(char_pos, len(og_syllables) - 1)

        if arp is not None and arp != '':
            align_phs = arp.split('|')
            for aph in align_phs:
                if ph_idx < len(flat):
                    aph_base = aph.rstrip('012')
                    flat_base = flat[ph_idx].rstrip('012')
                    if flat_base == aph_base:
                        syl_phonemes[syl_idx].append(flat[ph_idx])
                        ph_idx += 1
                    elif flat_base == 'ER' and aph_base in ARPABET_VOWELS:
                        # Vowel absorbed into ER
                        pass
                    elif flat_base == 'ER' and aph_base == 'R':
                        syl_phonemes[syl_idx].append(flat[ph_idx])
                        ph_idx += 1
                    else:
                        # Mismatch — consume one phoneme anyway
                        syl_phonemes[syl_idx].append(flat[ph_idx])
                        ph_idx += 1

        char_pos += len(g)

    # Remaining phonemes go to last syllable
    while ph_idx < len(flat):
        syl_phonemes[-1].append(flat[ph_idx])
        ph_idx += 1

    return syl_phonemes
