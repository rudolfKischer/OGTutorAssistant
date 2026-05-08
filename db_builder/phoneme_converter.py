from .mappings import ARPABET_TO_OG, R_CONTROLLED_COMBOS
from .og_digraph_lookup import OG_DIGRAPH_LOOKUP


def arpabet_to_og_single(arpabet_with_stress):
    base = arpabet_with_stress.rstrip('012')
    if base == 'AH':
        return 'short_u' if '1' in arpabet_with_stress else 'schwa'
    return ARPABET_TO_OG.get(base, base.lower())


def _try_merge_pair(base, next_base):
    """Check if two consecutive phonemes form a combo (r-controlled or Y+UW).
    Returns (arpabet_str, og_id) or None."""
    if base == 'Y' and next_base == 'UW':
        return (f'{base}+{next_base}', 'long_u')
    combo_key = (base, next_base)
    if combo_key in R_CONTROLLED_COMBOS:
        return (f'{base}+{next_base}', R_CONTROLLED_COMBOS[combo_key])
    return None


def convert_phoneme_sequence(phonemes_list):
    result = []
    i = 0
    while i < len(phonemes_list):
        ph = phonemes_list[i]
        base = ph.rstrip('012')

        if i + 1 < len(phonemes_list):
            next_base = phonemes_list[i + 1].rstrip('012')
            merged = _try_merge_pair(base, next_base)
            if merged:
                result.append(merged)
                i += 2
                continue

        result.append((base, arpabet_to_og_single(ph)))
        i += 1
    return result


def _try_merge_graphemes_forward(alignment, i):
    """Merge a sounded grapheme with following silent graphemes into an OG digraph.

    Pattern: letter(sounded) + letter(silent) [+ letter(silent)]
    Example: 'e'(long_e) + 'e'(silent) → 'ee'
    Example: 'o'(long_o) + 'r'(silent) + 'e'(silent) → ore (if valid)
    Also handles multi-letter base: 'or'(or) + 'e'(silent) → 'ore'
    """
    g, arp = alignment[i]
    if arp is None:
        return None

    og_id = arpabet_to_og_single(arp)

    # Try merging 3, then 2 positions ahead
    for lookahead in (3, 2):
        if i + lookahead > len(alignment):
            continue

        candidate_letters = [alignment[i + k][0] for k in range(lookahead)]
        candidate = ''.join(candidate_letters)

        all_silent_after = all(
            alignment[i + k][1] is None for k in range(1, lookahead)
        )
        if not all_silent_after:
            continue

        if candidate in OG_DIGRAPH_LOOKUP and og_id in OG_DIGRAPH_LOOKUP[candidate]:
            base = arp.rstrip('012')
            return (candidate, base, og_id, lookahead)

    return None


def _try_merge_silent_before(alignment, i):
    """Merge a silent grapheme with the following sounded grapheme into an OG digraph.

    Pattern: letter(silent) + letter(sounded) [+ letter(silent)]
    Example: 't'(silent) + 'ch'(ch) → 'tch'
    Example: 'g'(silent) + 'n'(n) → 'gn'
    """
    g, arp = alignment[i]
    if arp is not None:
        return None  # this entry must be silent

    # Need at least one more entry after this
    if i + 1 >= len(alignment):
        return None

    next_g, next_arp = alignment[i + 1]
    if next_arp is None:
        return None  # next must be sounded

    next_og = arpabet_to_og_single(next_arp)
    next_base = next_arp.rstrip('012')

    # Try 2-entry merge: silent + sounded
    candidate2 = g + next_g
    if candidate2 in OG_DIGRAPH_LOOKUP and next_og in OG_DIGRAPH_LOOKUP[candidate2]:
        return (candidate2, next_base, next_og, 2)

    # Try 3-entry merge: silent + sounded + silent
    if i + 2 < len(alignment) and alignment[i + 2][1] is None:
        candidate3 = g + next_g + alignment[i + 2][0]
        if candidate3 in OG_DIGRAPH_LOOKUP and next_og in OG_DIGRAPH_LOOKUP[candidate3]:
            return (candidate3, next_base, next_og, 3)

    return None


def merge_alignment_with_og(alignment):
    result = []
    i = 0
    while i < len(alignment):
        g, arp = alignment[i]

        # Handle silent entries — try to merge with next sounded entry
        if arp is None:
            merged = _try_merge_silent_before(alignment, i)
            if merged:
                merged_g, merged_arp, merged_og, consumed = merged
                result.append((merged_g, merged_arp, merged_og, 0))
                i += consumed
                continue
            result.append((g, None, None, 1))
            i += 1
            continue

        base = arp.rstrip('012')

        # Try phoneme-level merge first (r-controlled, Y+UW)
        if i + 1 < len(alignment) and alignment[i + 1][1] is not None:
            next_g, next_arp = alignment[i + 1]
            next_base = next_arp.rstrip('012')
            merged = _try_merge_pair(base, next_base)
            if merged:
                # After phoneme merge, also try absorbing trailing silent letters
                combined_g = g + next_g
                consumed = 2
                # Check if adding a trailing silent makes a known OG grapheme
                while i + consumed < len(alignment) and alignment[i + consumed][1] is None:
                    test_g = combined_g + alignment[i + consumed][0]
                    if test_g in OG_DIGRAPH_LOOKUP and merged[1] in OG_DIGRAPH_LOOKUP[test_g]:
                        combined_g = test_g
                        consumed += 1
                    else:
                        break
                result.append((combined_g, merged[0], merged[1], 0))
                i += consumed
                continue

        # Try grapheme-level forward merge (sounded + silent → digraph)
        digraph = _try_merge_graphemes_forward(alignment, i)
        if digraph:
            merged_g, merged_arp, merged_og, consumed = digraph
            result.append((merged_g, merged_arp, merged_og, 0))
            i += consumed
            continue

        result.append((g, base, arpabet_to_og_single(arp), 0))
        i += 1
    return result
