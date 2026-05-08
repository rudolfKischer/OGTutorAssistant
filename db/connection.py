import re

from sqlalchemy import create_engine, event
from db.tables import metadata

_engines = {}

# Cache compiled regexes for grapheme_only checks
_grapheme_re_cache = {}


def _grapheme_only(word, pattern):
    """SQLite custom function: returns 1 if word is fully composed of the
    allowed graphemes (pipe-separated in pattern), 0 otherwise.

    Graphemes are tried longest-first so 'sh' is matched before 's'.
    Split digraphs like 'a_e' are expanded to 'a.e' (vowel + any consonant + e).
    """
    if not word or not pattern:
        return 0
    rx = _grapheme_re_cache.get(pattern)
    if rx is None:
        parts = pattern.split('|')
        # Sort longest first so multi-letter graphemes match before singles
        parts.sort(key=len, reverse=True)
        re_parts = []
        for p in parts:
            if '_' in p:
                # Split digraph like a_e → a[^aeiou]e
                halves = p.split('_')
                re_parts.append(re.escape(halves[0]) + '[^aeiou]' + re.escape(halves[1]))
            else:
                re_parts.append(re.escape(p))
        rx = re.compile('^(' + '|'.join(re_parts) + ')+$', re.IGNORECASE)
        _grapheme_re_cache[pattern] = rx
    return 1 if rx.match(word) else 0


def get_engine(db_path, wal=False):
    key = (db_path, wal)
    if key not in _engines:
        engine = create_engine(f'sqlite:///{db_path}')

        @event.listens_for(engine, 'connect')
        def _on_connect(dbapi_conn, _):
            dbapi_conn.create_function('grapheme_only', 2, _grapheme_only)
            if wal:
                dbapi_conn.execute('PRAGMA journal_mode=WAL')

        _engines[key] = engine
    return _engines[key]


def create_tables(engine):
    metadata.drop_all(engine)
    metadata.create_all(engine)
