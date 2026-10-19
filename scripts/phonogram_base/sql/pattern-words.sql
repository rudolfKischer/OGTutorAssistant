SELECT analyses.word, analyses.rank, analyses.status
FROM analyses
WHERE analyses.status = ? AND EXISTS (
 SELECT 1 FROM occurrences WHERE occurrences.word = analyses.word AND occurrences.pattern_id = ?
)
ORDER BY analyses.rank, analyses.word LIMIT ? OFFSET ?;
