# Pipeline Forecast Dashboard

Pipeline forecasting and BI for a B2B sales team, built end to end on a **synthetic** CRM extract:
weighted pipeline, commit / best case / pipeline categories, stage conversion, win rate, coverage vs
quota, and a quarter-by-quarter forecast-vs-actual backtest. Python reference implementation, SQL
versions of the same metrics, a static Chart.js dashboard, a LookML semantic model and Tableau
calculated fields.

## Data is synthetic

`pfd/data.py` generates 1,800 opportunities and their stage history with a fixed seed (42). The
snapshot date is 2025-09-30. Account names are `Account 0001`-style placeholders, owners are
`Rep 01`-`Rep 12`. Stage probabilities, win/advance rates, deal sizes and quotas are **assumptions
I chose**, not benchmarks. Metric values in this repo describe the generator, not any real business,
and nothing here should be read as evidence about real-world forecast accuracy.

## Run

```
pip install -r requirements.txt
python -m pfd        # writes data/*.csv, data/metrics.json, docs/dashboard.html
python -m pytest -q
```

Open `docs/dashboard.html` in a browser (it loads Chart.js 4.4.1 from cdnjs).

## What is computed

| Metric | Definition |
|---|---|
| Weighted pipeline | open amount x assumed stage probability (10/25/50/75%) |
| Categories | rep-assigned Commit / Best Case / Pipeline; Best Case and Pipeline shown cumulatively |
| Stage conversion | advanced / (advanced + lost at that stage); deals still sitting in the stage are excluded |
| Win rate | closed-won / closed, by count and by amount, plus by segment |
| Coverage | open pipeline planned to close in the quarter / (quota - closed-won so far); 3x is a rule of thumb |
| Backtest | snapshot at each quarter start (history strictly before it); cohort = open deals planned to close in the quarter; forecast = sum(amount x P(stage)); actual = cohort deals that closed won in the quarter |

The backtest compares two weightings: the assumed probabilities, and empirical probabilities
(share of deals that reached a stage and eventually won) learned only from deals closed before the
snapshot, falling back to the assumed value under 30 samples.

## Layout

- `pfd/` Python: `data.py` generator, `metrics.py` reference metrics, `sqlmetrics.py` SQLite loader, `dashboard.py` HTML generator
- `sql/schema.sql`, `sql/metrics.sql` SQLite versions of the key metrics (needs SQLite 3.25+ for window functions)
- `lookml/` LookML model, views, measures, explore
- `docs/dashboard.html` generated dashboard; `docs/tableau_calculated_fields.md`
- `tests/` pytest suite

## What is verified, and what is not

Verified by the test suite (run locally, Python 3.12, SQLite 3.53):
- generator is deterministic and internally consistent (dates, stage history vs current stage)
- metric functions match hand-calculated values on small fixtures, including a no-leakage check on the backtest snapshot
- every SQL query returns the same numbers as the Python implementation on the full synthetic set
- the committed dashboard HTML equals what the generator produces, embeds valid JSON, and loads only cdnjs
- the LookML and Tableau docs carry the "not run" label and the Tableau stage probabilities match `pfd/config.py`

Not verified:
- **LookML** and **Tableau** files are authored by hand and have never been loaded into Looker or Tableau. Syntax and behaviour there are unchecked.
- The dashboard's JavaScript passes `node --check`, and the pinned Chart.js URL returned HTTP 200, but I did not render the page in a browser in this build.
- SQL is SQLite dialect only; other warehouses need small changes (date and window syntax).
- The empirical-probability backtest is Python only; the SQL backtest uses the assumed probabilities.

## Known simplifications

Forecast category is the rep flag on each open deal today, so the backtest does not use historical
category snapshots. Deal amounts do not change over time. The Tableau doc keys closed-won by planned
quarter for brevity (noted in the file).
