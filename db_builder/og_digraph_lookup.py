"""Build a lookup of multi-letter OG graphemes and their valid phoneme mappings.

OG_DIGRAPH_LOOKUP: dict mapping grapheme string -> set of valid og phoneme IDs.
Example: {'ee': {'long_e', 'short_i', 'long_a'}, 'ie': {'long_e', 'long_i', 'short_e', 'short_i'}, ...}

Used by merge_alignment_with_og() to recognize when adjacent single-letter
grapheme entries should be merged into a proper OG digraph.
"""

import json
import os

from config import MAPPINGS_DIR


def _build_lookup():
    path = os.path.join(MAPPINGS_DIR, 'og_grapheme_spellings.json')
    with open(path, 'r') as f:
        data = json.load(f)

    lookup = {}
    for entry in data:
        g = entry['grapheme']
        if len(g) < 2 or '_' in g:  # skip single letters and split digraphs (a_e)
            continue
        lookup.setdefault(g, set()).add(entry['phoneme_id'])
    return lookup


OG_DIGRAPH_LOOKUP = _build_lookup()
