"""Generate static HTML dashboard from decision_report.csv."""

import os
import sys
import csv
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DECISION_REPORT_CSV, OUTPUT_DIR

SIGNAL_LOG = os.path.join(OUTPUT_DIR, "signal_log.csv")
DASHBOARD_PATH = os.path.join("docs", "index.html")

LABEL_FA = {
    "Entry Candidate": "ورود قوی",
    "Technical Entry Watch": "ورود",
    "Wait for Pullback": "تماشا",
    "Watch - Needs Volume Confirmation": "تماشا",
    "Watch Only": "نگهداری",
    "Avoid Entry Now - Overbought": "خروج",
    "Missing Technical Data": "داده ناقص",
}

def label_fa(label: str) -> str:
    return LABEL_FA.get(label, label)

def label_color(label: str) -> str:
    fa = label_fa(label)
    if fa in ("ورود قوی",): return "#00c853"
    if fa in ("ورود",): return "#69f0ae"
    if fa in ("تماشا",): return "#ffd740"
    if fa in ("نگهداری",): return "#40c4ff"
    if fa in ("خروج",): return "#ff5252"
    return "#9e9e9e"

def label_bg(label: str) -> str:
    fa = label_fa(label)
    if fa in ("ورود قوی",): return "#003300"
    if fa in ("ورود",): return "#003322"
    if fa in ("تماشا",): return "#333300"
    if fa in ("نگهداری",): return "#003344"
    if fa in ("خروج",): return "#330000"
    return "#222"

def grade_color(grade: str) -> str:
    g = grade.upper() if grade else ""
    if g == "A+": return "#00e676"
    if g == "A": return "#69f0ae"
    if g == "B": return "#ffd740"
    if g == "C": return "#ff9100"
    return "#9e9e9e"

def load_prev_labels() -> dict:
    """Load previous decision_label per symbol from signal_log."""
    prev = {}
    if not os.path.exists(SIGNAL_LOG):
        return prev
    with open(SIGNAL_LOG, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = row.get("symbol", "")
            lbl = row.get("decision_label", "")
            dt = row.get("date", "")
            if sym and lbl:
                if sym not in prev or dt > prev[sym]["date"]:
                    prev[sym] = {"label": lbl, "date": dt}
    return {k: v["label"] for k, v in prev.items()}

def build_html(rows: list, generated_at: str) -> str:
    prev_labels = load_prev_labels()

    table_rows = ""
    for r in rows:
        sym = r.get("symbol", "")
        label = r.get("decision_label", "")
        grade = r.get("confidence_grade", "")
        score = r.get("confidence_score", "")
        sector = r.get("sector", "")
        rsi = r.get("rsi", "")
        price = r.get("latest_close", "")
        sm = r.get("smart_money_signal", "")
        q = r.get("queue_signal", "")
        reasons = r.get("decision_reasons", "")
        close_20d = r.get("close_20d", "")
        factors = r.get("confidence_factors", "")

        # Status change
        prev = prev_labels.get(sym, "")
        if prev and prev != label:
            prev_fa = label_fa(prev)
            cur_fa = label_fa(label)
            change_icon = "⬆️" if label in ("Entry Candidate", "Technical Entry Watch") and prev not in ("Entry Candidate", "Technical Entry Watch") else "⬇️" if prev in ("Entry Candidate", "Technical Entry Watch") and label not in ("Entry Candidate", "Technical Entry Watch") else "🔄"
            change_cell = f'<span title="از {prev_fa} به {cur_fa}">{change_icon}</span>'
        else:
            change_cell = ""

        color = label_color(label)
        bg = label_bg(label)
        gc = grade_color(grade)

        try:
            score_val = float(score)
            score_bar = f'<div style="background:#333;border-radius:4px;height:6px;margin-top:3px"><div style="background:{color};width:{min(score_val,100):.0f}%;height:6px;border-radius:4px"></div></div>'
        except Exception:
            score_bar = ""

        sparkline = ""
        if close_20d:
            sparkline = f'<canvas class="spark" data-prices="{close_20d}" width="80" height="30"></canvas>'

        label_display = label_fa(label)

        popup_id = f"pop_{sym}"
        row_html = f"""<tr onclick="showPopup('{popup_id}')" style="cursor:pointer">
  <td><b>{sym}</b> {change_cell}</td>
  <td style="color:{color};background:{bg};text-align:center;border-radius:4px;padding:2px 6px">{label_display}</td>
  <td style="color:{gc};text-align:center">{grade}</td>
  <td style="text-align:center">{score_val:.0f if score else score}<br>{score_bar}</td>
  <td style="text-align:center">{rsi}</td>
  <td style="text-align:center">{price}</td>
  <td style="text-align:center;font-size:11px">{sector}</td>
  <td style="text-align:center">{sm}</td>
  <td style="text-align:center">{q}</td>
  <td>{sparkline}</td>
</tr>"""

        popup_html = f"""<div id="{popup_id}" class="popup" style="display:none">
  <div class="popup-box">
    <button onclick="closePopup('{popup_id}')" style="float:left;background:none;border:none;color:#fff;font-size:18px;cursor:pointer">✕</button>
    <h3 style="color:{color}">{sym} — {label_display}</h3>
    <p><b>امتیاز:</b> {score} | <b>رتبه:</b> <span style="color:{gc}">{grade}</span></p>
    <p><b>سکتور:</b> {sector}</p>
    <p><b>RSI:</b> {rsi} | <b>قیمت:</b> {price}</p>
    <p><b>پول هوشمند:</b> {sm} — {r.get('smart_money_fa','')}</p>
    <p><b>صف:</b> {q} — {r.get('queue_fa','')}</p>
    <p><b>دلایل:</b> {reasons}</p>
    <p style="font-size:11px;color:#aaa"><b>عوامل:</b> {factors}</p>
    <div style="margin-top:10px">{sparkline.replace('width="80" height="30"','width="280" height="80"') if close_20d else ''}</div>
  </div>
</div>"""

        table_rows += row_html + popup_html

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="900">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Iran Stock AI Dashboard</title>
<style>
  body{{background:#121212;color:#e0e0e0;font-family:Tahoma,Arial,sans-serif;margin:0;padding:10px;font-size:13px}}
  h1{{text-align:center;color:#90caf9;margin:10px 0 4px}}
  .meta{{text-align:center;color:#888;font-size:11px;margin-bottom:8px}}
  .controls{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;align-items:center}}
  input,select{{background:#1e1e1e;border:1px solid #333;color:#e0e0e0;padding:4px 8px;border-radius:4px;font-size:12px}}
  button.btn{{background:#1565c0;color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px}}
  button.btn:hover{{background:#1976d2}}
  table{{width:100%;border-collapse:collapse}}
  th{{background:#1e1e1e;color:#90caf9;padding:6px 8px;text-align:center;position:sticky;top:0;cursor:pointer;user-select:none}}
  th:hover{{background:#263238}}
  td{{padding:5px 8px;border-bottom:1px solid #222;vertical-align:middle}}
  tr:hover{{background:#1a1a2e}}
  .popup{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:999;display:flex;align-items:center;justify-content:center}}
  .popup-box{{background:#1e1e1e;border:1px solid #333;border-radius:8px;padding:20px;max-width:400px;width:90%;direction:rtl}}
  #countdown{{display:inline-block;background:#1a237e;padding:2px 10px;border-radius:10px;font-size:11px;color:#90caf9}}
  .spark{{display:block}}
</style>
</head>
<body>
<h1>🇮🇷 Iran Stock AI Dashboard</h1>
<div class="meta">
  آخرین بروزرسانی: {generated_at} |
  <span id="countdown"></span>
  <span style="margin-right:10px;color:#546e7a">⟳ هر ۱۵ دقیقه خودکار بروز می‌شود</span>
</div>

<div class="controls">
  <input type="text" id="searchBox" placeholder="🔍 جستجو نماد..." oninput="filterTable()" style="width:150px">
  <select id="labelFilter" onchange="filterTable()">
    <option value="">همه وضعیت‌ها</option>
    <option value="ورود قوی">ورود قوی</option>
    <option value="ورود">ورود</option>
    <option value="تماشا">تماشا</option>
    <option value="نگهداری">نگهداری</option>
    <option value="خروج">خروج</option>
    <option value="داده ناقص">داده ناقص</option>
  </select>
  <select id="gradeFilter" onchange="filterTable()">
    <option value="">همه رتبه‌ها</option>
    <option value="A+">A+</option>
    <option value="A">A</option>
    <option value="B">B</option>
    <option value="C">C</option>
    <option value="D">D</option>
  </select>
  <button class="btn" onclick="exportCSV()">📥 خروجی Excel</button>
</div>

<table id="mainTable">
<thead>
<tr>
  <th onclick="sortTable(0)">نماد ↕</th>
  <th onclick="sortTable(1)">وضعیت ↕</th>
  <th onclick="sortTable(2)">رتبه ↕</th>
  <th onclick="sortTable(3)">امتیاز ↕</th>
  <th onclick="sortTable(4)">RSI ↕</th>
  <th onclick="sortTable(5)">قیمت ↕</th>
  <th onclick="sortTable(6)">سکتور ↕</th>
  <th onclick="sortTable(7)">پول هوشمند ↕</th>
  <th onclick="sortTable(8)">صف ↕</th>
  <th>نمودار</th>
</tr>
</thead>
<tbody id="tableBody">
{table_rows}
</tbody>
</table>

<script>
// Countdown timer
var refreshSecs = 900;
function updateCountdown() {{
  var m = Math.floor(refreshSecs/60), s = refreshSecs%60;
  document.getElementById('countdown').textContent = 'بروزرسانی بعدی: '+m+':'+(s<10?'0':'')+s;
  if(refreshSecs>0) refreshSecs--;
  setTimeout(updateCountdown,1000);
}}
updateCountdown();

// Sparklines
window.addEventListener('load', function() {{
  document.querySelectorAll('.spark').forEach(function(c) {{
    var prices = c.dataset.prices.split(',').map(Number).filter(n=>!isNaN(n));
    if(!prices.length) return;
    var ctx = c.getContext('2d');
    var w=c.width, h=c.height, n=prices.length;
    var mn=Math.min(...prices), mx=Math.max(...prices), rng=mx-mn||1;
    ctx.strokeStyle = prices[n-1]>=prices[0]?'#00e676':'#ff5252';
    ctx.lineWidth=1.5;
    ctx.beginPath();
    prices.forEach(function(p,i) {{
      var x=i/(n-1)*w, y=h-(p-mn)/rng*(h-4)-2;
      i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
    }});
    ctx.stroke();
  }});
}});

// Filter
function filterTable() {{
  var q=document.getElementById('searchBox').value.toLowerCase();
  var lf=document.getElementById('labelFilter').value;
  var gf=document.getElementById('gradeFilter').value;
  document.querySelectorAll('#tableBody tr.data-row').forEach(function(tr) {{
    var sym=tr.cells[0].textContent.toLowerCase();
    var lbl=tr.cells[1].textContent;
    var grd=tr.cells[2].textContent;
    var show=sym.includes(q)&&(lf===''||lbl.includes(lf))&&(gf===''||grd===gf);
    tr.style.display=show?'':'none';
  }});
}}

// Sort
var sortDir={{}};
function sortTable(col) {{
  var tb=document.getElementById('tableBody');
  var rows=Array.from(tb.querySelectorAll('tr.data-row'));
  var asc=!sortDir[col]; sortDir[col]=asc;
  rows.sort(function(a,b) {{
    var av=a.cells[col].textContent.trim(), bv=b.cells[col].textContent.trim();
    var an=parseFloat(av), bn=parseFloat(bv);
    if(!isNaN(an)&&!isNaN(bn)) return asc?an-bn:bn-an;
    return asc?av.localeCompare(bv,'fa'):bv.localeCompare(av,'fa');
  }});
  rows.forEach(r=>tb.appendChild(r));
}}

// Popup
function showPopup(id) {{ document.getElementById(id).style.display='flex'; }}
function closePopup(id) {{ document.getElementById(id).style.display='none'; }}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')document.querySelectorAll('.popup').forEach(p=>p.style.display='none');}});

// CSV Export
function exportCSV() {{
  var rows=[['نماد','وضعیت','رتبه','امتیاز','RSI','قیمت','سکتور','پول هوشمند','صف']];
  document.querySelectorAll('#tableBody tr.data-row').forEach(function(tr) {{
    if(tr.style.display==='none') return;
    rows.push(Array.from(tr.cells).slice(0,9).map(td=>td.textContent.trim()));
  }});
  var csv=rows.map(r=>r.join(',')).join('\\n');
  var a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,\\uFEFF'+encodeURIComponent(csv);
  a.download='stock_dashboard.csv';a.click();
}}
</script>
</body>
</html>"""


def run():
    if not os.path.exists(DECISION_REPORT_CSV):
        print(f"[dashboard] {DECISION_REPORT_CSV} not found")
        return

    rows = []
    with open(DECISION_REPORT_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    rows.sort(key=lambda r: float(r.get("confidence_score", 0) or 0), reverse=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = build_html(rows, generated_at)

    os.makedirs("docs", exist_ok=True)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[dashboard] Saved to {DASHBOARD_PATH} ({len(rows)} rows)")


if __name__ == "__main__":
    run()