SELECT cs.sound, COUNT(DISTINCT wc.word_id)
FROM concept_sounds cs JOIN word_concepts wc ON wc.concept = cs.concept
GROUP BY cs.sound
