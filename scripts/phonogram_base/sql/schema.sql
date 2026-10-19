CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE analyses (
    word TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('consistent', 'excluded')),
    reasons TEXT NOT NULL CHECK(json_valid(reasons)),
    rank INTEGER NOT NULL,
    weight REAL NOT NULL,
    detail TEXT NOT NULL CHECK(json_valid(detail))
);
CREATE TABLE patterns (
    id TEXT PRIMARY KEY,
    definition TEXT NOT NULL CHECK(json_valid(definition))
);
CREATE TABLE occurrences (
    word TEXT NOT NULL REFERENCES analyses(word),
    ordinal INTEGER NOT NULL,
    pattern_id TEXT NOT NULL REFERENCES patterns(id),
    layer TEXT NOT NULL,
    PRIMARY KEY(word, ordinal)
);
CREATE INDEX occurrences_pattern ON occurrences(pattern_id, word);
CREATE INDEX analyses_status_rank ON analyses(status, rank);
CREATE TABLE pronunciations (
    word TEXT NOT NULL REFERENCES analyses(word),
    ordinal INTEGER NOT NULL,
    source TEXT NOT NULL,
    phones TEXT NOT NULL CHECK(json_valid(phones)),
    senses TEXT NOT NULL CHECK(json_valid(senses)),
    status TEXT NOT NULL,
    reasons TEXT NOT NULL CHECK(json_valid(reasons)),
    detail TEXT NOT NULL CHECK(json_valid(detail)),
    PRIMARY KEY(word, ordinal)
);
