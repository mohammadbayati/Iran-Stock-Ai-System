"""
Generates a static HTML dashboard from decision_report.csv.
Output: docs/index.html — served via GitHub Pages.
"""

import sys
import os
import pandas as pd
from datetime import datetime

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
    "Watch Only": "#9ca3af",
    "Missing Technical Data": "#4b5563",
}

GRADE_COLOR = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}

ORDER = [
    "Entry Candidate", "Technical Entry Watch", "Wait for Pullback",
    "Watch - Needs Volume Confirmation", "Watch Only",
    "Avoid Entry Now - Overbought", "Missing Technical Data",
]


def _fmt(val, suffix="", decimals=1):
    if val is None:
        return "—"
    try:
        if pd.isna(val):
            return "—"
        return f"{float(val):.{decimals}f}{suffix}"
    except Exception:
        return str(val)


def _row_html(row) -> str:
    label = str(row.get("decision_label", ""))
    color = LABEL_COLOR.get(label, "#9ca3af")
    label_fa = LABEL_FA.get(label, label)
    grade = str(row.get("confidence_grade", ""))
    grade_color = GRADE_COLOR.get(grade, "#9ca3af")
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
    sm = str(row.get("smart_money_fa", "—"))
    candle = str(row.get("candle_pattern", ""))
    macd = str(row.get("macd_crossover", ""))
    w_trend = str(row.get("weekly_trend", ""))
    w_rsi = _fmt(row.get("weekly_rsi"), decimals=0)
    factors = str(row.get("confidence_factors", ""))
    reasons = str(row.get("decision_reasons", ""))

    macd_badge = ""
    if macd == "bullish":
        macd_badge = '<span class="badge green">MACD↑</span>'
    elif macd == "bearish":
        macd_badge = '<span class="badge red">MACD↓</span>'

    wt_badge = ""
    if w_trend == "up":
        wt_badge = f'<span class="badge green">هفتگی↑ {w_rsi}</span>'
    elif w_trend == "down":
        wt_badge = f'<span class="badge red">هفتگی↓ {w_rsi}</span>'

    candle_badge = ""
    if candle and candle not in ("nan", "none", ""):
        candle_badge = f'<span class="badge yellow">🕯 {candle}</span>'

    data_rows = "" if missing else f"""
        <div class="data-grid">
            <div class="data-item"><span class="label">RSI</span><span>{rsi}</span></div>
            <div class="data-item"><span class="label">روند</span><span>{trend}/6</span></div>
            <div class="data-item"><span class="label">حجم</span><span>{vol}x</span></div>
            <div class="data-item"><span class="label">بازده ۵روزه</span><span>{ret5}</span></div>
            <div class="data-item"><span class="label">حد ضرر</span><span>{sl}</span></div>
            <div class="data-item"><span class="label">هدف</span><span>{tgt}</span></div>
            <div class="data-item"><span class="label">R/R</span><span>{rr}</span></div>
            <div class="data-item"><span class="label">سکتور</span><span>{sector}</span></div>
        </div>
        <div class="badges">{macd_badge}{wt_badge}{candle_badge}</div>
        <div class="smart-money">{sm if sm not in ("nan","—","") else ""}</div>
        <div class="factors">{factors if factors not in ("nan","") else ""}</div>
    """

    return f"""
    <div class="card" data-label="{label}" data-score="{score}">
        <div class="card-header">
            <div class="symbol-name">{row.get("symbol", "?")}</div>
            <div class="grade-badge" style="background:{grade_color}">درجه {grade}</div>
            <div class="score-badge" style="border-color:{color}">{score}</div>
        </div>
        <div class="decision-label" style="color:{color}">● {label_fa}</div>
        {data_rows}
        <div class="reasons">{reasons if reasons not in ("nan","") else ""}</div>
    </div>
    """


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
            market_header = f.read().replace("\n", "<br>")

    entry_count = len(df[df["decision_label"] == "Entry Candidate"])
    missing_count = len(df[df["missing"].astype(str).str.lower() == "true"])
    high_conf = len(df[df["confidence_score"] >= 70]) if "confidence_score" in df.columns else 0

    cards_html = ""
    for label in ORDER:
        group = df[df["decision_label"] == label]
        if group.empty:
            continue
        group = group.sort_values("confidence_score", ascending=False)
        color = LABEL_COLOR.get(label, "#9ca3af")
        label_fa = LABEL_FA.get(label, label)
        cards_html += f'<div class="section-header" style="border-color:{color}">● {label_fa} ({len(group)} نماد)</div>'
        cards_html += '<div class="cards-grid">'
        for _, row in group.iterrows():
            cards_html += _row_html(row)
        cards_html += "</div>"

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Iran Stock AI Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Tahoma, Arial, sans-serif; background: #0f172a; color: #e2e8f0; direction: rtl; }}
  .header {{ background: #1e293b; padding: 20px; border-bottom: 2px solid #334155; }}
  .header h1 {{ font-size: 1.4rem; color: #38bdf8; margin-bottom: 8px; }}
  .header .time {{ font-size: 0.8rem; color: #64748b; }}
  .stats {{ display: flex; gap: 16px; margin-top: 12px; flex-wrap: wrap; }}
  .stat {{ background: #0f172a; padding: 8px 16px; border-radius: 8px; font-size: 0.85rem; }}
  .stat span {{ color: #38bdf8; font-weight: bold; }}
  .market-mood {{ background: #1e293b; padding: 16px 20px; border-right: 3px solid #38bdf8; margin: 16px; border-radius: 8px; font-size: 0.85rem; line-height: 1.8; }}
  .section-header {{ font-size: 1rem; font-weight: bold; padding: 12px 20px; margin: 20px 16px 8px; border-right: 4px solid; border-radius: 4px; background: #1e293b; }}
  .cards-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; padding: 0 16px 16px; }}
  .card {{ background: #1e293b; border-radius: 10px; padding: 14px; border: 1px solid #334155; transition: border-color 0.2s; }}
  .card:hover {{ border-color: #38bdf8; }}
  .card-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
  .symbol-name {{ font-size: 1.1rem; font-weight: bold; color: #f1f5f9; flex: 1; }}
  .grade-badge {{ padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; color: #0f172a; font-weight: bold; }}
  .score-badge {{ padding: 2px 10px; border-radius: 12px; font-size: 0.85rem; border: 2px solid; font-weight: bold; }}
  .decision-label {{ font-size: 0.85rem; margin-bottom: 10px; font-weight: bold; }}
  .data-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-bottom: 8px; }}
  .data-item {{ display: flex; justify-content: space-between; font-size: 0.78rem; padding: 3px 6px; background: #0f172a; border-radius: 4px; }}
  .data-item .label {{ color: #64748b; }}
  .badges {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }}
  .badge {{ padding: 2px 8px; border-radius: 10px; font-size: 0.72rem; font-weight: bold; }}
  .badge.green {{ background: #14532d; color: #86efac; }}
  .badge.red {{ background: #450a0a; color: #fca5a5; }}
  .badge.yellow {{ background: #422006; color: #fde68a; }}
  .smart-money {{ font-size: 0.78rem; color: #94a3b8; margin-bottom: 4px; }}
  .factors {{ font-size: 0.72rem; color: #475569; margin-bottom: 4px; line-height: 1.5; }}
  .reasons {{ font-size: 0.75rem; color: #64748b; border-top: 1px solid #334155; padding-top: 6px; margin-top: 4px; }}
  .filter-bar {{ padding: 12px 16px; display: flex; gap: 8px; flex-wrap: wrap; background: #1e293b; }}
  .filter-btn {{ padding: 6px 14px; border-radius: 20px; border: 1px solid #334155; background: transparent; color: #94a3b8; cursor: pointer; font-size: 0.8rem; }}
  .filter-btn.active, .filter-btn:hover {{ background: #38bdf8; color: #0f172a; border-color: #38bdf8; }}
</style>
</head>
<body>
<div class="header">
  <h1>📊 Iran Stock AI Dashboard</h1>
  <div class="time">آخرین بروزرسانی: {now}</div>
  <div class="stats">
    <div class="stat">کل نمادها: <span>{len(df)}</span></div>
    <div class="stat">کاندید ورود: <span>{entry_count}</span></div>
    <div class="stat">امتیاز بالا: <span>{high_conf}</span></div>
    <div class="stat">فاقد داده: <span>{missing_count}</span></div>
  </div>
</div>
<div class="market-mood">{market_header}</div>
<div class="filter-bar">
  <button class="filter-btn active" onclick="filterCards('all')">همه</button>
  <button class="filter-btn" onclick="filterCards('Entry Candidate')">کاندید ورود</button>
  <button class="filter-btn" onclick="filterCards('Technical Entry Watch')">واچ تکنیکال</button>
  <button class="filter-btn" onclick="filterCards('Avoid Entry Now - Overbought')">اشباع خرید</button>
</div>
{cards_html}
<script>
function filterCards(label) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.card').forEach(c => {{
    c.style.display = (label === 'all' || c.dataset.label === label) ? '' : 'none';
  }});
}}
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