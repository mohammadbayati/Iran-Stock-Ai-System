"""
Generates a professional static HTML dashboard from decision_report.csv.
Output: docs/index.html — served via GitHub Pages.
"""

import os
import pandas as pd
from datetime import datetime
import json

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

LABEL_ROW_BG = {
    "Entry Candidate": "rgba(34,197,94,0.07)",
    "Technical Entry Watch": "rgba(234,179,8,0.07)",
    "Wait for Pullback": "rgba(249,115,22,0.05)",
    "Avoid Entry Now - Overbought": "rgba(239,68,68,0.07)",
    "Watch - Needs Volume Confirmation": "rgba(59,130,246,0.05)",
    "Watch Only": "transparent",
    "Missing Technical Data": "transparent",
}

GRADE_COLOR = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}

CANDLE_FA = {
    "hammer": "🔨 چکش",
    "inverted_hammer": "🔨 چکش معکوس",
    "bullish_engulfing": "🟢 پوشش صعودی",
    "bearish_engulfing": "🔴 پوشش نزولی",
    "morning_star": "⭐ ستاره صبح",
    "doji": "〰️ دوجی",
}


def _fmt(val, suffix="", decimals=1):
    if val is None:
        return "—"
    try:
        if pd.isna(val):
            return "—"
        return f"{float(val):.{decimals}f}{suffix}"
    except Exception:
        return str(val)


def _safe_str(val):
    if val is None:
        return ""
    s = str(val)
    return "" if s in ("nan", "none", "None", "") else s


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

    total = len(df)
    entry_count = len(df[df["decision_label"] == "Entry Candidate"])
    watch_count = len(df[df["decision_label"] == "Technical Entry Watch"])
    avoid_count = len(df[df["decision_label"] == "Avoid Entry Now - Overbought"])
    missing_count = len(df[df["missing"].astype(str).str.lower() == "true"])
    high_conf = len(df[df["confidence_score"] >= 70]) if "confidence_score" in df.columns else 0

    # --- Donut data ---
    donut_data = []
    for label, fa in LABEL_FA.items():
        cnt = len(df[df["decision_label"] == label])
        if cnt > 0:
            donut_data.append({"label": fa, "count": cnt, "color": LABEL_COLOR.get(label, "#6b7280")})
    donut_json = json.dumps(donut_data, ensure_ascii=False)

    # --- Sector heatmap ---
    sector_html = ""
    if "sector" in df.columns:
        sectors = df.groupby("sector").agg(
            avg_score=("confidence_score", "mean"),
            sector_status=("sector_status", "first")
        ).reset_index()
        for _, row in sectors.iterrows():
            status = _safe_str(row.get("sector_status"))
            if "پیشرو" in status:
                bg, border, dot = "#14532d", "#22c55e", "🟢"
            elif "عقب" in status:
                bg, border, dot = "#450a0a", "#ef4444", "🔴"
            else:
                bg, border, dot = "#1e293b", "#475569", "🟡"
            avg = row.get("avg_score", 0)
            sector_html += f'<div class="sector-chip" style="background:{bg};border:1px solid {border}">{dot} {row["sector"]} <span class="sector-score">{avg:.0f}</span></div>'

    # --- All rows data for popup + table ---
    df_sorted = df.sort_values("confidence_score", ascending=False) if "confidence_score" in df.columns else df

    # Build JS data array for popup
    js_rows = []
    table_rows = ""

    for idx, row in df_sorted.iterrows():
        label = str(row.get("decision_label", ""))
        color = LABEL_COLOR.get(label, "#6b7280")
        row_bg = LABEL_ROW_BG.get(label, "transparent")
        label_fa = LABEL_FA.get(label, label)
        grade = str(row.get("grade", row.get("confidence_grade", "")))
        grade_color = GRADE_COLOR.get(grade, "#6b7280")
        score = row.get("confidence_score", 0)
        missing = str(row.get("missing", "True")).lower() == "true"

        symbol = str(row.get("symbol", ""))
        rsi = _fmt(row.get("rsi"))
        trend = _fmt(row.get("trend_score"), decimals=0)
        vol = _fmt(row.get("volume_ratio_20"))
        ret5 = _fmt(row.get("return_5d_percent"), suffix="%")
        sl = _fmt(row.get("stop_loss"), decimals=0)
        tgt = _fmt(row.get("target_1"), decimals=0)
        rr = _fmt(row.get("risk_reward"))
        sector = _safe_str(row.get("sector")) or "—"
        sm = _safe_str(row.get("smart_money_fa"))
        queue = _safe_str(row.get("queue_fa"))
        candle = _safe_str(row.get("candle_pattern"))
        candle_fa = CANDLE_FA.get(candle, candle)
        macd = _safe_str(row.get("macd_crossover"))
        w_trend = _safe_str(row.get("weekly_trend"))
        w_rsi = _fmt(row.get("weekly_rsi"), decimals=0)
        factors = _safe_str(row.get("confidence_factors"))
        reasons = _safe_str(row.get("decision_reasons"))
        atr = _fmt(row.get("atr"), decimals=0)
        poc = _safe_str(row.get("poc_position"))
        rsi_status = _safe_str(row.get("rsi_status"))

        badges = ""
        if macd == "bullish":
            badges += '<span class="badge g">MACD↑</span>'
        elif macd == "bearish":
            badges += '<span class="badge r">MACD↓</span>'
        if w_trend == "up":
            badges += f'<span class="badge g">W↑{w_rsi}</span>'
        elif w_trend == "down":
            badges += f'<span class="badge r">W↓{w_rsi}</span>'
        if candle and candle not in ("nan", "none"):
            badges += '<span class="badge y">🕯</span>'

        row_id = f"row_{idx}"

        # JS popup data
        popup = {
            "symbol": symbol,
            "label_fa": label_fa,
            "color": color,
            "grade": grade,
            "grade_color": grade_color,
            "score": int(score) if score else 0,
            "rsi": rsi,
            "rsi_status": rsi_status,
            "trend": trend,
            "vol": vol,
            "ret5": ret5,
            "sl": sl,
            "tgt": tgt,
            "rr": rr,
            "atr": atr,
            "sector": sector,
            "sm": sm,
            "queue": queue,
            "candle": candle_fa if candle else "",
            "macd": macd,
            "w_trend": w_trend,
            "w_rsi": w_rsi,
            "poc": poc,
            "factors": factors,
            "reasons": reasons,
            "missing": missing,
        }
        js_rows.append(f'"{row_id}": {json.dumps(popup, ensure_ascii=False)}')

        table_rows += f'''
        <tr data-label="{label}" data-sector="{sector}" data-grade="{grade}" data-score="{score}"
            style="background:{row_bg};cursor:pointer" onclick="showPopup('{row_id}')">
            <td><strong class="sym">{symbol}</strong></td>
            <td><span style="color:{color}">●</span> {label_fa}</td>
            <td><span class="grade-tag" style="background:{grade_color}">{grade}</span> {int(score) if score else 0}</td>
            <td>{rsi}</td>
            <td>{trend}/6</td>
            <td>{vol}x</td>
            <td>{ret5}</td>
            <td>{sl}</td>
            <td>{tgt}</td>
            <td>{rr}</td>
            <td>{sector}</td>
            <td>{badges}</td>
        </tr>'''

    js_data = "{" + ",\n".join(js_rows) + "}"
    mood_html = market_header.replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Iran Stock AI Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Tahoma,Arial,sans-serif;background:#0a0f1e;color:#e2e8f0;direction:rtl;font-size:13px}}
.topbar{{background:linear-gradient(135deg,#0f172a,#1e293b);padding:14px 24px;border-bottom:1px solid #1e3a5f;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.topbar h1{{font-size:1.1rem;color:#38bdf8;font-weight:bold}}
.time{{color:#64748b;font-size:0.78rem}}
.pulse{{display:inline-block;width:8px;height:8px;background:#22c55e;border-radius:50%;margin-left:6px;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
.stats{{display:flex;gap:10px;padding:14px 24px;flex-wrap:wrap}}
.stat-card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:10px 18px;min-width:110px;text-align:center}}
.stat-card .val{{font-size:1.5rem;font-weight:bold;line-height:1}}
.stat-card .lbl{{font-size:0.7rem;color:#64748b;margin-top:3px}}
.widgets{{display:flex;gap:14px;padding:0 24px 14px;flex-wrap:wrap;align-items:flex-start}}
.widget-box{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px}}
.widget-title{{font-size:0.78rem;color:#94a3b8;margin-bottom:10px}}
.sector-wrap{{padding:0 24px 14px}}
.sector-title{{font-size:0.78rem;color:#94a3b8;margin-bottom:8px}}
.sector-chips{{display:flex;gap:8px;flex-wrap:wrap}}
.sector-chip{{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:0.75rem}}
.sector-score{{font-weight:bold;color:#38bdf8}}
.mood-box{{background:#0f172a;border:1px solid #1e3a5f;border-radius:8px;padding:12px 16px;font-size:0.75rem;line-height:2;color:#94a3b8;margin:0 24px 14px;max-height:160px;overflow-y:auto}}
.filter-bar{{padding:8px 24px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;background:#0f172a;border-top:1px solid #1e293b;border-bottom:1px solid #1e293b}}
.filter-bar input{{background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:6px 12px;border-radius:6px;font-size:0.78rem;width:150px}}
.filter-bar input::placeholder{{color:#475569}}
.filter-bar select{{background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:6px 10px;border-radius:6px;font-size:0.78rem}}
.filter-btn{{padding:5px 14px;border-radius:16px;border:1px solid #334155;background:transparent;color:#94a3b8;cursor:pointer;font-size:0.75rem;font-family:Tahoma}}
.filter-btn:hover{{background:#38bdf8;color:#0a0f1e;border-color:#38bdf8}}
.export-btn{{padding:5px 14px;border-radius:16px;border:1px solid #22c55e;background:transparent;color:#22c55e;cursor:pointer;font-size:0.75rem;font-family:Tahoma;margin-right:auto}}
.export-btn:hover{{background:#22c55e;color:#0a0f1e}}
.table-wrap{{padding:0 24px 32px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:0.78rem}}
thead th{{background:#0f172a;color:#64748b;padding:9px 8px;text-align:right;border-bottom:2px solid #1e293b;cursor:pointer;white-space:nowrap;user-select:none}}
thead th:hover{{color:#38bdf8}}
thead th.sort-asc::after{{content:" ↑"}}
thead th.sort-desc::after{{content:" ↓"}}
tbody tr{{border-bottom:1px solid #111827;transition:filter 0.15s}}
tbody tr:hover{{filter:brightness(1.3)}}
tbody td{{padding:8px 8px;vertical-align:middle;white-space:nowrap}}
.sym{{color:#f1f5f9;font-size:0.88rem}}
.grade-tag{{padding:1px 7px;border-radius:10px;font-size:0.7rem;color:#0a0f1e;font-weight:bold}}
.badge{{padding:1px 5px;border-radius:8px;font-size:0.65rem;font-weight:bold;margin-left:2px}}
.badge.g{{background:#14532d;color:#86efac}}
.badge.r{{background:#450a0a;color:#fca5a5}}
.badge.y{{background:#422006;color:#fde68a}}

/* Popup */
.overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:100;align-items:center;justify-content:center}}
.overlay.open{{display:flex}}
.popup{{background:#1e293b;border:1px solid #334155;border-radius:14px;padding:24px;width:90%;max-width:520px;max-height:85vh;overflow-y:auto;position:relative;direction:rtl}}
.popup-close{{position:absolute;top:14px;left:14px;background:transparent;border:none;color:#64748b;font-size:1.2rem;cursor:pointer}}
.popup-close:hover{{color:#ef4444}}
.popup-header{{display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #334155}}
.popup-sym{{font-size:1.5rem;font-weight:bold;color:#f1f5f9}}
.popup-label{{font-size:0.82rem;font-weight:bold}}
.popup-grade{{padding:3px 10px;border-radius:10px;font-size:0.78rem;color:#0a0f1e;font-weight:bold}}
.popup-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}}
.popup-item{{background:#0f172a;border-radius:6px;padding:8px 12px}}
.popup-item .pi-label{{font-size:0.68rem;color:#64748b;margin-bottom:2px}}
.popup-item .pi-val{{font-size:0.88rem;color:#e2e8f0;font-weight:bold}}
.popup-section{{margin-bottom:10px}}
.popup-section-title{{font-size:0.72rem;color:#64748b;margin-bottom:4px;text-transform:uppercase}}
.popup-text{{font-size:0.78rem;color:#94a3b8;line-height:1.7;background:#0f172a;border-radius:6px;padding:8px 12px}}

::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:#0a0f1e}}
::-webkit-scrollbar-thumb{{background:#334155;border-radius:3px}}
</style>
</head>
<body>

<div class="topbar">
  <div style="display:flex;align-items:center;gap:8px">
    <span class="pulse"></span>
    <span class="topbar h1">📊 Iran Stock AI Dashboard</span>
  </div>
  <div class="time">آخرین آپدیت: {now}</div>
</div>

<div class="stats">
  <div class="stat-card"><div class="val" style="color:#e2e8f0">{total}</div><div class="lbl">کل نمادها</div></div>
  <div class="stat-card"><div class="val" style="color:#22c55e">{entry_count}</div><div class="lbl">کاندید ورود</div></div>
  <div class="stat-card"><div class="val" style="color:#eab308">{watch_count}</div><div class="lbl">واچ تکنیکال</div></div>
  <div class="stat-card"><div class="val" style="color:#ef4444">{avoid_count}</div><div class="lbl">اشباع خرید</div></div>
  <div class="stat-card"><div class="val" style="color:#38bdf8">{high_conf}</div><div class="lbl">امتیاز ۷۰+</div></div>
  <div class="stat-card"><div class="val" style="color:#6b7280">{missing_count}</div><div class="lbl">فاقد داده</div></div>
</div>

<div class="widgets">
  <div class="widget-box">
    <div class="widget-title">توزیع سیگنال‌ها</div>
    <canvas id="donut" width="170" height="170"></canvas>
    <div id="donut-legend" style="margin-top:8px;font-size:0.7rem"></div>
  </div>
  <div class="widget-box" style="text-align:center">
    <div class="widget-title">میانگین امتیاز بازار</div>
    <canvas id="gauge" width="170" height="105"></canvas>
    <div id="gauge-val" style="font-size:1.6rem;font-weight:bold;color:#38bdf8;margin-top:2px"></div>
    <div style="font-size:0.68rem;color:#64748b">از ۱۰۰</div>
  </div>
  <div class="widget-box" style="flex:1;min-width:240px">
    <div class="widget-title">وضعیت بازار</div>
    <div style="font-size:0.72rem;line-height:2;color:#94a3b8;max-height:180px;overflow-y:auto">{mood_html}</div>
  </div>
</div>

<div class="sector-wrap">
  <div class="sector-title">🗺 هیتمپ سکتورها</div>
  <div class="sector-chips">{sector_html}</div>
</div>

<div class="filter-bar">
  <input type="text" id="search" placeholder="🔍 جستجوی نماد..." oninput="applyFilters()">
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
  <button class="filter-btn" onclick="resetFilters()">ریست</button>
  <button class="export-btn" onclick="exportExcel()">⬇ Excel</button>
  <span id="count-label" style="color:#64748b;font-size:0.75rem"></span>
</div>

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
    <th onclick="sortTable(6)">بازده۵ر</th>
    <th onclick="sortTable(7)">حد ضرر</th>
    <th onclick="sortTable(8)">هدف</th>
    <th onclick="sortTable(9)">R/R</th>
    <th onclick="sortTable(10)">سکتور</th>
    <th>نشانه‌ها</th>
  </tr>
</thead>
<tbody id="table-body">
{table_rows}
</tbody>
</table>
</div>

<!-- Popup overlay -->
<div class="overlay" id="overlay" onclick="closePopup(event)">
  <div class="popup" id="popup">
    <button class="popup-close" onclick="closePopupBtn()">✕</button>
    <div id="popup-content"></div>
  </div>
</div>

<script>
const DATA = {js_data};
const donutData = {donut_json};

// --- Donut ---
(function(){{
  const c=document.getElementById('donut'),ctx=c.getContext('2d');
  const total=donutData.reduce((s,d)=>s+d.count,0);
  let angle=-Math.PI/2;
  const cx=85,cy=85,r=65,ir=42;
  donutData.forEach(d=>{{
    const sl=(d.count/total)*Math.PI*2;
    ctx.beginPath();ctx.moveTo(cx,cy);ctx.arc(cx,cy,r,angle,angle+sl);
    ctx.closePath();ctx.fillStyle=d.color;ctx.fill();angle+=sl;
  }});
  ctx.beginPath();ctx.arc(cx,cy,ir,0,Math.PI*2);ctx.fillStyle='#1e293b';ctx.fill();
  ctx.fillStyle='#e2e8f0';ctx.font='bold 13px Tahoma';ctx.textAlign='center';ctx.textBaseline='middle';
  ctx.fillText(total,cx,cy);
  const leg=document.getElementById('donut-legend');
  donutData.forEach(d=>{{
    leg.innerHTML+=`<div style="display:flex;align-items:center;gap:5px;margin-bottom:2px">
      <span style="width:8px;height:8px;background:${{d.color}};border-radius:2px;flex-shrink:0;display:inline-block"></span>
      <span style="color:#94a3b8">${{d.label}}: ${{d.count}}</span></div>`;
  }});
}})();

// --- Gauge ---
(function(){{
  const c=document.getElementById('gauge'),ctx=c.getContext('2d');
  const rows=[...document.querySelectorAll('#table-body tr')];
  const scores=rows.map(r=>parseFloat(r.dataset.score)||0);
  const avg=scores.length?scores.reduce((a,b)=>a+b,0)/scores.length:0;
  document.getElementById('gauge-val').textContent=avg.toFixed(0);
  const cx=85,cy=95,r=70;
  ctx.beginPath();ctx.arc(cx,cy,r,Math.PI,2*Math.PI);ctx.strokeStyle='#1e3a5f';ctx.lineWidth=12;ctx.stroke();
  const color=avg>=70?'#22c55e':avg>=50?'#eab308':'#ef4444';
  const pct=Math.min(avg/100,1);
  ctx.beginPath();ctx.arc(cx,cy,r,Math.PI,Math.PI+pct*Math.PI);
  ctx.strokeStyle=color;ctx.lineWidth=12;ctx.lineCap='round';ctx.stroke();
}})();

// --- Sector select ---
(function(){{
  const sel=document.getElementById('f-sector');
  const secs=[...new Set([...document.querySelectorAll('#table-body tr')].map(r=>r.dataset.sector))].filter(Boolean).sort();
  secs.forEach(s=>{{const o=document.createElement('option');o.value=s;o.textContent=s;sel.appendChild(o);}});
}})();

// --- Filters ---
function applyFilters(){{
  const s=document.getElementById('search').value.trim().toLowerCase();
  const l=document.getElementById('f-label').value;
  const g=document.getElementById('f-grade').value;
  const sec=document.getElementById('f-sector').value;
  let v=0;
  document.querySelectorAll('#table-body tr').forEach(r=>{{
    const sym=r.querySelector('.sym')?.textContent.toLowerCase()||'';
    const show=(!s||sym.includes(s))&&(!l||r.dataset.label===l)&&(!g||r.dataset.grade===g)&&(!sec||r.dataset.sector===sec);
    r.style.display=show?'':'none';
    if(show)v++;
  }});
  document.getElementById('count-label').textContent=v+' نماد';
}}

function resetFilters(){{
  ['search','f-label','f-grade','f-sector'].forEach(id=>{{const el=document.getElementById(id);if(el.tagName==='INPUT')el.value='';else el.selectedIndex=0;}});
  applyFilters();
}}

// --- Sort ---
let sc=-1,sd=1;
function sortTable(col){{
  const tbody=document.getElementById('table-body');
  const rows=[...tbody.querySelectorAll('tr')];
  if(sc===col)sd*=-1;else{{sc=col;sd=1;}};
  document.querySelectorAll('thead th').forEach((th,i)=>{{th.classList.remove('sort-asc','sort-desc');if(i===col)th.classList.add(sd===1?'sort-asc':'sort-desc');}});
  rows.sort((a,b)=>{{
    const av=a.cells[col]?.textContent.trim()||'',bv=b.cells[col]?.textContent.trim()||'';
    const an=parseFloat(av),bn=parseFloat(bv);
    return(!isNaN(an)&&!isNaN(bn))?(an-bn)*sd:av.localeCompare(bv,'fa')*sd;
  }});
  rows.forEach(r=>tbody.appendChild(r));
}}

// --- Popup ---
function showPopup(id){{
  const d=DATA[id];if(!d)return;
  const c=document.getElementById('popup-content');
  const macdBadge=d.macd==='bullish'?'<span class="badge g">MACD↑</span>':d.macd==='bearish'?'<span class="badge r">MACD↓</span>':'';
  const wBadge=d.w_trend==='up'?`<span class="badge g">هفتگی↑ ${{d.w_rsi}}</span>`:d.w_trend==='down'?`<span class="badge r">هفتگی↓ ${{d.w_rsi}}</span>`:'';
  const candleBadge=d.candle?`<span class="badge y">🕯 ${{d.candle}}</span>`:'';
  const pocBadge=d.poc?`<span class="badge g" style="background:#1e3a5f;color:#38bdf8">POC: ${{d.poc}}</span>`:'';

  c.innerHTML=`
    <div class="popup-header">
      <div>
        <div class="popup-sym">${{d.symbol}}</div>
        <div class="popup-label" style="color:${{d.color}}">${{d.label_fa}}</div>
      </div>
      <div style="margin-right:auto">
        <span class="popup-grade" style="background:${{d.grade_color}}">درجه ${{d.grade}}</span>
        <div style="font-size:1.4rem;font-weight:bold;color:${{d.color}};text-align:center;margin-top:4px">${{d.score}}</div>
      </div>
    </div>

    ${{d.missing?'<div style="color:#64748b;text-align:center;padding:20px">داده تکنیکال موجود نیست</div>':`
    <div class="popup-grid">
      <div class="popup-item"><div class="pi-label">RSI</div><div class="pi-val">${{d.rsi}} <small style="color:#64748b;font-size:0.7rem">${{d.rsi_status}}</small></div></div>
      <div class="popup-item"><div class="pi-label">روند</div><div class="pi-val">${{d.trend}}/6</div></div>
      <div class="popup-item"><div class="pi-label">حجم نسبی</div><div class="pi-val">${{d.vol}}x</div></div>
      <div class="popup-item"><div class="pi-label">بازده ۵ روزه</div><div class="pi-val">${{d.ret5}}</div></div>
      <div class="popup-item"><div class="pi-label">🛑 حد ضرر</div><div class="pi-val" style="color:#ef4444">${{d.sl}}</div></div>
      <div class="popup-item"><div class="pi-label">🎯 هدف</div><div class="pi-val" style="color:#22c55e">${{d.tgt}}</div></div>
      <div class="popup-item"><div class="pi-label">R/R</div><div class="pi-val">${{d.rr}}</div></div>
      <div class="popup-item"><div class="pi-label">ATR</div><div class="pi-val">${{d.atr}}</div></div>
    </div>

    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
      ${{macdBadge}}${{wBadge}}${{candleBadge}}${{pocBadge}}
    </div>

    ${{d.sm?`<div class="popup-section"><div class="popup-section-title">🧠 پول هوشمند</div><div class="popup-text">${{d.sm}}</div></div>`:''}}
    ${{d.queue?`<div class="popup-section"><div class="popup-section-title">📋 تحلیل صف</div><div class="popup-text">${{d.queue}}</div></div>`:''}}
    ${{d.factors?`<div class="popup-section"><div class="popup-section-title">💡 عوامل امتیاز</div><div class="popup-text">${{d.factors}}</div></div>`:''}}
    ${{d.reasons?`<div class="popup-section"><div class="popup-section-title">💬 دلایل تصمیم</div><div class="popup-text">${{d.reasons}}</div></div>`:''}}
    <div class="popup-section"><div class="popup-section-title">🏭 سکتور</div><div class="popup-text">${{d.sector}}</div></div>
    `}}
  `;
  document.getElementById('overlay').classList.add('open');
}}

function closePopup(e){{if(e.target===document.getElementById('overlay'))closePopupBtn();}}
function closePopupBtn(){{document.getElementById('overlay').classList.remove('open');}}
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closePopupBtn();}});

// --- Export Excel ---
function exportExcel(){{
  const rows=[...document.querySelectorAll('#table-body tr')].filter(r=>r.style.display!=='none');
  const headers=['نماد','سیگنال','امتیاز','RSI','روند','حجم','بازده۵روز','حد ضرر','هدف','R/R','سکتور'];
  let csv='\uFEFF'+headers.join(',')+'\n';
  rows.forEach(r=>{{
    const cells=[...r.cells].slice(0,11).map(c=>'"'+(c.textContent.trim().replace(/"/g,'""'))+'"');
    csv+=cells.join(',')+'\n';
  }});
  const blob=new Blob([csv],{{type:'text/csv;charset=utf-8'}});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='iran_stock_signals.csv';
  a.click();
}}

// Init
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