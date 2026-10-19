SELECT grapheme, arpabet, og_phoneme_id, is_silent
FROM word_graphemes WHERE word_id = (SELECT id FROM words WHERE word = ?)
ORDER BY position
