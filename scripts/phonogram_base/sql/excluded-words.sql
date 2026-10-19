SELECT analyses.word, analyses.rank, analyses.status
FROM analyses
WHERE EXISTS (SELECT 1 FROM json_each(analyses.reasons) WHERE value = ?)
ORDER BY analyses.rank, analyses.word LIMIT ? OFFSET ?;
