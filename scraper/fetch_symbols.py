"""
Fetch live market snapshot from tradersarena.ir
"""

import json
import sys
import os
import requests
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import LIVE_DATA_URL, SYMBOLS_CSV, SYMBOLS_JSON, DATA_DIR

COLUMN_NAMES = [
    "ins_code", "isin", "symbol", "buy_volume_or_count", "trade_value",
    "last_price", "last_price_change_percent", "close_price",
    "close_price_change_percent", "buy_power_numerator", "sell_power_denominator",
    "buyer_power", "real_money_flow", "unknown_1", "unknown_2",
    "volume", "best_buy_price", "best_sell_price", "best_sell_volume", "previous_close",
]


def fetch_symbols() -> pd.DataFrame:
    print(f"[fetch_symbols] Fetching live data from {LIVE_DATA_URL}")
    try:
        resp = requests.get(LIVE_DATA_URL, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        print(f"[fetch_symbols] ERROR: {e}")
        raise

    rows = raw if isinstance(raw, list) else raw.get("data", raw.get("symbols", []))

    records = []
    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        record = {}
        for i, col in enumerate(COLUMN_NAMES):
            record[col] = row[i] if i < len(row) else None
        records.append(record)

    df = pd.DataFrame(records)
    print(f"[fetch_symbols] {len(df)} symbols fetched")
    return df


def save_symbols(df: pd.DataFrame):
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(SYMBOLS_CSV, index=False, encoding="utf-8-sig")
    df.to_json(SYMBOLS_JSON, orient="records", force_ascii=False, indent=2)
    print(f"[fetch_symbols] Saved to {SYMBOLS_CSV}")


if __name__ == "__main__":
    df = fetch_symbols()
    save_symbols(df)