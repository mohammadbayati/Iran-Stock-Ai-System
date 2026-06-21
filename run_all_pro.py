import sys, os, time, argparse, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

IS_CI = os.getenv("CI", "false").lower() == "true"
start = time.time()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-history", action="store_true")
    args = parser.parse_args()
    if args.refresh_history:
        os.environ["FORCE_HISTORY_FETCH"] = "true"

    print(f"\n{'='*60}\n  Iran Stock AI — Pro Decision Engine  CI={IS_CI}\n{'='*60}\n")

    # Step 1 — Fetch live symbols
    print("[1/6] Fetching live market data...")
    from scraper.fetch_symbols import fetch_symbols, normalize_rows, save_json, save_csv
    raw = fetch_symbols()
    rows = normalize_rows(raw)
    save_json(rows)
    save_csv(rows)
    df_symbols = pd.DataFrame(rows)
    print(f"  {len(df_symbols)} symbols fetched")

    # Step 2 — Screen top 10
    print("\n[2/6] Screening top symbols...")
    from scraper.screen_top10 import main as screen_main
    screen_main()
    top10 = pd.read_csv("output/top10_initial.csv")

    # Step 3 — History (skip in CI)
    print("\n[3/6] Historical data...")
    if IS_CI and os.getenv("FETCH_HISTORY_IN_CI", "false").lower() != "true":
        print("  Skipped (CI mode) — using cached data/history/")
    else:
        from scraper.fetch_history import main as history_main
        history_main()

    # Step 4 — Indicators
    print("\n[4/6] Calculating indicators...")
    from scraper.calculate_indicators import main as calc_main
    calc_main()

    # Step 5 — Pro decision engine
    print("\n[5/6] Running pro decision engine (7 layers)...")
    from scraper.merge_decision_report_pro import run as pro_decision
    pro_decision()

    # Step 6 — Send Telegram
    print("\n[6/6] Sending Telegram report...")
    from src.reporting_pro import build_pro_report_from_csv
    from scraper.send_telegram_report import send_telegram_message
    chunks = build_pro_report_from_csv()
    sent = 0
    for i, chunk in enumerate(chunks, 1):
        print(f"  Sending chunk {i}/{len(chunks)}")
        try:
            send_telegram_message(chunk)
            sent += 1
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"  Done in {round(time.time()-start,1)}s | {sent}/{len(chunks)} chunks sent")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()