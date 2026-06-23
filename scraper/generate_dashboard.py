"""Generate static HTML dashboard — Professional Architecture."""

import os
import sys
import csv
import json
import html as html_mod
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DECISION_REPORT_CSV, OUTPUT_DIR

SIGNAL_LOG = os.path.join(OUTPUT_DIR, "signal_log.csv")
DASHBOARD_PATH = os.path.join("docs", "index.html")

LABEL_FA = {
    "Entry Candidate":                   "ورود قوی",
    "Technical Entry Watch":             "ورود",
    "Wait for Pullback":                 "تماشا — پولبک",
    "Watch - Needs Volume Confirmation": "تماشا — حجم",
    "Watch Only":                        "نگهداری",
    "Avoid Entry Now - Overbought":      "خروج / اشباع",
    "Missing Technical Data":            "داده ناقص",
}

LABEL_COLOR = {
    "ورود قوی":       "#00c853",
    "ورود":           "#69f0ae",
    "تماشا — پولبک": "#ffd740",
    "تماشا — حجم":   "#ffab40",
    "نگهداری":        "#40c4ff",
    "خروج / اشباع":  "#ff5252",
    "داده ناقص":      "#78909c",
}

LABEL_BG = {
    "ورود قوی":       "#003300",
    "ورود":           "#003322",
    "تماشا — پولبک": "#332e00",
    "تماشا — حجم":   "#332200",
    "نگهداری":        "#002233",
    "خروج / اشباع":  "#330000",
    "داده ناقص":      "#1c2529",
}

GRADE_COLOR = {"A+": "#00e676", "A": "#69f0ae", "B": "#ffd740", "C": "#ff9100"}

SM_FA = {
    "price_volume_bullish":  "حجم و قیمت صعودی",
    "price_volume_bearish":  "حجم و قیمت نزولی",
    "high_value_flat":       "ارزش بالا — قیمت ثابت",
    "no_queue_active":       "صف فعال — بی‌داده",
    "no_data":               "بدون داده",
    "hidden_accumulation":   "تجمع پنهان",
    "hidden_distribution":   "توزیع پنهان",
    "aligned_bullish":       "همسو صعودی",
    "aligned_bearish":       "همسو نزولی",
    "retail_driven_up":      "خرده‌فروش صعودی",
    "retail_driven_down":    "خرده‌فروش نزولی",
    "neutral":               "خنثی",
}

Q_FA = {
    "buy_queue_at_limit":    "صف خرید سقف",
    "sell_queue_at_limit":   "صف فروش کف",
    "buy_queue_dominant":    "غلبه صف خرید",
    "sell_queue_dominant":   "غلبه صف فروش",
    "balanced":              "متعادل",
    "mild_buy_pressure":     "فشار خرید ملایم",
    "mild_sell_pressure":    "فشار فروش ملایم",
}


def _fa(label):  return LABEL_FA.get(label, label)
def _sm_fa(v):   return SM_FA.get(v, v)
def _q_fa(v):    return Q_FA.get(v, v)
def _lc(label):  return LABEL_COLOR.get(_fa(label), "#9e9e9e")
def _lb(label):  return LABEL_BG.get(_fa(label), "#1a1a1a")
def _gc(grade):  return GRADE_COLOR.get((grade or "").upper(), "#78909c")

def _f(v, default=0.0):
    try: return float(v)
    except Exception: return default

def _esc(v): return html_mod.escape(str(v or ""))

def _rsi_band(rsi):
    v = _f(rsi)
    if v <= 0:  return ("نامشخص",           "#78909c")
    if v < 30:  return ("اشباع فروش",        "#40c4ff")
    if v < 55:  return ("محدوده ایده‌آل",    "#00c853")
    if v < 70:  return ("میانه",              "#ffd740")
    if v < 80:  return ("اشباع خرید",         "#ff9100")
    return           ("اشباع خرید شدید",       "#ff5252")

def _is_missing(r):
    return (str(r.get("missing", "")).lower() == "true"
            or r.get("decision_label", "") == "Missing Technical Data")

def _is_stale(r):
    d = r.get("latest_date", "") or r.get("date", "")
    if not d: return False
    try:
        dt = datetime.strptime(str(d)[:10], "%Y-%m-%d")
        return (datetime.now() - dt).days > 2
    except Exception:
        return False

def _is_conflict(r):
    return _f(r.get("confidence_score", 0)) >= 80 and _f(r.get("rsi", 0)) > 80

def load_prev_labels():
    prev = {}
    if not os.path.exists(SIGNAL_LOG):
        return prev
    with open(SIGNAL_LOG, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sym, lbl, dt = row.get("symbol",""), row.get("decision_label",""), row.get("date","")
            if sym and lbl:
                if sym not in prev or dt > prev[sym]["date"]:
                    prev[sym] = {"label": lbl, "date": dt}
    return {k: v["label"] for k, v in prev.items()}

def build_data(rows, prev_labels):
    out = []
    for r in rows:
        label   = r.get("decision_label", "")
        grade   = r.get("confidence_grade", "")
        score   = _f(r.get("confidence_score", 0))
        rsi_val = r.get("rsi", "")
        rsi_b, rsi_c = _rsi_band(rsi_val)
        fa      = _fa(label)
        prev    = prev_labels.get(r.get("symbol",""), "")
        change  = ""
        if prev and prev != label:
            is_up = label in ("Entry Candidate","Technical Entry Watch") and prev not in ("Entry Candidate","Technical Entry Watch")
            is_dn = prev in ("Entry Candidate","Technical Entry Watch") and label not in ("Entry Candidate","Technical Entry Watch")
            change = "up" if is_up else "down" if is_dn else "changed"

        out.append({
            "sym":         r.get("symbol",""),
            "label":       label,
            "label_fa":    fa,
            "label_color": _lc(label),
            "label_bg":    _lb(label),
            "grade":       grade,
            "grade_color": _gc(grade),
            "score":       score,
            "rsi":         rsi_val,
            "rsi_band":    rsi_b,
            "rsi_color":   rsi_c,
            "price":       r.get("latest_close",""),
            "sector":      r.get("sector",""),
            "sm":          _sm_fa(r.get("smart_money_signal","")),
            "sm_fa":       r.get("smart_money_fa",""),
            "q":           _q_fa(r.get("queue_signal","")),
            "q_fa":        r.get("queue_fa",""),
            "reasons":     r.get("decision_reasons",""),
            "factors":     r.get("confidence_factors",""),
            "close_20d":   r.get("close_20d",""),
            "trend":       r.get("trend_score",""),
            "vol":         r.get("volume_ratio_20",""),
            "support":     r.get("support",""),
            "resistance":  r.get("resistance",""),
            "stop_loss":   r.get("stop_loss",""),
            "target_1":    r.get("target_1",""),
            "rr":          r.get("risk_reward",""),
            "missing":     _is_missing(r),
            "stale":       _is_stale(r),
            "conflict":    _is_conflict(r),
            "change":      change,
            "prev_label_fa": _fa(prev) if prev else "",
        })
    return out

def calc_kpi(data):
    total      = len(data)
    entry      = sum(1 for d in data if d["label"] == "Entry Candidate")
    highc      = sum(1 for d in data if d["score"] >= 80)
    overbought = sum(1 for d in data if d["label"] == "Avoid Entry Now - Overbought")
    missing_n  = sum(1 for d in data if d["missing"])
    conflict   = sum(1 for d in data if d["conflict"])
    scores     = [d["score"] for d in data if d["score"] > 0]
    avg        = round(sum(scores)/len(scores), 1) if scores else 0
    miss_pct   = round(missing_n/total*100) if total else 0
    health     = "سالم" if miss_pct < 10 else "هشدار" if miss_pct < 25 else "مشکل داده"
    health_c   = "#00c853" if miss_pct < 10 else "#ffd740" if miss_pct < 25 else "#ff5252"
    return dict(total=total, entry=entry, highc=highc, overbought=overbought,
                missing_n=missing_n, miss_pct=miss_pct, conflict=conflict,
                avg=avg, health=health, health_c=health_c)

def build_html(data, generated_at, kpi):
    sectors    = sorted(set(d["sector"] for d in data if d["sector"]))
    sector_opts = "".join(f'<option value="{_esc(s)}">{_esc(s)}</option>' for s in sectors)
    data_json  = json.dumps(data, ensure_ascii=False)
    miss_pct   = kpi["miss_pct"]

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="900">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Iran Stock AI Dashboard</title>
<style>
:root{{--bg:#0d1117;--paper:#161b22;--border:#30363d;--text:#e6edf3;--muted:#8b949e}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:Tahoma,Arial,sans-serif;font-size:13px;min-height:100vh}}
.header{{background:#161b22;border-bottom:1px solid #30363d;padding:10px 16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;position:sticky;top:0;z-index:100}}
.header h1{{color:#58a6ff;font-size:16px;white-space:nowrap}}
.header-meta{{color:var(--muted);font-size:11px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
#countdown{{background:#0d1b36;padding:2px 10px;border-radius:10px;color:#58a6ff}}
.kpi-bar{{display:flex;gap:8px;padding:12px 16px;flex-wrap:wrap;background:#0d1117;border-bottom:1px solid #21262d}}
.kpi{{border-radius:8px;padding:10px 16px;text-align:center;min-width:110px;flex:1;transition:filter .15s}}
.kpi[onclick]{{cursor:pointer}}.kpi[onclick]:hover{{filter:brightness(1.2)}}
.kpi-val{{font-size:26px;font-weight:700;line-height:1.1}}
.kpi-lbl{{font-size:10px;color:var(--muted);margin-top:3px}}
.top-picks{{padding:10px 16px;border-bottom:1px solid #21262d;display:none}}
.top-picks h2{{color:#ffd700;font-size:13px;margin-bottom:8px}}
.picks-row{{display:flex;gap:8px;flex-wrap:wrap}}
.pick-card{{background:#161b22;border:1px solid #00c85344;border-radius:8px;padding:8px 12px;cursor:pointer;transition:border-color .15s;min-width:130px}}
.pick-card:hover{{border-color:#00c853}}
.pick-sym{{color:#fff;font-weight:700;font-size:14px}}
.pick-score{{color:#00c853;font-size:12px}}
.pick-grade{{font-size:11px;color:#aaa}}
.controls{{padding:10px 16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;background:#0d1117;border-bottom:1px solid #21262d}}
input,select{{background:#161b22;border:1px solid #30363d;color:var(--text);padding:5px 9px;border-radius:6px;font-size:12px;font-family:Tahoma,Arial,sans-serif}}
input:focus,select:focus{{outline:1px solid #58a6ff;border-color:#58a6ff}}
.btn{{background:#1f6feb;color:#fff;border:none;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px;font-family:Tahoma,Arial,sans-serif;white-space:nowrap}}
.btn:hover{{background:#388bfd}}
.tag-btn{{background:#21262d;color:#c9d1d9;border:1px solid #30363d;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px;white-space:nowrap;font-family:Tahoma,Arial,sans-serif}}
.tag-btn.on{{background:#1f6feb;border-color:#1f6feb;color:#fff}}
.tag-btn.danger.on{{background:#b91c1c;border-color:#b91c1c}}
.tbl-wrap{{overflow-x:auto;padding:0 16px 16px}}
table{{width:100%;border-collapse:collapse;min-width:700px}}
th{{background:#161b22;color:#58a6ff;padding:7px 8px;text-align:center;position:sticky;top:52px;z-index:9;cursor:pointer;user-select:none;border-bottom:2px solid #30363d;font-size:12px;white-space:nowrap}}
th:hover{{background:#1c2128}}
th .arr{{color:#484f58;margin-right:2px}}
td{{padding:6px 8px;border-bottom:1px solid #1c2128;vertical-align:middle}}
tr.row{{cursor:pointer}}
tr.row:hover td{{background:#1c2128}}
tr.row.is-missing td{{opacity:.55}}
tr.row.is-stale td{{opacity:.72}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;white-space:nowrap}}
.rsi-badge{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;background:#1c2128}}
.score-bar-wrap{{background:#21262d;border-radius:3px;height:4px;margin-top:3px;overflow:hidden}}
.score-bar{{height:4px;border-radius:3px}}
.spark{{display:block}}
#drawerOverlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:500}}
#drawerOverlay.open{{display:flex;justify-content:flex-start}}
#drawer{{background:#161b22;border-left:1px solid #30363d;width:400px;max-width:96vw;height:100%;overflow-y:auto;padding:20px;direction:rtl;position:relative}}
.drawer-close{{position:absolute;top:14px;left:14px;background:none;border:none;color:#8b949e;font-size:22px;cursor:pointer;line-height:1}}
.drawer-close:hover{{color:#fff}}
.drawer-section{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px;margin-top:10px}}
.drawer-section h4{{color:#8b949e;font-size:11px;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px}}
.dl{{display:grid;grid-template-columns:1fr 1fr;gap:6px 10px;font-size:12px}}
.dl dt{{color:#8b949e}}
.dl dd{{color:#e6edf3;font-weight:600}}
.warn-box{{border-radius:6px;padding:8px 12px;font-size:12px;margin-top:8px}}
.disclaimer{{text-align:center;color:#484f58;font-size:10px;padding:14px 16px;border-top:1px solid #21262d;line-height:1.7}}
@media(max-width:600px){{
  .kpi{{min-width:80px;padding:8px 10px}}.kpi-val{{font-size:20px}}
  #drawer{{width:100vw}}
  .controls{{gap:4px}}
  th,td{{font-size:11px;padding:4px 5px}}
}}
</style>
</head>
<body>

<div class="header">
  <h1>🇮🇷 Iran Stock AI Dashboard</h1>
  <div class="header-meta">
    <span>آخرین بروزرسانی: <b style="color:#e6edf3">{_esc(generated_at)}</b></span>
    <span>|</span>
    <span id="countdown">...</span>
    <span style="color:#30363d">|</span>
    <span style="color:{kpi['health_c']}">● {_esc(kpi['health'])}</span>
    <span style="color:#30363d">|</span>
    <span>Asia/Tehran</span>
  </div>
</div>

<div class="kpi-bar">
  <div class="kpi" style="background:#0d1b2a;border:1px solid #1f3a5f">
    <div class="kpi-val" style="color:#90caf9">{kpi['total']}</div>
    <div class="kpi-lbl">📊 کل نمادها</div>
  </div>
  <div class="kpi" style="background:#003300;border:1px solid #00c85355" onclick="kpiFilter('entry')">
    <div class="kpi-val" style="color:#00c853">{kpi['entry']}</div>
    <div class="kpi-lbl">🟢 کاندید ورود</div>
  </div>
  <div class="kpi" style="background:#1a1400;border:1px solid #ffd74055" onclick="kpiFilter('highc')">
    <div class="kpi-val" style="color:#ffd740">{kpi['highc']}</div>
    <div class="kpi-lbl">⭐ High Confidence</div>
  </div>
  <div class="kpi" style="background:#1a0000;border:1px solid #ff525255" onclick="kpiFilter('overbought')">
    <div class="kpi-val" style="color:#ff5252">{kpi['overbought']}</div>
    <div class="kpi-lbl">🔴 اشباع خرید</div>
  </div>
  <div class="kpi" style="background:#1a0e00;border:1px solid #ff910055" onclick="kpiFilter('conflict')">
    <div class="kpi-val" style="color:#ff9100">{kpi['conflict']}</div>
    <div class="kpi-lbl">⚠️ Risk Conflict</div>
  </div>
  <div class="kpi" style="background:#1c2529;border:1px solid #78909c55" onclick="kpiFilter('missing')">
    <div class="kpi-val" style="color:#78909c">{kpi['missing_n']}</div>
    <div class="kpi-lbl">📉 داده ناقص ({miss_pct}%)</div>
  </div>
  <div class="kpi" style="background:#1a0028;border:1px solid #ce93d855">
    <div class="kpi-val" style="color:#ce93d8">{kpi['avg']}</div>
    <div class="kpi-lbl">💯 میانگین Score</div>
  </div>
</div>

<div class="top-picks" id="topPicksBar">
  <h2>🏆 بهترین فرصت‌های امروز</h2>
  <div class="picks-row" id="topPicksRow"></div>
</div>

<div class="controls">
  <input type="text" id="q" placeholder="🔍 نماد..." oninput="render()" style="width:100px">
  <select id="fLabel" onchange="render()">
    <option value="">همه وضعیت‌ها</option>
    <option value="ورود قوی">ورود قوی</option>
    <option value="ورود">ورود</option>
    <option value="تماشا — پولبک">تماشا — پولبک</option>
    <option value="تماشا — حجم">تماشا — حجم</option>
    <option value="نگهداری">نگهداری</option>
    <option value="خروج / اشباع">خروج / اشباع</option>
    <option value="داده ناقص">داده ناقص</option>
  </select>
  <select id="fGrade" onchange="render()">
    <option value="">همه رتبه‌ها</option>
    <option>A+</option><option>A</option><option>B</option><option>C</option><option>D</option>
  </select>
  <select id="fSector" onchange="render()">
    <option value="">همه سکتورها</option>
    {sector_opts}
  </select>
  <select id="fRsi" onchange="render()">
    <option value="">همه RSI</option>
    <option value="محدوده ایده‌آل">ایده‌آل (30-55)</option>
    <option value="میانه">میانه (55-70)</option>
    <option value="اشباع خرید">اشباع خرید (70-80)</option>
    <option value="اشباع خرید شدید">اشباع خرید شدید (80+)</option>
    <option value="اشباع فروش">اشباع فروش (&lt;30)</option>
  </select>
  <button class="tag-btn" id="btnComplete" onclick="toggleTag('complete')">فقط داده کامل</button>
  <button class="tag-btn danger" id="btnConflict" onclick="toggleTag('conflict')">⚠️ Conflict</button>
  <button class="tag-btn" id="btnChanges" onclick="toggleTag('changes')">🔄 تغییر وضعیت</button>
  <button class="btn" onclick="exportCSV()">📥 Excel</button>
</div>

<div class="tbl-wrap">
<table>
<thead>
<tr>
  <th onclick="sortBy('sym',0)"><span class="arr" id="arr0"></span>نماد</th>
  <th onclick="sortBy('label_fa',1)"><span class="arr" id="arr1"></span>وضعیت</th>
  <th onclick="sortBy('grade',2)"><span class="arr" id="arr2"></span>رتبه</th>
  <th onclick="sortBy('score',3)"><span class="arr" id="arr3"></span>امتیاز</th>
  <th onclick="sortBy('rsi',4)"><span class="arr" id="arr4"></span>RSI</th>
  <th onclick="sortBy('price',5)"><span class="arr" id="arr5"></span>قیمت</th>
  <th onclick="sortBy('sector',6)"><span class="arr" id="arr6"></span>سکتور</th>
  <th onclick="sortBy('vol',7)"><span class="arr" id="arr7"></span>حجم×</th>
  <th onclick="sortBy('sm',8)"><span class="arr" id="arr8"></span>پول هوشمند</th>
  <th>نمودار</th>
</tr>
</thead>
<tbody id="tbody"></tbody>
</table>
<div id="emptyMsg" style="display:none;text-align:center;padding:40px;color:#484f58">نتیجه‌ای یافت نشد</div>
</div>

<div id="drawerOverlay" onclick="closeDrawer(event)">
  <div id="drawer">
    <button class="drawer-close" onclick="closeDrawer()">✕</button>
    <div id="drawerContent"></div>
  </div>
</div>

<div class="disclaimer">
  ⚠️ این داشبورد صرفاً ابزار تحلیل تکنیکال است و <b>توصیه خرید یا فروش</b> محسوب نمی‌شود.<br>
  تصمیم‌گیری مالی کاملاً مسئولیت کاربر است و سیستم هیچ ضمانتی در قبال نتایج ارائه نمی‌دهد.<br>
  Iran Stock AI © {generated_at[:4]}
</div>

<script>
const DATA = {data_json};

var _secs=900;
(function tick(){{
  var m=Math.floor(_secs/60),s=_secs%60;
  document.getElementById('countdown').textContent='بروزرسانی: '+m+':'+(s<10?'0':'')+s;
  if(_secs>0)_secs--;setTimeout(tick,1000);
}})();

var _tags={{}},_sortKey='score',_sortAsc=false,_kpiFilter=null;

function toggleTag(t){{
  _tags[t]=!_tags[t];_kpiFilter=null;
  document.getElementById('btn'+t.charAt(0).toUpperCase()+t.slice(1)).classList.toggle('on',_tags[t]);
  render();
}}

function kpiFilter(type){{
  _kpiFilter=_kpiFilter===type?null:type;
  document.getElementById('fLabel').value='';
  document.getElementById('fGrade').value='';
  Object.keys(_tags).forEach(function(t){{
    _tags[t]=false;
    var el=document.getElementById('btn'+t.charAt(0).toUpperCase()+t.slice(1));
    if(el)el.classList.remove('on');
  }});
  render();
}}

function filtered(){{
  var q=(document.getElementById('q').value||'').toLowerCase();
  var fL=document.getElementById('fLabel').value;
  var fG=document.getElementById('fGrade').value;
  var fS=document.getElementById('fSector').value;
  var fR=document.getElementById('fRsi').value;
  return DATA.filter(function(d){{
    if(q&&!d.sym.toLowerCase().includes(q)&&!d.sector.toLowerCase().includes(q))return false;
    if(fL&&d.label_fa!==fL)return false;
    if(fG&&d.grade!==fG)return false;
    if(fS&&d.sector!==fS)return false;
    if(fR&&d.rsi_band!==fR)return false;
    if(_tags.complete&&d.missing)return false;
    if(_tags.conflict&&!d.conflict)return false;
    if(_tags.changes&&!d.change)return false;
    if(_kpiFilter==='entry'&&d.label!=='Entry Candidate')return false;
    if(_kpiFilter==='highc'&&d.score<80)return false;
    if(_kpiFilter==='overbought'&&d.label!=='Avoid Entry Now - Overbought')return false;
    if(_kpiFilter==='conflict'&&!d.conflict)return false;
    if(_kpiFilter==='missing'&&!d.missing)return false;
    return true;
  }});
}}

function sorted(arr){{
  return arr.slice().sort(function(a,b){{
    var av=a[_sortKey],bv=b[_sortKey];
    if(typeof av==='number'&&typeof bv==='number')return _sortAsc?av-bv:bv-av;
    av=String(av||'');bv=String(bv||'');
    return _sortAsc?av.localeCompare(bv,'fa'):bv.localeCompare(av,'fa');
  }});
}}

function sortBy(key,col){{
  if(_sortKey===key)_sortAsc=!_sortAsc;else{{_sortKey=key;_sortAsc=false;}}
  document.querySelectorAll('.arr').forEach(function(el){{el.textContent='';}});
  var a=document.getElementById('arr'+col);if(a)a.textContent=_sortAsc?'↑':'↓';
  render();
}}

function esc(s){{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}

function render(){{
  var rows=sorted(filtered());
  var html='';
  rows.forEach(function(d,i){{
    var cls='row'+(d.missing?' is-missing':'')+(d.stale&&!d.missing?' is-stale':'');
    var scoreBar=d.score?'<div class="score-bar-wrap"><div class="score-bar" style="width:'+Math.min(d.score,100)+'%;background:'+esc(d.label_color)+'"></div></div>':'';
    var changeIcon='';
    if(d.change==='up')changeIcon='<span title="ارتقاء وضعیت" style="font-size:12px"> ⬆️</span>';
    else if(d.change==='down')changeIcon='<span title="افت وضعیت" style="font-size:12px"> ⬇️</span>';
    else if(d.change==='changed')changeIcon='<span title="تغییر وضعیت" style="font-size:12px"> 🔄</span>';
    var conflictIcon=d.conflict?'<span title="امتیاز بالا — RSI خطرناک" style="color:#ff9100;font-size:11px"> ⚠️</span>':'';
    var staleIcon=d.stale&&!d.missing?'<span title="داده قدیمی" style="color:#78909c;font-size:10px"> 🕐</span>':'';
    var vol=parseFloat(d.vol)||0;
    var volStr=vol>0?vol.toFixed(1)+'x':'—';
    var volColor=vol>=2?'#00c853':vol>=1?'#ffd740':'#78909c';
    var spark=d.close_20d?'<canvas class="spark" data-idx="'+i+'" data-p="'+esc(d.close_20d)+'" width="80" height="26"></canvas>':'';
    html+='<tr class="'+cls+'" onclick="openDrawer('+i+')">'
      +'<td><b>'+esc(d.sym)+'</b>'+changeIcon+conflictIcon+staleIcon+'</td>'
      +'<td><span class="badge" style="color:'+esc(d.label_color)+';background:'+esc(d.label_bg)+'">'+esc(d.label_fa)+'</span></td>'
      +'<td style="text-align:center"><b style="color:'+esc(d.grade_color)+'">'+esc(d.grade)+'</b></td>'
      +'<td style="text-align:center">'+(d.score?d.score.toFixed(0):'')+scoreBar+'</td>'
      +'<td style="text-align:center"><span class="rsi-badge" style="color:'+esc(d.rsi_color)+'">'+esc(d.rsi)+'</span></td>'
      +'<td style="text-align:center">'+esc(d.price)+'</td>'
      +'<td style="text-align:center;color:#90caf9;font-size:11px">'+esc(d.sector)+'</td>'
      +'<td style="text-align:center;color:'+volColor+'">'+volStr+'</td>'
      +'<td style="text-align:center;font-size:11px">'+esc(d.sm)+'</td>'
      +'<td>'+spark+'</td>'
      +'</tr>';
  }});
  document.getElementById('tbody').innerHTML=html;
  document.getElementById('emptyMsg').style.display=rows.length?'none':'block';
  drawSparklines();
  renderTopPicks();
}}

function drawSparklines(){{
  document.querySelectorAll('.spark').forEach(function(c){{
    var p=c.dataset.p.split(',').map(Number).filter(function(n){{return n>0;}});
    if(p.length<2)return;
    var ctx=c.getContext('2d'),w=c.width,h=c.height,n=p.length;
    var mn=Math.min.apply(null,p),mx=Math.max.apply(null,p),rng=mx-mn||1;
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle=p[n-1]>=p[0]?'#00e676':'#ff5252';
    ctx.lineWidth=1.5;ctx.beginPath();
    p.forEach(function(v,i){{var x=i/(n-1)*w,y=h-(v-mn)/rng*(h-4)-2;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}});
    ctx.stroke();
  }});
}}

function renderTopPicks(){{
  var picks=DATA.filter(function(d){{return d.label==='Entry Candidate'&&d.score>=75&&!d.missing;}})
    .sort(function(a,b){{return b.score-a.score;}}).slice(0,5);
  var bar=document.getElementById('topPicksBar');
  if(!picks.length){{bar.style.display='none';return;}}
  bar.style.display='block';
  document.getElementById('topPicksRow').innerHTML=picks.map(function(d){{
    var idx=DATA.indexOf(d);
    return '<div class="pick-card" onclick="openDrawer('+idx+')">'
      +'<div class="pick-sym">'+esc(d.sym)+'</div>'
      +'<div class="pick-score">امتیاز '+d.score.toFixed(0)+' | رتبه <span style="color:'+esc(d.grade_color)+'">'+esc(d.grade)+'</span></div>'
      +'<div class="pick-grade">'+esc(d.rsi_band)+' | '+esc(d.sector)+'</div>'
      +'</div>';
  }}).join('');
}}

function openDrawer(idx){{
  var d=DATA[idx];if(!d)return;
  var conflict=d.conflict?'<div class="warn-box" style="background:#1a0e00;border:1px solid #ff910088;color:#ff9100">⚠️ امتیاز بالا اما RSI خطرناک — ورود با احتیاط</div>':'';
  var missing=d.missing?'<div class="warn-box" style="background:#111518;border:1px solid #78909c88;color:#78909c">داده تکنیکال ناقص — سیگنال قابل اعتماد نیست</div>':'';
  var stale=d.stale&&!d.missing?'<div class="warn-box" style="background:#0d1117;border:1px solid #ffd74044;color:#ffd740">🕐 داده قدیمی — ممکن است قیمت به‌روز نباشد</div>':'';
  var change='';
  if(d.change){{
    var arrow=d.change==='up'?'⬆️':d.change==='down'?'⬇️':'🔄';
    change='<div style="color:#8b949e;font-size:11px;margin-top:6px">'+arrow+' از <b>'+esc(d.prev_label_fa)+'</b> به <b style="color:'+esc(d.label_color)+'">'+esc(d.label_fa)+'</b></div>';
  }}
  var spark=d.close_20d?'<canvas id="dSpark" data-p="'+esc(d.close_20d)+'" width="340" height="70" style="margin-top:10px;display:block"></canvas>':'';
  function row(lbl,val){{return val?'<dt>'+lbl+'</dt><dd>'+esc(val)+'</dd>':''}}
  var vol=parseFloat(d.vol)||0;
  document.getElementById('drawerContent').innerHTML=
    '<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:12px;padding-top:8px">'
    +'<div style="flex:1"><div style="font-size:18px;font-weight:700;color:#e6edf3">'+esc(d.sym)+'</div>'
    +'<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
    +'<span class="badge" style="color:'+esc(d.label_color)+';background:'+esc(d.label_bg)+'">'+esc(d.label_fa)+'</span>'
    +'<span style="color:'+esc(d.grade_color)+';font-weight:700;font-size:15px">'+esc(d.grade)+'</span>'
    +'<span style="color:#8b949e;font-size:13px">امتیاز '+d.score.toFixed(0)+'</span>'
    +'</div>'+change+'</div></div>'
    +conflict+missing+stale
    +'<div class="drawer-section"><h4>دلایل تصمیم</h4><p style="color:#ccc;font-size:12px;line-height:1.8">'+esc(d.reasons)+'</p></div>'
    +'<div class="drawer-section"><h4>عوامل امتیازدهی</h4><p style="color:#8b949e;font-size:11px;line-height:1.8">'+esc(d.factors)+'</p></div>'
    +'<div class="drawer-section"><h4>مشخصات فنی</h4><dl class="dl">'
    +row('RSI',d.rsi+(d.rsi_band?' ('+d.rsi_band+')':''))
    +row('قیمت',d.price)
    +row('روند',d.trend?d.trend+'/6':'')
    +row('نسبت حجم',vol>0?vol.toFixed(2)+'x':'')
    +row('سکتور',d.sector)
    +row('حمایت',d.support)
    +row('مقاومت',d.resistance)
    +row('حد ضرر',d.stop_loss)
    +row('هدف',d.target_1)
    +row('ریسک/ریوارد',d.rr)
    +'</dl></div>'
    +'<div class="drawer-section"><h4>پول هوشمند و صف</h4><dl class="dl">'
    +row('پول هوشمند',d.sm)
    +row('توضیح',d.sm_fa)
    +row('صف',d.q)
    +row('توضیح صف',d.q_fa)
    +'</dl></div>'
    +spark;
  document.getElementById('drawerOverlay').classList.add('open');
  document.body.style.overflow='hidden';
  if(d.close_20d){{
    setTimeout(function(){{
      var c=document.getElementById('dSpark');if(!c)return;
      var p=c.dataset.p.split(',').map(Number).filter(function(n){{return n>0;}});
      if(p.length<2)return;
      var ctx=c.getContext('2d'),w=c.width,h=c.height,n=p.length;
      var mn=Math.min.apply(null,p),mx=Math.max.apply(null,p),rng=mx-mn||1;
      ctx.strokeStyle=p[n-1]>=p[0]?'#00e676':'#ff5252';
      ctx.lineWidth=2;ctx.beginPath();
      p.forEach(function(v,i){{var x=i/(n-1)*w,y=h-(v-mn)/rng*(h-6)-3;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}});
      ctx.stroke();
    }},50);
  }}
}}

function closeDrawer(e){{
  if(e&&e.target!==document.getElementById('drawerOverlay'))return;
  document.getElementById('drawerOverlay').classList.remove('open');
  document.body.style.overflow='';
}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeDrawer();}});

function exportCSV(){{
  var rows=[['نماد','وضعیت','رتبه','امتیاز','RSI','باند RSI','قیمت','سکتور','حجم×','پول هوشمند','صف','دلایل']];
  filtered().forEach(function(d){{
    var vol=parseFloat(d.vol)||0;
    rows.push([d.sym,d.label_fa,d.grade,d.score.toFixed(0),d.rsi,d.rsi_band,d.price,d.sector,
      vol>0?vol.toFixed(2)+'x':'',d.sm,d.q,d.reasons]);
  }});
  var csv=rows.map(function(r){{return r.map(function(c){{return'"'+String(c||'').replace(/"/g,'""')+'"'}}).join(',')}}).join('\\n');
  var a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,\\uFEFF'+encodeURIComponent(csv);
  a.download='iran_stock_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
}}

document.getElementById('arr3').textContent='↓';
render();
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

    rows.sort(key=lambda r: _f(r.get("confidence_score", 0)), reverse=True)

    prev_labels = load_prev_labels()
    data = build_data(rows, prev_labels)
    kpi  = calc_kpi(data)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = build_html(data, generated_at, kpi)

    os.makedirs("docs", exist_ok=True)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"[dashboard] Saved → {DASHBOARD_PATH} | {len(rows)} symbols | KPI: {kpi}")


if __name__ == "__main__":
    run()