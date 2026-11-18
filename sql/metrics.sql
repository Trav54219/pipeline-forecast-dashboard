-- Key forecast metrics in SQL (SQLite dialect; window functions need 3.25+).
-- Named queries are split on the "-- name:" markers by pfd/sqlmetrics.py.
-- Parameters: :as_of, :quarter

-- name: weighted_by_stage
SELECT o.stage, COUNT(*) AS n, SUM(o.amount) AS amount, SUM(o.amount * p.prob) AS weighted
FROM opportunities o JOIN stage_prob p ON p.stage = o.stage
WHERE p.is_open = 1
GROUP BY o.stage, p.stage_order
ORDER BY p.stage_order;

-- name: category_rollup
SELECT o.forecast_category AS category, COUNT(*) AS n, SUM(o.amount) AS amount,
       SUM(o.amount * p.prob) AS weighted
FROM opportunities o JOIN stage_prob p ON p.stage = o.stage
WHERE p.is_open = 1
GROUP BY o.forecast_category;

-- name: win_rate
SELECT SUM(is_won) AS won,
       SUM(1 - is_won) AS lost,
       1.0 * SUM(is_won) / COUNT(*) AS win_rate,
       1.0 * SUM(CASE WHEN is_won = 1 THEN amount ELSE 0 END) / SUM(amount) AS win_rate_amount
FROM opportunities
WHERE is_closed = 1;

-- name: stage_conversion
WITH reach AS (
  SELECT o.opp_id, o.stage AS cur,
         (SELECT MAX(h.stage_order) FROM stage_history h
           WHERE h.opp_id = o.opp_id AND h.stage_order <= 5) AS ro
  FROM opportunities o
), agg AS (
  SELECT p.stage, p.stage_order,
         SUM(CASE WHEN r.ro >= p.stage_order THEN 1 ELSE 0 END) AS reached,
         SUM(CASE WHEN r.ro >  p.stage_order THEN 1 ELSE 0 END) AS advanced,
         SUM(CASE WHEN r.ro =  p.stage_order AND r.cur = 'Closed Lost' THEN 1 ELSE 0 END) AS lost_here
  FROM stage_prob p CROSS JOIN reach r
  WHERE p.is_open = 1
  GROUP BY p.stage, p.stage_order
)
SELECT stage, reached, advanced, lost_here,
       1.0 * advanced / NULLIF(advanced + lost_here, 0) AS conversion
FROM agg ORDER BY stage_order;

-- name: coverage
SELECT q.quarter, q.quota,
       COALESCE((SELECT SUM(amount) FROM opportunities
                  WHERE is_won = 1 AND closed_date BETWEEN q.q_start AND q.q_end), 0) AS closed_won,
       COALESCE(SUM(o.amount), 0) AS pipeline,
       COALESCE(SUM(o.amount * p.prob), 0) AS weighted
FROM quota q
LEFT JOIN opportunities o ON o.is_closed = 0 AND o.planned_close_date BETWEEN q.q_start AND q.q_end
LEFT JOIN stage_prob p ON p.stage = o.stage
WHERE q.quarter = :quarter
GROUP BY q.quarter, q.quota;

-- name: backtest_static
-- Snapshot at each quarter start: latest stage entered strictly before q_start.
WITH snap AS (
  SELECT q.quarter, h.opp_id, h.stage,
         ROW_NUMBER() OVER (PARTITION BY q.quarter, h.opp_id
                            ORDER BY h.entered_date DESC, h.stage_order DESC) AS rn
  FROM quota q JOIN stage_history h ON h.entered_date < q.q_start
  WHERE q.q_end <= :as_of
), cohort AS (
  SELECT s.quarter, o.amount, p.prob, o.is_won, o.closed_date, q.q_start, q.q_end
  FROM snap s
  JOIN opportunities o ON o.opp_id = s.opp_id
  JOIN stage_prob p ON p.stage = s.stage AND p.is_open = 1
  JOIN quota q ON q.quarter = s.quarter
  WHERE s.rn = 1 AND o.planned_close_date BETWEEN q.q_start AND q.q_end
)
SELECT quarter, COUNT(*) AS n_deals, SUM(amount) AS pipeline, SUM(amount * prob) AS forecast_static,
       SUM(CASE WHEN is_won = 1 AND closed_date BETWEEN q_start AND q_end THEN amount ELSE 0 END) AS actual_won
FROM cohort
GROUP BY quarter
ORDER BY quarter;
