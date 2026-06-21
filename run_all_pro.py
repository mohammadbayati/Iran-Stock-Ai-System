"""
Pro Pipeline Entry Point — uses all 7 intelligence layers.
"""

import sys
import os
import time
import argparse
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import IS_CI

start = time.time()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-history", action="store_true")
    args = parser.parse_args()

    if args.refresh_history:
        os.environ["FORCE_HISTORY_FETCH"] = "true"

    print(f"\n{'='*60}")
    print(f"  Iran Stock AI — Pro Decision Engine")
    print(f"  CI={IS_CI}")
    print(f"{'='*60}\n")

    # Step 1 — Live symbols
    print("[Step 1/6] Fetching live market data...")
    from scraper.fetch_symbols import fetch_symbols, save_symbols
    df_symbols = fetch_symbols()
    save_symbols(df_symbols)
    print(f"  {len(df_symbols)} symbols fetched")

    # Step 2 — Screen top N
    print("\n[Step 2/6] Screening top symbols...")
    from scraper.screen_top10 import screen_top10, save_top10
    top10 = screen_top10(df_symbols)
    save_top10(top10)

    # Step 3 — History (skipped in CI unless forced)
    print("\n[Step 3/6] Historical data...")
    from scraper.fetch_history import should_fetch, load_symbols_from_top10, fetch_all
    if should_fetch():
        symbols = load_symbols_from_top10()
        results = fetch_all(symbols)
        ok = sum(v for v in results.values())
        print(f"  History: {ok}/{len(results)} fetched")
    else:
        print("  Skipped (CI mode) — using cached data/history/")

    # Step 4 — Indicators
    print("\n[Step 4/6] Calculating technical indicators...")
    from scraper.calculate_indicators import run as calc_indicators
    calc_indicators()

    # Step 5 — Pro decision engine (all 7 layers)
    print("\n[Step 5/6] Running pro decision engine (7 layers)...")
    from scraper.merge_decision_report_pro import run as pro_decision
    pro_decision()

    # Step 6 — Send pro Telegram report
    print("\n[Step 6/6] Sending pro Telegram report...")
    from src.reporting_pro import build_pro_report_from_csv
    from src.telegram_client import send_chunks
    chunks = build_pro_report_from_csv()
    sent = send_chunks(chunks)

    elapsed = round(time.time() - start, 1)
    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {elapsed}s")
    print(f"  Symbols: {len(top10)} | Telegram chunks: {sent}/{len(chunks)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()