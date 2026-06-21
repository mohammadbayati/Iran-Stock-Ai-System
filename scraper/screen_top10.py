import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SYMBOLS_CSV, TOP10_CSV, TOP_N, OUTPUT_DIR, HISTORY_DIR, IS_CI

ARABIC_TO_PERSIAN = str.maketrans({"ك": "ک", "ي": "ی", "ة": "ه", "ى": "ی"})


def _normalize(symbol: str) -> str:
    return symbol.translate(ARABIC_TO_PERSIAN).strip()


def _safe_float(val) -> float:
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def _has_history(symbol: str) -> bool:
    return os.path.exists(os.path.join(HISTORY_DIR, f"{_normalize(symbol)}.csv"))


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

    if volume < 50_000 or value < 500_000_000:
        return False

    change = abs(_safe_float(row.get("close_price_change_percent")))
    if change == 0 and value < 2_000_000_000:
        return False

    return True


def score_symbol(row: pd.Series) -> float:
    score = 0.0

    bp = _safe_float(row.get("buyer_power"))
    if bp > 4.0:
        score += 30
    elif bp > 3.0:
        score += 25
    elif bp > 2.0:
        score += 18
    elif bp > 1.5:
        score += 10
    elif bp > 1.0:
        score += 4

    flow = _safe_float(row.get("real_money_flow"))
    if flow > 0:
        score += min(flow / 5e8 * 5, 25)
    elif flow < 0:
        score += max(flow / 5e8 * 3, -15)

    value = _safe_float(row.get("trade_value"))
    if value > 200e9:
        score += 20
    elif value > 100e9:
        score += 16
    elif value > 50e9:
        score += 12
    elif value > 10e9:
        score += 7
    elif value > 1e9:
        score += 3

    chg = _safe_float(row.get("close_price_change_percent"))
    if 1.0 < chg <= 3.5:
        score += 15
    elif 3.5 < chg <= 5.5:
        score += 10
    elif 5.5 < chg <= 7.0:
        score += 5
    elif chg > 7.0:
        score += 2
    elif 0 <= chg <= 1.0:
        score += 6
    elif -1.5 <= chg < 0:
        score += 3
    elif chg < -3.0:
        score -= 10

    buy_vol = _safe_float(row.get("buy_power_numerator") or row.get("best_buy_volume"))
    sell_vol = _safe_float(row.get("sell_power_denominator") or row.get("best_sell_volume"))
    if sell_vol > 0:
        q_ratio = buy_vol / sell_vol
        if q_ratio > 5:
            score += 10
        elif q_ratio > 3:
            score += 7
        elif q_ratio > 2:
            score += 4

    return round(score, 2)


def initial_label(score: float) -> str:
    if score >= 55:
        return "Strong Candidate"
    elif score >= 35:
        return "Moderate Candidate"
    elif score >= 15:
        return "Weak Candidate"
    return "Low Priority"


def screen_top10(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df[df.apply(_is_valid_symbol, axis=1)].copy()
    print(f"[screen_top10] {before} → {len(df)} after liquidity filter")

    df["initial_score"] = df.apply(score_symbol, axis=1)
    df["initial_label"] = df["initial_score"].apply(initial_label)
    df["has_history"] = df["symbol"].apply(_has_history)
    df = df.sort_values("initial_score", ascending=False).reset_index(drop=True)

    if IS_CI:
        # در CI فقط سمبل‌هایی که history کش دارن رو انتخاب کن
        df_hist = df[df["has_history"] == True].head(TOP_N).copy()
        print(f"[screen_top10] CI mode: {len(df_hist)}/{len(df)} symbols have cached history")
        result = df_hist
    else:
        result = df.head(TOP_N).copy()

    with_hist = result["has_history"].sum()
    print(f"[screen_top10] Selected {len(result)} symbols ({with_hist} with cached history)")
    return result


def save_top10(df: pd.DataFrame):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(TOP10_CSV, index=False, encoding="utf-8-sig")
    print(f"[screen_top10] Saved to {TOP10_CSV}")


if __name__ == "__main__":
    df = pd.read_csv(SYMBOLS_CSV)
    top10 = screen_top10(df)
    save_top10(top10)
    print(top10[["symbol", "initial_score", "initial_label", "has_history"]].to_string())