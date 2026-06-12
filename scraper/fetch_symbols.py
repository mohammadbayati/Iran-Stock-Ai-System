import csv
import json
from pathlib import Path

import requests


API_URL = "https://tradersarena.ir/data/mainwatch/symbols"

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)


COLUMNS = [
    "ins_code",
    "isin",
    "symbol",
    "buy_volume_or_count",
    "trade_value",
    "last_price",
    "last_price_change_percent",
    "close_price",
    "close_price_change_percent",
    "buy_power_numerator",
    "sell_power_denominator",
    "buyer_power",
    "real_money_flow",
    "unknown_1",
    "unknown_2",
    "volume",
    "best_buy_price",
    "best_sell_price",
    "best_sell_volume",
    "previous_close"
]


def fetch_symbols():
    session = requests.Session()
    session.trust_env = False  # جلوگیری از استفاده از Proxy سیستم

    response = session.get(
        API_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://tradersarena.ir/"
        },
        timeout=30
    )

    response.raise_for_status()
    return response.json()


def normalize_rows(raw_rows):
    normalized = []

    for row in raw_rows:
        item = {}

        for index, column_name in enumerate(COLUMNS):
            if index < len(row):
                item[column_name] = row[index]
            else:
                item[column_name] = None

        normalized.append(item)

    return normalized


def save_json(rows):
    output_path = OUTPUT_DIR / "symbols.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    return output_path


def save_csv(rows):
    output_path = OUTPUT_DIR / "symbols.csv"

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def main():
    raw_rows = fetch_symbols()
    rows = normalize_rows(raw_rows)

    json_path = save_json(rows)
    csv_path = save_csv(rows)

    print(f"Fetched symbols: {len(rows)}")
    print(f"JSON saved to: {json_path}")
    print(f"CSV saved to: {csv_path}")

    print("\nSample rows:")
    for item in rows[:5]:
        print(
            item["symbol"],
            item["last_price"],
            item["close_price"],
            item["buyer_power"],
            item["real_money_flow"]
        )


if __name__ == "__main__":
    main()