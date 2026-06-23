"""
Backtest Engine — fills outcome prices using actual historical CSVs.
"""

import os
import pandas as pd

SIGNAL_LOG = os.path.join("output", "signal_log.csv")
HISTORY_DIR = os.path.join("data", "history")


def _get_price_after(symbol: str, signal_date: str, trading_days: int = 5) -> float | None:
    path = os.path.join(HISTORY_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        if "date" not in df.columns or "close" not in df.columns:
            return None
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        sig_dt = pd.to_datetime(signal_date)
        future = df[df["date"] > sig_dt].reset_index(drop=True)
        if len(future) < trading_days:
            return None
        return float(future["close"].iloc[trading_days - 1])
    except Exception:
        return None


def fill_outcomes(trading_days: int = 5) -> int:
    """Read signal_log.csv, fill close_5d_later for rows that don't have it yet."""
    if not os.path.exists(SIGNAL_LOG):
        return 0
    df = pd.read_csv(SIGNAL_LOG)
    if "close_5d_later" not in df.columns:
        df["close_5d_later"] = None
    filled = 0
    for i, row in df.iterrows():
        if pd.notna(df.at[i, "close_5d_later"]):
            continue
        symbol = str(row.get("symbol", ""))
        date = str(row.get("date", ""))
        if not symbol or not date:
            continue
        price = _get_price_after(symbol, date, trading_days)
        if price is not None:
            df.at[i, "close_5d_later"] = price
            filled += 1
    df.to_csv(SIGNAL_LOG, index=False)
    return filled


def generate_report() -> str:
    """Generate Persian accuracy report grouped by label and grade."""
    if not os.path.exists(SIGNAL_LOG):
        return "❌ فایل signal_log.csv یافت نشد."
    df = pd.read_csv(SIGNAL_LOG)
    required = {"label", "close_price", "close_5d_later"}
    if not required.issubset(df.columns):
        return "❌ ستون‌های لازم در لاگ وجود ندارند."
    df = df.dropna(subset=["close_price", "close_5d_later"]).copy()
    if df.empty:
        return "⚠️ هنوز داده‌ای برای بک‌تست وجود ندارد."
    df["close_price"] = pd.to_numeric(df["close_price"], errors="coerce")
    df["close_5d_later"] = pd.to_numeric(df["close_5d_later"], errors="coerce")
    df = df.dropna(subset=["close_price", "close_5d_later"])
    df["return_5d"] = (df["close_5d_later"] / df["close_price"] - 1) * 100
    lines = ["📊 گزارش دقت سیگنال (بک‌تست ۵ روزه)\n", f"تعداد کل سیگنال با نتیجه: {len(df)}\n"]
    for label, group in df.groupby("label"):
        pos = (group["return_5d"] > 0).sum()
        neg = (group["return_5d"] <= 0).sum()
        total = len(group)
        avg_ret = group["return_5d"].mean()
        win_rate = pos / total * 100 if total > 0 else 0
        lines.append(
            f"🏷 {label}: {total} سیگنال | "
            f"✅ {pos} موفق | ❌ {neg} ناموفق | "
            f"نرخ موفقیت: {win_rate:.0f}% | "
            f"میانگین بازده: {avg_ret:+.1f}%"
        )
    if "grade" in df.columns:
        lines.append("\nبر اساس درجه:")
        for grade, group in df.groupby("grade"):
            total = len(group)
            avg_ret = group["return_5d"].mean()
            win_rate = (group["return_5d"] > 0).sum() / total * 100 if total > 0 else 0
            lines.append(
                f"  درجه {grade}: {total} سیگنال | "
                f"نرخ موفقیت: {win_rate:.0f}% | "
                f"میانگین بازده: {avg_ret:+.1f}%"
            )
    return "\n".join(lines)


def run():
    filled = fill_outcomes(trading_days=5)
    print(f"Filled {filled} outcomes.")
    print(generate_report())