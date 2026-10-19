INSERT INTO word_rarity
SELECT wc.word_id, MIN(usage.words)
FROM word_concepts wc
JOIN (
    SELECT inner_wc.concept, COUNT(*) AS words
    FROM word_concepts inner_wc
    JOIN concepts c ON c.concept = inner_wc.concept
    WHERE c.kind IN (SELECT value FROM json_each(?))
    GROUP BY inner_wc.concept
) usage ON usage.concept = wc.concept
GROUP BY wc.word_id;
