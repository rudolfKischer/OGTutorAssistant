# Maps "Introduction to Morphology" curriculum items to word_concepts tags.
#
# Two mechanisms, per record:
#   kind='morpheme' — matches word_morphemes rows (word_id, morpheme, morpheme_type).
#     `match` lists every surface spelling MorphoLex uses for this morpheme
#     (assimilated prefixes / collapsed suffixes count as the same concept).
#   kind='spelling' — matches word_morphemes never stores the taught spelling at
#     all (e.g. -tion/-ation/-sion collapse to a bare "ion" suffix, -ture is never
#     decomposed). Falls back to a spelling check on the word itself, optionally
#     gated by `requires_morpheme` to keep it an actual morpheme boundary rather
#     than a coincidental spelling match.
#
# -cur- is left out of this table entirely: MorphoLex stores concur/occur/recur/
# current etc. as monomorphemic whole words, so a word_morphemes-derived rule
# would yield ~1 word. It needs a hand-curated word list instead (not built here).

MORPHOLOGY_CONCEPTS = [
    {'id': 'morph_suffix_plural', 'label': 'Plurals (-s, -es)', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['s', 'es']},
    {'id': 'morph_suffix_ing', 'label': '-ing', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ing']},
    {'id': 'morph_suffix_ed', 'label': '-ed', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ed']},
    {'id': 'morph_suffix_er', 'label': '-er', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['er']},
    {'id': 'morph_suffix_ful', 'label': '-ful', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ful']},
    {'id': 'morph_suffix_less', 'label': '-less', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['less']},
    {'id': 'morph_suffix_est', 'label': '-est', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['est']},
    {'id': 'morph_suffix_y', 'label': '-y', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['y']},
    {'id': 'morph_suffix_ly', 'label': '-ly', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ly']},
    {'id': 'morph_suffix_ness', 'label': '-ness', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ness']},

    {'id': 'morph_prefix_re', 'label': 're-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['re']},
    {'id': 'morph_prefix_pre', 'label': 'pre-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['pre']},
    {'id': 'morph_prefix_un', 'label': 'un-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['un']},

    {'id': 'morph_suffix_tion', 'label': '-tion', 'kind': 'spelling',
     'word_suffix': 'tion', 'requires_morpheme': ('suffix', 'ion')},
    {'id': 'morph_suffix_ation', 'label': '-ation', 'kind': 'spelling',
     'word_suffix': 'ation', 'requires_morpheme': ('suffix', 'ion')},

    {'id': 'morph_root_ject', 'label': '-ject-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['ject']},
    {'id': 'morph_root_struct', 'label': '-struct-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['struct']},
    {'id': 'morph_root_act', 'label': '-act-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['act']},
    {'id': 'morph_root_tract', 'label': '-tract-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['tract']},
    {'id': 'morph_root_spect', 'label': '-spect-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['spect']},

    {'id': 'morph_prefix_pro', 'label': 'pro-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['pro']},
    {'id': 'morph_prefix_ex', 'label': 'ex-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['ex']},

    {'id': 'morph_suffix_sion', 'label': '-sion', 'kind': 'spelling',
     'word_suffix': 'sion', 'requires_morpheme': ('suffix', 'ion')},
    {'id': 'morph_suffix_ence', 'label': '-ence', 'kind': 'spelling',
     'word_suffix': 'ence'},

    {'id': 'morph_root_duce', 'label': '-duce-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['duce', 'duct']},
    {'id': 'morph_root_ture', 'label': '-tur(e)', 'kind': 'spelling',
     'word_suffix': 'ture'},
    {'id': 'morph_root_port', 'label': '-port-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['port']},
    {'id': 'morph_root_tort', 'label': '-tort-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['tort']},

    {'id': 'morph_suffix_able', 'label': '-able', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['able']},
    {'id': 'morph_root_sect', 'label': '-sect-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['sect']},

    {'id': 'morph_prefix_con', 'label': 'con-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['con', 'co', 'com', 'col', 'cor']},
    {'id': 'morph_prefix_sub', 'label': 'sub-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['sub']},
    {'id': 'morph_prefix_de', 'label': 'de-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['de']},
    {'id': 'morph_prefix_mid', 'label': 'mid-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['mid']},
    {'id': 'morph_prefix_mis', 'label': 'mis-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['mis']},
    {'id': 'morph_prefix_trans', 'label': 'trans-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['trans']},
    {'id': 'morph_prefix_dis', 'label': 'dis-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['dis', 'di']},
    {'id': 'morph_prefix_per', 'label': 'per-', 'kind': 'morpheme',
     'morpheme_type': 'prefix', 'match': ['per']},

    {'id': 'morph_root_fuse', 'label': '-fus(e)-', 'kind': 'morpheme',
     'morpheme_type': 'root', 'match': ['fuse', 'fus']},

    {'id': 'morph_suffix_ious', 'label': '-ious', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ious']},
    {'id': 'morph_suffix_ian', 'label': '-ian', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ian']},
    {'id': 'morph_suffix_ium', 'label': '-ium', 'kind': 'morpheme',
     'morpheme_type': 'suffix', 'match': ['ium']},
]
