"""
Backtest Engine — evaluates historical signal accuracy.

Uses local history CSV files (HISTORY_DIR) to find the actual price
N trading days after each signal, then computes accuracy per label and grade.
"""

import os
import pandas as pd
from datetime import datetime

from config.settings import DATA_DIR, HISTORY_DIR

SIGNAL_LOG = os.path.join(DATA_DIR, "signal_log.csv")
BULLISH_LABELS = {"Entry Candidate", "Technical Entry Watch"}
BEARISH_LABELS = {"Avoid Entry Now - Overbought"}


def _load_log() -> pd.DataFrame:
    if os.path.exists(SIGNAL_LOG):
        return pd.read_csv(SIGNAL_LOG)
    return pd.DataFrame()


def _save_log(df: pd.DataFrame):
    df.to_csv(SIGNAL_LOG, index=False, encoding="utf-8-sig")


def _get_price_after(symbol: str, signal_date: str, trading_days: int = 5):
    """
    Returns the closing price N trading days after signal_date,
    using the local history CSV for that symbol.
    """
    path = os.path.join(HISTORY_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        if "close" not in df.columns:
            return None

        # Try to find a date column
        date_col = None
        for col in ["date", "jdate", "j_date", "shamsi"]:
            if col in df.columns:
                date_col = col
                break
        if date_col is None:
            return None

        df[date_col] = df[date_col].astype(str).str.strip()
        df = df.sort_values(date_col).reset_index(drop=True)

        # Find index of signal date (or first date after it)
        signal_idx = None
        for i, row in df.iterrows():
            if str(row[date_col]) >= signal_date:
                signal_idx = i
                break

        if signal_idx is None:
            return None

        target_idx = signal_idx + trading_days
        if target_idx >= len(df):
            return None

        return float(df.at[target_idx, "close"])
    except Exception:
        return None


def fill_outcomes(trading_days: int = 5):
    """
    Fills in close_5d_later for signals that are old enough,
    using actual historical prices instead of current price proxy.
    """
    log = _load_log()
    if log.empty:
        print("[backtest] No signals in log yet")
        return

    updated = 0
    for idx, row in log.iterrows():
        if pd.notna(row.get("close_5d_later")):
            continue  # already filled

        signal_date = str(row["date"])
        symbol = str(row["symbol"])
        close_at = row.get("close_at_signal")
        label = str(row.get("decision_label", ""))

        price_after = _get_price_after(symbol, signal_date, trading_days)
        if price_after is None or not close_at or pd.isna(close_at):
            continue

        try:
            ret = (float(price_after) / float(close_at) - 1) * 100
            log.at[idx, "close_5d_later"] = price_after
            log.at[idx, "return_5d_pct"] = round(ret, 2)
            if label in BULLISH_LABELS:
                log.at[idx, "was_correct"] = ret > 0
            elif label in BEARISH_LABELS:
                log.at[idx, "was_correct"] = ret < 0
            updated += 1
        except Exception:
            pass

    if updated:
        _save_log(log)
        print(f"[backtest] Filled outcomes for {updated} signals")
    else:
        print("[backtest] No new outcomes to fill")


def generate_report() -> str:
    """
    Generates a Persian backtest accuracy report grouped by label and grade.
    """
    log = _load_log()
    if log.empty:
        return "📊 سیگنالی در لاگ یافت نشد"

    evaluated = log[log["was_correct"].notna()].copy()
    if evaluated.empty:
        return "📊 هنوز نتیجه‌ای برای ارزیابی ثبت نشده (سیگنال‌ها کمتر از ۵ روز قدیمی هستند)"

    total = len(evaluated)
    correct = int(evaluated["was_correct"].sum())
    accuracy = correct / total * 100

    lines = [
        f"📊 گزارش بک‌تست سیگنال‌ها",
        f"─────────────────────",
        f"کل سیگنال‌های ارزیابی‌شده: {total}",
        f"دقت کلی: {accuracy:.1f}%  ({correct}/{total})",
        f"",
        f"📌 دقت به تفکیک برچسب:",
    ]

    LABEL_FA = {
        "Entry Candidate": "کاندید ورود",
        "Technical Entry Watch": "واچ تکنیکال",
        "Avoid Entry Now - Overbought": "اشباع خرید (شرت)",
    }

    by_label = evaluated.groupby("decision_label")["was_correct"].agg(["sum", "count"])
    for label, row in by_label.iterrows():
        label_fa = LABEL_FA.get(label, label)
        acc = row["sum"] / row["count"] * 100
        lines.append(f"  {label_fa}: {acc:.0f}%  ({int(row['sum'])}/{int(row['count'])})")

    lines += ["", "🏅 دقت به تفکیک درجه:"]
    by_grade = evaluated.groupby("confidence_grade")["was_correct"].agg(["sum", "count"])
    for grade, row in by_grade.sort_index().iterrows():
        acc = row["sum"] / row["count"] * 100
        lines.append(f"  درجه {grade}: {acc:.0f}%  ({int(row['sum'])}/{int(row['count'])})")

    # Best and worst signals
    evaluated["return_5d_pct"] = pd.to_numeric(evaluated["return_5d_pct"], errors="coerce")
    top = evaluated.nlargest(3, "return_5d_pct")[["symbol", "date", "decision_label", "return_5d_pct"]]
    worst = evaluated.nsmallest(3, "return_5d_pct")[["symbol", "date", "decision_label", "return_5d_pct"]]

    lines += ["", "🏆 بهترین سیگنال‌ها:"]
    for _, r in top.iterrows():
        lines.append(f"  {r['symbol']} ({r['date']}): {r['return_5d_pct']:+.1f}%")

    lines += ["", "⚠️ ضعیف‌ترین سیگنال‌ها:"]
    for _, r in worst.iterrows():
        lines.append(f"  {r['symbol']} ({r['date']}): {r['return_5d_pct']:+.1f}%")

    return "\n".join(lines)


def run():
    print("[backtest] Filling outcomes from history files...")
    fill_outcomes(trading_days=5)
    print()
    print(generate_report())


if __name__ == "__main__":
    run()