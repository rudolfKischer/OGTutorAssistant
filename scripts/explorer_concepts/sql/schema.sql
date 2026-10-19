CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE families (
    family TEXT PRIMARY KEY, label TEXT NOT NULL, grp TEXT NOT NULL,
    ordinal INTEGER NOT NULL, collapsed INTEGER NOT NULL, lens TEXT NOT NULL
);
CREATE TABLE concepts (
    concept TEXT PRIMARY KEY, label TEXT NOT NULL, kind TEXT NOT NULL, family TEXT,
    sort_key TEXT NOT NULL, spelling TEXT NOT NULL, sounds TEXT NOT NULL, tail INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE word_concepts (
    word_id INTEGER NOT NULL, concept TEXT NOT NULL, PRIMARY KEY (word_id, concept)
) WITHOUT ROWID;
CREATE INDEX idx_overlay_wc_concept ON word_concepts(concept);
CREATE TABLE word_analysis (
    word_id INTEGER PRIMARY KEY, status TEXT NOT NULL, reasons TEXT NOT NULL, syllables TEXT NOT NULL, written TEXT NOT NULL, warnings TEXT NOT NULL
);
CREATE TABLE word_phonograms (
    word_id INTEGER NOT NULL, ordinal INTEGER NOT NULL, concept TEXT, layer TEXT NOT NULL, syllable INTEGER,
    spelling TEXT NOT NULL, sounds TEXT NOT NULL, spans TEXT NOT NULL, phones TEXT NOT NULL,
    PRIMARY KEY (word_id, ordinal)
) WITHOUT ROWID;
CREATE TABLE sounds (
    sound TEXT PRIMARY KEY, plain TEXT NOT NULL, dictionary TEXT NOT NULL, ipa TEXT NOT NULL, example TEXT NOT NULL
);
CREATE TABLE concept_sounds (concept TEXT NOT NULL, sound TEXT NOT NULL, PRIMARY KEY (concept, sound)) WITHOUT ROWID;
CREATE INDEX idx_overlay_cs_sound ON concept_sounds(sound);
CREATE INDEX idx_overlay_concepts_spelling ON concepts(spelling);
CREATE TABLE facet_counts (concept TEXT PRIMARY KEY, words INTEGER NOT NULL);
CREATE TABLE heteronyms (
    word_id INTEGER PRIMARY KEY, sources TEXT NOT NULL, senses TEXT NOT NULL, link TEXT NOT NULL, confidence TEXT NOT NULL
);
CREATE TABLE pronunciations (
    word_id INTEGER NOT NULL, ordinal INTEGER NOT NULL, source TEXT NOT NULL, sounds TEXT NOT NULL,
    senses TEXT NOT NULL, analysis TEXT NOT NULL, PRIMARY KEY (word_id, ordinal)
) WITHOUT ROWID;
CREATE TABLE word_origin_flags (word_id INTEGER NOT NULL, flag TEXT NOT NULL, detail TEXT NOT NULL, PRIMARY KEY (word_id, flag)) WITHOUT ROWID;
CREATE INDEX idx_overlay_origin_flag ON word_origin_flags(flag);
CREATE TABLE word_rarity (word_id INTEGER PRIMARY KEY, weakest INTEGER NOT NULL);
