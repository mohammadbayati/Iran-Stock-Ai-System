"""
Fetch historical OHLCV data using pytse-client.
In CI mode, skips fetch and uses cached data/history/ files.
"""

import sys
import os
import argparse
import shutil
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import IS_CI, FETCH_HISTORY_IN_CI, TOP10_CSV, HISTORY_DIR, DATA_DIR

FORCE_ENV = os.getenv("FORCE_HISTORY_FETCH", "false").lower() == "true"
PYTSE_CACHE = os.path.join(os.getcwd(), "tickers_data")


def should_fetch() -> bool:
    if FORCE_ENV:
        return True
    if IS_CI and not FETCH_HISTORY_IN_CI:
        print("[fetch_history] CI mode: skipping remote history fetch")
        return False
    return True


def fetch_ticker(symbol: str) -> bool:
    try:
        import pytse_client as tse
        tse.download(symbols=symbol, write_to_csv=True, include_jdate=True)
        src = os.path.join(PYTSE_CACHE, f"{symbol}.csv")
        if os.path.exists(src):
            os.makedirs(HISTORY_DIR, exist_ok=True)
            dst = os.path.join(HISTORY_DIR, f"{symbol}.csv")
            shutil.copy2(src, dst)
            print(f"[fetch_history] ✓ {symbol}")
            return True
        print(f"[fetch_history] ✗ {symbol}: no file produced")
        return False
    except Exception as e:
        print(f"[fetch_history] ✗ {symbol}: {e}")
        return False


def fetch_all(symbols: list) -> dict:
    results = {}
    for sym in symbols:
        results[sym] = fetch_ticker(sym)
    return results


def load_symbols_from_top10() -> list:
    if not os.path.exists(TOP10_CSV):
        print(f"[fetch_history] {TOP10_CSV} not found")
        return []
    df = pd.read_csv(TOP10_CSV)
    return df["symbol"].dropna().tolist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.force:
        os.environ["FORCE_HISTORY_FETCH"] = "true"
    if not should_fetch():
        sys.exit(0)
    symbols = load_symbols_from_top10()
    if not symbols:
        sys.exit(0)
    print(f"[fetch_history] Fetching: {symbols}")
    results = fetch_all(symbols)
    ok = sum(v for v in results.values())
    print(f"[fetch_history] Done: {ok}/{len(results)} succeeded")