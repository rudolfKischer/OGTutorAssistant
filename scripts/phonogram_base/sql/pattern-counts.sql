SELECT patterns.id, patterns.definition,
 COUNT(DISTINCT CASE WHEN analyses.status = 'consistent' THEN analyses.word END) AS consistent_words,
 COUNT(DISTINCT CASE WHEN analyses.status = 'excluded' THEN analyses.word END) AS excluded_words,
 COUNT(CASE WHEN analyses.status = 'consistent' THEN 1 END) AS consistent_occurrences
FROM patterns
LEFT JOIN occurrences ON occurrences.pattern_id = patterns.id
LEFT JOIN analyses ON analyses.word = occurrences.word
GROUP BY patterns.id;
