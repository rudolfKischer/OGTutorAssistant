import os

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
MAPPINGS_DIR = os.path.join(DATA_DIR, 'mappings')
DB_PATH = os.path.join(DATA_DIR, 'words.db')
WORDS_JSON_PATH = os.path.join(DATA_DIR, 'words.json')
PRODUCTION_CACHE_PATH = os.path.join(DATA_DIR, 'production_cache.json')
PRODUCTION_CACHE_KEYS_PATH = os.path.join(BASE_DIR, 'production_cache_keys.csv')
UI_CONFIG_PATH = os.path.join(BASE_DIR, 'static', 'data', 'ui-config.json')
WIKTIONARY_PATH = os.path.join(DATA_DIR, 'wiktionary_parsed.json')
SIGHT_WORDS_PATH = os.path.join(DATA_DIR, 'sight_words.json')
MORPHOLEX_JSON_PATH = os.path.join(DATA_DIR, 'morpholex_parsed.json')
G2P_ALIGNED_PATH = os.path.join(DATA_DIR, 'g2p_aligned.json')

FLASK_PORT = 5001
DEFAULT_WORD_LIMIT = 50
MAX_WORD_LIMIT = 2000
MAX_DEFINITIONS_PER_WORD = 5
FREQ_STATS_EXAMPLE_COUNT = 8

USE_OG_SYLLABLE_DIVIDER = True  # True = orthographic (OG rules), False = phoneme-based (Kondrak/MOP)

SIGHT_WORD_SOURCES_NO_GRADE = ('reach',)
# SIGHT_WORD_SOURCES_NO_GRADE = ('reach', 'ufli', 'dolch')
SIGHT_WORD_SOURCES_WITH_GRADE = ()
# SIGHT_WORD_SOURCES_WITH_GRADE = ('hardin', 'fundations')
