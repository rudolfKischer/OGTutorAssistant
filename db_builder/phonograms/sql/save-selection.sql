INSERT INTO review_selections(direction, concept_id, bundle_version) VALUES (?, ?, ?)
ON CONFLICT(direction) DO UPDATE SET concept_id = excluded.concept_id, bundle_version = excluded.bundle_version;
