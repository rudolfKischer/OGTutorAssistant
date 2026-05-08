# OG Tutor Assistant

A lesson-planning tool for Orton-Gillingham tutors. Provides a searchable word database with phoneme mappings, syllable analysis, morphology, definitions, and OG concept tagging.

## Quick Start

```bash
pip install cmudict wordfreq sqlalchemy flask
python3 build_sources.py all   # download external data (~20 min, wiktionary is large)
python3 build_word_data.py     # build words.json from CMU dict + wordfreq
python3 build_word_db.py       # build words.db (SQLite)
python3 web_app.py             # start the web app
```

## Data Pipeline

```
External sources          build_sources.py         build_word_data.py       build_word_db.py
─────────────────    ──>   ───────────────    ──>   ────────────────   ──>   ──────────────
aligned-cmudict            g2p_aligned.json         words.json               words.db
kaikki.org/wiktionary      wiktionary_parsed.json   (cmudict + wordfreq)
MorphoLex-en               morpholex_parsed.json
```

## Data Sources

### Generated from Python packages (fully reconstructible)

| File | Source | Rebuild |
|------|--------|---------|
| `data/words.json` | [cmudict](https://pypi.org/project/cmudict/) + [wordfreq](https://pypi.org/project/wordfreq/) | `python3 build_word_data.py` |
| `data/words.db` | All data files + mappings + project code | `python3 build_word_db.py` |

### Downloaded from external sources (reconstructible via `build_sources.py`)

| File | Source | URL |
|------|--------|-----|
| `data/g2p_aligned.json` | Phonetisaurus G2P alignments for CMU dict | [aligned-cmudict](https://github.com/ckw017/aligned-cmudict) |
| `data/wiktionary_parsed.json` | English Wiktionary definitions, POS, examples | [kaikki.org](https://kaikki.org/dictionary/rawdata.html) |
| `data/morpholex_parsed.json` | MorphoLex morphological segmentation | [MorphoLex-en](https://github.com/hugomailhot/MorphoLex-en) |

### Committed reference data (version-controlled in `data/mappings/`)

| File | Description |
|------|-------------|
| `arpabet_to_og.json` | ARPABET-to-OG phoneme map + 44 OG phoneme definitions (type, voiced, keyword) |
| `og_grapheme_spellings.json` | 384 grapheme-phoneme correspondences with OG categories, positions, notes |
| `og_concepts.json` | Blends, vowel teams, magic-e patterns, FLOSS rule, CV patterns |
| `contractions.json` | Valid contractions and apostrophe words |
| `inflectional_suffixes.json` | Suffix spelling change rules (-ing, -ed, -er, etc.) |
| `irregularity_detection.json` | Primary grapheme-phoneme expectations for irregularity detection |

### Committed reference data (version-controlled in `data/`)

| File | Description |
|------|-------------|
| `sight_words.json` | 253 sight words from REACH, Hardin, UFLI, and Fundations curricula |

## Compact Data Formats

All JSON data files use arrays instead of objects to minimize key repetition:

- **words.json** — `[word, [phonemes], zipf, per_million, rank]`
- **g2p_aligned.json** — `{word: [[grapheme, phoneme], ...]}`
- **wiktionary_parsed.json** — `{word: [[pos, definition, example], ...]}`
- **morpholex_parsed.json** — `{word: [[prefixes], [roots], [suffixes]]}`
