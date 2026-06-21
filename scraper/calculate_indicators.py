"""
Calculate technical indicators for top10 symbols → data/indicators.csv
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import TOP10_CSV, INDICATORS_CSV, DATA_DIR
from src.indicators import calculate_indicators


def run():
    if not os.path.exists(TOP10_CSV):
        print(f"[calculate_indicators] {TOP10_CSV} not found")
        return

    top10 = pd.read_csv(TOP10_CSV)
    symbols = top10["symbol"].dropna().tolist()
    print(f"[calculate_indicators] Processing {len(symbols)} symbols")

    rows = []
    for sym in symbols:
        ind = calculate_indicators(sym)
        match = top10[top10["symbol"] == sym]
        if not match.empty:
            ind["initial_score"] = match["initial_score"].values[0]
            ind["initial_label"] = match["initial_label"].values[0]
        rows.append(ind)

    df = pd.DataFrame(rows)
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(INDICATORS_CSV, index=False, encoding="utf-8-sig")
    print(f"[calculate_indicators] Saved to {INDICATORS_CSV}")

    missing = df[df["missing"] == True]
    if not missing.empty:
        print(f"[calculate_indicators] ⚠️  {len(missing)} missing: {missing['symbol'].tolist()}")


if __name__ == "__main__":
    run()