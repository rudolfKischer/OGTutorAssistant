# OG Tutor Assistant

A lesson-planning tool for Orton-Gillingham tutors. Provides a searchable word database with phoneme mappings, syllable analysis, morphology, definitions, and OG concept tagging.

## Setup

**Prerequisites:** Python 3.10+, `make`

```bash
git clone https://github.com/rudolfKischer/OGTutorAssistant.git
cd OGTutorAssistant
make setup
```

That's it. This installs dependencies, downloads external data (~20 min), and builds the database.

To start the app:

```bash
make run
# opens at http://localhost:5001
```

### Step-by-Step (if you prefer)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build_sources.py all     # download external sources (~20 min)
.venv/bin/python build_word_data.py       # build words.json
.venv/bin/python build_word_db.py         # build words.db
.venv/bin/python web_app.py               # start the web app
```

### Rebuilding the Database

The word bank database (`data/words.db`, ~200 MB) is not checked into git. It's rebuilt from source data.

```bash
make clean      # wipe generated files
make build-db   # rebuild everything
```

### Troubleshooting

- **`make build-sources` is slow** — The wiktionary download is ~700 MB compressed. Give it time.
- **`ModuleNotFoundError`** — Use the virtualenv: `source .venv/bin/activate`, or use `make run` / `make build-db` which use it automatically.
- **Database is missing** — Run `make build-db`.

## Project Structure

```
├── web_app.py              # Flask web app (API + serves static frontend)
├── config.py               # Paths, constants, feature flags
├── build_sources.py        # Downloads + parses external data into JSON
├── build_word_data.py      # Builds words.json from CMU dict + wordfreq
├── build_word_db.py        # Builds words.db from all JSON sources
├── db/                     # SQLAlchemy table definitions + query helpers
├── db_builder/             # Loaders that populate the database tables
├── data/
│   ├── mappings/           # Hand-curated OG reference data (version-controlled)
│   ├── sight_words.json    # Curated sight word lists (version-controlled)
│   └── cmudict_syllabified.rep  # Kondrak syllabification (version-controlled)
├── static/                 # Frontend (HTML/JS)
├── OG_DOCS/                # Reference PDFs (scope & sequence docs)
└── OG_Examples/            # Example lesson plans and scope sequences
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

### Generated (fully reconstructible)

| File | Source | Rebuild |
|------|--------|---------|
| `data/words.json` | [cmudict](https://pypi.org/project/cmudict/) + [wordfreq](https://pypi.org/project/wordfreq/) | `python3 build_word_data.py` |
| `data/words.db` | All data files + mappings + project code | `python3 build_word_db.py` |

### Downloaded (reconstructible via `build_sources.py`)

| File | Source | URL |
|------|--------|-----|
| `data/g2p_aligned.json` | Phonetisaurus G2P alignments for CMU dict | [aligned-cmudict](https://github.com/ckw017/aligned-cmudict) |
| `data/wiktionary_parsed.json` | English Wiktionary definitions, POS, examples | [kaikki.org](https://kaikki.org/dictionary/rawdata.html) |
| `data/morpholex_parsed.json` | MorphoLex morphological segmentation | [MorphoLex-en](https://github.com/hugomailhot/MorphoLex-en) |

### Version-controlled reference data

| File | Description |
|------|-------------|
| `data/mappings/arpabet_to_og.json` | ARPABET-to-OG phoneme map + 44 OG phoneme definitions |
| `data/mappings/og_grapheme_spellings.json` | 384 grapheme-phoneme correspondences with OG categories |
| `data/mappings/og_concepts.json` | Blends, vowel teams, magic-e patterns, FLOSS rule, CV patterns |
| `data/mappings/contractions.json` | Valid contractions and apostrophe words |
| `data/mappings/inflectional_suffixes.json` | Suffix spelling change rules (-ing, -ed, -er, etc.) |
| `data/mappings/irregularity_detection.json` | Primary grapheme-phoneme expectations for irregularity detection |
| `data/sight_words.json` | 253 sight words from REACH, Hardin, UFLI, and Fundations curricula |
