.PHONY: data test setup build-sources build-words build-db run clean explorer-concepts alignment-model pronunciation-corrections word-origins word-origin-sources word-origin-source

# Download the pinned data bundles in data/manifest.json and turn on the git hooks (upload edits on commit, download on checkout)
data:
	python3 scripts/data_bucket.py fetch

# Run the unit tests
test: data
	.venv/bin/python -B -m unittest discover -s tests

# Full setup: install deps + build everything
setup: venv build-db

# Create virtualenv and install dependencies
venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# Download external sources (~20 min, wiktionary is large)
build-sources:
	.venv/bin/python build_sources.py all

# Build words.json from CMU dict + wordfreq
build-words:
	.venv/bin/python build_word_data.py

# Build the SQLite database (runs full pipeline)
build-db: build-sources build-words
	.venv/bin/python build_word_db.py

# Train the letter-to-sound aligner on trusted source alignments
alignment-model:
	.venv/bin/python scripts/build_alignment_model.py

# Regenerate dictionary pronunciation corrections from their rules and manual entries
pronunciation-corrections:
	.venv/bin/python scripts/build_pronunciation_corrections.py

# Download every origin source (network): Wikipedia loan lists, US Census names, GeoNames, WordNet, Wiktionary categories
word-origin-sources:
	.venv/bin/python scripts/fetch_word_origins.py

# Download one source: make word-origin-source SOURCE=names|wikipedia|wiktionary (Wiktionary resumes after a rate limit)
word-origin-source:
	.venv/bin/python scripts/fetch_word_origins.py --only $(SOURCE)

# Rebuild data/mappings/word-origins.json from the saved sources (offline)
word-origins:
	.venv/bin/python scripts/build_word_origins.py

# Build the phonogram concept overlay used by the explorer (needs OBSERVATIONS=path to the phonogram observation database)
explorer-concepts:
	.venv/bin/python scripts/build_explorer_concepts.py --database $(OBSERVATIONS)

# Start the web app
run: data
	.venv/bin/python web_app.py

# Remove all generated data files
clean:
	rm -f data/words.json data/words.db data/words.db-shm data/words.db-wal data/words.db.bak
	rm -f data/g2p_aligned.json data/wiktionary_parsed.json data/morpholex_parsed.json
	rm -f data/missing_words.tsv data/_*
