"""Seeded synthetic CRM generator + CSV IO. Nothing here is real data."""
import csv
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .config import (ADVANCE_P, AS_OF, DATA_START, N_OPPS, N_REPS, OPEN_STAGES,
                     SEED, SEGMENT_MEDIAN, SEGMENT_MIX, SEGMENT_MOD, STAGE_ORDER)


@dataclass
class Opp:
    opp_id: str
    account: str
    owner: str
    segment: str
    amount: float
    created_date: date
    planned_close_date: date
    stage: str
    closed_date: date | None
    forecast_category: str

    @property
    def is_closed(self):
        return self.stage in ("Closed Won", "Closed Lost")

    @property
    def is_won(self):
        return self.stage == "Closed Won"


@dataclass
class Hist:
    opp_id: str
    stage: str
    stage_order: int
    entered_date: date


def _category(rng, stage):
    r = rng.random()
    if stage == "Negotiation":
        return "Commit" if r < 0.85 else "Best Case"
    if stage == "Proposal":
        return "Best Case" if r < 0.70 else ("Commit" if r < 0.80 else "Pipeline")
    return "Pipeline" if r < 0.95 else "Best Case"


def generate(seed=SEED, n=N_OPPS):
    rng = random.Random(seed)
    segs, weights = zip(*SEGMENT_MIX)
    span = (AS_OF - DATA_START).days
    opps, hist = [], []
    for i in range(1, n + 1):
        oid = f"OPP-{i:05d}"
        seg = rng.choices(segs, weights)[0]
        amount = round(rng.lognormvariate(math.log(SEGMENT_MEDIAN[seg]), 0.45), -2)
        created = DATA_START + timedelta(days=rng.randint(0, span))
        planned = created + timedelta(days=rng.randint(45, 150))
        t, idx = created, 0
        hist.append(Hist(oid, OPEN_STAGES[0], 1, created))
        stage, closed = OPEN_STAGES[0], None
        while True:
            t_next = t + timedelta(days=rng.randint(5, 35))
            if t_next > AS_OF:
                break
            adv = min(0.97, ADVANCE_P[OPEN_STAGES[idx]] * SEGMENT_MOD[seg])
            if rng.random() < adv:
                if idx == len(OPEN_STAGES) - 1:
                    stage, closed = "Closed Won", t_next
                    hist.append(Hist(oid, stage, STAGE_ORDER[stage], t_next))
                    break
                idx += 1
                stage = OPEN_STAGES[idx]
                hist.append(Hist(oid, stage, STAGE_ORDER[stage], t_next))
            else:
                stage, closed = "Closed Lost", t_next
                hist.append(Hist(oid, stage, STAGE_ORDER[stage], t_next))
                break
            t = t_next
        cat = "Closed" if closed else _category(rng, stage)
        opps.append(Opp(oid, f"Account {rng.randint(1, 600):04d}", f"Rep {rng.randint(1, N_REPS):02d}",
                        seg, amount, created, planned, stage, closed, cat))
    return opps, hist


OPP_FIELDS = ["opp_id", "account", "owner", "segment", "amount", "created_date",
              "planned_close_date", "stage", "closed_date", "forecast_category"]
HIST_FIELDS = ["opp_id", "stage", "stage_order", "entered_date"]


def write_csv(opps, hist, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "opportunities.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(OPP_FIELDS)
        for o in opps:
            w.writerow([o.opp_id, o.account, o.owner, o.segment, int(o.amount), o.created_date,
                        o.planned_close_date, o.stage, o.closed_date or "", o.forecast_category])
    with open(outdir / "stage_history.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HIST_FIELDS)
        for h in hist:
            w.writerow([h.opp_id, h.stage, h.stage_order, h.entered_date])


def read_csv(outdir):
    outdir = Path(outdir)
    d = date.fromisoformat
    with open(outdir / "opportunities.csv") as f:
        opps = [Opp(r["opp_id"], r["account"], r["owner"], r["segment"], float(r["amount"]),
                    d(r["created_date"]), d(r["planned_close_date"]), r["stage"],
                    d(r["closed_date"]) if r["closed_date"] else None, r["forecast_category"])
                for r in csv.DictReader(f)]
    with open(outdir / "stage_history.csv") as f:
        hist = [Hist(r["opp_id"], r["stage"], int(r["stage_order"]), d(r["entered_date"]))
                for r in csv.DictReader(f)]
    return opps, hist
