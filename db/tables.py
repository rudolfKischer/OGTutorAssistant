from sqlalchemy import (
    MetaData, Table, Column, Integer, Float, Text, Index,
    ForeignKey,
)

metadata = MetaData()

words = Table('words', metadata,
    Column('id', Integer, primary_key=True),
    Column('word', Text, nullable=False, unique=True),
    Column('syllable_count', Integer, nullable=False),
    Column('frequency_zipf', Float, nullable=False),
    Column('frequency_per_million', Float, nullable=False, server_default='0'),
    Column('frequency_rank', Integer, nullable=False),
)
Index('idx_words_word', words.c.word)
Index('idx_words_freq', words.c.frequency_zipf.desc())
Index('idx_words_rank', words.c.frequency_rank)

word_phonemes = Table('word_phonemes', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('position', Integer, nullable=False, primary_key=True),
    Column('arpabet', Text, nullable=False),
    Column('og_phoneme_id', Text, nullable=False),
)
Index('idx_wp_phoneme', word_phonemes.c.og_phoneme_id)
Index('idx_wp_arpabet', word_phonemes.c.arpabet)

word_graphemes = Table('word_graphemes', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('position', Integer, nullable=False, primary_key=True),
    Column('grapheme', Text, nullable=False),
    Column('arpabet', Text),
    Column('og_phoneme_id', Text),
    Column('is_silent', Integer, nullable=False, server_default='0'),
)
Index('idx_wg_grapheme', word_graphemes.c.grapheme)
Index('idx_wg_grapheme_phoneme', word_graphemes.c.grapheme, word_graphemes.c.og_phoneme_id)
Index('idx_wg_og_phoneme', word_graphemes.c.og_phoneme_id)

word_syllables = Table('word_syllables', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('position', Integer, nullable=False, primary_key=True),
    Column('cv_pattern', Text, nullable=False),
    Column('og_type', Text, nullable=False),
)
Index('idx_ws_type', word_syllables.c.og_type)
Index('idx_ws_cv', word_syllables.c.cv_pattern)

word_pos = Table('word_pos', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('pos', Text, nullable=False, primary_key=True),
)
Index('idx_wpos_pos', word_pos.c.pos)

sight_words = Table('sight_words', metadata,
    Column('word', Text, nullable=False, primary_key=True),
    Column('source', Text, nullable=False, primary_key=True),
    Column('grade_level', Text),
    Column('irregularity_reason', Text),
)
Index('idx_sw_word', sight_words.c.word)

word_morphemes = Table('word_morphemes', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('position', Integer, nullable=False, primary_key=True),
    Column('morpheme', Text, nullable=False),
    Column('morpheme_type', Text, nullable=False),
)
Index('idx_wm_morpheme', word_morphemes.c.morpheme)
Index('idx_wm_type', word_morphemes.c.morpheme_type)

word_concepts = Table('word_concepts', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('concept', Text, nullable=False, primary_key=True),
)
Index('idx_wc_concept', word_concepts.c.concept)

word_definitions = Table('word_definitions', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('position', Integer, nullable=False, primary_key=True),
    Column('pos', Text),
    Column('definition', Text, nullable=False),
    Column('example', Text),
)
Index('idx_wd_word', word_definitions.c.word_id)

word_og_graphemes = Table('word_og_graphemes', metadata,
    Column('word_id', Integer, ForeignKey('words.id'), nullable=False, primary_key=True),
    Column('grapheme', Text, nullable=False, primary_key=True),
    Column('phoneme_id', Text, nullable=False, primary_key=True),
)
Index('idx_wog_grapheme', word_og_graphemes.c.grapheme)
Index('idx_wog_gp', word_og_graphemes.c.grapheme, word_og_graphemes.c.phoneme_id)

og_phonemes = Table('og_phonemes', metadata,
    Column('id', Text, primary_key=True),
    Column('sound', Text, nullable=False),
    Column('type', Text, nullable=False),
    Column('keyword', Text, nullable=False),
    Column('voiced', Integer, nullable=False),
)

og_graphemes = Table('og_graphemes', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('grapheme', Text, nullable=False),
    Column('phoneme_id', Text, nullable=False),
    Column('category', Text, nullable=False),
    Column('position', Text, nullable=False),
    Column('examples', Text, nullable=False),
    Column('notes', Text),
)
Index('idx_og_gr', og_graphemes.c.grapheme, og_graphemes.c.phoneme_id)
