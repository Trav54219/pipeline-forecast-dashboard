"""python -m pfd  -> regenerate data, metrics.json and docs/dashboard.html"""
import json
from pathlib import Path

from .dashboard import render
from .data import generate, write_csv
from .metrics import all_metrics

ROOT = Path(__file__).resolve().parent.parent


def main():
    opps, hist = generate()
    write_csv(opps, hist, ROOT / "data")
    m = all_metrics(opps, hist)
    (ROOT / "data" / "metrics.json").write_text(json.dumps(m, indent=2, default=str))
    (ROOT / "docs" / "dashboard.html").write_text(render(m))
    print(f"{len(opps)} opps, {len(hist)} stage-history rows -> data/, docs/dashboard.html")


if __name__ == "__main__":
    main()
