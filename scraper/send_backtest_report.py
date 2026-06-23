"""Send weekly backtest accuracy report to Telegram."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import fill_outcomes, generate_report
from src.telegram_client import send_telegram_message


def run():
    fill_outcomes(trading_days=5)
    report = generate_report()
    send_telegram_message(report)
    print("Backtest report sent.")


if __name__ == "__main__":
    run()