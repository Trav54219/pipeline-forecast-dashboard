# Tableau calculated fields

**Status: authored, not run.** These formulas were written by hand against the schema in
`sql/schema.sql` and have never been opened in Tableau. The same metrics are implemented and
tested in Python (`pfd/metrics.py`) and SQLite (`sql/metrics.sql`); use those as the reference
when checking a Tableau build. All data in this repo is synthetic.

Data source: join `opportunities` to `stage_prob` on `stage`, and to `quota` on the planned-close quarter.

## Row-level

**Is Open**
```
[is_closed] = 0
```

**Stage Probability** (assumed, matches `pfd/config.py`)
```
CASE [stage]
  WHEN 'Qualify' THEN 0.10
  WHEN 'Discovery' THEN 0.25
  WHEN 'Proposal' THEN 0.50
  WHEN 'Negotiation' THEN 0.75
  WHEN 'Closed Won' THEN 1.00
  ELSE 0 END
```

**Weighted Amount**
```
IF [Is Open] THEN [amount] * [Stage Probability] ELSE 0 END
```

**Planned Close Quarter**
```
STR(YEAR([planned_close_date])) + 'Q' + STR(DATEPART('quarter', [planned_close_date]))
```

## Aggregates

**Open Pipeline**
```
SUM(IF [Is Open] THEN [amount] END)
```

**Weighted Pipeline**
```
SUM([Weighted Amount])
```

**Commit**
```
SUM(IF [Is Open] AND [forecast_category] = 'Commit' THEN [amount] END)
```

**Best Case (cumulative)**
```
SUM(IF [Is Open] AND ([forecast_category] = 'Commit' OR [forecast_category] = 'Best Case')
    THEN [amount] END)
```

**Win Rate (count)**
```
SUM(IF [stage] = 'Closed Won' THEN 1 END)
/ SUM(IF [is_closed] = 1 THEN 1 END)
```

**Win Rate (amount)**
```
SUM(IF [stage] = 'Closed Won' THEN [amount] END)
/ SUM(IF [is_closed] = 1 THEN [amount] END)
```

## Coverage (level-of-detail)

**Closed Won in Quarter**
```
{ FIXED [Planned Close Quarter] : SUM(IF [stage] = 'Closed Won' THEN [amount] END) }
```
Note: this keys closed-won by planned-close quarter for brevity; the Python and SQL versions key it
by actual `closed_date`. To match them exactly, add a `Closed Quarter` field and fix on that.

**Quota**
```
{ FIXED [Planned Close Quarter] : MAX([quota]) }
```

**Coverage Ratio**
```
SUM(IF [Is Open] THEN [amount] END)
/ ( MAX([Quota]) - ZN(MAX([Closed Won in Quarter])) )
```

**Coverage vs 3x Benchmark** (the 3x figure is a rule of thumb)
```
IF [Coverage Ratio] >= 3 THEN 'At or above 3x' ELSE 'Below 3x' END
```

## Stage conversion

Tableau cannot derive "reached stage" from the opportunity table alone. Join `stage_history` and use:

**Reached Stage** (view filtered to one `stage` at a time)
```
COUNTD([opp_id])
```
**Conversion to Next Stage** is a table calculation over the ordered stage axis:
```
SUM([Advanced]) / ( SUM([Advanced]) + SUM([Lost Here]) )
```
where `Advanced` and `Lost Here` are computed in a custom SQL data source mirroring the
`stage_conversion` query in `sql/metrics.sql`.

## Backtest

Snapshot logic needs the history table and is easier in custom SQL than in calculated fields.
Use the `backtest_static` query in `sql/metrics.sql` as the data source, then:

**Forecast Error %**
```
(SUM([forecast_static]) - SUM([actual_won])) / SUM([actual_won])
```
