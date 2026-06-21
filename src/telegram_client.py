"""
Send messages to Telegram.
"""

import os
import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IS_CI

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _credentials_available() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_message(text: str) -> bool:
    if not _credentials_available():
        if IS_CI:
            raise EnvironmentError(
                "[telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in CI."
            )
        print("[telegram] Credentials not set — printing report instead of sending:")
        print(text)
        return False

    url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        print(f"[telegram] Message sent ({len(text)} chars)")
        return True
    except Exception as e:
        print(f"[telegram] ERROR sending message: {e}")
        return False


def send_chunks(chunks: list[str]) -> int:
    sent = 0
    for i, chunk in enumerate(chunks, 1):
        print(f"[telegram] Sending chunk {i}/{len(chunks)}")
        if send_message(chunk):
            sent += 1
    return sent