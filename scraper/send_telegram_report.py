"""
Build and send the Persian decision report to Telegram.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reporting_pro import build_pro_report_from_csv
from src.telegram_client import send_chunks


def run():
    chunks = build_pro_report_from_csv()
    sent = send_chunks(chunks)
    print(f"[send_telegram_report] {sent}/{len(chunks)} chunks sent")


if __name__ == "__main__":
    run()