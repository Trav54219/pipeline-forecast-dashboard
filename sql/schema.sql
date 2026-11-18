-- SQLite schema for the synthetic CRM extract. Dates are ISO-8601 text (sortable).
CREATE TABLE opportunities (
  opp_id TEXT PRIMARY KEY, account TEXT, owner TEXT, segment TEXT, amount REAL,
  created_date TEXT, planned_close_date TEXT, stage TEXT, closed_date TEXT,
  forecast_category TEXT, is_won INTEGER, is_closed INTEGER
);
CREATE TABLE stage_history (opp_id TEXT, stage TEXT, stage_order INTEGER, entered_date TEXT);
CREATE TABLE stage_prob (stage TEXT PRIMARY KEY, stage_order INTEGER, prob REAL, is_open INTEGER);
CREATE TABLE quota (quarter TEXT PRIMARY KEY, q_start TEXT, q_end TEXT, quota REAL);
