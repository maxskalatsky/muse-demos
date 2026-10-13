#!/usr/bin/env python3
"""Build the cycling dashboard (index.html) and cycling_log.md from rides.json.
Single source of truth: rides.json. Run from the cycling-dashboard directory."""
import json, os
from datetime import date, timedelta
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
rides = json.load(open(os.path.join(HERE, "rides.json")))
rides.sort(key=lambda r: r["date"])

GOAL_MI_PER_WEEK = 30
TODAY = rides[-1]["date"]

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# weeks (Monday start)
weeks = OrderedDict()
for i, r in enumerate(rides):
    d = date.fromisoformat(r["date"])
    wk = d - timedelta(days=d.weekday())
    wkey = wk.isoformat()
    if wkey not in weeks:
        weeks[wkey] = {"label": f"{MONTHS[wk.month-1]} {wk.day}", "start": wkey, "idx": []}
    weeks[wkey]["idx"].append(i)
week_list = [{"label": w["label"], "start": w["start"], "idx": w["idx"]} for w in weeks.values()]

# ---- data checks (quiet): work (kJ) should equal avg power x time ----
for r in rides:
    r["flags"] = []
    r["bad"] = {}
    if r["watts"] is None:
        r["flags"].append(["nopower", "No power data"])
    if r["mins"] is None:
        r["flags"].append(["notime", "Time not recorded"])
    if r["time"] and r["time"].startswith("~"):
        r["flags"].append(["approx", "Approximate time"])
    if r["kj"] and r["watts"] and r["mins"]:
        implied_mins = r["kj"] * 1000 / (r["watts"] * 60)
        off = abs(implied_mins - r["mins"]) / r["mins"]
        r["consistent"] = off <= 0.05
        if not r["consistent"]:
            w = round(r["kj"] * 1000 / (r["mins"] * 60))
            r["bad"]["watts"] = True
            r["implied_watts"] = w
            r["flags"].append(["mismatch", "Power doesn't match work"])

for i in range(len(rides)):
    for j in range(i + 1, len(rides)):
        a, b = rides[i], rides[j]
        if a["kj"] and a["kj"] == b["kj"] and a["kcal"] and a["kcal"] == b["kcal"]:
            copy = a if not a.get("consistent") else b
            copy["bad"]["kj"] = True
            copy["bad"]["kcal"] = True
            copy["flags"].append(["dup", "Possible duplicate reading"])

# personal records (power/work from rides that pass the check)
records = []
def add_rec(key, fmt, title, pool=None):
    pool = pool if pool is not None else rides
    c = [(r[key], r) for r in pool if r.get(key) is not None]
    if not c:
        return
    v, r = max(c, key=lambda t: t[0])
    records.append({"title": title, "value": fmt(v), "ride": r["label"]})

add_rec("dist", lambda v: f"{v:.2f} mi", "Longest ride")
add_rec("speed", lambda v: f"{v:.1f} mph", "Fastest avg speed")
add_rec("mins", lambda v: f"{int(v)} min", "Longest time")
_clean_watts = [r for r in rides if r.get("consistent") and not r["bad"].get("watts")]
_clean_kj = [r for r in rides if r["kj"] and not r["bad"].get("kj")]
add_rec("watts", lambda v: f"{v} W", "Best avg power", _clean_watts)
add_rec("kj", lambda v: f"{v} kJ", "Most work", _clean_kj)

# aggregates for the readout strip
tot_mi = sum(r["dist"] for r in rides)
tot_mins = sum(r["mins"] for r in rides if r["mins"])
tot_kj = sum(r["kj"] for r in rides if r["kj"] and not r["bad"].get("kj"))
tot_kcal = sum(r["kcal"] for r in rides if r["kcal"] and not r["bad"].get("kcal"))
_w = [r["watts"] for r in _clean_watts]
agg = {
    "mi": round(tot_mi, 1),
    "time": f"{int(tot_mins // 60)}:{int(tot_mins % 60):02d}",
    "n_mins": sum(1 for r in rides if r["mins"]),
    "kj": tot_kj,
    "n_kj": sum(1 for r in rides if r["kj"] and not r["bad"].get("kj")),
    "watts": round(sum(_w) / len(_w)) if _w else None,
    "n_watts": len(_w),
    "kcal": tot_kcal,
    "n_kcal": sum(1 for r in rides if r["kcal"] and not r["bad"].get("kcal")),
    "n": len(rides),
}

# weekly goal: current (latest) week vs target
_last_w = week_list[-1]
goal_data = {
    "goal": GOAL_MI_PER_WEEK,
    "current": round(sum(rides[i]["dist"] for i in _last_w["idx"]), 2),
    "week_start": _last_w["start"],
}

def js(v):
    return json.dumps(v)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trainer Log</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f7f9fb; --panel:#ffffff; --ink:#1a1a1a; --muted:#6b7280; --faint:#9ca3af; --line:#e2eaf0;
  --accent:#0069AA; --accent-soft:#e3f0f8;
  --display:'Barlow Condensed','Arial Narrow',Arial,sans-serif;
  --body:'IBM Plex Sans',-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.5;margin:0;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:28px 18px 64px;display:grid;gap:18px}
h1,h2{font-family:var(--display);font-weight:700;letter-spacing:.01em;margin:0}
h1{font-size:42px;line-height:1}
h2{font-size:23px;text-transform:uppercase;letter-spacing:.05em}
.top{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:8px 20px}
.top p{margin:6px 0 0;color:var(--muted)}
.top .mock{font:700 11px var(--body);background:var(--accent);color:#fff;border-radius:5px;padding:3px 9px;margin-left:10px;vertical-align:4px;letter-spacing:.05em}
.label{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--faint);font-weight:600}
.num{font-family:var(--display);font-weight:600;font-variant-numeric:tabular-nums;line-height:1}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;min-width:0;box-shadow:0 1px 2px rgba(20,20,26,.03),0 8px 24px rgba(20,20,26,.04)}
.panel-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 16px;margin-bottom:14px}
.panel-head p{margin:2px 0 0;color:var(--muted);font-size:13px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media (max-width:760px){.grid2{grid-template-columns:1fr}}

/* readout strip */
.readout{display:grid;grid-template-columns:repeat(5,1fr);border:1px solid var(--line);border-radius:12px;background:var(--panel);overflow:hidden;box-shadow:0 1px 2px rgba(20,20,26,.03),0 8px 24px rgba(20,20,26,.04)}
.readout>div{padding:16px 18px;border-left:1px solid var(--line);min-width:0}
.readout>div:first-child{border-left:0}
.readout .num{font-size:40px;margin-top:6px}
.readout .num small{font-size:16px;color:var(--muted);margin-left:3px}
.readout .cov{font-size:12px;color:var(--faint);margin-top:4px}
@media (max-width:760px){.readout{grid-template-columns:repeat(2,1fr)}.readout>div{border-left:0;border-top:1px solid var(--line)}.readout>div:nth-child(-n+2){border-top:0}.readout>div:nth-child(even){border-left:1px solid var(--line)}.readout>div:last-child{grid-column:1/-1}}

/* this week */
.week{display:grid;grid-template-columns:auto 1fr;gap:24px;align-items:center}
.goalbar{height:14px;border-radius:7px;background:var(--accent-soft);overflow:hidden;margin:10px 0 8px}
.goalbar i{display:block;height:100%;background:var(--accent);border-radius:7px;transition:width .4s ease}
.stepper{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
.stepper button{width:26px;height:26px;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:7px;cursor:pointer;font:700 15px var(--body);line-height:1}
.stepper button:hover{background:#f0f1f4}
.days{display:flex;gap:6px;align-items:flex-start}
.day{width:34px;flex:none;text-align:center;font-size:11px;color:var(--faint);font-weight:600}
.day b{display:block;width:100%;height:34px;border-radius:7px;background:var(--bg);border:1px solid var(--line);margin:0 0 4px;padding:0}
.day.ride b{background:var(--accent);border-color:var(--accent)}
.day.today b{box-shadow:0 0 0 2px var(--ink)}
@media (max-width:520px){.week{grid-template-columns:1fr}.day{width:auto;flex:1}}

/* heatmap */
.heat{display:grid;grid-template-columns:52px repeat(7,1fr) 64px;gap:5px;align-items:center;font-size:12px}
.heat .h{color:var(--faint);text-align:center;font-size:11px;font-weight:600}
.heat .wk{color:var(--muted);font-family:var(--mono);font-size:11px}
.cell{aspect-ratio:1;max-width:100%;border-radius:5px;background:var(--bg);border:1px solid var(--line);position:relative}
.cell.future{border-style:dashed;background:transparent}
.cell.today{box-shadow:0 0 0 2px var(--ink)}
.heat .tot{text-align:right;color:var(--ink)}
.gapnote{margin-top:12px;font-size:13px;color:var(--muted)}

/* toggles */
.toggle{display:inline-flex;flex-wrap:wrap;background:#e4e6ea;border-radius:9px;padding:3px}
.toggle button{border:0;background:transparent;color:var(--muted);font:600 13px var(--body);padding:6px 14px;border-radius:7px;cursor:pointer}
.toggle button.on{background:var(--panel);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.14)}
.hint{font-size:12px;color:var(--faint);margin-bottom:6px}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--faint);font-family:var(--mono);font-size:10px}
.gridline{stroke:var(--line)}
.pt{cursor:pointer}
.tlabel{font-size:13px;font-weight:600;color:var(--muted);margin-bottom:6px}
.xlabels{display:flex;justify-content:space-between;font-size:10px;color:var(--faint);padding:4px 38px 0;font-family:var(--mono)}

/* records */
.recs{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.rec{border:1px solid #c4dcee;border-radius:10px;padding:12px 14px;background:var(--accent-soft)}
.rec .num{font-size:30px;margin:4px 0 2px}
.rec .num small{font-size:14px;color:var(--muted);margin-left:2px}
.rec .when{font-size:12px;color:var(--muted)}

/* feed */
.feed-head{display:flex;align-items:center;justify-content:space-between;margin:6px 2px 14px;cursor:pointer}
.feed-head h2{font-size:23px}
#feedArrow{color:var(--faint);font-size:14px;margin-right:8px;font-family:var(--body)}
.clear{font-size:13px;color:var(--accent);cursor:pointer;font-weight:700;display:none}
.clear.show{display:inline}
.ride{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:12px;box-shadow:0 1px 2px rgba(20,20,26,.03),0 6px 18px rgba(20,20,26,.04)}
.ride .top{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px}
.ride .title{font-family:var(--display);font-weight:700;font-size:21px;letter-spacing:.02em}
.ride .date{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.08em}
.ride .dist{font-family:var(--display);font-size:38px;font-weight:600;line-height:1;margin-bottom:10px}
.ride .dist small{font-size:16px;color:var(--muted);font-family:var(--body);font-weight:500}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media (max-width:640px){.metrics{grid-template-columns:repeat(2,1fr)}}
.metric .v{font-size:16px;font-weight:600;font-family:var(--mono)}
.metric .l{font-size:10px;color:var(--faint);text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-top:2px}
.foot{font-size:12px;color:var(--faint);text-align:center}
</style>

<div class="wrap">
  <header class="top">
    <div>
      <h1>Trainer Log<span class="mock">MOCKUP</span></h1>
      <p id="sub"></p>
    </div>
    <div class="label">All rides indoor</div>
  </header>

  <section class="readout" id="readout" aria-label="Totals"></section>

  <section class="panel">
    <div class="panel-head">
      <div><h2>This week</h2><p id="weekSub"></p></div>
      <div class="stepper"><span>Goal</span><button id="gMinus" aria-label="Lower goal">−</button><span class="mono" id="gVal"></span><button id="gPlus" aria-label="Raise goal">+</button><span>mi</span></div>
    </div>
    <div class="week">
      <div class="days" id="days"></div>
      <div>
        <div class="num" style="font-size:36px" id="weekNum"></div>
        <div class="goalbar"><i id="goalFill"></i></div>
        <div style="font-size:13px;color:var(--muted)" id="weekNote"></div>
      </div>
    </div>
  </section>

  <div class="grid2">
    <section class="panel">
      <div class="panel-head"><div><h2>Consistency</h2><p>Each square is a day. Darker means more miles.</p></div></div>
      <div class="heat" id="heat"></div>
      <div class="gapnote" id="gapnote"></div>
    </section>
    <section class="panel">
      <div class="panel-head"><div><h2>Weekly volume</h2><p>Tap a week to filter the log.</p></div></div>
      <div id="weekly"></div>
    </section>
  </div>

  <section class="panel">
    <div class="panel-head">
      <div><h2>Trend</h2><p>One chart per metric, plotted by ride.</p></div>
      <div class="toggle" id="metricToggle"></div>
    </div>
    <div id="chartArea" style="margin-top:4px"></div>
  </section>

  <section class="panel">
    <div class="panel-head"><div><h2>Personal records</h2><p>Computed from the rides below.</p></div></div>
    <div class="recs" id="recs"></div>
  </section>

  <div class="feed-head" id="feedHead">
    <h2><span id="feedArrow">▾</span><span id="feedTitle">Ride log</span></h2>
    <span class="clear" id="clearBtn">Show all</span>
  </div>
  <div id="feed"></div>

  <div class="foot">Speed on a trainer is a virtual estimate from the app, so power and work are the numbers to trust.</div>
</div>

<script>
const rides = __RIDES__;
const weekList = __WEEKS__;
const records = __RECORDS__;
const goal = __GOAL__;
const agg = __AGG__;
const TODAY = goal.today;

const DAY = 864e5;
const D = s => new Date(s + "T12:00:00Z");
const iso = d => d.toISOString().slice(0, 10);
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const WD = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const fmt = s => { const d = D(s); return `${WD[d.getUTCDay()]} ${MON[d.getUTCMonth()]} ${d.getUTCDate()}`; };
const short = s => { const d = D(s); return `${MON[d.getUTCMonth()]} ${d.getUTCDate()}`; };
const shortD = s => { const [y,m,dd] = s.split("-"); return `${+m}/${+dd}`; };
const monday = s => { const d = D(s); const k = (d.getUTCDay()+6)%7; return iso(new Date(d.getTime() - k*DAY)); };
const sum = (a,f) => a.reduce((s,r)=>s+(f(r) ?? 0),0);
const svgEl = (w,h,inner,label) => `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${label}">${inner}</svg>`;
function ticks(lo,hi,n){
  const span = hi-lo || 1, step0 = span/n, mag = 10**Math.floor(Math.log10(step0));
  const step = [1,2,2.5,5,10].map(m=>m*mag).find(s=>s>=step0);
  const a = Math.floor(lo/step)*step, b = Math.ceil(hi/step)*step, t = [];
  for(let v=a; v<=b+1e-9; v+=step) t.push(+v.toFixed(6));
  return t;
}

/* header + readout */
document.getElementById("sub").textContent = `${fmt(rides[0].date)} to ${fmt(TODAY)}, 2026 · ${rides.length} rides`;
(function(){
  const cov = n => n === agg.n ? "All rides" : `${n} of ${agg.n} rides`;
  const tiles = [
    ["Distance", agg.mi.toFixed(1), "mi", cov(agg.n)],
    ["Ride time", agg.time, "h", cov(agg.n_mins)],
    ["Work", agg.kj.toLocaleString(), "kJ", cov(agg.n_kj)],
    ["Avg power", agg.watts, "W", `${agg.n_watts} rides that pass the check`],
    ["Calories", agg.kcal.toLocaleString(), "kcal", cov(agg.n_kcal)],
  ];
  document.getElementById("readout").innerHTML =
    tiles.map(([l,v,u,c])=>`<div><div class="label">${l}</div><div class="num">${v}<small>${u}</small></div><div class="cov">${c}</div></div>`).join("");
})();

/* this week + goal */
let goalVal = goal.goal;
try { const g = +localStorage.getItem("cycleGoal"); if (g > 0) goalVal = g; } catch(e){}
const wkStart = goal.week_start;
function renderWeek(){
  const inWeek = rides.filter(r => monday(r.date) === wkStart);
  const mi = sum(inWeek, r => r.dist), pct = Math.min(mi / goalVal, 1);
  const daysLeft = 6 - (D(TODAY).getUTCDay()+6)%7;
  const avgRide = agg.mi / agg.n;
  document.getElementById("gVal").textContent = goalVal;
  document.getElementById("weekSub").textContent = `Week of ${short(wkStart)} · ${inWeek.length} ride${inWeek.length===1?"":"s"} so far`;
  document.getElementById("weekNum").innerHTML = `${mi.toFixed(1)} <small style="font-size:16px;color:var(--muted)">of ${goalVal} mi</small>`;
  document.getElementById("goalFill").style.width = (pct*100) + "%";
  const rem = goalVal - mi;
  document.getElementById("weekNote").textContent = rem <= 0
    ? "Goal hit for the week."
    : `${rem.toFixed(1)} mi to go with ${daysLeft} day${daysLeft===1?"":"s"} left after today. Your average ride is ${avgRide.toFixed(1)} mi, so about ${Math.ceil(rem/avgRide)} more ride${Math.ceil(rem/avgRide)===1?"":"s"}.`;
  document.getElementById("days").innerHTML = [0,1,2,3,4,5,6].map(k=>{
    const d = iso(new Date(D(wkStart).getTime() + k*DAY));
    const rode = rides.some(r => r.date === d);
    return `<div class="day${rode?" ride":""}${d===TODAY?" today":""}"><b title="${fmt(d)}${rode?" · ride":""}"></b>${WD[(k+1)%7][0]}</div>`;
  }).join("");
}
function bumpGoal(d){
  goalVal = Math.max(5, goalVal + d);
  try { localStorage.setItem("cycleGoal", goalVal); } catch(e){}
  renderWeek(); renderWeekly();
}
document.getElementById("gMinus").addEventListener("click", ()=>bumpGoal(-5));
document.getElementById("gPlus").addEventListener("click", ()=>bumpGoal(5));

/* consistency heatmap */
(function(){
  const maxMi = Math.max(...rides.map(r=>r.dist));
  const firstWk = weekList[0].start;
  let h = `<div></div>` + ["M","T","W","T","F","S","S"].map(x=>`<div class="h">${x}</div>`).join("") + `<div class="h" style="text-align:right">mi</div>`;
  weekList.forEach(w=>{
    h += `<div class="wk">${short(w.start)}</div>`;
    for(let k=0;k<7;k++){
      const d = iso(new Date(D(w.start).getTime() + k*DAY));
      const r = rides.find(x=>x.date===d);
      const fut = d > TODAY;
      const style = r ? `style="background:color-mix(in srgb, var(--accent) ${Math.round(35+65*r.dist/maxMi)}%, var(--panel));border-color:transparent"` : "";
      h += `<div class="cell${fut?" future":""}${d===TODAY?" today":""}" ${style} title="${fmt(d)}${r?` · ${r.dist} mi`:""}"></div>`;
    }
    h += `<div class="tot mono">${sum(rides.filter(r=>monday(r.date)===w.start), r=>r.dist).toFixed(1)}</div>`;
  });
  document.getElementById("heat").innerHTML = h;
  let gap = 0, ga = null, gb = null;
  for(let i=1;i<rides.length;i++){
    const g = (D(rides[i].date) - D(rides[i-1].date)) / DAY;
    if(g > gap){ gap = g; ga = rides[i-1].date; gb = rides[i].date; }
  }
  const gaps = rides.slice(1).map((r,i)=>(D(r.date)-D(rides[i].date))/DAY);
  const med = [...gaps].sort((a,b)=>a-b)[Math.floor(gaps.length/2)];
  document.getElementById("gapnote").innerHTML =
    `Typical gap between rides: <b>${med} days</b>. Longest: <b>${gap} days</b>, ${short(ga)} to ${short(gb)}.`;
})();

/* weekly volume bars with goal line, tap to filter */
let filterWeek = null;
function weekMi(w){ return sum(rides.filter(r=>monday(r.date)===w.start), r=>r.dist); }
function renderWeekly(){
  const data = weekList;
  const W=460, H=220, L=34, B=42, T=16;
  const top = ticks(0, Math.max(goalVal, ...data.map(weekMi))*1.05, 4);
  const ymax = top[top.length-1];
  const y = v => H-B-(v/ymax)*(H-B-T);
  const bw = (W-L-10)/data.length;
  let s = top.map(t=>`<line class="gridline" x1="${L}" x2="${W}" y1="${y(t)}" y2="${y(t)}"/><text x="${L-6}" y="${y(t)+3}" text-anchor="end">${t}</text>`).join("");
  data.forEach((w,i)=>{
    const mi = weekMi(w);
    const x = L+i*bw+bw*.18, bwid = bw*.64;
    const on = filterWeek === null || filterWeek === w.start;
    s += `<g class="pt" tabindex="0" role="button" aria-label="Week of ${short(w.start)}, ${mi.toFixed(1)} miles" data-w="${w.start}">
      <rect x="${L+i*bw}" y="${T}" width="${bw}" height="${H-B-T}" fill="transparent"/>
      <rect x="${x}" y="${y(mi)}" width="${bwid}" height="${Math.max(H-B-y(mi),1)}" rx="4" fill="var(--accent)" opacity="${on?1:.25}"/>
      <text x="${x+bwid/2}" y="${y(mi)-6}" text-anchor="middle" style="fill:var(--ink);font-weight:600">${mi.toFixed(1)}</text>
      <text x="${x+bwid/2}" y="${H-B+16}" text-anchor="middle">${short(w.start)}</text>
      <text x="${x+bwid/2}" y="${H-B+30}" text-anchor="middle">${w.idx.length}×</text></g>`;
  });
  s += `<line x1="${L}" x2="${W}" y1="${y(goalVal)}" y2="${y(goalVal)}" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="5 4"/>`;
  document.getElementById("weekly").innerHTML = svgEl(W,H,s,"Miles per week");
  document.querySelectorAll("#weekly .pt").forEach(g=>{
    const f = ()=>{ filterWeek = filterWeek===g.dataset.w ? null : g.dataset.w; renderWeekly(); renderFeed(); };
    g.onclick = f;
    g.onkeydown = e=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); f(); } };
  });
}

/* trends: 5 metrics */
const METRICS = {
  watts: {n:"Power",    u:"W",   c:"#0069AA", d:0},
  dist:  {n:"Distance", u:"mi",  c:"#0d2d6b", d:2},
  mins:  {n:"Duration", u:"min", c:"#00C99C", d:1},
  rpm:   {n:"Cadence",  u:"rpm", c:"#004F82", d:0},
  speed: {n:"Speed",    u:"mph", c:"#4d9fd1", d:1},
};
let metric = "watts";
document.getElementById("metricToggle").innerHTML =
  Object.entries(METRICS).map(([k,m])=>`<button data-k="${k}" class="${k===metric?"on":""}">${m.n}</button>`).join("");
document.querySelectorAll("#metricToggle button").forEach(b=>b.addEventListener("click", ()=>{
  metric = b.dataset.k;
  document.querySelectorAll("#metricToggle button").forEach(x=>x.classList.toggle("on", x===b));
  renderChart();
}));
function lineChart(elId, key, color){
  const el = document.getElementById(elId);
  const vals = rides.map(r=>r[key]);
  const pts = vals.map((v,i)=>({v,i})).filter(o=>o.v!=null);
  if(pts.length<2){ el.innerHTML = "<div class='hint'>Not enough data yet.</div>"; return; }
  const vs = pts.map(o=>o.v);
  const lo = Math.min(...vs), hi = Math.max(...vs), span = (hi-lo)||1;
  const w=640, h=170, p=38, base=h-30;
  const x = i => p + i*(w-2*p)/(vals.length-1);
  const y = v => base - (v-lo)/span*(base-22);
  const line = pts.map(o=>`${x(o.i).toFixed(1)},${y(o.v).toFixed(1)}`).join(" ");
  const area = `M${x(pts[0].i).toFixed(1)},${base} L` +
    pts.map(o=>`${x(o.i).toFixed(1)},${y(o.v).toFixed(1)}`).join(" L") +
    ` L${x(pts[pts.length-1].i).toFixed(1)},${base} Z`;
  const gid = "g"+key, mid = (lo+hi)/2;
  el.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto;display:block">
      <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${color}" stop-opacity=".20"/>
        <stop offset="1" stop-color="${color}" stop-opacity="0"/>
      </linearGradient></defs>
      ${[hi,mid,lo].map(v=>`<line class="gridline" x1="${p}" y1="${y(v).toFixed(1)}" x2="${w-16}" y2="${y(v).toFixed(1)}" stroke-dasharray="3 4"/>`).join("")}
      <path d="${area}" fill="url(#${gid})"/>
      <polyline points="${line}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
      ${pts.map(o=>`<circle cx="${x(o.i).toFixed(1)}" cy="${y(o.v).toFixed(1)}" r="4.5" fill="#fff" stroke="${color}" stroke-width="2.5"/>`).join("")}
      <text x="${p-9}" y="${(y(hi)+4).toFixed(1)}" text-anchor="end" font-size="11" fill="#a2a2ab" font-weight="600">${hi}</text>
      <text x="${p-9}" y="${(y(lo)+4).toFixed(1)}" text-anchor="end" font-size="11" fill="#a2a2ab" font-weight="600">${lo}</text>
    </svg>
    <div class="xlabels">${vals.map((_,i)=>`<span>${shortD(rides[i].date)}</span>`).join("")}</div>`;
}
function renderChart(){
  const m = METRICS[metric];
  document.getElementById("chartArea").innerHTML =
    `<div class="tlabel">${m.n} per ride (${m.u})</div><div id="chOne"></div>`;
  lineChart("chOne", metric, m.c);
}
renderChart();

/* records */
document.getElementById("recs").innerHTML = records.map(r=>`
  <div class="rec"><div class="label">${r.title}</div><div class="num">${r.value}</div><div class="when">${r.ride}</div></div>`).join("");

/* ride log feed */
function m(label, val){ return val==null ? "" : `<div class="metric"><div class="v">${val}</div><div class="l">${label}</div></div>`; }
function renderFeed(){
  let list = [...rides].reverse();
  let title = "Ride log";
  if(filterWeek){
    const w = weekList.find(w=>w.start===filterWeek);
    const set = new Set(w.idx);
    list = list.filter(r => set.has(rides.indexOf(r)));
    title = "Rides, week of " + w.label;
  }
  document.getElementById("feedTitle").textContent = title;
  document.getElementById("clearBtn").classList.toggle("show", filterWeek!==null);
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
document.getElementById("clearBtn").addEventListener("click", (e)=>{
  e.stopPropagation();
  filterWeek = null; renderWeekly(); renderFeed();
});
let feedOpen = true;
document.getElementById("feedHead").addEventListener("click", ()=>{
  feedOpen = !feedOpen;
  document.getElementById("feed").style.display = feedOpen ? "" : "none";
  document.getElementById("feedArrow").textContent = feedOpen ? "▾" : "▸";
});

renderWeek(); renderWeekly(); renderFeed();
</script>
</body>
</html>
"""

html = (html.replace("__RIDES__", js(rides))
            .replace("__WEEKS__", js(week_list))
            .replace("__RECORDS__", js(records))
            .replace("__GOAL__", js({**goal_data, "today": TODAY}))
            .replace("__AGG__", js(agg)))
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
for w in week_list:
    wk = date.fromisoformat(w["start"])
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
print(f"built: {len(rides)} rides")
