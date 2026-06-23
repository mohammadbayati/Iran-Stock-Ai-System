"""
Generate docs/index.html from output/decision_report.csv
Dashboard Level 2: sparkline charts + status change column + auto-refresh
"""

import os
import csv
import json
from datetime import datetime

INPUT_CSV = os.path.join("output", "decision_report.csv")
SIGNAL_LOG = os.path.join("output", "signal_log.csv")
OUTPUT_HTML = os.path.join("docs", "index.html")


def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_prev_labels(rows):
    """Return dict of symbol -> previous label from signal_log (second-to-last entry per symbol)."""
    prev = {}
    if not os.path.exists(SIGNAL_LOG):
        return prev
    by_symbol = {}
    with open(SIGNAL_LOG, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = row.get("symbol", "")
            if sym:
                by_symbol.setdefault(sym, []).append(row.get("label", ""))
    for sym, labels in by_symbol.items():
        if len(labels) >= 2:
            prev[sym] = labels[-2]
    return prev


def label_color(label):
    colors = {
        "ورود قوی": "#16a34a",
        "ورود": "#22c55e",
        "تماشا": "#ca8a04",
        "خروج": "#dc2626",
        "نگهداری": "#2563eb",
    }
    for key, col in colors.items():
        if key in str(label):
            return col
    return "#6b7280"


def label_bg(label):
    bgs = {
        "ورود قوی": "rgba(22,163,74,0.12)",
        "ورود": "rgba(34,197,94,0.10)",
        "تماشا": "rgba(202,138,4,0.10)",
        "خروج": "rgba(220,38,38,0.10)",
        "نگهداری": "rgba(37,99,235,0.10)",
    }
    for key, bg in bgs.items():
        if key in str(label):
            return bg
    return "transparent"


def build_html(rows, prev_labels):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    label_counts = {}
    for r in rows:
        lbl = r.get("label", "نامشخص")
        label_counts[lbl] = label_counts.get(lbl, 0) + 1

    entry_strong = sum(v for k, v in label_counts.items() if "ورود قوی" in k)
    entry = sum(v for k, v in label_counts.items() if "ورود" in k and "قوی" not in k)
    watch = sum(v for k, v in label_counts.items() if "تماشا" in k)
    exit_ = sum(v for k, v in label_counts.items() if "خروج" in k)
    hold = sum(v for k, v in label_counts.items() if "نگهداری" in k)
    total = len(rows)

    sector_counts = {}
    for r in rows:
        sec = r.get("sector", "سایر") or "سایر"
        sector_counts[sec] = sector_counts.get(sec, 0) + 1

    sector_chips = ""
    sector_options = '<option value="">همه سکتورها</option>'
    for sec, cnt in sorted(sector_counts.items(), key=lambda x: -x[1]):
        sector_chips += f'<span class="chip">{sec} <b>{cnt}</b></span>'
        sector_options += f'<option value="{sec}">{sec} ({cnt})</option>'

    table_rows_html = ""
    for r in rows:
        sym = r.get("symbol", "")
        label = r.get("label", "")
        grade = r.get("grade", "")
        sector = r.get("sector", "سایر") or "سایر"
        confidence = r.get("confidence_score", "")
        rsi = r.get("rsi", "")
        close = r.get("latest_close", "")
        support = r.get("support", "")
        resistance = r.get("resistance", "")
        stop_loss = r.get("stop_loss", "")
        target_1 = r.get("target_1", "")
        rr = r.get("risk_reward", "")
        bp = r.get("buyer_power", "")
        flow = r.get("real_money_flow", "")
        macd_x = r.get("macd_crossover", "")
        candle = r.get("candle_pattern", "")
        bb_sq = r.get("bb_squeeze", "")
        trend = r.get("trend_score", "")
        close_20d = r.get("close_20d", "")

        prev = prev_labels.get(sym, "")
        if prev and prev != label:
            arrow = "⬆️" if "ورود" in label else "⬇️" if "خروج" in label else "↔️"
            change_cell = f'<span title="{prev} → {label}">{arrow}</span>'
        else:
            change_cell = '<span style="color:#9ca3af">—</span>'

        spark_attr = f'data-spark="{close_20d}"' if close_20d else ""
        color = label_color(label)
        bg = label_bg(label)

        try:
            flow_b = float(flow) / 1e9
            flow_str = f"{flow_b:+.1f}B"
        except Exception:
            flow_str = flow or "—"

        popup_data = json.dumps({
            "symbol": sym, "label": label, "grade": grade,
            "sector": sector, "confidence": confidence,
            "rsi": rsi, "close": close, "support": support,
            "resistance": resistance, "stop_loss": stop_loss,
            "target_1": target_1, "rr": rr, "bp": bp,
            "flow": flow_str, "macd_x": macd_x,
            "candle": candle, "bb_sq": bb_sq, "trend": trend,
        }, ensure_ascii=False).replace("'", "&#39;")

        table_rows_html += f"""
<tr style="background:{bg}" data-label="{label}" data-grade="{grade}" data-sector="{sector}"
    onclick="showPopup('{sym}', '{popup_data.replace('"', '&quot;')}')">
  <td><b style="color:{color}">{sym}</b></td>
  <td><span style="color:{color};font-weight:600">{label}</span></td>
  <td>{grade}</td>
  <td>{sector}</td>
  <td>{confidence}</td>
  <td>{rsi}</td>
  <td>{close}</td>
  <td>{flow_str}</td>
  <td>{bp}</td>
  <td>{change_cell}</td>
  <td><canvas class="sparkline" width="80" height="30" {spark_attr}></canvas></td>
</tr>"""

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="900">
<title>داشبورد بازار ایران</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Tahoma, Arial, sans-serif; background: #0f172a; color: #e2e8f0; direction: rtl; }}
  header {{ background: linear-gradient(135deg, #1e3a5f, #0f2940); padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }}
  header h1 {{ font-size: 1.4rem; color: #60a5fa; }}
  header small {{ color: #94a3b8; font-size: 0.8rem; }}
  .top-bar {{ display: flex; gap: 12px; padding: 12px 24px; flex-wrap: wrap; align-items: center; }}
  input#search {{ flex: 1; min-width: 180px; padding: 8px 12px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: #e2e8f0; font-size: 0.9rem; }}
  select {{ padding: 8px 12px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: #e2e8f0; font-size: 0.9rem; cursor: pointer; }}
  .btn {{ padding: 8px 16px; border-radius: 8px; border: none; background: #2563eb; color: #fff; cursor: pointer; font-size: 0.9rem; font-family: Tahoma; }}
  .btn:hover {{ background: #1d4ed8; }}
  .stats {{ display: flex; gap: 10px; padding: 0 24px 12px; flex-wrap: wrap; }}
  .stat-card {{ background: #1e293b; border-radius: 10px; padding: 10px 16px; text-align: center; min-width: 80px; border: 1px solid #334155; }}
  .stat-card .num {{ font-size: 1.5rem; font-weight: bold; }}
  .stat-card .lbl {{ font-size: 0.7rem; color: #94a3b8; }}
  .chips {{ padding: 0 24px 12px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{ background: #1e293b; border: 1px solid #334155; border-radius: 20px; padding: 4px 10px; font-size: 0.75rem; color: #94a3b8; }}
  .table-wrap {{ overflow-x: auto; padding: 0 24px 80px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  thead th {{ background: #1e293b; color: #94a3b8; padding: 10px 8px; text-align: right; cursor: pointer; user-select: none; position: sticky; top: 0; border-bottom: 2px solid #334155; white-space: nowrap; }}
  thead th:hover {{ color: #60a5fa; }}
  tbody tr {{ border-bottom: 1px solid #1e293b; cursor: pointer; transition: filter 0.15s; }}
  tbody tr:hover {{ filter: brightness(1.2); }}
  td {{ padding: 8px 8px; white-space: nowrap; }}
  .popup-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 100; justify-content: center; align-items: center; }}
  .popup-overlay.active {{ display: flex; }}
  .popup {{ background: #1e293b; border-radius: 14px; padding: 24px; max-width: 480px; width: 90%; max-height: 80vh; overflow-y: auto; border: 1px solid #334155; position: relative; }}
  .popup h2 {{ font-size: 1.3rem; margin-bottom: 14px; color: #60a5fa; }}
  .popup-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .popup-item {{ background: #0f172a; border-radius: 8px; padding: 8px 10px; }}
  .popup-item .k {{ font-size: 0.7rem; color: #94a3b8; }}
  .popup-item .v {{ font-size: 0.95rem; font-weight: 600; margin-top: 2px; }}
  .close-btn {{ position: absolute; top: 12px; left: 16px; background: none; border: none; color: #94a3b8; font-size: 1.3rem; cursor: pointer; }}
  .close-btn:hover {{ color: #e2e8f0; }}
  footer {{ position: fixed; bottom: 0; left: 0; right: 0; background: #0f172a; border-top: 1px solid #1e293b; padding: 8px 24px; font-size: 0.75rem; color: #475569; display: flex; justify-content: space-between; }}
  .refresh-badge {{ color: #22c55e; }}
  canvas.sparkline {{ display: block; }}
</style>
</head>
<body>
<header>
  <h1>📈 داشبورد بازار سهام ایران</h1>
  <small>آخرین به‌روزرسانی: {now} | <span class="refresh-badge">🔄 هر ۱۵ دقیقه</span></small>
</header>

<div class="top-bar">
  <input type="text" id="search" placeholder="🔍 جستجوی نماد...">
  <select id="filter-label">
    <option value="">همه تصمیم‌ها</option>
    <option value="ورود قوی">ورود قوی</option>
    <option value="ورود">ورود</option>
    <option value="تماشا">تماشا</option>
    <option value="نگهداری">نگهداری</option>
    <option value="خروج">خروج</option>
  </select>
  <select id="filter-grade">
    <option value="">همه درجات</option>
    <option value="A">A</option>
    <option value="B">B</option>
    <option value="C">C</option>
    <option value="D">D</option>
  </select>
  <select id="filter-sector">{sector_options}</select>
  <button class="btn" onclick="exportCSV()">⬇️ خروجی Excel</button>
</div>

<div class="stats">
  <div class="stat-card"><div class="num" style="color:#16a34a">{entry_strong}</div><div class="lbl">ورود قوی</div></div>
  <div class="stat-card"><div class="num" style="color:#22c55e">{entry}</div><div class="lbl">ورود</div></div>
  <div class="stat-card"><div class="num" style="color:#ca8a04">{watch}</div><div class="lbl">تماشا</div></div>
  <div class="stat-card"><div class="num" style="color:#2563eb">{hold}</div><div class="lbl">نگهداری</div></div>
  <div class="stat-card"><div class="num" style="color:#dc2626">{exit_}</div><div class="lbl">خروج</div></div>
  <div class="stat-card"><div class="num" style="color:#94a3b8">{total}</div><div class="lbl">کل</div></div>
</div>

<div class="chips">{sector_chips}</div>

<div class="table-wrap">
<table id="main-table">
  <thead>
    <tr>
      <th onclick="sortTable(0)">نماد ↕</th>
      <th onclick="sortTable(1)">تصمیم ↕</th>
      <th onclick="sortTable(2)">درجه ↕</th>
      <th onclick="sortTable(3)">سکتور ↕</th>
      <th onclick="sortTable(4)">اطمینان ↕</th>
      <th onclick="sortTable(5)">RSI ↕</th>
      <th onclick="sortTable(6)">قیمت ↕</th>
      <th onclick="sortTable(7)">جریان پول ↕</th>
      <th onclick="sortTable(8)">قدرت خریدار ↕</th>
      <th>تغییر وضعیت</th>
      <th>نمودار ۲۰ روز</th>
    </tr>
  </thead>
  <tbody id="table-body">
    {table_rows_html}
  </tbody>
</table>
</div>

<div class="popup-overlay" id="popup-overlay" onclick="closePopup(event)">
  <div class="popup" id="popup-box">
    <button class="close-btn" onclick="closePopupDirect()">✕</button>
    <h2 id="popup-title"></h2>
    <div class="popup-grid" id="popup-content"></div>
  </div>
</div>

<footer>
  <span>Iran Stock AI Dashboard</span>
  <span id="countdown"></span>
</footer>

<script>
function drawSparkline(canvas, dataStr) {{
  if (!dataStr) return;
  const prices = dataStr.split(',').map(Number).filter(n => !isNaN(n));
  if (prices.length < 2) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const min = Math.min(...prices), max = Math.max(...prices);
  const range = max - min || 1;
  const pts = prices.map((p, i) => [
    (i / (prices.length - 1)) * w,
    h - ((p - min) / range) * (h - 4) - 2
  ]);
  ctx.clearRect(0, 0, w, h);
  const last = prices[prices.length - 1];
  const first = prices[0];
  const lineColor = last >= first ? '#22c55e' : '#ef4444';
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, last >= first ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)');
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.beginPath();
  ctx.moveTo(pts[0][0], h);
  pts.forEach(([x, y]) => ctx.lineTo(x, y));
  ctx.lineTo(pts[pts.length-1][0], h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.beginPath();
  pts.forEach(([x, y], i) => i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y));
  ctx.strokeStyle = lineColor;
  ctx.lineWidth = 1.5;
  ctx.stroke();
  const [lx, ly] = pts[pts.length - 1];
  ctx.beginPath();
  ctx.arc(lx, ly, 2.5, 0, Math.PI * 2);
  ctx.fillStyle = lineColor;
  ctx.fill();
}}

document.querySelectorAll('canvas.sparkline').forEach(c => {{
  drawSparkline(c, c.dataset.spark);
}});

function showPopup(sym, dataStr) {{
  const d = JSON.parse(dataStr);
  document.getElementById('popup-title').textContent = '📌 ' + sym;
  const fields = [
    ['تصمیم', d.label], ['درجه', d.grade], ['سکتور', d.sector],
    ['اطمینان', d.confidence], ['RSI', d.rsi], ['قیمت', d.close],
    ['حمایت', d.support], ['مقاومت', d.resistance],
    ['حد ضرر', d.stop_loss], ['هدف', d.target_1],
    ['R/R', d.rr], ['قدرت خریدار', d.bp],
    ['جریان پول', d.flow], ['MACD', d.macd_x],
    ['کندل', d.candle], ['BB Squeeze', d.bb_sq],
    ['ترند', d.trend],
  ];
  document.getElementById('popup-content').innerHTML = fields.map(([k,v]) =>
    `<div class="popup-item"><div class="k">${{k}}</div><div class="v">${{v || '—'}}</div></div>`
  ).join('');
  document.getElementById('popup-overlay').classList.add('active');
}}
function closePopup(e) {{
  if (e.target === document.getElementById('popup-overlay')) closePopupDirect();
}}
function closePopupDirect() {{
  document.getElementById('popup-overlay').classList.remove('active');
}}

function applyFilters() {{
  const search = document.getElementById('search').value.toLowerCase();
  const label = document.getElementById('filter-label').value;
  const grade = document.getElementById('filter-grade').value;
  const sector = document.getElementById('filter-sector').value;
  document.querySelectorAll('#table-body tr').forEach(tr => {{
    const sym = tr.cells[0]?.textContent.toLowerCase() || '';
    const lbl = tr.dataset.label || '';
    const grd = tr.dataset.grade || '';
    const sec = tr.dataset.sector || '';
    const ok = (!search || sym.includes(search))
      && (!label || lbl.includes(label))
      && (!grade || grd === grade)
      && (!sector || sec === sector);
    tr.style.display = ok ? '' : 'none';
  }});
}}
document.getElementById('search').addEventListener('input', applyFilters);
document.getElementById('filter-label').addEventListener('change', applyFilters);
document.getElementById('filter-grade').addEventListener('change', applyFilters);
document.getElementById('filter-sector').addEventListener('change', applyFilters);

let sortDir = {{}};
function sortTable(col) {{
  const tb = document.getElementById('table-body');
  const rows = Array.from(tb.querySelectorAll('tr'));
  sortDir[col] = !sortDir[col];
  rows.sort((a, b) => {{
    const av = a.cells[col]?.textContent.trim() || '';
    const bv = b.cells[col]?.textContent.trim() || '';
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return sortDir[col] ? an - bn : bn - an;
    return sortDir[col] ? av.localeCompare(bv, 'fa') : bv.localeCompare(av, 'fa');
  }});
  rows.forEach(r => tb.appendChild(r));
}}

function exportCSV() {{
  const rows = Array.from(document.querySelectorAll('#main-table tr'));
  const csv = rows.filter(r => r.style.display !== 'none').map(r =>
    Array.from(r.cells).slice(0, 9).map(c => '"' + c.textContent.trim().replace(/"/g,'""') + '"').join(',')
  ).join('\n');
  const blob = new Blob(['\uFEFF' + csv], {{type: 'text/csv;charset=utf-8;'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'iran-stock-signals.csv';
  a.click();
}}

(function() {{
  const start = Date.now();
  const interval = 900;
  function tick() {{
    const elapsed = Math.floor((Date.now() - start) / 1000);
    const left = interval - (elapsed % interval);
    const m = Math.floor(left / 60), s = left % 60;
    document.getElementById('countdown').textContent =
      'به‌روزرسانی بعدی: ' + m + ':' + String(s).padStart(2,'0');
  }}
  tick();
  setInterval(tick, 1000);
}})();
</script>
</body>
</html>"""


def run():
    rows = load_csv(INPUT_CSV)
    if not rows:
        print("No data to generate dashboard.")
        return
    prev_labels = load_prev_labels(rows)
    html = build_html(rows, prev_labels)
    os.makedirs("docs", exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard generated: {OUTPUT_HTML} ({len(rows)} rows)")


if __name__ == "__main__":
    run()