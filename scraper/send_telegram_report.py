import os
from pathlib import Path

import requests


CLAUDE_REPORT_FILE = Path("output") / "claude_strategy_report.txt"
FALLBACK_FILE = Path("output") / "top10_initial.csv"


def read_report() -> str:
    if CLAUDE_REPORT_FILE.exists():
        return CLAUDE_REPORT_FILE.read_text(encoding="utf-8")

    if FALLBACK_FILE.exists():
        return FALLBACK_FILE.read_text(encoding="utf-8-sig")

    raise FileNotFoundError("No report file found to send.")


def split_message(text: str, max_length: int = 3500) -> list[str]:
    """
    Telegram has message length limits.
    We split conservatively to avoid errors.
    """
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
    report = read_report()

    header = "📊 گزارش تحلیلی Claude برای بازار امروز\n\n"
    full_text = header + report

    chunks = split_message(full_text)

    for index, chunk in enumerate(chunks, start=1):
        if len(chunks) > 1:
            chunk = f"بخش {index}/{len(chunks)}\n\n{chunk}"

        result = send_telegram_message(chunk)
        print(f"Telegram message part {index} sent.")
        print(result)


if __name__ == "__main__":
    main()