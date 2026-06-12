import csv
import os
from datetime import datetime
from pathlib import Path

import requests


INPUT_FILE = Path("output") / "top10_initial.csv"


def read_top10():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def build_message(rows):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("📊 گزارش اولیه Top 10 بازار")
    lines.append(f"زمان اجرا: {now}")
    lines.append("")
    lines.append("⚠️ این گزارش توصیه خرید/فروش نیست؛ فقط خروجی اسکرینر اولیه است.")
    lines.append("")

    for index, row in enumerate(rows[:10], start=1):
        symbol = row.get("symbol", "-")
        score = row.get("initial_score", "-")
        label = row.get("initial_label", "-")
        buyer_power = row.get("buyer_power", "-")
        real_money_flow = row.get("real_money_flow", "-")
        reasons = row.get("reasons", "")

        lines.append(f"{index}. {symbol}")
        lines.append(f"امتیاز: {score} | وضعیت: {label}")
        lines.append(f"قدرت خریدار: {buyer_power}")
        lines.append(f"ورود/خروج پول: {real_money_flow}")
        lines.append(f"دلایل: {reasons}")
        lines.append("")

    return "\n".join(lines)


def send_telegram_message(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable")

    if not chat_id:
        raise ValueError("Missing TELEGRAM_CHAT_ID environment variable")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()
    return response.json()


def main():
    rows = read_top10()
    message = build_message(rows)
    result = send_telegram_message(message)

    print("Telegram message sent.")
    print(result)


if __name__ == "__main__":
    main()