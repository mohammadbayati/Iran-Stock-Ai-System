"""
Score and rank symbols, selecting top N candidates.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SYMBOLS_CSV, TOP10_CSV, TOP_N, OUTPUT_DIR


def score_symbol(row: pd.Series) -> float:
    score = 0.0

    try:
        bp = float(row.get("buyer_power", 0) or 0)
        if bp > 2.0:
            score += 30
        elif bp > 1.5:
            score += 20
        elif bp > 1.0:
            score += 10
    except (ValueError, TypeError):
        pass

    try:
        flow = float(row.get("real_money_flow", 0) or 0)
        if flow > 0:
            score += min(flow / 1e9 * 10, 30)
    except (ValueError, TypeError):
        pass

    try:
        vol = float(row.get("volume", 0) or 0)
        if vol > 5e6:
            score += 20
        elif vol > 1e6:
            score += 10
    except (ValueError, TypeError):
        pass

    try:
        chg = float(row.get("close_price_change_percent", 0) or 0)
        if 0 < chg <= 5:
            score += 10
        elif chg > 5:
            score += 5
        elif chg < 0:
            score -= 5
    except (ValueError, TypeError):
        pass

    return round(score, 2)


def initial_label(score: float) -> str:
    if score >= 75:
        return "Strong Candidate"
    elif score >= 50:
        return "Moderate Candidate"
    elif score >= 25:
        return "Weak Candidate"
    return "Low Priority"


def screen_top10(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["initial_score"] = df.apply(score_symbol, axis=1)
    df["initial_label"] = df["initial_score"].apply(initial_label)
    df = df.sort_values("initial_score", ascending=False).head(TOP_N).reset_index(drop=True)
    print(f"[screen_top10] Selected {len(df)} symbols")
    return df


def save_top10(df: pd.DataFrame):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(TOP10_CSV, index=False, encoding="utf-8-sig")
    print(f"[screen_top10] Saved to {TOP10_CSV}")


if __name__ == "__main__":
    df = pd.read_csv(SYMBOLS_CSV)
    top10 = screen_top10(df)
    save_top10(top10)