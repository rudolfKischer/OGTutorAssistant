SELECT status, COUNT(*), SUM(weight) FROM analyses GROUP BY status;
