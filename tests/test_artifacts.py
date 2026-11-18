import json
import re
from pathlib import Path

from pfd.config import STAGE_PROB
from pfd.dashboard import CHARTJS_URL, render
from pfd.metrics import all_metrics

ROOT = Path(__file__).resolve().parent.parent


def test_dashboard_html(synth):
    html = render(all_metrics(*synth))
    assert html.count("Synthetic data") >= 1
    assert CHARTJS_URL in html and re.search(r"Chart\.js/\d+\.\d+\.\d+/", CHARTJS_URL)
    m = re.search(r"const D = (\{.*?\});\nconst \$", html, re.S)
    data = json.loads(m.group(1))
    assert len(data["bt"]) == 7 and data["kpi"]["open_pipeline"] > 0
    # only cdnjs is loaded remotely
    assert set(re.findall(r'src="(https?://[^/"]+)', html)) == {"https://cdnjs.cloudflare.com"}


def test_committed_dashboard_matches_generator(synth):
    committed = (ROOT / "docs" / "dashboard.html").read_text()
    assert committed == render(all_metrics(*synth)), "run `python -m pfd` and commit"


def test_lookml_labeled_and_consistent():
    for f in (ROOT / "lookml").glob("*.lkml"):
        assert "NOT RUN" in f.read_text().upper(), f.name
    view = (ROOT / "lookml" / "opportunities.view.lkml").read_text()
    for name in ("weighted_pipeline", "win_rate", "open_pipeline", "commit_amount"):
        assert f"measure: {name}" in view
    assert "explore: opportunities" in (ROOT / "lookml" / "pipeline.model.lkml").read_text()


def test_tableau_doc_labeled_and_probs_match_config():
    doc = (ROOT / "docs" / "tableau_calculated_fields.md").read_text()
    assert "authored, not run" in doc.lower()
    for stage, p in STAGE_PROB.items():
        if 0 < p < 1:
            assert re.search(rf"WHEN '{stage}' THEN {p:.2f}", doc), stage
