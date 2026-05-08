# Setup Guide

## Prerequisites

- Python 3.10+
- `make` (pre-installed on macOS/Linux)

## Quick Start (one command)

```bash
make setup
```

This will:
1. Create a Python virtualenv in `.venv/`
2. Install all dependencies
3. Download external data sources (~20 min, wiktionary is the bottleneck)
4. Build `data/words.json` from CMU dict + wordfreq
5. Build `data/words.db` (the SQLite word bank database)

## Run the App

```bash
make run
```

Opens at `http://localhost:5001`.

## Step-by-Step (if you prefer)

```bash
# 1. Create virtualenv and install deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Download external sources (g2p alignments, wiktionary, morpholex)
.venv/bin/python build_sources.py all

# 3. Build words.json (CMU dict phonemes + wordfreq frequencies)
.venv/bin/python build_word_data.py

# 4. Build the SQLite database
.venv/bin/python build_word_db.py

# 5. Start the web app
.venv/bin/python web_app.py
```

## What Gets Built

The data pipeline downloads external sources and builds a single SQLite database (`data/words.db`, ~200 MB) containing:

- **~130k words** with phoneme sequences, grapheme-phoneme alignments, syllable analysis
- **OG concept tags** (blends, vowel teams, magic-e, FLOSS rule, etc.)
- **Morpheme segmentation** (prefixes, roots, suffixes)
- **Wiktionary definitions** and part-of-speech tags
- **Sight word lists** with irregularity analysis
- **Frequency data** (Zipf scale + per-million counts)

```
External sources          build_sources.py         build_word_data.py       build_word_db.py
─────────────────    ──>   ───────────────    ──>   ────────────────   ──>   ──────────────
aligned-cmudict            g2p_aligned.json         words.json               words.db
kaikki.org/wiktionary      wiktionary_parsed.json
MorphoLex-en               morpholex_parsed.json
```

## Rebuilding

To wipe generated data and rebuild from scratch:

```bash
make clean
make build-db
```

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

## Troubleshooting

**`make build-sources` hangs or is slow**: The wiktionary download is ~700 MB compressed. Give it time.

**`ModuleNotFoundError`**: Make sure you're using the virtualenv. Either activate it (`source .venv/bin/activate`) or use `make run` / `make build-db` which use the venv automatically.

**Database is missing**: Run `make build-db`. The database is not checked into git because it's ~200 MB — it's rebuilt from source data.
