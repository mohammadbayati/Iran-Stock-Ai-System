import os

IS_CI = os.getenv("CI", "false").lower() == "true"
FETCH_HISTORY_IN_CI = os.getenv("FETCH_HISTORY_IN_CI", "false").lower() == "true"

if IS_CI and not FETCH_HISTORY_IN_CI:
    print("[fetch_history] CI mode: skipping remote fetch. Using cached data/history/ files.")
    import sys
    sys.exit(0)
import csv
from pathlib import Path

import pandas as pd
import pytse_client as tse


TOP10_FILE = Path("output") / "top10_initial.csv"
HISTORY_DIR = Path("data") / "history"


def read_top10_symbols() -> list[str]:
    if not TOP10_FILE.exists():
        raise FileNotFoundError(f"Top 10 file not found: {TOP10_FILE}")

    symbols = []

    with TOP10_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            symbol = row.get("symbol", "").strip()

            if symbol:
                symbols.append(symbol)

    return symbols


def normalize_history_dataframe(history) -> pd.DataFrame:
    df = pd.DataFrame(history)

    if df.empty:
        return df

    df = df.reset_index()

    return df


def fetch_symbol_history(symbol: str) -> pd.DataFrame:
    print(f"Fetching history for: {symbol}")

    ticker = tse.Ticker(symbol)
    history = ticker.history

    df = normalize_history_dataframe(history)

    if df.empty:
        print(f"No history found for: {symbol}")
        return df

    df["symbol"] = symbol

    return df


def save_history(symbol: str, df: pd.DataFrame):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    safe_symbol = symbol.replace("/", "_").replace("\\", "_").replace(" ", "_")
    output_file = HISTORY_DIR / f"{safe_symbol}.csv"

    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(f"Saved history: {output_file}")


def main():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    symbols = read_top10_symbols()

    print(f"Symbols to fetch history for: {len(symbols)}")
    print(symbols)

    success_count = 0
    error_count = 0

    for symbol in symbols:
        try:
            df = fetch_symbol_history(symbol)

            if not df.empty:
                save_history(symbol, df)
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            error_count += 1
            print(f"ERROR fetching history for {symbol}: {e}")

    print("History fetch completed.")
    print(f"Successful histories: {success_count}")
    print(f"Failed histories: {error_count}")


if __name__ == "__main__":
    main()