SELECT reasons.value, COUNT(*) FROM analyses, json_each(analyses.reasons) AS reasons GROUP BY reasons.value;
