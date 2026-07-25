from .mappings import (
    INITIAL_BLENDS, FINAL_BLENDS, CONSONANT_LETTERS, VOWEL_LETTERS,
    VOWEL_TEAMS_MAP, MAGIC_E_VOWEL_MAP, FLOSS_VOWELS, FLOSS_DOUBLES,
    OG_VOWEL_PHONEMES, CV_PATTERNS, SHORT_VOWEL_PHONEMES,
)
from .morphology_concepts import MORPHOLOGY_CONCEPTS

R_CONTROLLED_IDS = ('ar', 'er', 'or', 'air', 'ear')

DIGRAPH_MAP = {
    ('sh', 'sh'): 'digraph_sh',
    ('ch', 'ch'): 'digraph_ch',
    ('ck', 'k'): 'digraph_ck',
}

Y_VOWEL_MAP = {
    'long_e': 'y_as_long_e',
    'long_i': 'y_as_long_i',
    'short_i': 'y_as_short_i',
}

SYLLABLE_TYPE_CONCEPTS = {
    'open': 'open_syllable', 'closed': 'closed_syllable',
    'vce': 'vce_syllable', 'vowel_team': 'vowel_team_syllable',
    'r_controlled': 'r_controlled_syllable', 'cle': 'cle_syllable',
}

NG_ENDINGS = ('ang', 'ing', 'ong', 'ung', 'eng')
NK_ENDINGS = ('ank', 'ink', 'onk', 'unk')


def _find_vowel_boundaries(non_silent):
    """Return (first_vowel_idx, last_vowel_idx) in non-silent entries."""
    first, last = None, None
    for i, (_, og_id) in enumerate(non_silent):
        if og_id in OG_VOWEL_PHONEMES:
            if first is None:
                first = i
            last = i
    return first, last


def _consonant_runs(non_silent, start, end):
    """Yield runs of single-char consonant letters from non_silent[start:end]."""
    run = []
    for i in range(start, end):
        g, _ = non_silent[i]
        if len(g) == 1 and g.lower() in CONSONANT_LETTERS:
            run.append(g.lower())
        else:
            if run:
                yield run
            run = []
    if run:
        yield run


def _blends_in_run(run, position, blend_set):
    """Find all blends (pairs and triples) within a consonant run."""
    found = set()
    combo = ''.join(run)
    if len(run) >= 3:
        for tri in (combo[:3], combo[-3:]):
            if tri in blend_set:
                found.add(f'blend_{position}_{tri}')
    for i in range(len(run) - 1):
        pair = run[i] + run[i + 1]
        if pair in blend_set:
            found.add(f'blend_{position}_{pair}')
    return found


def _detect_blends(entries, concepts):
    non_silent = [(g, og_id) for g, og_id, sil in entries if not sil and og_id]
    first_v, last_v = _find_vowel_boundaries(non_silent)

    if first_v is not None and first_v > 0:
        for run in _consonant_runs(non_silent, 0, first_v):
            concepts.update(_blends_in_run(run, 'initial', INITIAL_BLENDS))

    if last_v is not None and last_v < len(non_silent) - 1:
        for run in _consonant_runs(non_silent, last_v + 1, len(non_silent)):
            concepts.update(_blends_in_run(run, 'final', FINAL_BLENDS))


def _detect_ng_nk(spelling, entries, concepts):
    if not any(og_id == 'ng' for _, og_id, _ in entries):
        return
    for ending in NG_ENDINGS:
        if spelling.endswith(ending):
            concepts.add(f'ng_ending_{ending}')
            break
    for ending in NK_ENDINGS:
        if spelling.endswith(ending):
            concepts.add(f'nk_ending_{ending}')
            break


def _detect_digraphs(entries, concepts):
    for g, og_id, is_silent in entries:
        gl = g.lower()
        if (gl, og_id) in DIGRAPH_MAP:
            concepts.add(DIGRAPH_MAP[(gl, og_id)])
        elif gl == 'th' and og_id in ('th_voiceless', 'th_voiced'):
            concepts.add('digraph_th')
        elif gl == 'wh' and og_id in ('w', 'h'):
            concepts.add('digraph_wh')
        elif gl in ('dg', 'dge') and og_id == 'j':
            concepts.add('digraph_dge')

    for i in range(len(entries) - 1):
        g1, _, sil1 = entries[i]
        g2, og2, _ = entries[i + 1]
        if g1.lower() == 't' and sil1 and g2.lower() == 'ch' and og2 == 'ch':
            concepts.add('digraph_tch')


def _detect_s_as_z(entries, concepts):
    if any(g.lower() == 's' and og_id == 'z' for g, og_id, _ in entries):
        concepts.add('s_as_z')


def _detect_y_as_vowel(entries, concepts):
    for g, og_id, is_silent in entries:
        if g.lower() == 'y' and not is_silent and og_id in Y_VOWEL_MAP:
            concepts.add(Y_VOWEL_MAP[og_id])


def _last_vowel_before_e(pre):
    """Find the last vowel letter and its position in the string before trailing 'e'."""
    for i in range(len(pre) - 1, -1, -1):
        if pre[i] in VOWEL_LETTERS:
            return i, pre[i]
    return -1, None


def _detect_magic_e(spelling, entries, concepts):
    if len(spelling) < 3 or not spelling.endswith('e'):
        return
    if not entries or not entries[-1][2]:  # last entry must be silent
        return

    pre = spelling[:-1]
    pos, vowel = _last_vowel_before_e(pre)
    if pos < 0 or pos >= len(pre) - 1:
        return

    between = pre[pos + 1:]
    if all(c in CONSONANT_LETTERS for c in between) and vowel in MAGIC_E_VOWEL_MAP:
        concepts.add(MAGIC_E_VOWEL_MAP[vowel])


def _detect_floss(spelling, entries, num_syllables, concepts):
    if num_syllables != 1:
        return
    for double in FLOSS_DOUBLES:
        if not spelling.endswith(double):
            continue
        if any(og_id in FLOSS_VOWELS for _, og_id, sil in entries if not sil):
            concepts.add(f'floss_{double}')
        return


DOUBLING_SUFFIXES = ('ing', 'ed', 'er', 'est')


def is_111_doubling_base(spelling, og_phonemes, num_syllables):
    """Would this word double its final consonant before a vowel suffix?

    The 1-1-1 rule: 1 syllable, 1 short vowel, ends in exactly 1 consonant.

    Two deliberate departures from a naive grapheme-alignment check:

    - The vowel check uses `og_phonemes` (the stress-aware word_phonemes
      sequence), not the grapheme alignment. The alignment's static
      ARPABET_TO_OG table maps AH -> schwa unconditionally, so stressed
      /ah/ words like "run"/"cut"/"hug" never show up as short_u there even
      though they are - og_phonemes distinguishes them correctly.
    - The consonant-count check is letter-based rather than grapheme-based:
      the DB's grapheme alignment can fold a final liquid into the vowel
      grapheme (e.g. "walk" -> w + al(short_o) + k), which would make a
      2-letter cluster look like a single trailing consonant. Counting raw
      letters after the last vowel letter avoids that, and naturally excludes
      digraphs/doubled letters (ck, ss, ll, ...) as a side effect since those
      are 2 letters too.
    """
    if num_syllables != 1:
        return False

    vowel_phonemes = [pid for pid in og_phonemes if pid in OG_VOWEL_PHONEMES]
    if len(vowel_phonemes) != 1 or vowel_phonemes[0] not in SHORT_VOWEL_PHONEMES:
        return False

    last_vowel_idx = None
    for i in range(len(spelling) - 1, -1, -1):
        if spelling[i] in VOWEL_LETTERS:
            last_vowel_idx = i
            break
    if last_vowel_idx is None:
        return False

    tail = spelling[last_vowel_idx + 1:]
    # "x" spells /ks/ - phonetically a blend despite being one letter, so it
    # never doubles (box -> boxing, not boxxing).
    return len(tail) == 1 and tail in CONSONANT_LETTERS and tail != 'x'


def _detect_doubled_word(morpheme_parts, base_words_111, concepts):
    """Tag WORDS THAT SHOW the rule applied (running), not the base (run).

    Uses the word's own MorphoLex-derived root/suffix split (already
    computed for `detect_morphology_concepts`) instead of reconstructing a
    candidate base by string surgery on the surface spelling. That matters:
    a blind "strip vowel-suffix, undouble the final letter, does that
    spelling exist" check will happily "reconstruct" a real word out of
    total coincidences - e.g. "matter" -> "matte", "summer" -> "sum" - even
    though those words have nothing to do with this rule. MorphoLex's own
    decomposition already gets this right: it records "matter"/"summer" as
    their own unsplit root, not root+doubled-suffix, so trusting its root
    field is a strictly more reliable signal than re-deriving one.
    """
    for morpheme, mtype in morpheme_parts:
        if mtype == 'root' and morpheme in base_words_111:
            if any(m in DOUBLING_SUFFIXES for m, t in morpheme_parts if t == 'suffix'):
                concepts.add('doubling_rule_111')
            return


FINAL_E_SUFFIXES = ('ing', 'ed', 'er', 'est', 'able', 'y')
# "-oe"/"-ee" are the documented exceptions that KEEP the e (hoe -> hoeing,
# see -> seeing), unlike other vowel-preceded e's (argue -> arguing).
FINAL_E_KEEP_EXCEPTIONS = ('ee', 'oe')
# Roots ending in soft c/g keep the e before -able to preserve that sound
# (notice -> noticeable, change -> changeable, manage -> manageable), unlike
# every other -able case (use -> usable, love -> lovable, note -> notable).
SOFT_CG_KEEP_E = ('ce', 'ge')


def is_final_e_base(spelling):
    """Does this base word end in a silent e that gets dropped before a vowel suffix?

    Requires at least 2 letters before the e (>= 3 total): 2-letter words
    like "be"/"he" are real but too atomic to be a sane example of this
    rule, and being so common they'd otherwise turn up as a false "base" for
    tons of unrelated short words (by/her/best all reconstruct to "be"/"he"
    if this floor weren't here).
    """
    if len(spelling) < 3 or not spelling.endswith('e'):
        return False
    return not spelling.endswith(FINAL_E_KEEP_EXCEPTIONS)


def _detect_final_e_word(morpheme_parts, base_words_final_e, concepts):
    """Tag words that SHOW the rule applied (basing), not the base (base).

    Uses the word's own MorphoLex-derived root/suffix split rather than
    reconstructing a candidate base by adding an 'e' back onto the stripped
    spelling. A blind reconstruction check can't tell "city" (root "city",
    no suffix at all) from "icy" (root "ice", suffix "y") - both end in "y",
    and "cit" + "e" = "cite" is a real word, so a spelling-only check would
    wrongly treat "city" as if it dropped an e from "cite". MorphoLex's own
    decomposition already draws that line correctly.
    """
    for morpheme, mtype in morpheme_parts:
        if mtype != 'root' or morpheme not in base_words_final_e:
            continue
        for m, t in morpheme_parts:
            if t != 'suffix' or m not in FINAL_E_SUFFIXES:
                continue
            if m == 'able' and morpheme.endswith(SOFT_CG_KEEP_E):
                continue
            concepts.add('final_e_rule')
        return


def is_final_y_base(spelling):
    """Does this base word end in a y that changes to i before most suffixes?

    Requires at least 2 letters before the y (>= 3 total, same rationale as
    `is_final_e_base`'s length floor), and that the letter right before the
    y is a consonant - vowel+y words (play, monkey, boy) never change and so
    are never candidates in the first place, not just an exception to check
    per-suffix.
    """
    if len(spelling) < 3 or not spelling.endswith('y'):
        return False
    return spelling[-2] in CONSONANT_LETTERS


FINAL_Y_SUFFIXES = ('ed', 'er', 'est', 'es', 'ly', 'ness', 'ful', 'able')

# MorphoLex occasionally parses a word into a real dictionary root that
# happens to be a coincidental substring, not an actual derivation -
# "navigable"/"navigated" get root "navy" (from "navi-" + "gable"/"gated"),
# but neither word has anything to do with "navy"; both trace to Latin
# "navigare" instead. This isn't something the structural checks below can
# catch (the "navi" substring genuinely is there), so it's a manual
# exclusion found by reviewing every word this concept tagged.
FINAL_Y_MANUAL_EXCLUSIONS = {'navigable'}


def _detect_final_y_word(spelling, morpheme_parts, base_words_final_y, concepts):
    """Tag words that SHOW the rule applied (happier, carried, babies).

    Uses the word's own MorphoLex-derived root/suffix split, same rationale
    as `_detect_final_e_word` and `_detect_doubled_word`: MorphoLex already
    normalizes the spelling change away, always recording the root with its
    true "y" ending (happy, carry, baby) regardless of whether the surface
    word shows "y" or "i".

    The suffix list is a curated "classic" set rather than the broader "any
    suffix not starting with i" the stated rule implies - that broader rule
    also matches Latinate derivational suffixes (-al, -ion: try -> trial,
    vary -> variation), which are correct y->i changes but not the simple
    inflectional pattern this concept is meant to teach. Only the suffix
    immediately following the root is checked, not any suffix anywhere in
    the word's decomposition: "navigated" is root "navy" + "ate" + "ed", and
    checking suffixes anywhere would wrongly credit the unrelated trailing
    "ed" even though "ate" (attached directly to the coincidental "navy"
    root) isn't a real y-changing suffix at all.

    A root+suffix match alone isn't enough, though: MorphoLex records the
    same root+suffix pair regardless of whether the surface spelling
    actually shows the change. "dryer"/"flyer" are lexical exceptions that
    keep the y (root "dry"+"er", but spelled "dryer" not "drier"), and some
    words get a spurious self-referential root equal to the whole word
    itself (e.g. "belly" -> root "belly" + a stray "ly" suffix tag) - a data
    quirk of the inflection-detection heuristic, not a real decomposition.
    Requiring the "i"-substituted spelling ("root minus y, plus i") to
    actually appear in the word confirms the change is real and catches
    both cases: neither "dryer" (contains "dry", not "dri") nor "belly"
    (contains "lly", not "lli") passes.
    """
    if spelling in FINAL_Y_MANUAL_EXCLUSIONS:
        return
    for i, (morpheme, mtype) in enumerate(morpheme_parts):
        if mtype != 'root' or morpheme not in base_words_final_y:
            continue
        if morpheme[:-1] + 'i' not in spelling:
            continue
        if i + 1 >= len(morpheme_parts):
            continue
        next_morpheme, next_type = morpheme_parts[i + 1]
        if next_type == 'suffix' and next_morpheme in FINAL_Y_SUFFIXES:
            concepts.add('final_y_rule')
        return


def _detect_vowel_teams(entries, concepts):
    for g, _, is_silent in entries:
        gl = g.lower()
        if gl in VOWEL_TEAMS_MAP and not is_silent:
            concepts.add(VOWEL_TEAMS_MAP[gl])


def _detect_r_controlled(entries, concepts):
    for _, og_id, _ in entries:
        if og_id in R_CONTROLLED_IDS:
            concepts.add(f'r_controlled_{og_id}')


def _has_doubled_consonant(spelling):
    return any(
        spelling[i] == spelling[i + 1]
        and spelling[i] in CONSONANT_LETTERS
        and spelling[i] not in 'wxyz'
        for i in range(len(spelling) - 1)
    )


def _detect_syllable_concepts(num_syllables, syllable_info, morpheme_parts, spelling, concepts):
    if not syllable_info:
        return

    for syl in syllable_info:
        concept = SYLLABLE_TYPE_CONCEPTS.get(syl['og_type'])
        if concept:
            concepts.add(concept)

    if num_syllables >= 2:
        if morpheme_parts and sum(1 for _, t in morpheme_parts if t == 'root') >= 2:
            concepts.add('syllable_div_compound')
        if _has_doubled_consonant(spelling):
            concepts.add('syllable_div_rabbit')


def detect_morphology_concepts(word, morpheme_parts, concepts):
    spelling = word.lower()
    by_type = {}
    for morpheme, mtype in morpheme_parts or []:
        by_type.setdefault(mtype, set()).add(morpheme)

    for rec in MORPHOLOGY_CONCEPTS:
        if rec['kind'] == 'morpheme':
            if any(m in by_type.get(rec['morpheme_type'], ()) for m in rec['match']):
                concepts.add(rec['id'])
        else:  # 'spelling'
            if not spelling.endswith(rec['word_suffix']):
                continue
            gate = rec.get('requires_morpheme')
            if gate:
                gate_type, gate_morpheme = gate
                if gate_morpheme not in by_type.get(gate_type, ()):
                    continue
            concepts.add(rec['id'])


def _detect_cv_patterns(syllable_info, concepts):
    for syl in syllable_info:
        cv = syl['cv_pattern']
        if cv:
            concepts.add(f'pattern_{cv}')


def _split_segments(alignment):
    segments = []
    current_entries = []
    current_spelling = []
    for g, arp, og_id, is_silent in alignment:
        if g == '-':
            if current_entries:
                segments.append((''.join(current_spelling), current_entries))
            current_entries = []
            current_spelling = []
        else:
            current_entries.append((g, og_id, is_silent))
            current_spelling.append(g)
    if current_entries:
        segments.append((''.join(current_spelling), current_entries))
    return segments


def _detect_on_segment(spelling, entries, concepts):
    non_silent_phonemes = [og_id for _, og_id, sil in entries if not sil and og_id]
    num_syllables = max(1, sum(1 for pid in non_silent_phonemes if pid in OG_VOWEL_PHONEMES))

    _detect_blends(entries, concepts)
    _detect_ng_nk(spelling, entries, concepts)
    _detect_digraphs(entries, concepts)
    _detect_s_as_z(entries, concepts)
    _detect_y_as_vowel(entries, concepts)
    _detect_magic_e(spelling, entries, concepts)
    _detect_floss(spelling, entries, num_syllables, concepts)
    _detect_vowel_teams(entries, concepts)
    _detect_r_controlled(entries, concepts)


def detect_concepts(word, alignment, og_phonemes, syllables_phonemes, syllable_info, morpheme_parts,
                     base_words_111=(), base_words_final_e=(), base_words_final_y=()):
    concepts = set()

    # Always add phoneme concepts, even without alignment
    for pid in set(og_phonemes):
        concepts.add(f'phoneme_{pid}')

    spelling = word.lower()
    num_syllables = len(syllables_phonemes) if syllables_phonemes else 1

    # Syllable/CV concepts don't need alignment
    _detect_syllable_concepts(num_syllables, syllable_info, morpheme_parts, spelling, concepts)
    _detect_cv_patterns(syllable_info, concepts)
    detect_morphology_concepts(word, morpheme_parts, concepts)
    _detect_doubled_word(morpheme_parts, base_words_111, concepts)
    _detect_final_e_word(morpheme_parts, base_words_final_e, concepts)
    _detect_final_y_word(spelling, morpheme_parts, base_words_final_y, concepts)

    if not alignment:
        return sorted(concepts)
    entries = [(g, og_id, is_silent) for g, arp, og_id, is_silent in alignment]

    if '-' in word:
        for seg_spelling, seg_entries in _split_segments(alignment):
            _detect_on_segment(seg_spelling.lower(), seg_entries, concepts)
    else:
        _detect_blends(entries, concepts)
        _detect_ng_nk(spelling, entries, concepts)
        _detect_digraphs(entries, concepts)
        _detect_s_as_z(entries, concepts)
        _detect_y_as_vowel(entries, concepts)
        _detect_magic_e(spelling, entries, concepts)
        _detect_floss(spelling, entries, num_syllables, concepts)
        _detect_vowel_teams(entries, concepts)
        _detect_r_controlled(entries, concepts)

    return sorted(concepts)
