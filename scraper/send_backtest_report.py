"""
Sends the backtest accuracy report to Telegram.
Run manually or on a weekly schedule.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import fill_outcomes, generate_report
from src.telegram_sender import send_telegram_message


def run():
    print("[backtest_report] Filling outcomes...")
    fill_outcomes(trading_days=5)

    print("[backtest_report] Generating report...")
    report = generate_report()
    print(report)

    print("[backtest_report] Sending to Telegram...")
    send_telegram_message(report)
    print("[backtest_report] Done.")


if __name__ == "__main__":
    run()