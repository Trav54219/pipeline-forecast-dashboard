import pytest

from pfd.config import AS_OF
from pfd.metrics import (backtest, backtest_quarters, category_rollup, coverage,
                         stage_conversion, weighted_pipeline, win_rate)
from pfd.sqlmetrics import build_db, load_queries, run


@pytest.fixture(scope="module")
def con(synth):
    return build_db(*synth)


def test_all_queries_parse():
    assert set(load_queries()) == {"weighted_by_stage", "category_rollup", "win_rate",
                                   "stage_conversion", "coverage", "backtest_static"}


def test_weighted_by_stage(con, synth):
    py = weighted_pipeline(synth[0])["by_stage"]
    rows = run(con, "weighted_by_stage")
    assert [r["stage"] for r in rows] == list(py)
    for r in rows:
        assert r["n"] == py[r["stage"]]["n"]
        assert r["amount"] == pytest.approx(py[r["stage"]]["amount"])
        assert r["weighted"] == pytest.approx(py[r["stage"]]["weighted"])


def test_category_rollup(con, synth):
    py = category_rollup(synth[0])["by_category"]
    for r in run(con, "category_rollup"):
        assert r["amount"] == pytest.approx(py[r["category"]]["amount"])
        assert r["weighted"] == pytest.approx(py[r["category"]]["weighted"])


def test_win_rate(con, synth):
    py = win_rate(synth[0])
    r = run(con, "win_rate")[0]
    assert (r["won"], r["lost"]) == (py["won"], py["lost"])
    assert r["win_rate"] == pytest.approx(py["win_rate"])
    assert r["win_rate_amount"] == pytest.approx(py["win_rate_amount"])


def test_stage_conversion(con, synth):
    py = stage_conversion(*synth)
    rows = run(con, "stage_conversion")
    for a, b in zip(rows, py):
        assert a["stage"] == b["stage"]
        assert (a["reached"], a["advanced"], a["lost_here"]) == (b["reached"], b["advanced"], b["lost_here"])
        assert a["conversion"] == pytest.approx(b["conversion"])


@pytest.mark.parametrize("q", ["2025Q4", "2026Q1"])
def test_coverage(con, synth, q):
    py = coverage(synth[0], q)
    r = run(con, "coverage", quarter=q)[0]
    assert r["pipeline"] == pytest.approx(py["pipeline"])
    assert r["weighted"] == pytest.approx(py["weighted"])
    assert r["closed_won"] == pytest.approx(py["closed_won"])
    assert r["quota"] == py["quota"]


def test_backtest_static(con, synth):
    py = backtest(*synth, backtest_quarters())
    rows = run(con, "backtest_static")
    assert [r["quarter"] for r in rows] == [r["quarter"] for r in py]
    for a, b in zip(rows, py):
        assert a["n_deals"] == b["n_deals"]
        assert a["pipeline"] == pytest.approx(b["pipeline"])
        assert a["forecast_static"] == pytest.approx(b["forecast_static"])
        assert a["actual_won"] == pytest.approx(b["actual_won"])
