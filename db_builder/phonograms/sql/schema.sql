CREATE TABLE IF NOT EXISTS phonogram_definitions (
    id TEXT PRIMARY KEY,
    spelling TEXT NOT NULL,
    sounds TEXT NOT NULL CHECK(json_valid(sounds))
);
CREATE TABLE IF NOT EXISTS blend_definitions (
    concept_id TEXT PRIMARY KEY,
    definition TEXT NOT NULL CHECK(json_valid(definition)),
    bundle_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS blend_components (
    concept_id TEXT NOT NULL REFERENCES blend_definitions(concept_id),
    ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
    phonogram_id TEXT NOT NULL REFERENCES phonogram_definitions(id),
    start INTEGER NOT NULL CHECK(start >= 0),
    end INTEGER NOT NULL CHECK(end > start),
    PRIMARY KEY(concept_id, ordinal)
);
CREATE TABLE IF NOT EXISTS review_selections (
    direction TEXT PRIMARY KEY CHECK(direction IN ('reading', 'spelling')),
    concept_id TEXT NOT NULL REFERENCES blend_definitions(concept_id),
    bundle_version TEXT NOT NULL
);
