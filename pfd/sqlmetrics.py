"""Load the synthetic extract into in-memory SQLite and run sql/metrics.sql."""
import re
import sqlite3
from pathlib import Path

from .config import AS_OF, QUOTA, STAGES
from .metrics import quarter_bounds

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def build_db(opps, hist):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript((SQL_DIR / "schema.sql").read_text())
    con.executemany("INSERT INTO opportunities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
        (o.opp_id, o.account, o.owner, o.segment, o.amount, o.created_date.isoformat(),
         o.planned_close_date.isoformat(), o.stage,
         o.closed_date.isoformat() if o.closed_date else None, o.forecast_category,
         int(o.is_won), int(o.is_closed)) for o in opps])
    con.executemany("INSERT INTO stage_history VALUES (?,?,?,?)",
                    [(h.opp_id, h.stage, h.stage_order, h.entered_date.isoformat()) for h in hist])
    con.executemany("INSERT INTO stage_prob VALUES (?,?,?,?)", [(s, o, p, int(op)) for s, o, p, op in STAGES])
    rows = []
    for q, v in QUOTA.items():
        a, b = quarter_bounds(q)
        rows.append((q, a.isoformat(), b.isoformat(), v))
    con.executemany("INSERT INTO quota VALUES (?,?,?,?)", rows)
    return con


def load_queries():
    text = (SQL_DIR / "metrics.sql").read_text()
    parts = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run(con, name, **params):
    q = load_queries()[name]
    params.setdefault("as_of", AS_OF.isoformat())
    needed = {k: v for k, v in params.items() if f":{k}" in q}
    return [dict(r) for r in con.execute(q, needed)]
