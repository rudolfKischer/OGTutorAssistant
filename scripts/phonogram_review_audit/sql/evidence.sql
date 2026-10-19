SELECT DISTINCT a.word, a.status, a.rank, a.weight, a.reasons
FROM occurrences AS o JOIN analyses AS a ON a.word = o.word
WHERE o.pattern_id = ? ORDER BY a.rank, a.word;
