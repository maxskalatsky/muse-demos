#!/usr/bin/env python3
"""Build the cycling dashboard (index.html) and cycling_log.md from rides.json.
Single source of truth: rides.json. Run from the cycling-dashboard directory."""
import json, os
from datetime import date, timedelta
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
rides = json.load(open(os.path.join(HERE, "rides.json")))
rides.sort(key=lambda r: r["date"])

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# week buckets (Monday start), month buckets
weeks = OrderedDict()
months = OrderedDict()
for i, r in enumerate(rides):
    d = date.fromisoformat(r["date"])
    wk = d - timedelta(days=d.weekday())
    wkey = wk.isoformat()
    if wkey not in weeks:
        weeks[wkey] = {"label": f"{MONTHS[wk.month-1]} {wk.day}", "idx": []}
    weeks[wkey]["idx"].append(i)
    mkey = r["date"][:7]
    if mkey not in months:
        months[mkey] = {"label": f"{MONTHS[int(mkey[5:7])-1]} {mkey[:4]}", "idx": []}
    months[mkey]["idx"].append(i)

buckets = {
    "week": [{"label": w["label"], "idx": w["idx"]} for w in weeks.values()],
    "month": [{"label": m["label"], "idx": m["idx"]} for m in months.values()],
}

# personal records
records = []
def add_rec(key, fmt, title):
    c = [(r[key], r) for r in rides if r.get(key) is not None]
    if not c:
        return
    v, r = max(c, key=lambda t: t[0])
    records.append({"title": title, "value": fmt(v), "ride": r["label"]})

add_rec("dist", lambda v: f"{v:.2f} mi", "Longest ride")
add_rec("speed", lambda v: f"{v:.1f} mph", "Fastest avg speed")
add_rec("watts", lambda v: f"{v} W", "Best avg power")
add_rec("kcal", lambda v: f"{v} kcal", "Most calories")
add_rec("mins", lambda v: f"{int(v)} min", "Longest time")

def js(v):
    return json.dumps(v)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cycling Dashboard (mockup)</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; margin: 0; background: #f4f4f4; color: #1a1a1a; }
  header { background: #1a1a1a; color: #fff; padding: 20px 24px; }
  header h1 { margin: 0; font-size: 22px; letter-spacing: -0.01em; }
  header h1 .mock { font-size: 12px; font-weight: 600; background: #fc4c02; border-radius: 4px; padding: 2px 8px; margin-left: 10px; vertical-align: 3px; }
  header p { margin: 6px 0 0; color: #aaa; font-size: 13px; }
  .wrap { max-width: 860px; margin: 0 auto; padding: 20px 16px 48px; }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }
  @media (max-width: 640px) { .stats { grid-template-columns: repeat(2, 1fr); } }
  .stat { background: #fff; border: 1px solid #e6e6e6; border-radius: 10px; padding: 14px 16px; }
  .stat .v { font-size: 26px; font-weight: 700; letter-spacing: -0.02em; }
  .stat .v small { font-size: 14px; font-weight: 500; color: #777; }
  .stat .l { font-size: 12px; color: #777; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.06em; }
  .card { background: #fff; border: 1px solid #e6e6e6; border-radius: 10px; padding: 18px; margin-bottom: 18px; }
  .card h2 { margin: 0 0 4px; font-size: 16px; }
  .toggle { display: inline-flex; background: #eee; border-radius: 8px; padding: 3px; margin-bottom: 10px; }
  .toggle button { border: 0; background: transparent; font-size: 13px; font-weight: 600; padding: 6px 16px; border-radius: 6px; cursor: pointer; color: #555; }
  .toggle button.on { background: #fff; color: #111; box-shadow: 0 1px 3px rgba(0,0,0,.15); }
  .hint { font-size: 12px; color: #888; margin-bottom: 6px; }
  .bars { display: flex; align-items: flex-end; gap: 10px; height: 150px; padding-top: 8px; }
  .bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; cursor: pointer; }
  .bar { width: 100%; max-width: 64px; background: #fc4c02; border-radius: 6px 6px 0 0; min-height: 4px; }
  .bar-lbl { font-size: 11px; color: #777; margin-top: 6px; white-space: nowrap; }
  .bar-val { font-size: 11px; font-weight: 700; margin-bottom: 4px; }
  .feed-head { display: flex; align-items: baseline; justify-content: space-between; margin: 4px 0 12px; }
  .feed-head h2 { font-size: 16px; margin: 0; }
  .clear { font-size: 13px; color: #fc4c02; cursor: pointer; font-weight: 600; display: none; }
  .clear.show { display: inline; }
  .ride { background: #fff; border: 1px solid #e6e6e6; border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }
  .ride .top { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 10px; }
  .ride .title { font-weight: 700; font-size: 16px; }
  .ride .date { font-size: 13px; color: #777; }
  .ride .dist { font-size: 30px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 8px; }
  .ride .dist small { font-size: 15px; font-weight: 500; color: #777; }
  .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  @media (max-width: 640px) { .metrics { grid-template-columns: repeat(2, 1fr); } }
  .metric .v { font-size: 17px; font-weight: 650; }
  .metric .l { font-size: 11px; color: #777; text-transform: uppercase; letter-spacing: 0.05em; }
  .records { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
  .record { background: #fafafa; border: 1px solid #eee; border-radius: 8px; padding: 12px 14px; }
  .record .v { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; }
  .record .t { font-size: 12px; color: #555; font-weight: 600; margin-top: 2px; }
  .record .r { font-size: 11px; color: #999; margin-top: 2px; }
  .trend { margin-bottom: 18px; }
  .trend:last-child { margin-bottom: 0; }
  .tlabel { font-size: 13px; font-weight: 600; color: #555; margin-bottom: 4px; }
  .xlabels { display: flex; justify-content: space-between; font-size: 10px; color: #999; padding: 2px 30px 0; }
  .foot { text-align: center; color: #999; font-size: 12px; margin-top: 24px; }
</style>
</head>
<body>
<header>
  <h1>Cycling<span class="mock">MOCKUP</span></h1>
  <p>Indoor bike log, Strava-style. v1 for review.</p>
</header>
<div class="wrap">
  <div class="stats" id="stats"></div>

  <div class="card">
    <h2>Personal records</h2>
    <div class="records" id="records"></div>
  </div>

  <div class="card">
    <h2>Trends</h2>
    <div class="trend"><div class="tlabel">Distance per ride (mi)</div><div id="chDist"></div></div>
    <div class="trend"><div class="tlabel">Avg speed (mph)</div><div id="chSpeed"></div></div>
    <div class="trend"><div class="tlabel">Avg power (W)</div><div id="chPower"></div></div>
  </div>

  <div class="card">
    <h2>Distance</h2>
    <div class="toggle">
      <button id="tWeek" class="on">Week</button><button id="tMonth">Month</button>
    </div>
    <div class="hint">Tap a bar to filter the rides below. Tap again to clear.</div>
    <div class="bars" id="bars"></div>
  </div>

  <div class="feed-head">
    <h2 id="feedTitle">Recent rides</h2>
    <span class="clear" id="clearBtn">Show all</span>
  </div>
  <div id="feed"></div>

  <div class="foot">Mockup v1. Data: __RANGE__, all indoor bike.</div>
</div>

<script>
const rides = __RIDES__;
const buckets = __BUCKETS__;
const records = __RECORDS__;

document.getElementById("records").innerHTML = records.map(r=>`
  <div class="record"><div class="v">${r.value}</div><div class="t">${r.title}</div><div class="r">${r.ride}</div></div>`).join("");

const shortDate = d => { const [y,m,dd] = d.split("-"); return `${+m}/${+dd}`; };

function lineChart(elId, key, color){
  const el = document.getElementById(elId);
  const vals = rides.map(r=>r[key]);
  const pts = vals.map((v,i)=>({v,i})).filter(o=>o.v!=null);
  if(pts.length<2){ el.innerHTML = "<div class='hint'>Not enough data yet.</div>"; return; }
  const vs = pts.map(o=>o.v);
  const lo = Math.min(...vs), hi = Math.max(...vs), span = (hi-lo)||1;
  const w=600, h=150, p=34;
  const x = i => p + i*(w-2*p)/(vals.length-1);
  const y = v => h-p - (v-lo)/span*(h-2*p);
  const line = pts.map(o=>`${x(o.i).toFixed(1)},${y(o.v).toFixed(1)}`).join(" ");
  const dots = pts.map(o=>`<circle cx="${x(o.i).toFixed(1)}" cy="${y(o.v).toFixed(1)}" r="4" fill="${color}"/>`).join("");
  el.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto;display:block">
      <line x1="${p}" y1="${h-p}" x2="${w-p}" y2="${h-p}" stroke="#e0e0e0"/>
      <text x="${p-8}" y="${(y(hi)+4).toFixed(1)}" text-anchor="end" font-size="11" fill="#999">${hi}</text>
      <text x="${p-8}" y="${(y(lo)+4).toFixed(1)}" text-anchor="end" font-size="11" fill="#999">${lo}</text>
      <polyline points="${line}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>
      ${dots}
    </svg>
    <div class="xlabels">${vals.map((_,i)=>`<span>${shortDate(rides[i].date)}</span>`).join("")}</div>`;
}
lineChart("chDist","dist","#fc4c02");
lineChart("chSpeed","speed","#0069AA");
lineChart("chPower","watts","#00a37a");

const bucketMi = b => b.idx.reduce((s,i)=>s+rides[i].dist,0);

let mode = "week";
let activeBucket = -1;

const totalMi = rides.reduce((s,r)=>s+r.dist,0);
const totalKcal = rides.reduce((s,r)=>s+(r.kcal||0),0);
const totalMins = rides.reduce((s,r)=>s+(r.mins||0),0);
const hrs = Math.floor(totalMins/60), min = Math.round(totalMins%60);

document.getElementById("stats").innerHTML = [
  [totalMi.toFixed(1)+" <small>mi</small>", "Distance"],
  [rides.length, "Rides"],
  [hrs+"h "+min+"m", "Time"],
  [totalKcal.toLocaleString(), "Calories"],
].map(([v,l])=>`<div class="stat"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");

function renderBars(){
  const bs = buckets[mode];
  const max = Math.max(...bs.map(bucketMi));
  document.getElementById("bars").innerHTML = bs.map((b,i)=>{
    const dim = activeBucket!==-1 && activeBucket!==i;
    return `
    <div class="bar-col" data-i="${i}">
      <div class="bar-val">${bucketMi(b).toFixed(1)}</div>
      <div class="bar" style="height:${Math.round(bucketMi(b)/max*100)}%;${dim?"opacity:.35":""}"></div>
      <div class="bar-lbl">${b.label}</div>
    </div>`;}).join("");
  document.querySelectorAll(".bar-col").forEach(el=>{
    el.addEventListener("click", ()=>{
      const i = +el.dataset.i;
      activeBucket = (activeBucket===i) ? -1 : i;
      renderBars(); renderFeed();
    });
  });
}

function m(label, val){ return val==null ? "" : `<div class="metric"><div class="v">${val}</div><div class="l">${label}</div></div>`; }

function renderFeed(){
  let list = [...rides].reverse();
  let title = "Recent rides";
  if(activeBucket!==-1){
    const b = buckets[mode][activeBucket];
    const set = new Set(b.idx);
    list = list.filter(r => set.has(rides.indexOf(r)));
    title = "Rides, " + (mode==="week" ? "week of " : "") + b.label;
  }
  document.getElementById("feedTitle").textContent = title;
  document.getElementById("clearBtn").classList.toggle("show", activeBucket!==-1);
  document.getElementById("feed").innerHTML = list.map(r=>`
    <div class="ride">
      <div class="top"><div class="title">Indoor Ride</div><div class="date">${r.label}</div></div>
      <div class="dist">${r.dist.toFixed(2)} <small>mi</small></div>
      <div class="metrics">
        ${m("Time", r.time)}${m("Avg speed", r.speed==null?null:r.speed.toFixed(1)+" mph")}
        ${m("Calories", r.kcal==null?null:r.kcal+" kcal")}${m("Avg power", r.watts==null?null:r.watts+" W")}
        ${m("Avg cadence", r.rpm==null?null:r.rpm+" rpm")}${m("Output", r.kj==null?null:r.kj+" kJ")}
      </div>
    </div>`).join("");
}

document.getElementById("tWeek").addEventListener("click", ()=>{
  mode="week"; activeBucket=-1;
  document.getElementById("tWeek").classList.add("on");
  document.getElementById("tMonth").classList.remove("on");
  renderBars(); renderFeed();
});
document.getElementById("tMonth").addEventListener("click", ()=>{
  mode="month"; activeBucket=-1;
  document.getElementById("tMonth").classList.add("on");
  document.getElementById("tWeek").classList.remove("on");
  renderBars(); renderFeed();
});
document.getElementById("clearBtn").addEventListener("click", ()=>{
  activeBucket=-1; renderBars(); renderFeed();
});

renderBars(); renderFeed();
</script>
</body>
</html>
"""

first = date.fromisoformat(rides[0]["date"])
last = date.fromisoformat(rides[-1]["date"])
rng = f"{MONTHS[first.month-1]} {first.day} to {MONTHS[last.month-1]} {last.day}, {last.year}"

html = html.replace("__RIDES__", js(rides)).replace("__BUCKETS__", js(buckets)).replace("__RECORDS__", js(records)).replace("__RANGE__", rng)
open(os.path.join(HERE, "index.html"), "w").write(html)

# markdown log
def notes(r):
    s = "Indoor bike"
    rest = []
    if r["kcal"]:
        rest.append(f"{r['kcal']} kcal")
    if r["kj"]:
        rest.append(f"{r['kj']} kJ total output")
    if r["watts"] or r["rpm"]:
        w = f"{r['watts']} W" if r["watts"] else ""
        c = f"{r['rpm']} rpm" if r["rpm"] else ""
        rest.append("avg " + " / ".join(x for x in [w, c] if x))
    return s + ("; " + ", ".join(rest) if rest else "") if (r["kcal"] or r["kj"]) else ""

lines = ["# Cycling Log", ""]
for wkey, w in weeks.items():
    wk = date.fromisoformat(wkey)
    lines.append(f"## Week of {MONTHS[wk.month-1]} {wk.day}, {wk.year}")
    lines.append("")
    lines.append("| Date | Distance | Time | Avg speed | Notes |")
    lines.append("|------|----------|------|-----------|-------|")
    tot = 0
    for i in w["idx"]:
        r = rides[i]
        tot += r["dist"]
        t = r["time"] if r["time"] else "—"
        sp = f"{r['speed']:.1f} mph" if r["speed"] else "—"
        lines.append(f"| {r['label']} | {r['dist']:.2f} mi | {t} | {sp} | {notes(r)} |")
    lines.append("")
    lines.append(f"**Weekly total:** {tot:.2f} mi")
    lines.append("")

open(os.path.expanduser("~/workspace/cycling_log.md"), "w").write("\n".join(lines))
print(f"built: {len(rides)} rides, {rng}")
