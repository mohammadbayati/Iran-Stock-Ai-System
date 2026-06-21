import csv
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


INPUT_FILE = Path("output") / "decision_report.csv"
CLAUDE_REPORT_FILE = Path("output") / "claude_strategy_report.txt"


def read_decision_csv() -> list[dict]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def format_number(value):
    try:
        if value is None or value == "":
            return "-"
        number = float(value)
        return f"{number:,.0f}"
    except Exception:
        return str(value)


def format_float(value, digits=2):
    try:
        if value is None or value == "":
            return "-"
        number = float(value)
        return f"{number:.{digits}f}"
    except Exception:
        return str(value)


def translate_decision(label: str) -> str:
    mapping = {
        "Entry Candidate": "کاندید ورود",
        "Wait for Pullback": "صبر برای پولبک",
        "Watch - Needs Volume Confirmation": "واچ؛ نیازمند تأیید حجم",
        "Watch Only": "فقط واچ",
        "Avoid Entry Now - Overbought": "عدم ورود فعلاً؛ اشباع خرید",
    }

    return mapping.get(label, label)


def build_telegram_report(rows: list[dict]) -> str:
    lines = []

    tehran_offset = timedelta(hours=3, minutes=30)
    now_tehran = datetime.now(timezone.utc) + tehran_offset
    timestamp = now_tehran.strftime("%Y-%m-%d | %H:%M تهران")

    lines.append("📊 گزارش تصمیم‌محور بازار")
    lines.append(f"🕐 {timestamp}")
    lines.append("")
    lines.append("⚠️ این گزارش توصیه خرید/فروش نیست؛ خروجی سیستم کمک‌تصمیم است.")
    lines.append("معیارها: امتیاز اولیه، روند تکنیکال، RSI، حجم ۲۰ روزه، فاصله از سقف/کف ۲۰ روزه.")
    lines.append("")

    groups = {
        "Entry Candidate": [],
        "Wait for Pullback": [],
        "Watch - Needs Volume Confirmation": [],
        "Watch Only": [],
        "Avoid Entry Now - Overbought": [],
    }

    for row in rows:
        decision = row.get("decision_label", "Watch Only")
        groups.setdefault(decision, []).append(row)

    for decision, grouped_rows in groups.items():
        if not grouped_rows:
            continue

        lines.append(f"🔹 {translate_decision(decision)}")
        lines.append("")

        for row in grouped_rows:
            symbol = row.get("symbol", "")
            initial_score = row.get("initial_score", "")
            initial_label = row.get("initial_label", "")
            trend_score = row.get("trend_score", "")
            rsi = row.get("rsi_14", "")
            rsi_status = row.get("rsi_status", "")
            volume_ratio = row.get("volume_ratio_20", "")
            return_5d = row.get("return_5d_percent", "")
            distance_to_high = row.get("distance_to_20d_high_percent", "")
            reasons = row.get("decision_reasons", "")

            lines.append(f"نماد: {symbol}")
            lines.append(f"امتیاز اولیه: {initial_score} | وضعیت اولیه: {initial_label}")
            lines.append(f"Trend Score: {format_float(trend_score, 0)}")
            lines.append(f"RSI: {format_float(rsi)} | وضعیت RSI: {rsi_status}")
            lines.append(f"نسبت حجم به میانگین ۲۰ روزه: {format_float(volume_ratio)}")
            lines.append(f"بازده ۵ روزه: {format_float(return_5d)}٪")
            lines.append(f"فاصله تا سقف ۲۰ روزه: {format_float(distance_to_high)}٪")
            lines.append(f"منطق تصمیم: {reasons}")
            lines.append("")

    lines.append("✅ نسخه فعلی: Decision Support Engine v1")

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
    is_ci = os.environ.get("CI", "").lower() == "true"

    if not token or not chat_id:
        if is_ci:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variable")

        print("Telegram credentials not found. Local run: skipping Telegram send.")
        print("")
        print(message)
        return {"ok": False, "skipped": True}

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


def send_report(text: str, label: str):
    chunks = split_message(text)

    for index, chunk in enumerate(chunks, start=1):
        if len(chunks) > 1:
            chunk = f"بخش {index}/{len(chunks)}\n\n{chunk}"

        result = send_telegram_message(chunk)
        print(f"{label} part {index} processed.")
        print(result)


def main():
    rows = read_decision_csv()
    decision_report = build_telegram_report(rows)
    send_report(decision_report, "Decision report")

    if CLAUDE_REPORT_FILE.exists():
        claude_report = CLAUDE_REPORT_FILE.read_text(encoding="utf-8").strip()
        if claude_report:
            send_report(claude_report, "Claude strategy report")
    else:
        print("Claude strategy report not found; skipping.")


if __name__ == "__main__":
    main()