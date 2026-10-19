INSERT INTO phonogram_definitions(id, spelling, sounds) VALUES (?, ?, ?)
ON CONFLICT(id) DO UPDATE SET spelling = excluded.spelling, sounds = excluded.sounds;
