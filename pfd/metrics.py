"""Pure-Python reference implementation of the forecast metrics."""
from collections import defaultdict
from datetime import date, timedelta

from .config import (AS_OF, CATEGORIES, COVERAGE_BENCHMARK, MIN_N_EMPIRICAL, OPEN_STAGES,
                     QUOTA, STAGE_ORDER, STAGE_PROB)


def quarter_label(d):
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def quarter_bounds(label):
    y, q = int(label[:4]), int(label[5])
    start = date(y, 3 * (q - 1) + 1, 1)
    nxt = date(y + (q == 4), 1 if q == 4 else 3 * q + 1, 1)
    return start, nxt - timedelta(days=1)


def open_opps(opps):
    return [o for o in opps if not o.is_closed]


def weighted_pipeline(opps, probs=STAGE_PROB):
    """Open pipeline at AS_OF: amount x stage probability, by stage and total."""
    by = {s: {"n": 0, "amount": 0.0, "weighted": 0.0} for s in OPEN_STAGES}
    for o in open_opps(opps):
        r = by[o.stage]
        r["n"] += 1
        r["amount"] += o.amount
        r["weighted"] += o.amount * probs[o.stage]
    total = {k: sum(v[k] for v in by.values()) for k in ("n", "amount", "weighted")}
    return {"by_stage": by, "total": total}


def category_rollup(opps, probs=STAGE_PROB):
    by = {c: {"n": 0, "amount": 0.0, "weighted": 0.0} for c in CATEGORIES}
    for o in open_opps(opps):
        r = by[o.forecast_category]
        r["n"] += 1
        r["amount"] += o.amount
        r["weighted"] += o.amount * probs[o.stage]
    commit = by["Commit"]["amount"]
    best_case = commit + by["Best Case"]["amount"]          # cumulative, as in most CRMs
    pipeline = best_case + by["Pipeline"]["amount"]
    return {"by_category": by, "commit": commit, "best_case_cumulative": best_case,
            "pipeline_cumulative": pipeline}


def reached_order(opp, hist_by_opp):
    """Highest open-or-won stage order the opportunity ever reached."""
    return max(h.stage_order for h in hist_by_opp[opp.opp_id] if h.stage_order <= 5)


def index_history(hist):
    d = defaultdict(list)
    for h in hist:
        d[h.opp_id].append(h)
    for v in d.values():
        v.sort(key=lambda h: (h.entered_date, h.stage_order))
    return d


def stage_conversion(opps, hist):
    """Resolved-only conversion: advanced / (advanced + lost at that stage).
    Opps still sitting in the stage are excluded so open deals do not bias it."""
    hbo = index_history(hist)
    ro = {o.opp_id: reached_order(o, hbo) for o in opps}
    out = []
    for s in OPEN_STAGES:
        k = STAGE_ORDER[s]
        reached = sum(1 for o in opps if ro[o.opp_id] >= k)
        advanced = sum(1 for o in opps if ro[o.opp_id] > k)
        lost = sum(1 for o in opps if ro[o.opp_id] == k and o.stage == "Closed Lost")
        den = advanced + lost
        out.append({"stage": s, "reached": reached, "advanced": advanced, "lost_here": lost,
                    "conversion": advanced / den if den else None})
    return out


def win_rate(opps, segment=None):
    cl = [o for o in opps if o.is_closed and (segment is None or o.segment == segment)]
    won = [o for o in cl if o.is_won]
    won_amt = sum(o.amount for o in won)
    tot_amt = sum(o.amount for o in cl)
    return {"won": len(won), "lost": len(cl) - len(won),
            "win_rate": len(won) / len(cl) if cl else None,
            "win_rate_amount": won_amt / tot_amt if tot_amt else None,
            "avg_won_amount": won_amt / len(won) if won else None}


def stage_at(hlist, day):
    """Stage held at the start of `day` (history entered strictly before it)."""
    cur = None
    for h in hlist:
        if h.entered_date < day:
            cur = h.stage
        else:
            break
    return cur


def empirical_win_probs(opps, hbo, before):
    """P(eventually win | reached stage), from opps closed strictly before `before`.
    Falls back to the assumed probability where sample < MIN_N_EMPIRICAL."""
    closed = [o for o in opps if o.is_closed and o.closed_date < before]
    ro = {o.opp_id: reached_order(o, hbo) for o in closed}
    probs = {}
    for s in OPEN_STAGES:
        k = STAGE_ORDER[s]
        reach = [o for o in closed if ro[o.opp_id] >= k]
        probs[s] = (sum(o.is_won for o in reach) / len(reach)) if len(reach) >= MIN_N_EMPIRICAL else STAGE_PROB[s]
    return probs


def backtest(opps, hist, quarters):
    """At each quarter start, snapshot open opps whose planned close falls in the quarter,
    forecast = sum(amount x prob(stage at snapshot)); actual = those same opps that closed
    won inside the quarter. Uses only information dated before the snapshot."""
    hbo = index_history(hist)
    rows = []
    for q in quarters:
        qs, qe = quarter_bounds(q)
        probs_emp = empirical_win_probs(opps, hbo, qs)
        n = 0
        pipe = f_static = f_emp = actual = 0.0
        for o in opps:
            if not (qs <= o.planned_close_date <= qe):
                continue
            st = stage_at(hbo[o.opp_id], qs)
            if st not in OPEN_STAGES:
                continue
            n += 1
            pipe += o.amount
            f_static += o.amount * STAGE_PROB[st]
            f_emp += o.amount * probs_emp[st]
            if o.is_won and qs <= o.closed_date <= qe:
                actual += o.amount
        rows.append({"quarter": q, "n_deals": n, "pipeline": pipe, "forecast_static": f_static,
                     "forecast_empirical": f_emp, "actual_won": actual,
                     "err_static": (f_static - actual) / actual if actual else None,
                     "err_empirical": (f_emp - actual) / actual if actual else None})
    return rows


def backtest_quarters(as_of=AS_OF, first="2024Q1"):
    out, y, q = [], int(first[:4]), int(first[5])
    while quarter_bounds(f"{y}Q{q}")[1] <= as_of:
        out.append(f"{y}Q{q}")
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def backtest_summary(rows):
    def mape(key):
        v = [abs(r[key]) for r in rows if r[key] is not None]
        return sum(v) / len(v) if v else None

    def bias(key):
        v = [r[key] for r in rows if r[key] is not None]
        return sum(v) / len(v) if v else None
    return {"mape_static": mape("err_static"), "mape_empirical": mape("err_empirical"),
            "bias_static": bias("err_static"), "bias_empirical": bias("err_empirical")}


def coverage(opps, quarter, quota=None, as_of=AS_OF):
    """Open pipeline with planned close in `quarter` / (quota - closed-won already in quarter)."""
    qs, qe = quarter_bounds(quarter)
    quota = QUOTA[quarter] if quota is None else quota
    won = sum(o.amount for o in opps if o.is_won and qs <= o.closed_date <= qe)
    pipe = [o for o in open_opps(opps) if qs <= o.planned_close_date <= qe]
    pa = sum(o.amount for o in pipe)
    pw = sum(o.amount * STAGE_PROB[o.stage] for o in pipe)
    gap = quota - won
    return {"quarter": quarter, "quota": quota, "closed_won": won, "gap": gap,
            "pipeline": pa, "weighted": pw, "n": len(pipe),
            "coverage": pa / gap if gap > 0 else None,
            "weighted_coverage": pw / gap if gap > 0 else None,
            "benchmark": COVERAGE_BENCHMARK}


def past_due(opps, as_of=AS_OF):
    p = [o for o in open_opps(opps) if o.planned_close_date < as_of]
    return {"n": len(p), "amount": sum(o.amount for o in p)}


def segment_win_rates(opps):
    return {s: win_rate(opps, s) for s in sorted({o.segment for o in opps})}


def all_metrics(opps, hist):
    quarters = backtest_quarters()
    bt = backtest(opps, hist, quarters)
    fq = ["2025Q4", "2026Q1"]
    return {
        "as_of": AS_OF.isoformat(),
        "n_opps": len(opps),
        "weighted": weighted_pipeline(opps),
        "categories": category_rollup(opps),
        "conversion": stage_conversion(opps, hist),
        "win_rate": win_rate(opps),
        "win_by_segment": segment_win_rates(opps),
        "empirical_probs_now": empirical_win_probs(opps, index_history(hist), AS_OF + timedelta(days=1)),
        "assumed_probs": dict(STAGE_PROB),
        "backtest": bt,
        "backtest_summary": backtest_summary(bt),
        "coverage": [coverage(opps, q) for q in fq],
        "past_due": past_due(opps),
    }
