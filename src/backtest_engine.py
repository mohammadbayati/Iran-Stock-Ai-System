"""
Backtest Engine — fills outcome prices using actual historical CSVs,
and computes alpha vs the TSE benchmark index (شاخص کل / هم وزن).
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DATA_DIR
SIGNAL_LOG = os.path.join(DATA_DIR, "signal_log.csv")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
BENCHMARK_NAME = "شاخص کل"


def _load_history_df(symbol: str) -> pd.DataFrame | None:
    path = os.path.join(HISTORY_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        if "date" not in df.columns or "close" not in df.columns:
            return None
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    except Exception:
        return None


def _get_price_after(symbol: str, signal_date: str, trading_days: int = 5) -> float | None:
    df = _load_history_df(symbol)
    if df is None:
        return None
    sig_dt = pd.to_datetime(signal_date)
    future = df[df["date"] > sig_dt].reset_index(drop=True)
    if len(future) < trading_days:
        return None
    return float(future["close"].iloc[trading_days - 1])


def _get_benchmark_return(signal_date: str, trading_days: int) -> float | None:
    """Return شاخص کل return (%) over the same window as the signal, or None if not available."""
    df = _load_history_df(BENCHMARK_NAME)
    if df is None:
        return None
    sig_dt = pd.to_datetime(signal_date)

    entry_rows = df[df["date"] <= sig_dt]
    if entry_rows.empty:
        return None
    entry_price = float(entry_rows["close"].iloc[-1])

    future = df[df["date"] > sig_dt].reset_index(drop=True)
    if len(future) < trading_days:
        return None
    later_price = float(future["close"].iloc[trading_days - 1])

    if not entry_price:
        return None
    return (later_price / entry_price - 1) * 100


def fill_outcomes(trading_days: int = 5) -> int:
    """Read signal_log.csv and fill forward outcome + alpha columns for a given horizon."""
    if not os.path.exists(SIGNAL_LOG):
        return 0
    df = pd.read_csv(SIGNAL_LOG)
    close_col = f"close_{trading_days}d_later"
    return_col = f"return_{trading_days}d_pct"
    correct_col = "was_correct" if trading_days == 5 else f"was_correct_{trading_days}d"
    bench_col = f"benchmark_return_{trading_days}d_pct"
    alpha_col = f"alpha_{trading_days}d_pct"

    for col in [close_col, return_col, correct_col, bench_col, alpha_col]:
        if col not in df.columns:
            df[col] = None
    df[correct_col] = df[correct_col].astype("object")

    filled = 0
    for i, row in df.iterrows():
        if pd.notna(df.at[i, close_col]):
            continue
        symbol = str(row.get("symbol", ""))
        date = str(row.get("date", ""))
        entry = row.get("close_at_signal", "")
        if not symbol or not date or pd.isna(entry):
            continue
        price = _get_price_after(symbol, date, trading_days)
        if price is None:
            continue
        try:
            entry_price = float(entry)
            ret = (float(price) / entry_price - 1) * 100
        except Exception:
            continue

        label = str(row.get("decision_label", ""))
        if label in {"Entry Candidate", "Technical Entry Watch"}:
            correct = ret > 0
        elif label in {"Avoid Entry Now - Overbought"}:
            correct = ret < 0
        else:
            correct = None

        df.at[i, close_col] = price
        df.at[i, return_col] = round(ret, 2)
        df.at[i, correct_col] = correct

        bench_ret = _get_benchmark_return(date, trading_days)
        if bench_ret is not None:
            df.at[i, bench_col] = round(bench_ret, 2)
            df.at[i, alpha_col] = round(ret - bench_ret, 2)

        filled += 1

    df.to_csv(SIGNAL_LOG, index=False, encoding="utf-8-sig")
    return filled


def generate_report() -> str:
    """Generate Persian accuracy + alpha report grouped by label and grade."""
    if not os.path.exists(SIGNAL_LOG):
        return "❌ فایل signal_log.csv یافت نشد."
    df = pd.read_csv(SIGNAL_LOG)
    required = {"decision_label", "close_at_signal", "close_5d_later"}
    if not required.issubset(df.columns):
        return "❌ ستون‌های لازم در لاگ وجود ندارند."
    df = df.dropna(subset=["close_at_signal", "close_5d_later"]).copy()
    if df.empty:
        return "⚠️ هنوز داده‌ای برای بک‌تست وجود ندارد."
    df["close_at_signal"] = pd.to_numeric(df["close_at_signal"], errors="coerce")
    df["close_5d_later"] = pd.to_numeric(df["close_5d_later"], errors="coerce")
    df = df.dropna(subset=["close_at_signal", "close_5d_later"])
    df["return_5d"] = (df["close_5d_later"] / df["close_at_signal"] - 1) * 100

    has_alpha = "alpha_5d_pct" in df.columns and df["alpha_5d_pct"].notna().any()

    lines = ["📊 گزارش دقت سیگنال (بک‌تست ۵ روزه)\n", f"تعداد کل سیگنال با نتیجه: {len(df)}\n"]
    for label, group in df.groupby("decision_label"):
        pos = (group["return_5d"] > 0).sum()
        neg = (group["return_5d"] <= 0).sum()
        total = len(group)
        avg_ret = group["return_5d"].mean()
        win_rate = pos / total * 100 if total > 0 else 0
        line = (
            f"🏷 {label}: {total} سیگنال | "
            f"✅ {pos} موفق | ❌ {neg} ناموفق | "
            f"نرخ موفقیت: {win_rate:.0f}% | "
            f"میانگین بازده: {avg_ret:+.1f}%"
        )
        if has_alpha:
            alpha_group = group["alpha_5d_pct"].dropna()
            if not alpha_group.empty:
                line += f" | Alpha: {alpha_group.mean():+.1f}%"
        lines.append(line)

    if "confidence_grade" in df.columns:
        lines.append("\nبر اساس درجه:")
        for grade, group in df.groupby("confidence_grade"):
            total = len(group)
            avg_ret = group["return_5d"].mean()
            win_rate = (group["return_5d"] > 0).sum() / total * 100 if total > 0 else 0
            line = (
                f"  درجه {grade}: {total} سیگنال | "
                f"نرخ موفقیت: {win_rate:.0f}% | "
                f"میانگین بازده: {avg_ret:+.1f}%"
            )
            if has_alpha:
                alpha_group = group["alpha_5d_pct"].dropna()
                if not alpha_group.empty:
                    line += f" | Alpha: {alpha_group.mean():+.1f}%"
            lines.append(line)

    if has_alpha:
        overall_alpha = df["alpha_5d_pct"].dropna()
        if not overall_alpha.empty:
            lines.append(f"\n📈 میانگین Alpha کل نسبت به شاخص کل: {overall_alpha.mean():+.1f}% ({len(overall_alpha)} سیگنال)")

    return "\n".join(lines)


def run():
    filled_5d = fill_outcomes(trading_days=5)
    filled_10d = fill_outcomes(trading_days=10)
    print(f"Filled {filled_5d} 5D outcomes and {filled_10d} 10D outcomes.")
    print(generate_report())