INSERT INTO blend_definitions(concept_id, definition, bundle_version) VALUES (?, ?, ?)
ON CONFLICT(concept_id) DO UPDATE SET definition = excluded.definition, bundle_version = excluded.bundle_version;
