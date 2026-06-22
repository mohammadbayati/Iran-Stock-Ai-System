"""
Layer 6 — Self-Learning Signal Tracker

Logs every signal generated, then on the next run checks
whether the 5-day outcome was positive. Builds a running
accuracy record so you know if the system is actually working.

Log file: data/signal_log.csv
"""

import os
import pandas as pd
from datetime import datetime, timedelta

from config.settings import DATA_DIR

SIGNAL_LOG = os.path.join(DATA_DIR, "signal_log.csv")

BULLISH_LABELS = {"Entry Candidate", "Technical Entry Watch"}
BEARISH_LABELS = {"Avoid Entry Now - Overbought"}

LOG_COLUMNS = [
    "date", "symbol", "decision_label", "confidence_score",
    "confidence_grade", "close_at_signal", "close_5d_later",
    "return_5d_pct", "was_correct",
]


def _load_log() -> pd.DataFrame:
    if os.path.exists(SIGNAL_LOG):
        return pd.read_csv(SIGNAL_LOG)
    return pd.DataFrame(columns=LOG_COLUMNS)


def _save_log(df: pd.DataFrame):
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(SIGNAL_LOG, index=False, encoding="utf-8-sig")


def log_signals(report_df: pd.DataFrame):
    log = _load_log()
    today = datetime.now().strftime("%Y-%m-%d")

    new_rows = []
    for _, row in report_df.iterrows():
        symbol = str(row.get("symbol", ""))
        label = str(row.get("decision_label", ""))
        conf = row.get("confidence_score", 0)
        grade = row.get("confidence_grade", "")
        close = row.get("latest_close", None)

        already = log[(log["date"] == today) & (log["symbol"] == symbol)]
        if not already.empty:
            continue

        new_rows.append({
            "date": today,
            "symbol": symbol,
            "decision_label": label,
            "confidence_score": conf,
            "confidence_grade": grade,
            "close_at_signal": close,
            "close_5d_later": None,
            "return_5d_pct": None,
            "was_correct": None,
        })

    if new_rows:
        log = pd.concat([log, pd.DataFrame(new_rows)], ignore_index=True)
        _save_log(log)
        print(f"[signal_tracker] Logged {len(new_rows)} new signals")


def update_outcomes(report_df: pd.DataFrame):
    log = _load_log()
    if log.empty:
        return

    cutoff = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
    price_lookup = {str(r["symbol"]): r.get("latest_close") for _, r in report_df.iterrows()}

    updated = 0
    for idx, row in log.iterrows():
        if pd.isna(row.get("close_5d_later")) and str(row["date"]) <= cutoff:
            sym = str(row["symbol"])
            current_price = price_lookup.get(sym)
            if current_price and row.get("close_at_signal"):
                try:
                    ret = (float(current_price) / float(row["close_at_signal"]) - 1) * 100
                    log.at[idx, "close_5d_later"] = current_price
                    log.at[idx, "return_5d_pct"] = round(ret, 2)
                    label = str(row["decision_label"])
                    if label in BULLISH_LABELS:
                        log.at[idx, "was_correct"] = ret > 0
                    elif label in BEARISH_LABELS:
                        log.at[idx, "was_correct"] = ret < 0
                    updated += 1
                except Exception:
                    pass

    if updated:
        _save_log(log)
        print(f"[signal_tracker] Updated outcomes for {updated} signals")


def get_status_changes(report_df: pd.DataFrame) -> list[dict]:
    """
    Compare today's decision_label to yesterday's for each symbol.
    Returns list of symbols that changed label.
    """
    log = _load_log()
    if log.empty:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday_rows = log[log["date"] < today].sort_values("date", ascending=False)

    if yesterday_rows.empty:
        return []

    prev_labels = (
        yesterday_rows.groupby("symbol")
        .first()
        .reset_index()[["symbol", "decision_label"]]
    )
    prev_lookup = dict(zip(prev_labels["symbol"], prev_labels["decision_label"]))

    UPGRADE = {
        ("Missing Technical Data", "Entry Candidate"),
        ("Watch Only", "Entry Candidate"),
        ("Watch - Needs Volume Confirmation", "Entry Candidate"),
        ("Technical Entry Watch", "Entry Candidate"),
        ("Wait for Pullback", "Entry Candidate"),
        ("Watch Only", "Technical Entry Watch"),
        ("Watch - Needs Volume Confirmation", "Technical Entry Watch"),
        ("Missing Technical Data", "Technical Entry Watch"),
    }

    changes = []
    for _, row in report_df.iterrows():
        symbol = str(row.get("symbol", ""))
        curr_label = str(row.get("decision_label", ""))
        prev_label = prev_lookup.get(symbol)
        if prev_label and prev_label != curr_label:
            is_upgrade = (prev_label, curr_label) in UPGRADE
            changes.append({
                "symbol": symbol,
                "prev_label": prev_label,
                "curr_label": curr_label,
                "is_upgrade": is_upgrade,
                "confidence_score": row.get("confidence_score", 0),
            })

    return sorted(changes, key=lambda x: (not x["is_upgrade"], -x["confidence_score"]))


def format_status_changes(changes: list[dict]) -> str:
    if not changes:
        return ""

    upgrades = [c for c in changes if c["is_upgrade"]]
    downgrades = [c for c in changes if not c["is_upgrade"]]

    LABEL_SHORT = {
        "Entry Candidate": "کاندید ورود",
        "Technical Entry Watch": "واچ تکنیکال",
        "Wait for Pullback": "صبر پولبک",
        "Avoid Entry Now - Overbought": "اشباع خرید",
        "Watch - Needs Volume Confirmation": "نیاز به حجم",
        "Watch Only": "فقط رصد",
        "Missing Technical Data": "داده ناقص",
    }

    lines = ["🔔 تغییر وضعیت نمادها:"]
    for c in upgrades:
        prev = LABEL_SHORT.get(c["prev_label"], c["prev_label"])
        curr = LABEL_SHORT.get(c["curr_label"], c["curr_label"])
        lines.append(f"  ⬆️ *{c['symbol']}*: {prev} → {curr} (امتیاز: {c['confidence_score']})")
    for c in downgrades:
        prev = LABEL_SHORT.get(c["prev_label"], c["prev_label"])
        curr = LABEL_SHORT.get(c["curr_label"], c["curr_label"])
        lines.append(f"  ⬇️ {c['symbol']}: {prev} → {curr}")

    return "\n".join(lines)


def get_accuracy_summary() -> str:
    log = _load_log()
    evaluated = log[log["was_correct"].notna()]

    if evaluated.empty:
        return "📊 هنوز نتیجه‌ای برای ارزیابی دقت سیگنال‌ها ثبت نشده"

    total = len(evaluated)
    correct = evaluated["was_correct"].sum()
    accuracy = correct / total * 100

    by_label = evaluated.groupby("decision_label")["was_correct"].agg(["sum", "count"])

    lines = [f"🎯 دقت سیگنال‌ها ({total} سیگنال ارزیابی‌شده):"]
    lines.append(f"  کل دقت: {accuracy:.0f}%  ({int(correct)}/{total})")

    for label, row in by_label.iterrows():
        label_acc = row["sum"] / row["count"] * 100
        lines.append(f"  {label}: {label_acc:.0f}% ({int(row['sum'])}/{int(row['count'])})")

    return "\n".join(lines)