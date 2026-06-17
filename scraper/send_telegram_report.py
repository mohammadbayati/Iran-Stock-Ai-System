import csv
import os
from pathlib import Path

import requests


INPUT_FILE = Path("output") / "top10_initial.csv"


def read_top10_csv() -> list[dict]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def format_number(value):
    try:
        number = float(value)
        return f"{number:,.0f}"
    except Exception:
        return str(value)


def build_telegram_report(rows: list[dict]) -> str:
    lines = []

    lines.append("📊 گزارش خودکار Top 10 بازار")
    lines.append("")
    lines.append("⚠️ این گزارش توصیه خرید/فروش نیست؛ فقط خروجی غربالگری اولیه بازار است.")
    lines.append("برای تصمیم نهایی باید حمایت/مقاومت، RSI، MACD، روند صنعت و ریسک بازار هم بررسی شود.")
    lines.append("")

    for index, row in enumerate(rows, start=1):
        symbol = row.get("symbol", "")
        score = row.get("initial_score", "")
        label = row.get("initial_label", "")
        last_price = row.get("last_price", "")
        close_change = row.get("close_price_change_percent", "")
        buyer_power = row.get("buyer_power", "")
        real_money_flow = row.get("real_money_flow", "")
        trade_value = row.get("trade_value", "")
        volume = row.get("volume", "")
        reasons = row.get("reasons", "")

        lines.append(f"{index}) {symbol}")
        lines.append(f"امتیاز: {score} | وضعیت: {label}")
        lines.append(f"قیمت آخرین: {format_number(last_price)}")
        lines.append(f"تغییر پایانی: {close_change}%")
        lines.append(f"قدرت خریدار: {buyer_power}")
        lines.append(f"پول حقیقی: {format_number(real_money_flow)}")
        lines.append(f"ارزش معاملات: {format_number(trade_value)}")
        lines.append(f"حجم: {format_number(volume)}")
        lines.append(f"دلایل: {reasons}")
        lines.append("")

    lines.append("✅ نسخه فعلی: Screener اولیه بدون Claude API")
    lines.append("مرحله بعدی پیشنهادی: اضافه کردن اندیکاتورها و حمایت/مقاومت برای تصمیم‌سازی دقیق‌تر.")

    return "\n".join(lines)


def split_message(text: str, max_length: int = 3500) -> list[str]:
    chunks = []
    current = ""

    for line in text.splitlines():
        candidate = current + line + "\n"

        if len(candidate) > max_length:
            if current.strip():
                chunks.append(current.strip())
            current = line + "\n"
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks


def send_telegram_message(message: str):
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
    rows = read_top10_csv()
    report = build_telegram_report(rows)
    chunks = split_message(report)

    for index, chunk in enumerate(chunks, start=1):
        if len(chunks) > 1:
            chunk = f"بخش {index}/{len(chunks)}\n\n{chunk}"

        result = send_telegram_message(chunk)
        print(f"Telegram message part {index} sent.")
        print(result)


if __name__ == "__main__":
    main()