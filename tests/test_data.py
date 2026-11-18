from datetime import date

from pfd.config import AS_OF, DATA_START, N_OPPS
from pfd.data import generate, read_csv, write_csv
from pfd.metrics import index_history


def test_deterministic():
    a, ha = generate(seed=7, n=200)
    b, hb = generate(seed=7, n=200)
    assert a == b and ha == hb
    c, _ = generate(seed=8, n=200)
    assert a != c


def test_size_and_ids_unique(synth):
    opps, _ = synth
    assert len(opps) == N_OPPS
    assert len({o.opp_id for o in opps}) == N_OPPS


def test_dates_valid(synth):
    opps, _ = synth
    for o in opps:
        assert DATA_START <= o.created_date <= AS_OF
        assert o.planned_close_date > o.created_date
        if o.is_closed:
            assert o.created_date < o.closed_date <= AS_OF
        else:
            assert o.closed_date is None


def test_history_consistent_with_current_stage(synth):
    opps, hist = synth
    hbo = index_history(hist)
    for o in opps:
        rows = hbo[o.opp_id]
        assert rows[0].stage == "Qualify" and rows[0].entered_date == o.created_date
        assert rows[-1].stage == o.stage
        orders = [r.stage_order for r in rows]
        assert orders == sorted(orders)
        dates = [r.entered_date for r in rows]
        assert all(b > a for a, b in zip(dates, dates[1:]))   # strictly increasing


def test_open_deals_have_forecast_category_closed_do_not(synth):
    opps, _ = synth
    for o in opps:
        assert (o.forecast_category == "Closed") == o.is_closed


def test_csv_roundtrip(tmp_path):
    opps, hist = generate(seed=3, n=50)
    write_csv(opps, hist, tmp_path)
    o2, h2 = read_csv(tmp_path)
    assert [x.opp_id for x in o2] == [x.opp_id for x in opps]
    assert [x.stage for x in o2] == [x.stage for x in opps]
    assert h2 == hist
