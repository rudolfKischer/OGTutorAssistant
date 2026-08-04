# Production Cache: concept → words, and sight-word lookup

A single JSON file, `data/production_cache.json`, holds the two "hot path"
lookups any consuming app needs:

1. All words tagged with a given phonics concept (e.g. `syllable_div_tiger`,
   `soft_c`, `bossy_r_ur`).
2. Whether a given word is a sight word.

It is generated from the full authoring database (`data/words.db`) by
`build_production_cache.py`, and is meant to be loaded **once, fully into
memory**, by whatever process needs these lookups. There is no runtime
database dependency on this path — no SQLite, no network call, no query.
This doc specifies the file format so any Python app can consume it
directly, independent of this repo's code.

## Why in-memory, not a live query

The full dataset here is small (currently ~330 concepts, ~850K
concept-word pairs, ~65K distinct words, ~110 sight words) — a few MB as
JSON. At that size, loading it into a plain dict/set at process startup and
serving lookups from RAM is faster and simpler than querying a database on
every request, and removes an entire class of production dependency (DB
connectivity, connection pooling, query latency) from the hot path.

## File format

```json
{
  "concept_to_words": {
    "<concept_id>": ["word1", "word2", "..."],
    "...": ["..."]
  },
  "sight_words": ["word1", "word2", "..."]
}
```

- `concept_to_words` — object keyed by concept id (string). Each value is a
  list of every word tagged with that concept, sorted alphabetically. A
  concept id not present in this object has zero words for it (treat a
  missing key the same as an empty list, not an error).
- `sight_words` — a flat, deduplicated, sorted list of every word that is a
  sight word under any source/grade. This file only records sight-word
  *membership* (yes/no) — it does not carry which source or grade a word
  came from. If you need that, you must go back to `words.db`'s
  `sight_words` table.
- Every word string is lowercase, matching the spelling stored in `words.word`.
- The file has no version field. Treat it as fully replaced on every
  rebuild — do not attempt to diff or merge it.

## How to load it (minimal, dependency-free)

Any Python app can consume the file with nothing beyond the standard
library:

```python
import json

with open("production_cache.json") as f:
    _cache = json.load(f)

CONCEPT_TO_WORDS = _cache["concept_to_words"]
SIGHT_WORDS = set(_cache["sight_words"])  # convert once, for O(1) membership


def words_for_concept(concept: str) -> list[str]:
    return CONCEPT_TO_WORDS.get(concept, [])


def is_sight_word(word: str) -> bool:
    return word in SIGHT_WORDS
```

Load it exactly once (e.g. at module import time, or in your app's startup
hook) and hold `CONCEPT_TO_WORDS` / `SIGHT_WORDS` as long-lived
process-global state. Do not re-read the file per request.

### Using the reference implementation instead

If your app already lives in this repo (or vendors this file), you can
import the maintained version directly rather than re-implementing the
loader:

```python
import production_cache

production_cache.words_for_concept("syllable_div_tiger")   # -> list[str]
production_cache.is_sight_word("the")                       # -> bool
production_cache.known_concepts()                           # -> list[str], all valid concept ids
production_cache.reload()                                   # re-read the file from disk into memory
```

`production_cache.py` reads its file path from `config.PRODUCTION_CACHE_PATH`
(`data/production_cache.json` by default) and loads it at import time — the
same one-load-then-serve-from-RAM contract described above, just with
`reload()` available if you need to refresh without restarting the process.

## Keeping it up to date

The cache is a build artifact, not a live view of the database — it goes
stale the moment `words.db`'s concepts or sight words change. Regenerate it
with:

```bash
python build_production_cache.py
```

This is a **separate, deliberate step** from `build_word_db.py` — rebuilding
the full authoring database does not automatically refresh this file, so an
in-progress/broken rebuild of `words.db` can never leak into production
through this path. Run `build_production_cache.py` explicitly whenever you
want a change (new concept, new word, new sight-word list) to reach
consumers of this file.

After regenerating the file, either:
- restart the consuming process (simplest — the file is only read at
  import/startup), or
- call `production_cache.reload()` (or your own equivalent) if the process
  needs to pick up the change without restarting.

## What this does *not* cover

Phonemes, graphemes, syllable structure, morphemes, definitions, and
frequency data all remain in `words.db` only. This cache is deliberately
narrow — concept membership and sight-word status only — matching the
current production scope. If a consumer needs anything beyond those two
lookups, it needs to query `words.db` directly (see `db/tables.py` for that
schema), not this file.
