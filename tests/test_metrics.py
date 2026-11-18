from datetime import date

import pytest

from pfd.config import STAGE_PROB
from pfd.data import Hist
from pfd.metrics import (backtest, category_rollup, coverage, quarter_bounds, stage_at,
                         stage_conversion, weighted_pipeline, win_rate, index_history)
from tests.conftest import mk


def test_quarter_bounds():
    assert quarter_bounds("2025Q4") == (date(2025, 10, 1), date(2025, 12, 31))
    assert quarter_bounds("2024Q1") == (date(2024, 1, 1), date(2024, 3, 31))


def test_weighted_pipeline_hand_calc():
    opps = [mk("a", "Qualify", 1000, date(2025, 11, 1)),
            mk("b", "Proposal", 2000, date(2025, 11, 1)),
            mk("c", "Negotiation", 4000, date(2025, 11, 1)),
            mk("d", "Closed Won", 9999, date(2025, 5, 1), closed=date(2025, 5, 1), cat="Closed")]
    w = weighted_pipeline(opps)["total"]
    assert w["amount"] == 7000 and w["n"] == 3
    assert w["weighted"] == pytest.approx(1000 * .10 + 2000 * .50 + 4000 * .75)


def test_category_rollup_is_cumulative():
    opps = [mk("a", "Negotiation", 100, date(2025, 11, 1), cat="Commit"),
            mk("b", "Proposal", 200, date(2025, 11, 1), cat="Best Case"),
            mk("c", "Qualify", 400, date(2025, 11, 1), cat="Pipeline")]
    r = category_rollup(opps)
    assert (r["commit"], r["best_case_cumulative"], r["pipeline_cumulative"]) == (100, 300, 700)


def _fixture_with_history():
    # won: reached Negotiation. lost-at-Discovery. lost-at-Negotiation. open in Proposal.
    mkc = lambda oid, stage, closed=None: mk(oid, stage, 100, date(2025, 3, 1), created=date(2025, 1, 1), closed=closed)
    opps = [mkc("w", "Closed Won", date(2025, 3, 1)), mkc("l1", "Closed Lost", date(2025, 2, 1)),
            mkc("l2", "Closed Lost", date(2025, 3, 1)), mkc("o", "Proposal")]
    D = date
    h = [Hist("w", "Qualify", 1, D(2025, 1, 1)), Hist("w", "Discovery", 2, D(2025, 1, 10)),
         Hist("w", "Proposal", 3, D(2025, 1, 20)), Hist("w", "Negotiation", 4, D(2025, 2, 1)),
         Hist("w", "Closed Won", 5, D(2025, 3, 1)),
         Hist("l1", "Qualify", 1, D(2025, 1, 1)), Hist("l1", "Discovery", 2, D(2025, 1, 10)),
         Hist("l1", "Closed Lost", 6, D(2025, 2, 1)),
         Hist("l2", "Qualify", 1, D(2025, 1, 1)), Hist("l2", "Discovery", 2, D(2025, 1, 10)),
         Hist("l2", "Proposal", 3, D(2025, 1, 20)), Hist("l2", "Negotiation", 4, D(2025, 2, 1)),
         Hist("l2", "Closed Lost", 6, D(2025, 3, 1)),
         Hist("o", "Qualify", 1, D(2025, 1, 1)), Hist("o", "Discovery", 2, D(2025, 1, 10)),
         Hist("o", "Proposal", 3, D(2025, 1, 20))]
    return opps, h


def test_stage_conversion_resolved_only():
    opps, h = _fixture_with_history()
    c = {r["stage"]: r for r in stage_conversion(opps, h)}
    assert c["Qualify"]["conversion"] == 1.0            # 4 advanced, 0 lost at Qualify
    assert (c["Discovery"]["advanced"], c["Discovery"]["lost_here"]) == (3, 1)
    assert c["Discovery"]["conversion"] == pytest.approx(0.75)
    # open deal in Proposal is neither advanced nor lost: excluded from the ratio
    assert (c["Proposal"]["advanced"], c["Proposal"]["lost_here"]) == (2, 0)
    assert c["Negotiation"]["conversion"] == pytest.approx(0.5)


def test_win_rate():
    opps, _ = _fixture_with_history()
    r = win_rate(opps)
    assert (r["won"], r["lost"]) == (1, 2)
    assert r["win_rate"] == pytest.approx(1 / 3)


def test_stage_at_is_strictly_before():
    _, h = _fixture_with_history()
    hl = index_history(h)["w"]
    assert stage_at(hl, date(2025, 1, 1)) is None            # entered that day, not yet visible
    assert stage_at(hl, date(2025, 1, 2)) == "Qualify"
    assert stage_at(hl, date(2025, 2, 2)) == "Negotiation"
    assert stage_at(hl, date(2025, 6, 1)) == "Closed Won"


def test_backtest_hand_calc_and_no_leakage():
    opps, h = _fixture_with_history()
    # snapshot 2025Q2 start = 2025-04-01: everything already closed except "o" (Proposal)
    opps[3].planned_close_date = date(2025, 5, 15)
    rows = backtest(opps, h, ["2025Q2"])
    assert rows[0]["n_deals"] == 1
    assert rows[0]["forecast_static"] == pytest.approx(100 * 0.5)
    assert rows[0]["actual_won"] == 0
    # An opp created after the snapshot must never enter the cohort
    late = mk("late", "Closed Won", 5000, date(2025, 5, 20), created=date(2025, 4, 15), closed=date(2025, 5, 20), cat="Closed")
    h2 = h + [Hist("late", "Qualify", 1, date(2025, 4, 15)), Hist("late", "Closed Won", 5, date(2025, 5, 20))]
    rows2 = backtest(opps + [late], h2, ["2025Q2"])
    assert rows2[0]["n_deals"] == 1 and rows2[0]["actual_won"] == 0


def test_coverage():
    opps = [mk("a", "Proposal", 3000, date(2025, 11, 1)),
            mk("b", "Qualify", 3000, date(2026, 2, 1)),
            mk("w", "Closed Won", 1000, date(2025, 10, 5), closed=date(2025, 10, 5), cat="Closed")]
    c = coverage(opps, "2025Q4", quota=2000)
    assert c["pipeline"] == 3000 and c["closed_won"] == 1000 and c["gap"] == 1000
    assert c["coverage"] == pytest.approx(3.0)
    assert coverage(opps, "2025Q4", quota=500)["coverage"] is None   # quota already met


def test_synthetic_sanity(synth):
    from pfd.metrics import all_metrics
    opps, hist = synth
    m = all_metrics(opps, hist)
    assert 0.05 < m["win_rate"]["win_rate"] < 0.6
    assert all(0 < r["conversion"] < 1 for r in m["conversion"])
    assert len(m["backtest"]) == 7 and m["backtest"][0]["quarter"] == "2024Q1"
    assert m["categories"]["pipeline_cumulative"] == pytest.approx(m["weighted"]["total"]["amount"])
