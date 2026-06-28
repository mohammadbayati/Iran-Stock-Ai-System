"""Generate static HTML dashboard — Phase 3: Performance tab."""

import os
import sys
import csv
import json
import html as html_mod
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DECISION_REPORT_CSV, OUTPUT_DIR, DATA_DIR

SIGNAL_LOG = os.path.join(DATA_DIR, "signal_log.csv")
DASHBOARD_PATH = os.path.join("docs", "index.html")
JS_PATH = os.path.join("docs", "dashboard.js")
PILOT_REPORT_PATH = os.path.join("docs", "pilot-report.html")

LABEL_FA = {
    "Entry Candidate":                   "کاندید بررسی قوی",
    "Technical Entry Watch":             "کاندید بررسی",
    "Wait for Pullback":                 "بررسی پس از پولبک",
    "Watch - Needs Volume Confirmation": "نیازمند تایید حجم",
    "Watch Only":                        "صرفا رصد",
    "Avoid Entry Now - Overbought":      "ریسک اشباع خرید",
    "Missing Technical Data":            "داده ناقص",
}
LABEL_COLOR = {
    "کاندید بررسی قوی": "#00c853", "کاندید بررسی": "#69f0ae",
    "بررسی پس از پولبک": "#ffd740", "نیازمند تایید حجم": "#ffab40",
    "صرفا رصد": "#40c4ff", "ریسک اشباع خرید": "#ff5252",
    "داده ناقص": "#78909c",
}
LABEL_BG = {
    "کاندید بررسی قوی": "#003300", "کاندید بررسی": "#003322",
    "بررسی پس از پولبک": "#332e00", "نیازمند تایید حجم": "#332200",
    "صرفا رصد": "#002233", "ریسک اشباع خرید": "#330000",
    "داده ناقص": "#1c2529",
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
    "buy_queue_at_limit":  "صف خرید سقف",
    "sell_queue_at_limit": "صف فروش کف",
    "buy_queue_dominant":  "غلبه صف خرید",
    "sell_queue_dominant": "غلبه صف فروش",
    "balanced":            "متعادل",
    "mild_buy_pressure":   "فشار خرید ملایم",
    "mild_sell_pressure":  "فشار فروش ملایم",
}

def _fa(l):  return LABEL_FA.get(l, l)
def _sm(v):  return SM_FA.get(v, v)
def _q(v):   return Q_FA.get(v, v)
def _lc(l):  return LABEL_COLOR.get(_fa(l), "#9e9e9e")
def _lb(l):  return LABEL_BG.get(_fa(l), "#1a1a1a")
def _gc(g):  return GRADE_COLOR.get((g or "").upper(), "#78909c")
def _f(v, d=0.0):
    try: return float(v)
    except: return d
def _esc(v): return html_mod.escape(str(v or ""))

def _rsi_band(rsi):
    v = _f(rsi)
    if v <= 0:  return ("نامشخص",          "#78909c")
    if v < 30:  return ("اشباع فروش",       "#40c4ff")
    if v < 55:  return ("محدوده ایده‌آل",   "#00c853")
    if v < 70:  return ("میانه",             "#ffd740")
    if v < 80:  return ("اشباع خرید",        "#ff9100")
    return           ("اشباع خرید شدید",      "#ff5252")

def _is_missing(r):
    return (str(r.get("missing","")).lower()=="true"
            or r.get("decision_label","")=="Missing Technical Data")
def _is_stale(r):
    d = r.get("latest_date","") or r.get("date","")
    if not d: return False
    try:
        dt = datetime.strptime(str(d)[:10], "%Y-%m-%d")
        return (datetime.now()-dt).days > 2
    except: return False
def _is_conflict(r):
    return _f(r.get("confidence_score",0))>=80 and _f(r.get("rsi",0))>80

def load_prev_labels():
    prev = {}
    if not os.path.exists(SIGNAL_LOG): return prev
    with open(SIGNAL_LOG, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sym,lbl,dt = row.get("symbol",""),row.get("decision_label",""),row.get("date","")
            if sym and lbl:
                if sym not in prev or dt > prev[sym]["date"]:
                    prev[sym] = {"label":lbl,"date":dt}
    return {k:v["label"] for k,v in prev.items()}


def load_perf_data():
    """Load signal log and expose track-record readiness for the dashboard."""
    import csv

    def to_float(value):
        try:
            if value is None:
                return None
            s = str(value).strip()
            if not s or s.lower() == "nan":
                return None
            return float(s)
        except Exception:
            return None

    def is_complete(row, horizon):
        ret = to_float(row.get(f"return_{horizon}d_pct"))
        close_later = to_float(row.get(f"close_{horizon}d_later"))
        return ret is not None or close_later is not None

    def signed_return(row, horizon):
        ret = to_float(row.get(f"return_{horizon}d_pct"))
        if ret is not None:
            return ret
        start = to_float(row.get("close_at_signal"))
        later = to_float(row.get(f"close_{horizon}d_later"))
        if start and later:
            return (later - start) / start * 100
        return None

    def expected_success(row, ret):
        label = str(row.get("decision_label", ""))
        if "Overbought" in label or "Avoid" in label or "اشباع" in label:
            return ret < 0
        return ret > 0

    def summarize(rows, horizon):
        completed = []
        pending = 0
        by_label = {}
        by_grade = {}
        high_conf = []
        recent = []

        for row in rows:
            ret = signed_return(row, horizon)
            if ret is None:
                pending += 1
                continue

            win = expected_success(row, ret)
            score = to_float(row.get("confidence_score")) or 0
            label = str(row.get("decision_label", "") or "نامشخص")
            grade = str(row.get("confidence_grade", "") or "نامشخص")
            item = {
                "date": row.get("date", ""),
                "symbol": row.get("symbol", ""),
                "label": label,
                "grade": grade,
                "score": score,
                "ret": ret,
                "win": win,
            }
            completed.append(item)
            if score >= 80:
                high_conf.append(item)

            bucket = by_label.setdefault(label, {"n": 0, "wins": 0, "avg": 0.0})
            bucket["n"] += 1
            bucket["wins"] += 1 if win else 0
            bucket["avg"] += ret

            gbucket = by_grade.setdefault(grade, {"n": 0, "wins": 0, "avg": 0.0})
            gbucket["n"] += 1
            gbucket["wins"] += 1 if win else 0
            gbucket["avg"] += ret

        for group in (by_label, by_grade):
            for stats in group.values():
                stats["avg"] = stats["avg"] / stats["n"] if stats["n"] else 0
                stats["win_rate"] = stats["wins"] / stats["n"] * 100 if stats["n"] else 0

        def avg_ret(items):
            return sum(x["ret"] for x in items) / len(items) if items else 0

        def win_rate(items):
            return sum(1 for x in items if x["win"]) / len(items) * 100 if items else 0

        recent = sorted(completed, key=lambda x: (x["date"], x["symbol"]))[-20:]
        equity = []
        acc = 0.0
        for item in sorted(completed, key=lambda x: (x["date"], x["symbol"])):
            acc += item["ret"]
            equity.append(round(acc, 2))

        return {
            "horizon": f"{horizon}D",
            "total_logged": len(rows),
            "completed": len(completed),
            "pending": pending,
            "win_rate": win_rate(completed),
            "avg_ret": avg_ret(completed),
            "high_conf_completed": len(high_conf),
            "high_conf_win_rate": win_rate(high_conf),
            "high_conf_avg_ret": avg_ret(high_conf),
            "by_label": by_label,
            "by_grade": by_grade,
            "recent": recent,
            "equity_curve": equity,
        }

    if not os.path.exists(SIGNAL_LOG):
        empty = {"total_logged": 0, "completed": 0, "pending": 0, "win_rate": 0, "avg_ret": 0}
        return {"total_logged": 0, "completed": 0, "win_rate": 0, "avg_ret": 0, "horizons": {"5D": empty, "10D": empty}}

    with open(SIGNAL_LOG, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    dates = []
    for row in rows:
        raw_date = str(row.get("date", "")).strip()
        try:
            dates.append(datetime.strptime(raw_date[:10], "%Y-%m-%d").date())
        except Exception:
            pass
    first_signal_date = min(dates).isoformat() if dates else ""
    last_signal_date = max(dates).isoformat() if dates else ""
    track_age_days = (date.today() - min(dates)).days if dates else 0
    earliest_5d_review = ""
    earliest_10d_review = ""
    if dates:
        earliest = min(dates)
        earliest_5d_review = (earliest + timedelta(days=7)).isoformat()
        earliest_10d_review = (earliest + timedelta(days=14)).isoformat()

    h5 = summarize(rows, 5)
    h10 = summarize(rows, 10)
    return {
        "total_logged": len(rows),
        "completed": h5["completed"],
        "win_rate": h5["win_rate"],
        "avg_ret": h5["avg_ret"],
        "first_signal_date": first_signal_date,
        "last_signal_date": last_signal_date,
        "track_age_days": track_age_days,
        "earliest_5d_review": earliest_5d_review,
        "earliest_10d_review": earliest_10d_review,
        "by_label": h5["by_label"],
        "by_grade": h5["by_grade"],
        "recent": h5["recent"],
        "equity_curve": h5["equity_curve"],
        "horizons": {"5D": h5, "10D": h10},
    }

def build_data(rows, prev_labels):
    out = []
    for r in rows:
        label=r.get("decision_label",""); grade=r.get("confidence_grade","")
        score=_f(r.get("confidence_score",0)); rsi_v=r.get("rsi","")
        rsi_b,rsi_c=_rsi_band(rsi_v); fa=_fa(label)
        prev=prev_labels.get(r.get("symbol",""),""); change=""
        if prev and prev!=label:
            is_up=label in("Entry Candidate","Technical Entry Watch") and prev not in("Entry Candidate","Technical Entry Watch")
            is_dn=prev in("Entry Candidate","Technical Entry Watch") and label not in("Entry Candidate","Technical Entry Watch")
            change="up" if is_up else "down" if is_dn else "changed"
        out.append({"sym":r.get("symbol",""),"label":label,"label_fa":fa,
            "label_color":_lc(label),"label_bg":_lb(label),"grade":grade,"grade_color":_gc(grade),
            "score":score,"rsi":rsi_v,"rsi_band":rsi_b,"rsi_color":rsi_c,
            "price":r.get("latest_close",""),"sector":r.get("sector",""),
            "sm":_sm(r.get("smart_money_signal","")),"sm_fa":r.get("smart_money_fa",""),
            "q":_q(r.get("queue_signal","")),"q_fa":r.get("queue_fa",""),
            "reasons":r.get("decision_reasons",""),"factors":r.get("confidence_factors",""),
            "close_20d":r.get("close_20d",""),"trend":r.get("trend_score",""),
            "vol":r.get("volume_ratio_20",""),"support":r.get("support",""),
            "resistance":r.get("resistance",""),"stop_loss":r.get("stop_loss",""),
            "target_1":r.get("target_1",""),"rr":r.get("risk_reward",""),
            "latest_date":r.get("latest_date","") or r.get("date",""),
            "data_quality":"ناقص" if _is_missing(r) else "قدیمی" if _is_stale(r) else "قابل اتکا",
            "risk_flags":", ".join(x for x in [
                "داده ناقص" if _is_missing(r) else "",
                "داده قدیمی" if _is_stale(r) else "",
                "تعارض RSI/امتیاز" if _is_conflict(r) else "",
                "RSI اشباع خرید" if _f(r.get("rsi",0))>=80 else "",
            ] if x) or "بدون هشدار",
            "invalidation":"اگر داده ناقص/قدیمی شود، RSI وارد محدوده پرریسک شود، یا قیمت سطح ابطال را بشکند، این کاندید باید دوباره بررسی شود.",
            "missing":_is_missing(r),"stale":_is_stale(r),"conflict":_is_conflict(r),
            "change":change,"prev_label_fa":_fa(prev) if prev else ""})
    return out

def calc_kpi(data):
    total=len(data); entry=sum(1 for d in data if d["label"]=="Entry Candidate")
    highc=sum(1 for d in data if d["score"]>=80)
    over=sum(1 for d in data if d["label"]=="Avoid Entry Now - Overbought")
    miss=sum(1 for d in data if d["missing"]); conf=sum(1 for d in data if d["conflict"])
    sc=[d["score"] for d in data if d["score"]>0]; avg=round(sum(sc)/len(sc),1) if sc else 0
    mp=round(miss/total*100) if total else 0
    hc="#00c853" if mp<10 else "#ffd740" if mp<25 else "#ff5252"
    ht="سالم" if mp<10 else "هشدار" if mp<25 else "مشکل داده"
    return dict(total=total,entry=entry,highc=highc,overbought=over,
                missing_n=miss,miss_pct=mp,conflict=conf,avg=avg,health=ht,health_c=hc)

def build_html(data, generated_at, kpi, perf):
    sectors=sorted(set(d["sector"] for d in data if d["sector"]))
    sector_opts="".join(f'<option value="{_esc(s)}">{_esc(s)}</option>' for s in sectors)
    data_json=json.dumps(data,ensure_ascii=True).replace("</","<\\/")
    perf_json=json.dumps(perf or {},ensure_ascii=True).replace("</","<\\/")
    mp=kpi["miss_pct"]
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
body{{background:var(--bg);color:var(--text);font-family:Tahoma,Arial,sans-serif;font-size:13px}}
.header{{background:#161b22;border-bottom:1px solid #30363d;padding:10px 16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;position:sticky;top:0;z-index:100}}
.header h1{{color:#58a6ff;font-size:16px;white-space:nowrap}}
.hm{{color:var(--muted);font-size:11px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
#cd{{background:#0d1b36;padding:2px 10px;border-radius:10px;color:#58a6ff}}
.tab-bar{{display:flex;gap:0;padding:0 16px;background:#161b22;border-bottom:2px solid #21262d}}
.tab{{padding:9px 18px;font-size:12px;cursor:pointer;color:#8b949e;border-bottom:2px solid transparent;margin-bottom:-2px;user-select:none;transition:color .15s}}
.tab:hover{{color:#c9d1d9}}
.tab.active{{color:#58a6ff;border-bottom-color:#58a6ff;font-weight:600}}
.tab-panel{{display:none}}
.tab-panel.active{{display:block}}
.kpi-bar{{display:flex;gap:8px;padding:12px 16px;flex-wrap:wrap;border-bottom:1px solid #21262d}}
.kpi{{border-radius:8px;padding:10px 14px;text-align:center;min-width:105px;flex:1;transition:filter .15s}}
.kpi[onclick]{{cursor:pointer}}.kpi[onclick]:hover{{filter:brightness(1.2)}}
.kv{{font-size:24px;font-weight:700;line-height:1.1}}
.kl{{font-size:10px;color:var(--muted);margin-top:3px}}
.charts-section{{padding:12px 16px;border-bottom:1px solid #21262d}}
.charts-toggle{{display:flex;align-items:center;gap:8px;margin-bottom:10px;cursor:pointer;user-select:none}}
.charts-toggle h2{{color:#8b949e;font-size:12px;font-weight:600;letter-spacing:.5px}}
.charts-toggle .arrow{{color:#484f58;transition:transform .2s;font-size:12px}}
.charts-toggle.open .arrow{{transform:rotate(90deg)}}
.charts-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}
.chart-box{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px}}
.chart-box h3{{color:#8b949e;font-size:11px;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}}
.chart-box canvas{{display:block;width:100%}}
.heatmap-grid{{display:flex;flex-direction:column;gap:4px}}
.hm-row{{display:flex;align-items:center;gap:6px;cursor:pointer;padding:3px 4px;border-radius:4px}}
.hm-row:hover{{background:#1c2128}}
.hm-name{{font-size:11px;color:#c9d1d9;min-width:90px;text-align:right}}
.hm-bar-wrap{{flex:1;background:#21262d;border-radius:3px;height:14px;overflow:hidden}}
.hm-bar{{height:14px;border-radius:3px;display:flex;align-items:center;padding-right:4px;font-size:9px;color:#000;font-weight:700;white-space:nowrap;overflow:hidden}}
.hm-meta{{font-size:10px;color:#484f58;white-space:nowrap;min-width:60px}}
@media(max-width:900px){{.charts-grid{{grid-template-columns:1fr 1fr}}}}
@media(max-width:600px){{.charts-grid{{grid-template-columns:1fr}}}}
.top-picks{{padding:10px 16px;border-bottom:1px solid #21262d;display:none}}
.top-picks h2{{color:#ffd700;font-size:13px;margin-bottom:8px}}
.picks-row{{display:flex;gap:8px;flex-wrap:wrap}}
.pick{{background:#161b22;border:1px solid #00c85344;border-radius:8px;padding:8px 12px;cursor:pointer;transition:border-color .15s;min-width:130px}}
.pick:hover{{border-color:#00c853}}
.pick-sym{{color:#fff;font-weight:700;font-size:14px}}
.pick-sc{{color:#00c853;font-size:12px}}
.pick-gr{{font-size:11px;color:#aaa}}
.controls{{padding:10px 16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;border-bottom:1px solid #21262d}}
input,select{{background:#161b22;border:1px solid #30363d;color:var(--text);padding:5px 9px;border-radius:6px;font-size:12px;font-family:Tahoma,Arial,sans-serif}}
input:focus,select:focus{{outline:1px solid #58a6ff;border-color:#58a6ff}}
.btn{{background:#1f6feb;color:#fff;border:none;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px;font-family:Tahoma,Arial,sans-serif;white-space:nowrap}}
.btn:hover{{background:#388bfd}}
.tbtn{{background:#21262d;color:#c9d1d9;border:1px solid #30363d;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px;white-space:nowrap;font-family:Tahoma,Arial,sans-serif}}
.tbtn.on{{background:#1f6feb;border-color:#1f6feb;color:#fff}}
.tbtn.danger.on{{background:#b91c1c;border-color:#b91c1c}}
.tbl-wrap{{overflow-x:auto;padding:0 16px 16px}}
table{{width:100%;border-collapse:collapse;min-width:700px}}
th{{background:#161b22;color:#58a6ff;padding:7px 8px;text-align:center;position:static;top:auto;z-index:auto;cursor:pointer;user-select:none;border-bottom:2px solid #30363d;font-size:12px;white-space:nowrap}}
th:hover{{background:#1c2128}}
.arr{{color:#484f58;margin-right:2px}}
td{{padding:6px 8px;border-bottom:1px solid #1c2128;vertical-align:middle}}
tr.row{{cursor:pointer}}
tr.row:hover td{{background:#1c2128}}
tr.row.is-missing td{{opacity:.55}}
tr.row.is-stale td{{opacity:.72}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;white-space:nowrap}}
.rbadge{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;background:#1c2128}}
.sb-wrap{{background:#21262d;border-radius:3px;height:4px;margin-top:3px;overflow:hidden}}
.sb{{height:4px;border-radius:3px}}
.spark{{display:block}}
#ov{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:500}}
#ov.open{{display:flex;justify-content:flex-start}}
#drawer{{background:#161b22;border-left:1px solid #30363d;width:400px;max-width:96vw;height:100%;overflow-y:auto;padding:20px;direction:rtl;position:relative}}
.dcls{{position:absolute;top:14px;left:14px;background:none;border:none;color:#8b949e;font-size:22px;cursor:pointer;line-height:1}}
.dcls:hover{{color:#fff}}
.dsec{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px;margin-top:10px}}
.dsec h4{{color:#8b949e;font-size:11px;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px}}
.dl{{display:grid;grid-template-columns:1fr 1fr;gap:6px 10px;font-size:12px}}
.dl dt{{color:#8b949e}}.dl dd{{color:#e6edf3;font-weight:600}}
.wbox{{border-radius:6px;padding:8px 12px;font-size:12px;margin-top:8px}}
.perf-section{{padding:16px;border-bottom:1px solid #21262d}}
.perf-kpi{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}}
.perf-card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 16px;text-align:center;min-width:120px;flex:1}}
.perf-card .pv{{font-size:22px;font-weight:700}}
.perf-card .pl{{font-size:10px;color:#8b949e;margin-top:3px}}
.perf-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.perf-box{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px}}
.perf-box h3{{color:#8b949e;font-size:11px;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}}
.perf-row{{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:12px}}
.perf-label{{min-width:110px;color:#c9d1d9;text-align:right}}
.perf-bar-wrap{{flex:1;background:#21262d;border-radius:3px;height:12px;overflow:hidden}}
.perf-bar{{height:12px;border-radius:3px;min-width:2px}}
.perf-val{{font-size:11px;white-space:nowrap;min-width:80px;text-align:left}}
.recent-table{{width:100%;border-collapse:collapse;font-size:11px;margin-top:8px}}
.recent-table th{{background:#0d1117;color:#8b949e;padding:5px 8px;text-align:center;border-bottom:1px solid #21262d;position:static;top:auto;z-index:auto;cursor:default}}
.recent-table td{{padding:5px 8px;border-bottom:1px solid #1c2128;text-align:center}}
.perf-empty{{color:#484f58;text-align:center;padding:40px;font-size:13px;line-height:2}}
.sym-link{{cursor:pointer;color:#58a6ff;text-decoration:underline dotted;font-weight:600}}
.sym-link:hover{{color:#79c0ff}}
.disc{{text-align:center;color:#484f58;font-size:10px;padding:14px 16px;border-top:1px solid #21262d;line-height:1.7}}
#stt{{position:fixed;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 10px;font-size:11px;color:#e6edf3;pointer-events:none;display:none;z-index:200;direction:rtl;max-width:180px}}
@media(max-width:700px){{
  .kpi{{min-width:80px;padding:8px 10px}}.kv{{font-size:18px}}
  #drawer{{width:100vw}}
  th,td{{font-size:11px;padding:4px 5px}}
  .perf-grid{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<div class="header">
  <h1>&#x1f1ee;&#x1f1f7; Iran Stock AI Dashboard</h1>
  <div class="hm">
    <span>&#x622;&#x62e;&#x631;&#x6cc;&#x646; &#x628;&#x631;&#x648;&#x632;&#x631;&#x633;&#x627;&#x646;&#x6cc;: <b style="color:#e6edf3">{_esc(generated_at)}</b></span>
    <span>|</span><span id="cd">...</span><span>|</span>
    <span style="color:{kpi['health_c']}">&#x25cf; {_esc(kpi['health'])}</span>
    <span>|</span><span>Asia/Tehran</span>
  </div>
</div>
<div class="tab-bar">
  <div class="tab active" id="tab-btn-main" onclick="switchTab('main')">&#x1f4ca; &#x62f;&#x627;&#x634;&#x628;&#x648;&#x631;&#x62f;</div>
  <div class="tab" id="tab-btn-perf" onclick="switchTab('perf')">&#x1f4c8; &#x639;&#x645;&#x644;&#x6a9;&#x631;&#x62f;</div>
</div>
<div class="tab-panel active" id="tab-main">
<div class="kpi-bar">
  <div class="kpi" style="background:#0d1b2a;border:1px solid #1f3a5f">
    <div class="kv" style="color:#90caf9">{kpi['total']}</div><div class="kl">&#x1f4ca; &#x6a9;&#x644; &#x646;&#x645;&#x627;&#x62f;&#x647;&#x627;</div>
  </div>
  <div class="kpi" style="background:#003300;border:1px solid #00c85355" onclick="kpiF('entry')">
    <div class="kv" style="color:#00c853">{kpi['entry']}</div><div class="kl">&#x1f7e2; کاندید بررسی</div>
  </div>
  <div class="kpi" style="background:#1a1400;border:1px solid #ffd74055" onclick="kpiF('highc')">
    <div class="kv" style="color:#ffd740">{kpi['highc']}</div><div class="kl">&#x2b50; High Confidence</div>
  </div>
  <div class="kpi" style="background:#1a0000;border:1px solid #ff525255" onclick="kpiF('overbought')">
    <div class="kv" style="color:#ff5252">{kpi['overbought']}</div><div class="kl">&#x1f534; &#x627;&#x634;&#x628;&#x627;&#x639; &#x62e;&#x631;&#x6cc;&#x62f;</div>
  </div>
  <div class="kpi" style="background:#1a0e00;border:1px solid #ff910055" onclick="kpiF('conflict')">
    <div class="kv" style="color:#ff9100">{kpi['conflict']}</div><div class="kl">&#x26a0;&#xfe0f; Risk Conflict</div>
  </div>
  <div class="kpi" style="background:#1c2529;border:1px solid #78909c55" onclick="kpiF('missing')">
    <div class="kv" style="color:#78909c">{kpi['missing_n']}</div><div class="kl">&#x1f4c9; &#x62f;&#x627;&#x62f;&#x647; &#x646;&#x627;&#x642;&#x635; ({mp}%)</div>
  </div>
  <div class="kpi" style="background:#1a0028;border:1px solid #ce93d855">
    <div class="kv" style="color:#ce93d8">{kpi['avg']}</div><div class="kl">&#x1f4af; &#x645;&#x6cc;&#x627;&#x646;&#x6af;&#x6cc;&#x646; Score</div>
  </div>
</div>
<div class="charts-section">
  <div class="charts-toggle open" id="chartsToggle" onclick="toggleCharts()">
    <span class="arrow">&#x25b6;</span>
    <h2>&#x1f4c8; &#x62a;&#x62d;&#x644;&#x6cc;&#x644; &#x633;&#x631;&#x6cc;&#x639; &#x628;&#x627;&#x632;&#x627;&#x631;</h2>
    <span style="color:#484f58;font-size:10px;margin-right:auto">&#x6a9;&#x644;&#x6cc;&#x6a9; &#x631;&#x648;&#x6cc; &#x646;&#x645;&#x648;&#x62f;&#x627;&#x631; &#x628;&#x631;&#x627;&#x6cc; &#x641;&#x6cc;&#x644;&#x62a;&#x631;</span>
  </div>
  <div id="chartsBody" style="display:block">
    <div class="charts-grid">
      <div class="chart-box"><h3>&#x62a;&#x648;&#x632;&#x6cc;&#x639; &#x648;&#x636;&#x639;&#x6cc;&#x62a;&#x200c;&#x647;&#x627;</h3><canvas id="cDist" height="190"></canvas></div>
      <div class="chart-box"><h3>Confidence vs RSI</h3><canvas id="cScatter" height="190"></canvas></div>
      <div class="chart-box"><h3>&#x647;&#x6cc;&#x62a;&#x645;&#x67e; &#x633;&#x6a9;&#x62a;&#x648;&#x631;&#x647;&#x627;</h3><div class="heatmap-grid" id="cHeat"></div></div>
    </div>
  </div>
</div>
<div class="top-picks" id="tpBar">
  <h2>&#x1f3c6; کاندیدهای بررسی امروز</h2>
  <div class="picks-row" id="tpRow"></div>
</div>
<div class="controls">
  <input type="text" id="q" placeholder="&#x1f50d; &#x646;&#x645;&#x627;&#x62f;..." oninput="render()" style="width:100px">
  <select id="fL" onchange="render()">
    <option value="">&#x647;&#x645;&#x647; &#x648;&#x636;&#x639;&#x6cc;&#x62a;&#x200c;&#x647;&#x627;</option>
    <option value="&#x648;&#x631;&#x648;&#x62f; &#x642;&#x648;&#x6cc;">&#x648;&#x631;&#x648;&#x62f; &#x642;&#x648;&#x6cc;</option>
    <option value="&#x648;&#x631;&#x648;&#x62f;">&#x648;&#x631;&#x648;&#x62f;</option>
    <option value="&#x62a;&#x645;&#x627;&#x634;&#x627; &#x2014; &#x67e;&#x648;&#x644;&#x628;&#x6a9;">&#x62a;&#x645;&#x627;&#x634;&#x627; &#x2014; &#x67e;&#x648;&#x644;&#x628;&#x6a9;</option>
    <option value="&#x62a;&#x645;&#x627;&#x634;&#x627; &#x2014; &#x62d;&#x62c;&#x645;">&#x62a;&#x645;&#x627;&#x634;&#x627; &#x2014; &#x62d;&#x62c;&#x645;</option>
    <option value="&#x646;&#x6af;&#x647;&#x62f;&#x627;&#x631;&#x6cc;">&#x646;&#x6af;&#x647;&#x62f;&#x627;&#x631;&#x6cc;</option>
    <option value="&#x62e;&#x631;&#x648;&#x62c; / &#x627;&#x634;&#x628;&#x627;&#x639;">&#x62e;&#x631;&#x648;&#x62c; / &#x627;&#x634;&#x628;&#x627;&#x639;</option>
    <option value="&#x62f;&#x627;&#x62f;&#x647; &#x646;&#x627;&#x642;&#x635;">&#x62f;&#x627;&#x62f;&#x647; &#x646;&#x627;&#x642;&#x635;</option>
  </select>
  <select id="fG" onchange="render()">
    <option value="">&#x647;&#x645;&#x647; &#x631;&#x62a;&#x628;&#x647;&#x200c;&#x647;&#x627;</option>
    <option>A+</option><option>A</option><option>B</option><option>C</option><option>D</option>
  </select>
  <select id="fS" onchange="render()">
    <option value="">&#x647;&#x645;&#x647; &#x633;&#x6a9;&#x62a;&#x648;&#x631;&#x647;&#x627;</option>
    {sector_opts}
  </select>
  <select id="fR" onchange="render()">
    <option value="">&#x647;&#x645;&#x647; RSI</option>
    <option value="&#x645;&#x62d;&#x62f;&#x648;&#x62f;&#x647; &#x627;&#x6cc;&#x62f;&#x647;&#x200c;&#x622;&#x644;">&#x627;&#x6cc;&#x62f;&#x647;&#x200c;&#x622;&#x644; (30-55)</option>
    <option value="&#x645;&#x6cc;&#x627;&#x646;&#x647;">&#x645;&#x6cc;&#x627;&#x646;&#x647; (55-70)</option>
    <option value="&#x627;&#x634;&#x628;&#x627;&#x639; &#x62e;&#x631;&#x6cc;&#x62f;">&#x627;&#x634;&#x628;&#x627;&#x639; &#x62e;&#x631;&#x6cc;&#x62f; (70-80)</option>
    <option value="&#x627;&#x634;&#x628;&#x627;&#x639; &#x62e;&#x631;&#x6cc;&#x62f; &#x634;&#x62f;&#x6cc;&#x62f;">&#x627;&#x634;&#x628;&#x627;&#x639; &#x62e;&#x631;&#x6cc;&#x62f; &#x634;&#x62f;&#x6cc;&#x62f; (80+)</option>
    <option value="&#x627;&#x634;&#x628;&#x627;&#x639; &#x641;&#x631;&#x648;&#x634;">&#x627;&#x634;&#x628;&#x627;&#x639; &#x641;&#x631;&#x648;&#x634; (&lt;30)</option>
  </select>
  <button class="tbtn" id="btnComplete" onclick="toggleTag('complete')">&#x641;&#x642;&#x637; &#x62f;&#x627;&#x62f;&#x647; &#x6a9;&#x627;&#x645;&#x644;</button>
  <button class="tbtn danger" id="btnConflict" onclick="toggleTag('conflict')">&#x26a0;&#xfe0f; Conflict</button>
  <button class="tbtn" id="btnChanges" onclick="toggleTag('changes')">&#x1f504; &#x62a;&#x63a;&#x6cc;&#x6cc;&#x631;</button>
  <button class="btn" onclick="doExport()">&#x1f4e5; Excel</button>
</div>
<div class="tbl-wrap">
<table>
<thead><tr>
  <th onclick="srt('sym',0)"><span class="arr" id="a0"></span>&#x646;&#x645;&#x627;&#x62f;</th>
  <th onclick="srt('label_fa',1)"><span class="arr" id="a1"></span>&#x648;&#x636;&#x639;&#x6cc;&#x62a;</th>
  <th onclick="srt('grade',2)"><span class="arr" id="a2"></span>&#x631;&#x62a;&#x628;&#x647;</th>
  <th onclick="srt('score',3)"><span class="arr" id="a3"></span>&#x627;&#x645;&#x62a;&#x6cc;&#x627;&#x632;</th>
  <th onclick="srt('rsi',4)"><span class="arr" id="a4"></span>RSI</th>
  <th onclick="srt('price',5)"><span class="arr" id="a5"></span>&#x642;&#x6cc;&#x645;&#x62a;</th>
  <th onclick="srt('sector',6)"><span class="arr" id="a6"></span>&#x633;&#x6a9;&#x62a;&#x648;&#x631;</th>
  <th onclick="srt('vol',7)"><span class="arr" id="a7"></span>&#x62d;&#x62c;&#x645;&#xd7;</th>
  <th onclick="srt('sm',8)"><span class="arr" id="a8"></span>&#x67e;&#x648;&#x644; &#x647;&#x648;&#x634;&#x645;&#x646;&#x62f;</th>
  <th>&#x646;&#x645;&#x648;&#x62f;&#x627;&#x631;</th>
</tr></thead>
<tbody id="tb"></tbody>
</table>
<div id="emp" style="display:none;text-align:center;padding:40px;color:#484f58">&#x646;&#x62a;&#x6cc;&#x62c;&#x647;&#x200c;&#x627;&#x6cc; &#x6cc;&#x627;&#x641;&#x62a; &#x646;&#x634;&#x62f;</div>
</div>
</div>
<div class="tab-panel" id="tab-perf"><div id="perfContent"></div></div>
<div id="ov" onclick="closeDr(event)">
  <div id="drawer">
    <button class="dcls" onclick="closeDr()">&#x2715;</button>
    <div id="dc"></div>
  </div>
</div>
<div id="stt"></div>
<div class="disc">
  &#x26a0;&#xfe0f; این داشبورد ابزار تصمیم‌یار و غربالگری است، نه توصیه قطعی خرید یا فروش. هر خروجی باید همراه با ریسک، کیفیت داده و سناریوی ابطال بررسی شود.
  Iran Stock AI &copy; {generated_at[:4]}
</div>
<script id="__DATA__" type="application/json">{data_json}</script>
<script id="__PERF__" type="application/json">{perf_json}</script>
<script src="dashboard.js?v={generated_at.replace(' ', '-').replace(':', '')}"></script>
</body>
</html>"""



def build_pilot_report_html(perf, generated_at):
    h5 = (perf.get("horizons") or {}).get("5D", {})
    h10 = (perf.get("horizons") or {}).get("10D", {})
    total = perf.get("total_logged", 0)
    first = perf.get("first_signal_date") or "-"
    last = perf.get("last_signal_date") or "-"
    age = perf.get("track_age_days", 0)
    next5 = perf.get("earliest_5d_review") or "-"
    next10 = perf.get("earliest_10d_review") or "-"

    def n(value):
        try:
            return int(value or 0)
        except Exception:
            return 0

    cards = [
        ("کل سیگنال‌های ثبت‌شده", total, "ثبت‌شده در signal_log.csv"),
        ("نتیجه 5D کامل", n(h5.get("completed")), "آماده ارزیابی"),
        ("در انتظار 5D", n(h5.get("pending")), "پس از 5 روز معاملاتی"),
        ("در انتظار 10D", n(h10.get("pending")), "پس از 10 روز معاملاتی"),
    ]
    card_html = "\n".join(
        f'<div class="card"><span>{html_mod.escape(str(title))}</span><b>{html_mod.escape(str(value))}</b><small>{html_mod.escape(str(sub))}</small></div>'
        for title, value, sub in cards
    )
    return f'''<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Iran Stock AI Dashboard - Pilot Validation Report</title>
  <style>
    :root {{
      --bg:#0d1117; --panel:#161b22; --panel2:#101923; --border:#30363d;
      --text:#c9d1d9; --muted:#8b949e; --blue:#58a6ff; --green:#00c853; --yellow:#ffd740; --orange:#ffab40;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:Tahoma,Arial,sans-serif; line-height:1.9; }}
    main {{ max-width:1120px; margin:0 auto; padding:28px 18px 42px; }}
    header {{ border-bottom:1px solid var(--border); padding-bottom:18px; margin-bottom:18px; }}
    h1 {{ margin:0; color:var(--blue); font-size:24px; }}
    h2 {{ margin:0 0 10px; color:#e6edf3; font-size:16px; }}
    p {{ margin:0 0 10px; }}
    .meta {{ color:var(--muted); font-size:12px; margin-top:8px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:18px 0; }}
    .card, section {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; }}
    .card {{ padding:14px; min-height:96px; }}
    .card span {{ display:block; color:var(--muted); font-size:12px; }}
    .card b {{ display:block; color:var(--blue); font-size:28px; margin-top:4px; }}
    .card small {{ display:block; color:var(--muted); font-size:11px; }}
    section {{ padding:16px; margin-top:14px; }}
    .summary {{ background:var(--panel2); border-color:#58a6ff55; }}
    .facts {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .fact {{ background:#0d1117; border:1px solid var(--border); border-radius:8px; padding:12px; }}
    .fact span {{ color:var(--muted); font-size:12px; }}
    .fact b {{ display:block; color:var(--yellow); font-size:15px; }}
    ul {{ margin:8px 0 0; padding:0 18px 0 0; }}
    li {{ margin:5px 0; }}
    a.btn {{ display:inline-block; margin-top:14px; background:#238636; border:1px solid #2ea043; color:white; text-decoration:none; border-radius:6px; padding:8px 12px; font-size:13px; }}
    .warn {{ color:var(--orange); }}
    @media (max-width:800px) {{ .grid,.facts {{ grid-template-columns:1fr 1fr; }} }}
    @media (max-width:520px) {{ .grid,.facts {{ grid-template-columns:1fr; }} main {{ padding:18px 12px; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Iran Stock AI Dashboard - Pilot Validation Report</h1>
    <div class="meta">آخرین تولید گزارش: {html_mod.escape(str(generated_at))} | این گزارش از داده‌های Track Record ساخته شده است.</div>
    <a class="btn" href="./index.html">بازگشت به داشبورد</a>
  </header>

  <section class="summary">
    <h2>خلاصه وضعیت پایلوت</h2>
    <p>این سیستم وارد مرحله Track Record شده است. سیگنال‌ها ثبت می‌شوند، اما ارزیابی عملکرد فقط پس از کامل شدن پنجره‌های 5D و 10D معتبر است.</p>
    <p class="warn">تا قبل از تکمیل این پنجره‌ها، خروجی‌ها صرفا کاندید بررسی هستند و توصیه قطعی خرید/فروش یا ادعای بازدهی قطعی محسوب نمی‌شوند.</p>
  </section>

  <div class="facts">
    <div class="fact"><span>شروع Track Record</span><b>{html_mod.escape(str(first))}</b></div>
    <div class="fact"><span>آخرین سیگنال</span><b>{html_mod.escape(str(last))}</b></div>
    <div class="fact"><span>سن تاریخچه</span><b>{html_mod.escape(str(age))} روز</b></div>
    <div class="fact"><span>اولین بررسی تقریبی</span><b>5D: {html_mod.escape(str(next5))} | 10D: {html_mod.escape(str(next10))}</b></div>
  </div>

  <div class="grid">
    {card_html}
  </div>

  <section>
    <h2>معیارهای قضاوت آینده</h2>
    <ul>
      <li>نرخ موفقیت سیگنال‌ها پس از تکمیل 5D و 10D</li>
      <li>میانگین بازده تحقق‌یافته در هر افق زمانی</li>
      <li>تفکیک عملکرد سیگنال‌های High Confidence</li>
      <li>مقایسه وضعیت‌های مختلف مثل کاندید بررسی، ریسک اشباع خرید و داده ناقص</li>
    </ul>
  </section>

  <section>
    <h2>محدودیت‌ها و مرز استفاده</h2>
    <ul>
      <li>این گزارش ابزار تصمیم‌یار و غربالگری است، نه توصیه قطعی خرید یا فروش.</li>
      <li>داده‌های ناقص، قدیمی یا دارای هشدار ریسک باید قبل از تصمیم‌گیری دوباره بررسی شوند.</li>
      <li>نتایج عملکرد تا زمانی که تعداد کافی سیگنال کامل‌شده وجود نداشته باشد، از نظر آماری قطعی نیستند.</li>
    </ul>
  </section>
</main>
</body>
</html>'''

def build_js():
    return r"""/* Iran Stock AI Dashboard — external JS */
'use strict';
const DATA = JSON.parse(document.getElementById('__DATA__').textContent);
const PERF = JSON.parse(document.getElementById('__PERF__').textContent);

function switchTab(t){
  ['main','perf'].forEach(function(n){
    document.getElementById('tab-'+n).classList.toggle('active',n===t);
    document.getElementById('tab-btn-'+n).classList.toggle('active',n===t);
  });
  if(t==='perf')renderPerf();
}
var _s=900;
(function tick(){
  var m=Math.floor(_s/60),s=_s%60;
  document.getElementById('cd').textContent='بروزرسانی: '+m+':'+(s<10?'0':'')+s;
  if(_s>0)_s--;
  setTimeout(tick,1000);
})();
var _tags={},_sk='score',_sa=false,_kf=null,_chartsOpen=true;
function toggleCharts(){
  _chartsOpen=!_chartsOpen;
  document.getElementById('chartsBody').style.display=_chartsOpen?'block':'none';
  document.getElementById('chartsToggle').classList.toggle('open',_chartsOpen);
}
function toggleTag(t){
  _tags[t]=!_tags[t];_kf=null;
  document.getElementById('btn'+t.charAt(0).toUpperCase()+t.slice(1)).classList.toggle('on',_tags[t]);
  render();
}
function kpiF(type){
  _kf=_kf===type?null:type;
  document.getElementById('fL').value='';document.getElementById('fG').value='';
  Object.keys(_tags).forEach(function(t){
    _tags[t]=false;
    var el=document.getElementById('btn'+t.charAt(0).toUpperCase()+t.slice(1));
    if(el)el.classList.remove('on');
  });
  render();
}
function filtered(){
  var q=(document.getElementById('q').value||'').toLowerCase();
  var fL=document.getElementById('fL').value,fG=document.getElementById('fG').value;
  var fS=document.getElementById('fS').value,fR=document.getElementById('fR').value;
  return DATA.filter(function(d){
    if(q&&!d.sym.toLowerCase().includes(q)&&!(d.sector||'').toLowerCase().includes(q))return false;
    if(fL&&d.label_fa!==fL)return false;
    if(fG&&d.grade!==fG)return false;
    if(fS&&d.sector!==fS)return false;
    if(fR&&d.rsi_band!==fR)return false;
    if(_tags.complete&&d.missing)return false;
    if(_tags.conflict&&!d.conflict)return false;
    if(_tags.changes&&!d.change)return false;
    if(_kf==='entry'&&d.label!=='Entry Candidate')return false;
    if(_kf==='highc'&&d.score<80)return false;
    if(_kf==='overbought'&&d.label!=='Avoid Entry Now - Overbought')return false;
    if(_kf==='conflict'&&!d.conflict)return false;
    if(_kf==='missing'&&!d.missing)return false;
    return true;
  });
}
function sorted(arr){
  return arr.slice().sort(function(a,b){
    var av=a[_sk],bv=b[_sk];
    if(typeof av==='number'&&typeof bv==='number')return _sa?av-bv:bv-av;
    av=String(av||'');bv=String(bv||'');
    return _sa?(av<bv?-1:av>bv?1:0):(bv<av?-1:bv>av?1:0);
  });
}
function srt(k,c){
  if(_sk===k)_sa=!_sa;else{_sk=k;_sa=false;}
  document.querySelectorAll('.arr').forEach(function(el){el.textContent='';});
  var a=document.getElementById('a'+c);if(a)a.textContent=_sa?'↑':'↓';
  render();
}
function e(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function render(){
  var rows=sorted(filtered()),html='';
  rows.forEach(function(d){
    var cls='row'+(d.missing?' is-missing':'')+(d.stale&&!d.missing?' is-stale':'');
    var sb=d.score?'<div class="sb-wrap"><div class="sb" style="width:'+Math.min(d.score,100)+'%;background:'+e(d.label_color)+'"></div></div>':'';
    var ci=d.change==='up'?'<span title="ارتقاء"> ⬆️</span>':d.change==='down'?'<span title="افت"> ⬇️</span>':d.change==='changed'?'<span title="تغییر"> 🔄</span>':'';
    var wi=d.conflict?'<span style="color:#ff9100;font-size:11px"> ⚠️</span>':'';
    var si=d.stale&&!d.missing?'<span style="color:#78909c;font-size:10px"> 🕐</span>':'';
    var vol=parseFloat(d.vol)||0,vc=vol>=2?'#00c853':vol>=1?'#ffd740':'#78909c';
    var sp=d.close_20d?'<canvas class="spark" data-p="'+e(d.close_20d)+'" width="80" height="26"></canvas>':'';
    html+='<tr class="'+cls+'" onclick="openDr('+DATA.indexOf(d)+')">'
      +'<td><b>'+e(d.sym)+'</b>'+ci+wi+si+'</td>'
      +'<td><span class="badge" style="color:'+e(d.label_color)+';background:'+e(d.label_bg)+'">'+e(d.label_fa)+'</span></td>'
      +'<td style="text-align:center"><b style="color:'+e(d.grade_color)+'">'+e(d.grade)+'</b></td>'
      +'<td style="text-align:center">'+(d.score?d.score.toFixed(0):'')+sb+'</td>'
      +'<td style="text-align:center"><span class="rbadge" style="color:'+e(d.rsi_color)+'">'+e(d.rsi)+'</span></td>'
      +'<td style="text-align:center">'+e(d.price)+'</td>'
      +'<td style="text-align:center;color:#90caf9;font-size:11px">'+e(d.sector)+'</td>'
      +'<td style="text-align:center;color:'+vc+'">'+(vol>0?vol.toFixed(1)+'x':'—')+'</td>'
      +'<td style="font-size:11px">'+e(d.sm)+'</td>'
      +'<td>'+sp+'</td></tr>';
  });
  document.getElementById('tb').innerHTML=html;
  document.getElementById('emp').style.display=rows.length?'none':'block';
  drawSparks();drawTopPicks();
  requestAnimationFrame(function(){drawDist();drawScatter();drawHeat();});
}
function drawSparks(){
  document.querySelectorAll('.spark').forEach(function(c){
    var p=c.dataset.p.split(',').map(Number).filter(function(n){return n>0;});
    if(p.length<2)return;
    var ctx=c.getContext('2d'),w=c.width,h=c.height,n=p.length;
    var mn=Math.min.apply(null,p),mx=Math.max.apply(null,p),rng=mx-mn||1;
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle=p[n-1]>=p[0]?'#00e676':'#ff5252';
    ctx.lineWidth=1.5;ctx.beginPath();
    p.forEach(function(v,i){var x=i/(n-1)*w,y=h-(v-mn)/rng*(h-4)-2;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.stroke();
  });
}
function drawTopPicks(){
  var picks=DATA.filter(function(d){return d.label==='Entry Candidate'&&d.score>=75&&!d.missing;})
    .sort(function(a,b){return b.score-a.score;}).slice(0,5);
  var bar=document.getElementById('tpBar');
  if(!picks.length){bar.style.display='none';return;}
  bar.style.display='block';
  document.getElementById('tpRow').innerHTML=picks.map(function(d){
    return '<div class="pick" onclick="openDr('+DATA.indexOf(d)+')">'
      +'<div class="pick-sym">'+e(d.sym)+'</div>'
      +'<div class="pick-sc">امتیاز '+d.score.toFixed(0)+' | <span style="color:'+e(d.grade_color)+'">'+e(d.grade)+'</span></div>'
      +'<div class="pick-gr">'+e(d.rsi_band)+' | '+e(d.sector)+'</div></div>';
  }).join('');
}
function drawDist(){
  var c=document.getElementById('cDist');if(!c)return;
  var W=c.offsetWidth||300;c.width=W;c.height=190;
  var ctx=c.getContext('2d');ctx.clearRect(0,0,W,190);
  var labels=['کاندید بررسی قوی','کاندید بررسی','بررسی پس از پولبک','نیازمند تایید حجم','صرفا رصد','ریسک اشباع خرید','داده ناقص'];
  var colors=['#00c853','#69f0ae','#ffd740','#ffab40','#40c4ff','#ff5252','#78909c'];
  var counts=labels.map(function(l){return DATA.filter(function(d){return d.label_fa===l;}).length;});
  var mx=Math.max.apply(null,counts)||1;
  var rowH=24,pad=4,labelW=110,barX=labelW+8,barMaxW=W-labelW-50;
  ctx.font='11px Tahoma,Arial,sans-serif';ctx.textAlign='right';ctx.textBaseline='middle';
  labels.forEach(function(l,i){
    var y=pad+i*rowH+rowH/2,bw=Math.max((counts[i]/mx)*barMaxW,1);
    ctx.fillStyle='#21262d';ctx.fillRect(barX,y-8,barMaxW,16);
    ctx.fillStyle=colors[i];ctx.fillRect(barX,y-8,bw,16);
    ctx.fillStyle='#c9d1d9';ctx.fillText(l,labelW,y);
    ctx.fillStyle=colors[i];ctx.textAlign='left';ctx.fillText(counts[i],barX+bw+4,y);ctx.textAlign='right';
  });
  c.onclick=function(ev){
    var rect=c.getBoundingClientRect(),y=ev.clientY-rect.top,i=Math.floor((y-pad)/rowH);
    if(i>=0&&i<labels.length&&counts[i]>0){document.getElementById('fL').value=labels[i];render();}
  };
  c.style.cursor='pointer';
}
function drawScatter(){
  var c=document.getElementById('cScatter');if(!c)return;
  var W=c.offsetWidth||300;c.width=W;c.height=190;
  var ctx=c.getContext('2d');ctx.clearRect(0,0,W,190);
  var PAD={t:10,r:10,b:30,l:30},pw=W-PAD.l-PAD.r,ph=190-PAD.t-PAD.b;
  var dz=PAD.l+pw*0.8;
  ctx.fillStyle='rgba(255,82,82,.07)';ctx.fillRect(dz,PAD.t,pw*0.2,ph);
  ctx.strokeStyle='#ff525255';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(dz,PAD.t);ctx.lineTo(dz,PAD.t+ph);ctx.stroke();
  ctx.strokeStyle='#30363d';ctx.beginPath();
  ctx.moveTo(PAD.l,PAD.t);ctx.lineTo(PAD.l,PAD.t+ph);
  ctx.moveTo(PAD.l,PAD.t+ph);ctx.lineTo(PAD.l+pw,PAD.t+ph);ctx.stroke();
  ctx.fillStyle='#484f58';ctx.font='9px Tahoma';ctx.textAlign='center';
  [0,25,50,75,100].forEach(function(v){ctx.fillText(v,PAD.l+pw*(v/100),PAD.t+ph+14);});
  ctx.textAlign='right';
  [0,25,50,75,100].forEach(function(v){ctx.fillText(v,PAD.l-4,PAD.t+ph-ph*(v/100)+3);});
  ctx.fillStyle='#8b949e';ctx.font='10px Tahoma';ctx.textAlign='center';
  ctx.fillText('RSI',PAD.l+pw/2,PAD.t+ph+26);
  var visible=filtered();
  DATA.forEach(function(d){
    var rsi=parseFloat(d.rsi)||0,sc=d.score||0;if(!rsi||!sc)return;
    var x=PAD.l+pw*(rsi/100),y=PAD.t+ph-ph*(sc/100);
    var vol=parseFloat(d.vol)||1,r=Math.min(Math.max(vol*2.5,3),10);
    var inFilter=visible.indexOf(d)>=0;
    ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);
    ctx.fillStyle=inFilter?d.label_color+'cc':'#30363d';ctx.fill();
    if(inFilter&&d.conflict){ctx.strokeStyle='#ff9100';ctx.lineWidth=2;ctx.stroke();}
  });
  var tt=document.getElementById('stt');
  c.onmousemove=function(ev){
    var rect=c.getBoundingClientRect(),mx=ev.clientX-rect.left,my=ev.clientY-rect.top,found=null,minD=999;
    DATA.forEach(function(d){
      var rsi=parseFloat(d.rsi)||0,sc=d.score||0;if(!rsi||!sc)return;
      var x=PAD.l+pw*(rsi/100),y2=PAD.t+ph-ph*(sc/100),dist=Math.sqrt((mx-x)*(mx-x)+(my-y2)*(my-y2));
      if(dist<14&&dist<minD){minD=dist;found=d;}
    });
    if(found){
      tt.style.display='block';tt.style.left=(ev.clientX+12)+'px';tt.style.top=(ev.clientY-10)+'px';
      tt.innerHTML='<b>'+e(found.sym)+'</b><br>Score: '+found.score.toFixed(0)+'<br>RSI: '+e(found.rsi)+'<br>'+e(found.label_fa);
      c.style.cursor='pointer';
    }else{tt.style.display='none';c.style.cursor='crosshair';}
  };
  c.onmouseleave=function(){tt.style.display='none';};
  c.onclick=function(ev){
    var rect=c.getBoundingClientRect(),mx=ev.clientX-rect.left,my=ev.clientY-rect.top,found=null,minD=999;
    DATA.forEach(function(d){
      var rsi=parseFloat(d.rsi)||0,sc=d.score||0;if(!rsi||!sc)return;
      var x=PAD.l+pw*(rsi/100),y2=PAD.t+ph-ph*(sc/100),dist=Math.sqrt((mx-x)*(mx-x)+(my-y2)*(my-y2));
      if(dist<14&&dist<minD){minD=dist;found=d;}
    });
    if(found)openDr(DATA.indexOf(found));
  };
}
function drawHeat(){
  var el=document.getElementById('cHeat');if(!el)return;
  var sectors={};
  DATA.forEach(function(d){
    if(!d.sector)return;
    if(!sectors[d.sector])sectors[d.sector]={n:0,sc:0,entry:0,over:0,miss:0};
    var s=sectors[d.sector];s.n++;s.sc+=d.score;
    if(d.label==='Entry Candidate')s.entry++;
    if(d.label==='Avoid Entry Now - Overbought')s.over++;
    if(d.missing)s.miss++;
  });
  var arr=Object.keys(sectors).map(function(k){
    var s=sectors[k];return{name:k,avg:s.n?Math.round(s.sc/s.n):0,entry:s.entry,over:s.over,miss:s.miss};
  }).sort(function(a,b){return b.avg-a.avg;});
  var maxAvg=arr.length?arr[0].avg:100;
  el.innerHTML=arr.map(function(s){
    var pct=maxAvg?s.avg/maxAvg*100:0;
    var bc=s.avg>=80?'#00c853':s.avg>=65?'#ffd740':s.avg>=50?'#ff9100':'#ff5252';
    var meta=(s.entry?'🟢'+s.entry+' ':'')+(s.over?'🔴'+s.over+' ':'')+(s.miss?'□'+s.miss:'');
    return '<div class="hm-row" onclick="filterBySector(\''+e(s.name)+'\')">'
      +'<div class="hm-name">'+e(s.name)+'</div>'
      +'<div class="hm-bar-wrap"><div class="hm-bar" style="width:'+pct+'%;background:'+bc+'">'+s.avg+'</div></div>'
      +'<div class="hm-meta">'+meta+'</div></div>';
  }).join('');
}
function filterBySector(sec){
  document.getElementById('fS').value=sec;render();
  document.getElementById('tb').scrollIntoView({behavior:'smooth',block:'start'});
}
function openDr(idx){
  var d=DATA[idx];if(!d)return;
  var cw=d.conflict?'<div class="wbox" style="background:#1a0e00;border:1px solid #ff910088;color:#ff9100">⚠️ تعارض ریسک: امتیاز بالا همراه با RSI پرریسک</div>':'';
  var mw=d.missing?'<div class="wbox" style="background:#111518;border:1px solid #78909c88;color:#78909c">داده تکنیکال ناقص</div>':'';
  var sw=d.stale&&!d.missing?'<div class="wbox" style="background:#0d1117;border:1px solid #ffd74044;color:#ffd740">داده قدیمی</div>':'';
  var chg='';
  if(d.change){
    var ar=d.change==='up'?'⬆️':d.change==='down'?'⬇️':'🔄';
    chg='<div style="color:#8b949e;font-size:11px;margin-top:6px">'+ar+' از <b>'+e(d.prev_label_fa)+'</b> به <b style="color:'+e(d.label_color)+'">'+e(d.label_fa)+'</b></div>';
  }
  var sp=d.close_20d?'<canvas id="dsp" data-p="'+e(d.close_20d)+'" width="340" height="70" style="margin-top:10px;display:block"></canvas>':'';
  function r(l,v){return v?'<dt>'+l+'</dt><dd>'+e(v)+'</dd>':''}
  var vol=parseFloat(d.vol)||0;
  document.getElementById('dc').innerHTML=
    '<div style="padding-top:8px;margin-bottom:12px">'
    +'<div style="font-size:18px;font-weight:700">'+e(d.sym)+'</div>'
    +'<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
    +'<span class="badge" style="color:'+e(d.label_color)+';background:'+e(d.label_bg)+'">'+e(d.label_fa)+'</span>'
    +'<span style="color:'+e(d.grade_color)+';font-weight:700;font-size:15px">'+e(d.grade)+'</span>'
    +'<span style="color:#8b949e">امتیاز '+d.score.toFixed(0)+'</span>'
    +'</div>'+chg+'</div>'
    +cw+mw+sw
    +'<div class="wbox" style="background:#101923;border:1px solid #58a6ff55;color:#90caf9">این خروجی کاندید بررسی است و توصیه قطعی خرید/فروش نیست.</div>'
    +'<div class="dsec"><h4>کیفیت داده و هشدار ریسک</h4><dl class="dl">'
    +r('آخرین داده',d.latest_date)+r('کیفیت داده',d.data_quality)+r('هشدارها',d.risk_flags)
    +'</dl><p style="color:#8b949e;font-size:11px;line-height:1.8;margin-top:8px">'+e(d.invalidation)+'</p></div>'
    +'<div class="dsec"><h4>دلایل وضعیت/کاندید بررسی</h4><p style="color:#ccc;font-size:12px;line-height:1.8">'+e(d.reasons)+'</p></div>'
    +'<div class="dsec"><h4>عوامل امتیاز</h4><p style="color:#8b949e;font-size:11px;line-height:1.8">'+e(d.factors)+'</p></div>'
    +'<div class="dsec"><h4>مشخصات فنی</h4><dl class="dl">'
    +r('RSI',d.rsi+(d.rsi_band?' ('+d.rsi_band+')':''))
    +r('قیمت',d.price)+r('روند',d.trend?d.trend+'/6':'')
    +r('نسبت حجم',vol>0?vol.toFixed(2)+'x':'')
    +r('سکتور',d.sector)+r('حمایت',d.support)+r('مقاومت',d.resistance)
    +r('سطح ابطال',d.stop_loss)+r('هدف تحلیلی',d.target_1)+r('R/R',d.rr)
    +'</dl></div>'
    +'<div class="dsec"><h4>پول هوشمند</h4><dl class="dl">'
    +r('پول هوشمند',d.sm)+r('توضیح',d.sm_fa)+r('صف',d.q)+r('توضیح صف',d.q_fa)
    +'</dl></div>'+sp;
  document.getElementById('ov').classList.add('open');
  document.body.style.overflow='hidden';
  if(d.close_20d){
    setTimeout(function(){
      var c=document.getElementById('dsp');if(!c)return;
      var p=c.dataset.p.split(',').map(Number).filter(function(n){return n>0;});
      if(p.length<2)return;
      var ctx=c.getContext('2d'),w=c.width,h=c.height,n=p.length;
      var mn=Math.min.apply(null,p),mx=Math.max.apply(null,p),rng=mx-mn||1;
      ctx.strokeStyle=p[n-1]>=p[0]?'#00e676':'#ff5252';
      ctx.lineWidth=2;ctx.beginPath();
      p.forEach(function(v,i){var x=i/(n-1)*w,y=h-(v-mn)/rng*(h-6)-3;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
      ctx.stroke();
    },50);
  }
}
function closeDr(ev){
  if(ev&&ev.target!==document.getElementById('ov'))return;
  document.getElementById('ov').classList.remove('open');
  document.body.style.overflow='';
}
document.addEventListener('keydown',function(ev){if(ev.key==='Escape')closeDr();});
function copyPilotReport(){
  var horizons=(PERF&&PERF.horizons)?PERF.horizons:{};
  var h5=horizons['5D']||{},h10=horizons['10D']||{};
  var total=(PERF&&PERF.total_logged)||0;
  var first=(PERF&&PERF.first_signal_date)||'-';
  var last=(PERF&&PERF.last_signal_date)||'-';
  var age=(PERF&&PERF.track_age_days)||0;
  var lines=[
    'گزارش پایلوت Iran Stock AI Dashboard',
    'شروع Track Record: '+first,
    'آخرین سیگنال: '+last,
    'سن تاریخچه: '+age+' روز',
    'کل سیگنال‌های ثبت‌شده: '+total,
    'نتیجه 5D کامل: '+(h5.completed||0)+' | در انتظار 5D: '+(h5.pending||0),
    'نتیجه 10D کامل: '+(h10.completed||0)+' | در انتظار 10D: '+(h10.pending||0),
    '',
    'وضعیت اعتبارسنجی: سیستم وارد مرحله Track Record شده است. ارزیابی عملکرد فقط پس از کامل شدن پنجره‌های 5D و 10D معتبر است.',
    'مرز استفاده: خروجی‌ها کاندید بررسی هستند و توصیه قطعی خرید/فروش یا ادعای بازدهی قطعی محسوب نمی‌شوند.',
    'معیارهای قضاوت آینده: نرخ موفقیت، میانگین بازده، نتیجه 5D، نتیجه 10D و تفکیک High Confidence.'
  ];
  var text=lines.join('\n');
  function done(){
    var el=document.getElementById('pilotCopyStatus');
    if(el){el.textContent='کپی شد';setTimeout(function(){el.textContent='';},1800);}
  }
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(function(){window.prompt('گزارش پایلوت را کپی کنید:',text);});
  }else{
    window.prompt('گزارش پایلوت را کپی کنید:',text);
  }
}

function doExport(){
  var rows=[['نماد','وضعیت','رتبه','امتیاز','RSI','باند RSI','قیمت','سکتور','حجم','کیفیت داده','هشدار ریسک','پول هوشمند','صف','دلایل','سناریوی ابطال']];
  filtered().forEach(function(d){
    var vol=parseFloat(d.vol)||0;
    rows.push([d.sym,d.label_fa,d.grade,d.score.toFixed(0),d.rsi,d.rsi_band,d.price,d.sector,
      vol>0?vol.toFixed(2)+'x':'',d.data_quality,d.risk_flags,d.sm,d.q,d.reasons,d.invalidation]);
  });
  var csv=rows.map(function(r){return r.map(function(c){return'"'+String(c||'').replace(/"/g,'""')+'"'}).join(',')}).join('\n');
  var a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,﻿'+encodeURIComponent(csv);
  a.download='iran_stock_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
}
function renderPerf(){
  var rootId='perfContent';
  try{
    var current=arguments.callee.__rootId;
    if(current){rootId=current;}
  }catch(_){}
  var root=document.getElementById(rootId)||document.getElementById('performance')||document.getElementById('perfTab')||document.querySelector('[data-tab="perf"]')||document.querySelector('[data-view="perf"]');
  if(!root)return;
  var horizons=(PERF&&PERF.horizons)?PERF.horizons:{'5D':PERF||{}};
  var h5=horizons['5D']||{};
  var h10=horizons['10D']||{};
  var total=PERF&&PERF.total_logged?PERF.total_logged:((h5&&h5.total_logged)||0);
  var firstDate=(PERF&&PERF.first_signal_date)||'-';
  var lastDate=(PERF&&PERF.last_signal_date)||'-';
  var ageDays=(PERF&&PERF.track_age_days)||0;
  var next5=(PERF&&PERF.earliest_5d_review)||'-';
  var next10=(PERF&&PERF.earliest_10d_review)||'-';
  function num(v,d){v=Number(v||0);return isFinite(v)?v.toFixed(d||0):'0';}
  function pct(v){return num(v,1)+'%';}
  function card(title,value,sub,color){
    return '<div class="pcard" style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;min-height:86px">'
      +'<div style="color:#8b949e;font-size:12px">'+title+'</div>'
      +'<div style="color:'+(color||'#58a6ff')+';font-size:26px;font-weight:800;margin-top:6px">'+value+'</div>'
      +'<div style="color:#8b949e;font-size:11px;margin-top:4px">'+sub+'</div></div>';
  }
  function horizonBox(name,h){
    var completed=Number(h.completed||0), pending=Number(h.pending||0);
    var body='';
    if(completed<=0){
      body='<div style="color:#ffd740;font-weight:700;margin-top:8px">در انتظار تکمیل روزهای معاملاتی</div>'
        +'<div style="color:#8b949e;font-size:12px;line-height:1.9;margin-top:8px">برای '+name+' باید '+(name==='5D'?'5':'10')+' روز معاملاتی بعد از تاریخ سیگنال کامل شود. فعلا نتیجه قابل قضاوت ثبت نشده است.</div>';
    }else{
      body='<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:10px">'
        +card('نرخ موفقیت',pct(h.win_rate),'سیگنال‌های کامل‌شده','#00c853')
        +card('میانگین بازده',pct(h.avg_ret),'بر اساس بازده تحقق‌یافته',Number(h.avg_ret||0)>=0?'#00c853':'#ff5252')
        +card('High Confidence',pct(h.high_conf_win_rate),'تعداد: '+(h.high_conf_completed||0),'#ffd740')
        +'</div>';
    }
    return '<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:14px">'
      +'<div style="display:flex;justify-content:space-between;gap:12px;align-items:center">'
      +'<h3 style="margin:0;color:#c9d1d9;font-size:15px">Track Record '+name+'</h3>'
      +'<span style="color:#8b949e;font-size:12px">کامل‌شده: '+completed+' | در انتظار: '+pending+'</span>'
      +'</div>'+body+'</div>';
  }
  var html='<section style="padding:18px 10px 28px;max-width:1280px;margin:0 auto">'
    +'<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px 14px;margin-bottom:12px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;color:#c9d1d9;font-size:12px">'
    +'<div><span style="color:#8b949e">شروع Track Record</span><br><b style="color:#58a6ff">'+firstDate+'</b></div>'
    +'<div><span style="color:#8b949e">آخرین سیگنال</span><br><b style="color:#58a6ff">'+lastDate+'</b></div>'
    +'<div><span style="color:#8b949e">سن تاریخچه</span><br><b style="color:#ffd740">'+ageDays+' روز</b></div>'
    +'<div><span style="color:#8b949e">اولین بررسی تقریبی</span><br><b style="color:#ffab40">5D: '+next5+' | 10D: '+next10+'</b></div>'
    +'</div>'
    +'<div style="background:#101923;border:1px solid #58a6ff55;border-radius:8px;padding:13px 15px;margin-bottom:12px;color:#c9d1d9;line-height:1.9">'
    +'<div style="display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:4px">'
    +'<div style="color:#58a6ff;font-weight:800;font-size:14px">خلاصه اعتبارسنجی پایلوت</div>'
    +'<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
    +'<a href="pilot-report.html" target="_blank" style="background:#1f6feb;border:1px solid #388bfd;color:#fff;border-radius:6px;padding:6px 10px;font-size:12px;text-decoration:none">مشاهده گزارش رسمی</a>'
    +'<button type="button" onclick="copyPilotReport()" style="background:#238636;border:1px solid #2ea043;color:#fff;border-radius:6px;padding:6px 10px;font-size:12px;cursor:pointer">کپی گزارش پایلوت</button>'
    +'</div>'
    +'</div>'
    +'<div id="pilotCopyStatus" style="color:#00c853;font-size:11px;height:16px;margin-bottom:2px"></div>'
    +'<div style="font-size:12px;color:#c9d1d9">این سیستم وارد مرحله Track Record شده است. سیگنال‌ها ثبت می‌شوند، اما ارزیابی عملکرد فقط پس از کامل شدن پنجره‌های 5D و 10D معتبر است. تا قبل از تکمیل این پنجره‌ها، خروجی‌ها صرفا کاندید بررسی هستند و ادعای بازدهی قطعی ندارند.</div>'
    +'<div style="margin-top:7px;font-size:11px;color:#8b949e">معیارهای قضاوت آینده: نرخ موفقیت، میانگین بازده، نتیجه 5D، نتیجه 10D و تفکیک High Confidence.</div>'
    +'</div>'
    +'<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px">'
    +card('کل سیگنال‌های ثبت‌شده',String(total),'خوانده‌شده از signal_log.csv','#58a6ff')
    +card('نتیجه 5D کامل',String(h5.completed||0),'آماده ارزیابی','#00c853')
    +card('در انتظار 5D',String(h5.pending||0),'پس از 5 روز معاملاتی کامل می‌شود','#ffab40')
    +card('در انتظار 10D',String(h10.pending||0),'پس از 10 روز معاملاتی کامل می‌شود','#ffd740')
    +'</div>'
    +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'+horizonBox('5D',h5)+horizonBox('10D',h10)+'</div>'
    +'<div style="margin-top:14px;color:#8b949e;font-size:12px;line-height:1.9;text-align:center">این بخش سابقه عملکرد را پس از کامل شدن روزهای معاملاتی نشان می‌دهد و توصیه قطعی خرید/فروش نیست.</div>'
    +'</section>';
  root.innerHTML=html;
}
function drawEquity(curve,canvasId){
  var c=document.getElementById(canvasId||'eqCurve');if(!c)return;
  var dpr=window.devicePixelRatio||1,W=c.offsetWidth,H=c.offsetHeight||140;
  c.width=W*dpr;c.height=H*dpr;
  var ctx=c.getContext('2d');ctx.scale(dpr,dpr);
  var vals=curve.map(function(p){return p.e;}),dates=curve.map(function(p){return p.d;}),n=vals.length;
  var mn=Math.min.apply(null,vals),mx=Math.max.apply(null,vals);
  var pad={t:12,r:8,b:24,l:44},cw=W-pad.l-pad.r,ch=H-pad.t-pad.b;
  function xp(i){return pad.l+i/(n-1)*cw;}
  function yp(v){return pad.t+ch-(v-mn)/((mx-mn)||1)*ch;}
  ctx.strokeStyle='#30363d';ctx.lineWidth=1;ctx.setLineDash([3,3]);
  ctx.beginPath();ctx.moveTo(pad.l,yp(100));ctx.lineTo(pad.l+cw,yp(100));ctx.stroke();
  ctx.setLineDash([]);
  var isUp=vals[n-1]>=100;
  var grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ch);
  grad.addColorStop(0,isUp?'rgba(0,200,83,.3)':'rgba(255,82,82,.3)');
  grad.addColorStop(1,'rgba(0,0,0,0)');
  ctx.beginPath();ctx.moveTo(xp(0),yp(vals[0]));
  for(var i=1;i<n;i++)ctx.lineTo(xp(i),yp(vals[i]));
  ctx.lineTo(xp(n-1),pad.t+ch);ctx.lineTo(xp(0),pad.t+ch);ctx.closePath();
  ctx.fillStyle=grad;ctx.fill();
  ctx.beginPath();ctx.lineWidth=2;ctx.strokeStyle=isUp?'#00c853':'#ff5252';
  ctx.moveTo(xp(0),yp(vals[0]));
  for(var j=1;j<n;j++)ctx.lineTo(xp(j),yp(vals[j]));
  ctx.stroke();
  ctx.fillStyle='#8b949e';ctx.font='10px sans-serif';ctx.textAlign='right';
  ctx.fillText(mn.toFixed(1),pad.l-3,yp(mn)+3);ctx.fillText(mx.toFixed(1),pad.l-3,yp(mx)+3);
  ctx.textAlign='center';ctx.font='9px sans-serif';
  ctx.fillText(dates[0],xp(0),H-6);ctx.fillText(dates[n-1],xp(n-1),H-6);
  var lx=xp(n-1),ly=yp(vals[n-1]);
  ctx.beginPath();ctx.arc(lx,ly,4,0,Math.PI*2);ctx.fillStyle=isUp?'#00c853':'#ff5252';ctx.fill();
  ctx.fillStyle='#fff';ctx.font='bold 10px sans-serif';ctx.textAlign='left';
  ctx.fillText(vals[n-1].toFixed(1),lx+6,ly+4);
}
function drawRollingWR(rwr){
  var c=document.getElementById('rwrChart');if(!c)return;
  var dpr=window.devicePixelRatio||1,W=c.offsetWidth,H=c.offsetHeight||140;
  c.width=W*dpr;c.height=H*dpr;
  var ctx=c.getContext('2d');ctx.scale(dpr,dpr);
  var vals=rwr.map(function(p){return p.wr;}),dates=rwr.map(function(p){return p.d;}),n=vals.length;
  var pad={t:12,r:8,b:24,l:36},cw=W-pad.l-pad.r,ch=H-pad.t-pad.b;
  function xp(i){return pad.l+i/(n-1)*cw;}
  function yp(v){return pad.t+ch-(v/100)*ch;}
  [[50,'#30363d'],[60,'#1f3a1f']].forEach(function(pair){
    ctx.strokeStyle=pair[1];ctx.lineWidth=1;ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(pad.l,yp(pair[0]));ctx.lineTo(pad.l+cw,yp(pair[0]));ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle='#484f58';ctx.font='9px sans-serif';ctx.textAlign='right';
    ctx.fillText(pair[0]+'%',pad.l-2,yp(pair[0])+3);
  });
  var grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ch);
  grad.addColorStop(0,'rgba(88,166,255,.25)');grad.addColorStop(1,'rgba(0,0,0,0)');
  ctx.beginPath();ctx.moveTo(xp(0),yp(vals[0]));
  for(var i=1;i<n;i++)ctx.lineTo(xp(i),yp(vals[i]));
  ctx.lineTo(xp(n-1),pad.t+ch);ctx.lineTo(xp(0),pad.t+ch);ctx.closePath();
  ctx.fillStyle=grad;ctx.fill();
  ctx.beginPath();ctx.lineWidth=2;ctx.strokeStyle='#58a6ff';
  ctx.moveTo(xp(0),yp(vals[0]));
  for(var j=1;j<n;j++)ctx.lineTo(xp(j),yp(vals[j]));
  ctx.stroke();
  ctx.textAlign='center';ctx.font='9px sans-serif';ctx.fillStyle='#8b949e';
  ctx.fillText(dates[0],xp(0),H-6);ctx.fillText(dates[n-1],xp(n-1),H-6);
  var lx=xp(n-1),ly=yp(vals[n-1]);
  ctx.beginPath();ctx.arc(lx,ly,4,0,Math.PI*2);ctx.fillStyle='#58a6ff';ctx.fill();
  ctx.fillStyle='#fff';ctx.font='bold 10px sans-serif';ctx.textAlign='left';
  ctx.fillText(vals[n-1]+'%',lx+6,ly+4);
}
function openSymDrill(sym){
  var trades=(PERF.by_symbol||{})[sym];if(!trades||!trades.length)return;
  var wins=trades.filter(function(t){return t.win;}).length;
  var wr=Math.round(wins/trades.length*100);
  var avgRet=trades.reduce(function(s,t){return s+t.ret;},0)/trades.length;
  var wrColor=wr>=60?'#00c853':wr>=45?'#ffd740':'#ff5252';
  var arColor=avgRet>0?'#00c853':avgRet<0?'#ff5252':'#aaa';
  var lc={'ورود قوی':'#00c853','ورود':'#69f0ae'};
  var rows=trades.slice().reverse().map(function(t){
    var rc=t.ret>0?'#00c853':t.ret<0?'#ff5252':'#aaa';
    return '<tr><td>'+e(t.label_fa)+'</td><td>'+e(t.grade)+'</td><td>'+e(t.date.slice(0,10))+'</td>'
      +'<td>'+e(t.entry)+'</td><td>'+e(t.exit)+'</td>'
      +'<td style="color:'+rc+';font-weight:600">'+(t.ret>0?'+':'')+t.ret+'%</td></tr>';
  }).join('');
  var eq=100,symCurve=trades.map(function(t){eq*=(1+t.ret/100);return {d:t.date.slice(0,10),e:Math.round(eq*100)/100};});
  document.getElementById('dc').innerHTML=
    '<div style="margin-bottom:12px">'
    +'<div style="font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:6px">📌 '+e(sym)+'</div>'
    +'<div style="display:flex;gap:18px;font-size:12px;margin-bottom:14px">'
    +'<span>معاملات: <b style="color:#c9d1d9">'+trades.length+'</b></span>'
    +'<span>موفق: <b style="color:'+wrColor+'">'+wr+'%</b></span>'
    +'<span>میانگین: <b style="color:'+arColor+'">'+(avgRet>0?'+':'')+avgRet.toFixed(2)+'%</b></span></div>'
    +(symCurve.length>1?'<canvas id="symEq" style="width:100%;height:100px;display:block;margin-bottom:12px"></canvas>':'')
    +'<table class="recent-table"><thead><tr><th>وضعیت</th><th>رتبه</th><th>تاریخ</th><th>ورود</th><th>خروج</th><th>بازده</th></tr></thead>'
    +'<tbody>'+rows+'</tbody></table></div>';
  document.getElementById('ov').classList.add('open');
  document.body.style.overflow='hidden';
  if(symCurve.length>1)setTimeout(function(){
    drawEquity([{d:'شروع',e:100}].concat(symCurve),'symEq');
  },0);
}
document.getElementById('a3').textContent='↓';
window.addEventListener('resize',function(){drawDist();drawScatter();drawHeat();});
render();
"""


def run():
    if not os.path.exists(DECISION_REPORT_CSV):
        print(f"[dashboard] {DECISION_REPORT_CSV} not found")
        return
    rows = []
    with open(DECISION_REPORT_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    rows.sort(key=lambda r: _f(r.get("confidence_score",0)), reverse=True)
    prev  = load_prev_labels()
    data  = build_data(rows, prev)
    kpi   = calc_kpi(data)
    perf  = load_perf_data()
    gen   = datetime.now().strftime("%Y-%m-%d %H:%M")
    page  = build_html(data, gen, kpi, perf)
    js    = build_js()
    report = build_pilot_report_html(perf, gen)
    os.makedirs("docs", exist_ok=True)
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(page)
    with open(JS_PATH, "w", encoding="utf-8") as f:
        f.write(js)
    with open(PILOT_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[dashboard] -> {DASHBOARD_PATH} + {JS_PATH} + {PILOT_REPORT_PATH} | {len(rows)} symbols")


if __name__ == "__main__":
    run()
