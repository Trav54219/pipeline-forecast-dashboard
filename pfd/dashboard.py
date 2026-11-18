"""Render a single static HTML dashboard (inline JS, Chart.js from cdnjs, pinned)."""
import json

CHARTJS_URL = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"


def _payload(m):
    w, c, cov = m["weighted"], m["categories"], m["coverage"][0]
    return {
        "as_of": m["as_of"],
        "kpi": {
            "open_pipeline": w["total"]["amount"], "weighted": w["total"]["weighted"],
            "commit": c["commit"], "best_case": c["best_case_cumulative"],
            "win_rate": m["win_rate"]["win_rate"], "coverage": cov["coverage"],
            "coverage_quarter": cov["quarter"], "benchmark": cov["benchmark"],
            "past_due_n": m["past_due"]["n"], "past_due_amount": m["past_due"]["amount"],
        },
        "stages": list(w["by_stage"].keys()),
        "stage_amount": [v["amount"] for v in w["by_stage"].values()],
        "stage_weighted": [v["weighted"] for v in w["by_stage"].values()],
        "cats": list(c["by_category"].keys()),
        "cat_amount": [v["amount"] for v in c["by_category"].values()],
        "cat_weighted": [v["weighted"] for v in c["by_category"].values()],
        "conv_stage": [r["stage"] for r in m["conversion"]],
        "conv": [r["conversion"] for r in m["conversion"]],
        "assumed": [m["assumed_probs"][r["stage"]] for r in m["conversion"]],
        "empirical": [m["empirical_probs_now"][r["stage"]] for r in m["conversion"]],
        "bt": m["backtest"], "bt_summary": m["backtest_summary"],
        "seg": {k: v["win_rate"] for k, v in m["win_by_segment"].items()},
        "coverage": m["coverage"],
    }


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pipeline Forecast Dashboard (synthetic data)</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mute:#667085;--line:#e3e6eb;--a:#2f6fdb;--b:#e08a1e;--c:#2a9d8f;--d:#8e5bd1;--warn:#fff4d6}
@media (prefers-color-scheme:dark){:root{--bg:#10151c;--card:#182029;--ink:#e8edf3;--mute:#9aa7b6;--line:#2a3441;--a:#6ea1ff;--b:#f0a84a;--c:#4fc5b6;--d:#b18af0;--warn:#3a3118}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 14px}
.banner{background:var(--warn);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:16px;font-size:14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .l{color:var(--mute);font-size:12px}.kpi .v{font-size:22px;font-weight:650;margin-top:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));gap:14px}
.card h2{font-size:15px;margin:0 0 8px}.card p{color:var(--mute);font-size:12.5px;margin:6px 0 0}
canvas{max-height:300px}table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:5px 6px;border-bottom:1px solid var(--line);text-align:right}th:first-child,td:first-child{text-align:left}
</style></head><body><main>
<h1>Pipeline Forecast Dashboard</h1>
<p class="sub">Snapshot as of <span id="asof"></span></p>
<div class="banner"><strong>Synthetic data.</strong> Every opportunity here is randomly generated (seeded) by this repo. No real company, customer or result is represented. Stage probabilities and quotas are assumptions.</div>
<section class="kpis" id="kpis"></section>
<section class="grid">
<div class="card"><h2>Open pipeline by stage</h2><canvas id="c1"></canvas><p>Weighted = amount x assumed stage probability.</p></div>
<div class="card"><h2>Forecast categories (open)</h2><canvas id="c2"></canvas><p>Category is the rep-assigned flag on each open opportunity.</p></div>
<div class="card"><h2>Stage conversion</h2><canvas id="c3"></canvas><p>Bars: resolved-only conversion to the next stage. Lines: assumed vs empirical win probability from that stage.</p></div>
<div class="card"><h2>Backtest: forecast vs actual by quarter</h2><canvas id="c4"></canvas><p id="btnote"></p></div>
<div class="card"><h2>Win rate by segment</h2><canvas id="c5"></canvas></div>
<div class="card"><h2>Coverage vs quota</h2><table id="cov"></table><p>Coverage = open pipeline planned to close in the quarter / (quota - closed-won so far). The 3x benchmark is a rule of thumb.</p></div>
</section>
<script src="__CHARTJS__"></script>
<script>
const D = __DATA__;
const $ = id => document.getElementById(id);
const usd = v => v == null ? "n/a" : "$" + (v >= 1e6 ? (v/1e6).toFixed(2) + "M" : Math.round(v/1e3) + "k");
const pct = v => v == null ? "n/a" : (v*100).toFixed(1) + "%";
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
$("asof").textContent = D.as_of;
const k = D.kpi;
[["Open pipeline", usd(k.open_pipeline)],["Weighted pipeline", usd(k.weighted)],["Commit", usd(k.commit)],
 ["Best case (cum.)", usd(k.best_case)],["Win rate (count)", pct(k.win_rate)],
 ["Coverage "+k.coverage_quarter, k.coverage==null?"n/a":k.coverage.toFixed(2)+"x"],
 ["Past-due open deals", k.past_due_n+" / "+usd(k.past_due_amount)]
].forEach(([l,v]) => $("kpis").insertAdjacentHTML("beforeend", `<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div></div>`));
const A=css("--a"),B=css("--b"),C=css("--c"),Dd=css("--d"),mute=css("--mute"),line=css("--line");
Chart.defaults.color = mute; Chart.defaults.borderColor = line;
const money = {ticks:{callback:v=>usd(v)}};
const tip = {callbacks:{label:c=>c.dataset.label+": "+(c.dataset.pct?pct(c.parsed.y):usd(c.parsed.y))}};
new Chart($("c1"),{type:"bar",data:{labels:D.stages,datasets:[{label:"Pipeline",data:D.stage_amount,backgroundColor:A},{label:"Weighted",data:D.stage_weighted,backgroundColor:B}]},options:{scales:{y:money},plugins:{tooltip:tip}}});
new Chart($("c2"),{type:"bar",data:{labels:D.cats,datasets:[{label:"Pipeline",data:D.cat_amount,backgroundColor:A},{label:"Weighted",data:D.cat_weighted,backgroundColor:B}]},options:{scales:{y:money},plugins:{tooltip:tip}}});
const pc = {ticks:{callback:v=>pct(v)}};
new Chart($("c3"),{data:{labels:D.conv_stage,datasets:[
 {type:"bar",label:"Conversion to next stage",data:D.conv,backgroundColor:A,pct:1},
 {type:"line",label:"Assumed win prob.",data:D.assumed,borderColor:B,backgroundColor:B,pct:1},
 {type:"line",label:"Empirical win prob.",data:D.empirical,borderColor:C,backgroundColor:C,pct:1}]},options:{scales:{y:pc},plugins:{tooltip:tip}}});
new Chart($("c4"),{data:{labels:D.bt.map(r=>r.quarter),datasets:[
 {type:"bar",label:"Actual won",data:D.bt.map(r=>r.actual_won),backgroundColor:A},
 {type:"line",label:"Forecast (assumed probs)",data:D.bt.map(r=>r.forecast_static),borderColor:B,backgroundColor:B},
 {type:"line",label:"Forecast (empirical probs)",data:D.bt.map(r=>r.forecast_empirical),borderColor:C,backgroundColor:C}]},options:{scales:{y:money},plugins:{tooltip:tip}}});
const s = D.bt_summary;
$("btnote").textContent = "Mean abs. % error: assumed "+pct(s.mape_static)+", empirical "+pct(s.mape_empirical)+". Mean signed error (bias): assumed "+pct(s.bias_static)+", empirical "+pct(s.bias_empirical)+". Snapshot at quarter start; cohort = open deals planned to close that quarter.";
new Chart($("c5"),{type:"bar",data:{labels:Object.keys(D.seg),datasets:[{label:"Win rate",data:Object.values(D.seg),backgroundColor:Dd,pct:1}]},options:{scales:{y:pc},plugins:{tooltip:tip,legend:{display:false}}}});
$("cov").innerHTML = "<tr><th>Quarter</th><th>Quota</th><th>Closed won</th><th>Pipeline</th><th>Weighted</th><th>Coverage</th></tr>" +
 D.coverage.map(c=>`<tr><td>${c.quarter}</td><td>${usd(c.quota)}</td><td>${usd(c.closed_won)}</td><td>${usd(c.pipeline)}</td><td>${usd(c.weighted)}</td><td>${c.coverage==null?"n/a":c.coverage.toFixed(2)+"x"}</td></tr>`).join("");
</script></main></body></html>
"""


def render(m):
    data = json.dumps(_payload(m)).replace("</", "<\\/")
    return PAGE.replace("__CHARTJS__", CHARTJS_URL).replace("__DATA__", data)
