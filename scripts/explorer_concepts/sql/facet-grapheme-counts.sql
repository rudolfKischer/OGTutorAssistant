SELECT c.spelling, COUNT(DISTINCT wc.word_id)
FROM concepts c JOIN word_concepts wc ON wc.concept = c.concept
WHERE c.kind IN (SELECT value FROM json_each(?))
GROUP BY c.spelling
