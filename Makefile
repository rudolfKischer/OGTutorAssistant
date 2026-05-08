.PHONY: setup build-sources build-words build-db run clean

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

# Start the web app
run:
	.venv/bin/python web_app.py

# Remove all generated data files
clean:
	rm -f data/words.json data/words.db data/words.db-shm data/words.db-wal data/words.db.bak
	rm -f data/g2p_aligned.json data/wiktionary_parsed.json data/morpholex_parsed.json
	rm -f data/missing_words.tsv data/_*
