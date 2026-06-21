import os
import pandas as pd
from datetime import datetime, timedelta

DATA_DIR = "data"
SIGNAL_LOG = os.path.join(DATA_DIR, "signal_log.csv")
BULLISH_LABELS = {"Entry Candidate", "Technical Entry Watch"}
BEARISH_LABELS = {"Avoid Entry Now - Overbought"}

LOG_COLUMNS = ["date", "symbol", "decision_label", "confidence_score",
               "confidence_grade", "close_at_signal", "close_5d_later",
               "return_5d_pct", "was_correct"]


def _load_log():
    if os.path.exists(SIGNAL_LOG):
        return pd.read_csv(SIGNAL_LOG)
    return pd.DataFrame(columns=LOG_COLUMNS)


def _save_log(df):
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(SIGNAL_LOG, index=False, encoding="utf-8-sig")


def log_signals(report_df):
    log = _load_log()
    today = datetime.now().strftime("%Y-%m-%d")
    new_rows = []

    for _, row in report_df.iterrows():
        symbol = str(row.get("symbol", ""))
        already = log[(log["date"] == today) & (log["symbol"] == symbol)]
        if not already.empty:
            continue
        new_rows.append({
            "date": today, "symbol": symbol,
            "decision_label": str(row.get("decision_label", "")),
            "confidence_score": row.get("confidence_score", 0),
            "confidence_grade": row.get("confidence_grade", ""),
            "close_at_signal": row.get("latest_close", None),
            "close_5d_later": None, "return_5d_pct": None, "was_correct": None,
        })

    if new_rows:
        log = pd.concat([log, pd.DataFrame(new_rows)], ignore_index=True)
        _save_log(log)
        print(f"[signal_tracker] Logged {len(new_rows)} signals")


def update_outcomes(report_df):
    log = _load_log()
    if log.empty:
        return
    cutoff = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
    price_lookup = {str(r["symbol"]): r.get("latest_close") for _, r in report_df.iterrows()}
    updated = 0
    for idx, row in log.iterrows():
        if pd.isna(row.get("close_5d_later")) and str(row["date"]) <= cutoff:
            sym = str(row["symbol"])
            price = price_lookup.get(sym)
            if price and row.get("close_at_signal"):
                try:
                    ret = (float(price) / float(row["close_at_signal"]) - 1) * 100
                    log.at[idx, "close_5d_later"] = price
                    log.at[idx, "return_5d_pct"] = round(ret, 2)
                    log.at[idx, "was_correct"] = ret > 0 if row["decision_label"] in BULLISH_LABELS else ret < 0
                    updated += 1
                except Exception:
                    pass
    if updated:
        _save_log(log)
        print(f"[signal_tracker] Updated {updated} outcomes")


def get_accuracy_summary() -> str:
    log = _load_log()
    evaluated = log[log["was_correct"].notna()]
    if evaluated.empty:
        return "📊 هنوز نتیجه‌ای برای ارزیابی دقت ثبت نشده"
    total = len(evaluated)
    correct = int(evaluated["was_correct"].sum())
    acc = correct / total * 100
    return f"🎯 دقت سیگنال‌ها: {acc:.0f}% ({correct}/{total})"