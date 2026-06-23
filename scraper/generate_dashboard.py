"""
Generates a professional static HTML dashboard from decision_report.csv.
Output: docs/index.html — served via GitHub Pages.
"""

import os
import pandas as pd
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DECISION_REPORT_CSV, DATA_DIR

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

LABEL_FA = {
    "Entry Candidate": "کاندید ورود",
    "Technical Entry Watch": "واچ تکنیکال",
    "Wait for Pullback": "صبر برای پولبک",
    "Avoid Entry Now - Overbought": "اشباع خرید",
    "Watch - Needs Volume Confirmation": "نیاز به تایید حجم",
    "Watch Only": "فقط رصد",
    "Missing Technical Data": "داده ناقص",
}

LABEL_COLOR = {
    "Entry Candidate": "#22c55e",
    "Technical Entry Watch": "#eab308",
    "Wait for Pullback": "#f97316",
    "Avoid Entry Now - Overbought": "#ef4444",
    "Watch - Needs Volume Confirmation": "#3b82f6",
    "Watch Only": "#6b7280",
    "Missing Technical Data": "#374151",
}

GRADE_COLOR = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}


def _fmt(val, suffix="", decimals=1):
    if val is None:
        return "—"
    try:
        if pd.isna(val):
            return "—"
        return f"{float(val):.{decimals}f}{suffix}"
    except Exception:
        return str(val)


def generate():
    if not os.path.exists(DECISION_REPORT_CSV):
        print("[dashboard] decision_report.csv not found")
        return

    df = pd.read_csv(DECISION_REPORT_CSV)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    market_header = ""
    header_path = os.path.join(DATA_DIR, "market_header.txt")
    if os.path.exists(header_path):
        with open(header_path, encoding="utf-8") as f:
            market_header = f.read()

    # --- Stats ---
    total = len(df)
    entry_count = len(df[df["decision_label"] == "Entry Candidate"])
    watch_count = len(df[df["decision_label"] == "Technical Entry Watch"])
    avoid_count = len(df[df["decision_label"] == "Avoid Entry Now - Overbought"])
    missing_count = len(df[df["missing"].astype(str).str.lower() == "true"])
    high_conf = len(df[df["confidence_score"] >= 70]) if "confidence_score" in df.columns else 0

    # --- Donut chart data ---
    label_counts = {}
    for label, fa in LABEL_FA.items():
        cnt = len(df[df["decision_label"] == label])
        if cnt > 0:
            label_counts[fa] = {"count": cnt, "color": LABEL_COLOR.get(label, "#6b7280")}

    donut_data = []
    for fa, info in label_counts.items():
        donut_data.append(f'{{"label":"{fa}","count":{info["count"]},"color":"{info["color"]}"}}'  )
    donut_json = "[" + ",".join(donut_data) + "]"

    # --- Sector heatmap data ---
    sectors = df.groupby("sector").agg(
        count=("symbol", "count"),
        avg_score=("confidence_score", "mean"),
        sector_status=("sector_status", "first")
    ).reset_index() if "sector" in df.columns else pd.DataFrame()

    sector_html = ""
    if not sectors.empty:
        for _, row in sectors.iterrows():
            status = str(row.get("sector_status", ""))
            if "پیشرو" in status:
                bg = "#14532d"
                border = "#22c55e"
                dot = "🟢"
            elif "عقب" in status:
                bg = "#450a0a"
                border = "#ef4444"
                dot = "🔴"
            else:
                bg = "#1e293b"
                border = "#475569"
                dot = "🟡"
            avg = row.get("avg_score", 0)
            sector_html += f'''
            <div class="sector-chip" style="background:{bg};border:1px solid {border}">
                <span>{dot} {row["sector"]}</span>
                <span class="sector-score">{avg:.0f}</span>
            </div>'''

    # --- Table rows ---
    df_sorted = df.sort_values("confidence_score", ascending=False) if "confidence_score" in df.columns else df
    table_rows = ""
    for _, row in df_sorted.iterrows():
        label = str(row.get("decision_label", ""))
        color = LABEL_COLOR.get(label, "#6b7280")
        label_fa = LABEL_FA.get(label, label)
        grade = str(row.get("confidence_grade", ""))
        grade_color = GRADE_COLOR.get(grade, "#6b7280")
        score = row.get("confidence_score", 0)
        missing = str(row.get("missing", "True")).lower() == "true"

        rsi = _fmt(row.get("rsi"))
        trend = _fmt(row.get("trend_score"), decimals=0)
        vol = _fmt(row.get("volume_ratio_20"))
        ret5 = _fmt(row.get("return_5d_percent"), suffix="%")
        sl = _fmt(row.get("stop_loss"), decimals=0)
        tgt = _fmt(row.get("target_1"), decimals=0)
        rr = _fmt(row.get("risk_reward"))
        sector = str(row.get("sector", "—"))
        sm = str(row.get("smart_money_fa", ""))
        candle = str(row.get("candle_pattern", ""))
        macd = str(row.get("macd_crossover", ""))
        w_trend = str(row.get("weekly_trend", ""))

        badges = ""
        if macd == "bullish":
            badges += '<span class="badge g">MACD↑</span>'
        elif macd == "bearish":
            badges += '<span class="badge r">MACD↓</span>'
        if w_trend == "up":
            badges += '<span class="badge g">W↑</span>'
        elif w_trend == "down":
            badges += '<span class="badge r">W↓</span>'
        if candle and candle not in ("nan", "none", ""):
            badges += f'<span class="badge y">🕯</span>'

        sm_txt = sm if sm and sm not in ("nan", "") else ""

        table_rows += f'''
        <tr data-label="{label}" data-sector="{sector}" data-grade="{grade}" data-score="{score}">
            <td><strong class="sym">{row.get("symbol","")}</strong></td>
            <td><span class="label-dot" style="color:{color}">●</span> {label_fa}</td>
            <td><span class="grade-tag" style="background:{grade_color}">{grade}</span> {score}</td>
            <td>{rsi}</td>
            <td>{trend}/6</td>
            <td>{vol}x</td>
            <td>{ret5}</td>
            <td>{sl}</td>
            <td>{tgt}</td>
            <td>{rr}</td>
            <td>{sector}</td>
            <td>{badges} <small>{sm_txt}</small></td>
        </tr>'''

    # --- Market mood lines ---
    mood_html = market_header.replace("\n", "<br>") if market_header else ""

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Iran Stock AI</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Tahoma,Arial,sans-serif;background:#0a0f1e;color:#e2e8f0;direction:rtl;font-size:13px}}

/* Header */
.topbar{{background:linear-gradient(135deg,#0f172a,#1e293b);padding:16px 24px;border-bottom:1px solid #1e3a5f;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
.topbar h1{{font-size:1.2rem;color:#38bdf8;font-weight:bold}}
.topbar .time{{color:#64748b;font-size:0.8rem}}
.pulse{{display:inline-block;width:8px;height:8px;background:#22c55e;border-radius:50%;margin-left:6px;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}

/* Stat cards */
.stats{{display:flex;gap:12px;padding:16px 24px;flex-wrap:wrap}}
.stat-card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px 20px;min-width:120px;text-align:center}}
.stat-card .val{{font-size:1.6rem;font-weight:bold;line-height:1}}
.stat-card .lbl{{font-size:0.72rem;color:#64748b;margin-top:4px}}

/* Donut + gauge row */
.widgets{{display:flex;gap:16px;padding:0 24px 16px;flex-wrap:wrap;align-items:flex-start}}
.widget-box{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px}}

/* Sector heatmap */
.sector-wrap{{padding:0 24px 16px}}
.sector-title{{font-size:0.85rem;color:#94a3b8;margin-bottom:8px}}
.sector-chips{{display:flex;gap:8px;flex-wrap:wrap}}
.sector-chip{{display:flex;align-items:center;gap:8px;padding:6px 12px;border-radius:20px;font-size:0.78rem}}
.sector-score{{font-weight:bold;color:#38bdf8}}

/* Mood */
.mood-box{{background:#0f172a;border:1px solid #1e3a5f;border-radius:8px;padding:12px 16px;font-size:0.78rem;line-height:2;color:#94a3b8;margin:0 24px 16px}}

/* Filter bar */
.filter-bar{{padding:8px 24px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;background:#0f172a;border-top:1px solid #1e293b;border-bottom:1px solid #1e293b}}
.filter-bar input{{background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:6px 12px;border-radius:6px;font-size:0.8rem;width:160px}}
.filter-bar input::placeholder{{color:#475569}}
.filter-bar select{{background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:6px 10px;border-radius:6px;font-size:0.8rem}}
.filter-btn{{padding:5px 14px;border-radius:16px;border:1px solid #334155;background:transparent;color:#94a3b8;cursor:pointer;font-size:0.78rem;font-family:Tahoma}}
.filter-btn.active,.filter-btn:hover{{background:#38bdf8;color:#0a0f1e;border-color:#38bdf8}}

/* Table */
.table-wrap{{padding:0 24px 32px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:0.8rem}}
thead th{{background:#0f172a;color:#64748b;padding:10px 8px;text-align:right;border-bottom:2px solid #1e293b;cursor:pointer;white-space:nowrap;user-select:none}}
thead th:hover{{color:#38bdf8}}
thead th.sort-asc::after{{content:" ↑"}}
thead th.sort-desc::after{{content:" ↓"}}
tbody tr{{border-bottom:1px solid #1a2540;transition:background 0.15s}}
tbody tr:hover{{background:#1e293b}}
tbody td{{padding:9px 8px;vertical-align:middle;white-space:nowrap}}
.sym{{color:#f1f5f9;font-size:0.9rem}}
.label-dot{{font-size:1rem}}
.grade-tag{{padding:1px 7px;border-radius:10px;font-size:0.72rem;color:#0a0f1e;font-weight:bold}}
.badge{{padding:1px 6px;border-radius:8px;font-size:0.68rem;font-weight:bold;margin-left:2px}}
.badge.g{{background:#14532d;color:#86efac}}
.badge.r{{background:#450a0a;color:#fca5a5}}
.badge.y{{background:#422006;color:#fde68a}}

/* Canvas */
canvas{{display:block}}

/* Scrollbar */
::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:#0a0f1e}}
::-webkit-scrollbar-thumb{{background:#334155;border-radius:3px}}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <span class="pulse"></span>
    <span class="topbar h1" style="display:inline;font-size:1.1rem;color:#38bdf8;font-weight:bold">📊 Iran Stock AI Dashboard</span>
  </div>
  <div class="time">آخرین آپدیت: {now}</div>
</div>

<!-- Stat Cards -->
<div class="stats">
  <div class="stat-card"><div class="val" style="color:#e2e8f0">{total}</div><div class="lbl">کل نمادها</div></div>
  <div class="stat-card"><div class="val" style="color:#22c55e">{entry_count}</div><div class="lbl">کاندید ورود</div></div>
  <div class="stat-card"><div class="val" style="color:#eab308">{watch_count}</div><div class="lbl">واچ تکنیکال</div></div>
  <div class="stat-card"><div class="val" style="color:#ef4444">{avoid_count}</div><div class="lbl">اشباع خرید</div></div>
  <div class="stat-card"><div class="val" style="color:#38bdf8">{high_conf}</div><div class="lbl">امتیاز بالا ۷۰+</div></div>
  <div class="stat-card"><div class="val" style="color:#6b7280">{missing_count}</div><div class="lbl">فاقد داده</div></div>
</div>

<!-- Widgets Row -->
<div class="widgets">
  <!-- Donut Chart -->
  <div class="widget-box">
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:10px">توزیع سیگنال‌ها</div>
    <canvas id="donut" width="180" height="180"></canvas>
    <div id="donut-legend" style="margin-top:10px;font-size:0.72rem"></div>
  </div>

  <!-- Gauge -->
  <div class="widget-box" style="text-align:center">
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:10px">امتیاز میانگین بازار</div>
    <canvas id="gauge" width="180" height="110"></canvas>
    <div id="gauge-val" style="font-size:1.8rem;font-weight:bold;color:#38bdf8;margin-top:4px"></div>
    <div style="font-size:0.72rem;color:#64748b">از ۱۰۰</div>
  </div>

  <!-- Mood -->
  <div class="widget-box" style="flex:1;min-width:250px;max-height:220px;overflow-y:auto">
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:8px">وضعیت بازار</div>
    <div style="font-size:0.75rem;line-height:2;color:#94a3b8">{mood_html}</div>
  </div>
</div>

<!-- Sector Heatmap -->
<div class="sector-wrap">
  <div class="sector-title">🗺 هیتمپ سکتورها (میانگین امتیاز)</div>
  <div class="sector-chips">{sector_html}</div>
</div>

<!-- Filter Bar -->
<div class="filter-bar">
  <input type="text" id="search" placeholder="جستجوی نماد..." oninput="applyFilters()">
  <select id="f-label" onchange="applyFilters()">
    <option value="">همه سیگنال‌ها</option>
    <option value="Entry Candidate">کاندید ورود</option>
    <option value="Technical Entry Watch">واچ تکنیکال</option>
    <option value="Wait for Pullback">صبر پولبک</option>
    <option value="Avoid Entry Now - Overbought">اشباع خرید</option>
    <option value="Watch - Needs Volume Confirmation">نیاز به حجم</option>
    <option value="Watch Only">فقط رصد</option>
    <option value="Missing Technical Data">داده ناقص</option>
  </select>
  <select id="f-grade" onchange="applyFilters()">
    <option value="">همه درجه‌ها</option>
    <option value="A">درجه A</option>
    <option value="B">درجه B</option>
    <option value="C">درجه C</option>
    <option value="D">درجه D</option>
    <option value="F">درجه F</option>
  </select>
  <select id="f-sector" onchange="applyFilters()">
    <option value="">همه سکتورها</option>
  </select>
  <button class="filter-btn active" onclick="resetFilters()">ریست</button>
  <span id="count-label" style="color:#64748b;font-size:0.78rem;margin-right:auto"></span>
</div>

<!-- Table -->
<div class="table-wrap">
<table id="main-table">
<thead>
  <tr>
    <th onclick="sortTable(0)">نماد</th>
    <th onclick="sortTable(1)">سیگنال</th>
    <th onclick="sortTable(2)">امتیاز</th>
    <th onclick="sortTable(3)">RSI</th>
    <th onclick="sortTable(4)">روند</th>
    <th onclick="sortTable(5)">حجم</th>
    <th onclick="sortTable(6)">بازده۵روز</th>
    <th onclick="sortTable(7)">حد ضرر</th>
    <th onclick="sortTable(8)">هدف</th>
    <th onclick="sortTable(9)">R/R</th>
    <th onclick="sortTable(10)">سکتور</th>
    <th>سیگنال‌ها</th>
  </tr>
</thead>
<tbody id="table-body">
{table_rows}
</tbody>
</table>
</div>

<script>
// --- Donut Chart ---
const donutData = {donut_json};
(function(){{
  const canvas = document.getElementById('donut');
  const ctx = canvas.getContext('2d');
  const total = donutData.reduce((s,d)=>s+d.count,0);
  let angle = -Math.PI/2;
  const cx=90,cy=90,r=70,ir=45;
  donutData.forEach(d=>{{
    const slice = (d.count/total)*Math.PI*2;
    ctx.beginPath();ctx.moveTo(cx,cy);
    ctx.arc(cx,cy,r,angle,angle+slice);
    ctx.closePath();ctx.fillStyle=d.color;ctx.fill();
    angle+=slice;
  }});
  ctx.beginPath();ctx.arc(cx,cy,ir,0,Math.PI*2);
  ctx.fillStyle='#1e293b';ctx.fill();
  ctx.fillStyle='#e2e8f0';ctx.font='bold 14px Tahoma';
  ctx.textAlign='center';ctx.textBaseline='middle';
  ctx.fillText(total,cx,cy);

  const leg = document.getElementById('donut-legend');
  donutData.forEach(d=>{{
    leg.innerHTML+=`<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
      <span style="width:10px;height:10px;background:${{d.color}};border-radius:2px;display:inline-block"></span>
      <span style="color:#94a3b8">${{d.label}}: ${{d.count}}</span></div>`;
  }});
}})();

// --- Gauge ---
(function(){{
  const canvas = document.getElementById('gauge');
  const ctx = canvas.getContext('2d');
  const scores = [...document.querySelectorAll('#table-body tr')].map(r=>parseFloat(r.dataset.score)||0);
  const avg = scores.length ? scores.reduce((a,b)=>a+b,0)/scores.length : 0;
  document.getElementById('gauge-val').textContent = avg.toFixed(0);

  const cx=90,cy=100,r=75;
  const startA = Math.PI, endA = 2*Math.PI;
  ctx.beginPath();ctx.arc(cx,cy,r,startA,endA);
  ctx.strokeStyle='#1e3a5f';ctx.lineWidth=14;ctx.stroke();

  const pct = Math.min(avg/100,1);
  const color = avg>=70?'#22c55e':avg>=50?'#eab308':'#ef4444';
  ctx.beginPath();ctx.arc(cx,cy,r,startA,startA+pct*Math.PI);
  ctx.strokeStyle=color;ctx.lineWidth=14;ctx.lineCap='round';ctx.stroke();
}})();

// --- Sector filter populate ---
(function(){{
  const sel = document.getElementById('f-sector');
  const sectors = [...new Set([...document.querySelectorAll('#table-body tr')].map(r=>r.dataset.sector))].sort();
  sectors.forEach(s=>{{ const o=document.createElement('option');o.value=s;o.textContent=s;sel.appendChild(o); }});
}})();

// --- Filters ---
function applyFilters(){{
  const search = document.getElementById('search').value.trim().toLowerCase();
  const label = document.getElementById('f-label').value;
  const grade = document.getElementById('f-grade').value;
  const sector = document.getElementById('f-sector').value;
  let visible=0;
  document.querySelectorAll('#table-body tr').forEach(r=>{{
    const sym = r.querySelector('.sym')?.textContent.toLowerCase()||'';
    const show = (!search||sym.includes(search))&&
                 (!label||r.dataset.label===label)&&
                 (!grade||r.dataset.grade===grade)&&
                 (!sector||r.dataset.sector===sector);
    r.style.display=show?'':'none';
    if(show)visible++;
  }});
  document.getElementById('count-label').textContent=`${{visible}} نماد`;
}}

function resetFilters(){{
  document.getElementById('search').value='';
  document.getElementById('f-label').value='';
  document.getElementById('f-grade').value='';
  document.getElementById('f-sector').value='';
  applyFilters();
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
}}

// --- Sort ---
let sortCol=-1,sortDir=1;
function sortTable(col){{
  const tbody=document.getElementById('table-body');
  const rows=[...tbody.querySelectorAll('tr')];
  if(sortCol===col)sortDir*=-1; else{{sortCol=col;sortDir=1;}};
  document.querySelectorAll('thead th').forEach((th,i)=>{{
    th.classList.remove('sort-asc','sort-desc');
    if(i===col)th.classList.add(sortDir===1?'sort-asc':'sort-desc');
  }});
  rows.sort((a,b)=>{{
    const av=a.cells[col]?.textContent.trim()||'';
    const bv=b.cells[col]?.textContent.trim()||'';
    const an=parseFloat(av),bn=parseFloat(bv);
    if(!isNaN(an)&&!isNaN(bn))return(an-bn)*sortDir;
    return av.localeCompare(bv,'fa')*sortDir;
  }});
  rows.forEach(r=>tbody.appendChild(r));
}}

// Init count
applyFilters();
</script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[dashboard] Generated {out_path}")


if __name__ == "__main__":
    generate()