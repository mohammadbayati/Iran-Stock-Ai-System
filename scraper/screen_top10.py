"""
Screen top symbols from full market universe.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SYMBOLS_CSV, TOP10_CSV, TOP_N, OUTPUT_DIR, HISTORY_DIR


def _safe_float(val) -> float:
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def _has_history(symbol: str) -> bool:
    path = os.path.join(HISTORY_DIR, f"{symbol}.csv")
    return os.path.exists(path)


def _is_valid_symbol(row: pd.Series) -> bool:
    symbol = str(row.get("symbol", "")).strip()

    if not symbol or len(symbol) > 8:
        return False

    if symbol.startswith("ض") or symbol.startswith("ج"):
        return False

    if any(c.isdigit() for c in symbol):
        return False

    if symbol.startswith("ح") and len(symbol) > 3:
        return False

    volume = _safe_float(row.get("volume"))
    value = _safe_float(row.get("trade_value"))
    if volume < 10_000 and value < 100_000_000:
        return False

    return True


def score_symbol(row: pd.Series) -> float:
    score = 0.0

    bp = _safe_float(row.get("buyer_power"))
    if bp > 3.0:
        score += 35
    elif bp > 2.0:
        score += 25
    elif bp > 1.5:
        score += 15
    elif bp > 1.0:
        score += 5

    flow = _safe_float(row.get("real_money_flow"))
    if flow > 0:
        score += min(flow / 1e9 * 8, 25)
    elif flow < 0:
        score += max(flow / 1e9 * 4, -15)

    value = _safe_float(row.get("trade_value"))
    if value > 50e9:
        score += 20
    elif value > 10e9:
        score += 12
    elif value > 1e9:
        score += 5

    chg = _safe_float(row.get("close_price_change_percent"))
    if 0.5 < chg <= 4:
        score += 15
    elif 4 < chg <= 6:
        score += 8
    elif chg > 6:
        score += 3
    elif -1 <= chg <= 0:
        score += 2
    elif chg < -3:
        score -= 10

    buy_vol = _safe_float(row.get("buy_power_numerator") or row.get("best_buy_volume"))
    sell_vol = _safe_float(row.get("sell_power_denominator") or row.get("best_sell_volume"))
    if sell_vol > 0 and buy_vol / sell_vol > 3:
        score += 10

    return round(score, 2)


def initial_label(score: float) -> str:
    if score >= 60:
        return "Strong Candidate"
    elif score >= 40:
        return "Moderate Candidate"
    elif score >= 20:
        return "Weak Candidate"
    return "Low Priority"


def screen_top10(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df[df.apply(_is_valid_symbol, axis=1)].copy()
    print(f"[screen_top10] {before} → {len(df)} after liquidity filter")

    df["initial_score"] = df.apply(score_symbol, axis=1)
    df["initial_label"] = df["initial_score"].apply(initial_label)
    df = df.sort_values("initial_score", ascending=False)

    df["has_history"] = df["symbol"].apply(_has_history)
    df_with = df[df["has_history"]].head(TOP_N)
    df_without = df[~df["has_history"]].head(max(0, TOP_N - len(df_with)))
    df = pd.concat([df_with, df_without]).reset_index(drop=True)

    print(f"[screen_top10] Selected {len(df)} symbols ({len(df_with)} with cached history)")
    return df


def save_top10(df: pd.DataFrame):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(TOP10_CSV, index=False, encoding="utf-8-sig")
    print(f"[screen_top10] Saved to {TOP10_CSV}")


if __name__ == "__main__":
    df = pd.read_csv(SYMBOLS_CSV)
    top10 = screen_top10(df)
    save_top10(top10)
    print(top10[["symbol", "initial_score", "initial_label", "has_history"]].to_string())