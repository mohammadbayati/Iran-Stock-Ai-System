import subprocess
import sys


def run(command):
    print("=" * 60)
    print("Running:", " ".join(command))
    print("=" * 60)

    result = subprocess.run(command)

    if result.returncode != 0:
        print("ERROR: command failed")
        sys.exit(result.returncode)


def run_optional(command):
    print("=" * 60)
    print("Running (optional):", " ".join(command))
    print("=" * 60)

    result = subprocess.run(command)

    if result.returncode != 0:
        print("WARNING: optional step failed, continuing pipeline.")


def main():
    python_exe = sys.executable

    run([python_exe, "scraper/fetch_symbols.py"])
    run([python_exe, "scraper/screen_top10.py"])
    run([python_exe, "scraper/fetch_history.py"])
    run([python_exe, "scraper/calculate_indicators.py"])
    run([python_exe, "scraper/merge_decision_report_pro.py"])
    run_optional([python_exe, "scraper/claude_analyze_top10.py"])
    run([python_exe, "scraper/send_telegram_report.py"])

    print("\nDONE.")
    print("Output files:")
    print("  output/top10_initial.csv")
    print("  data/indicators.csv")
    print("  output/decision_report.csv")
    print("Telegram report sent.")


if __name__ == "__main__":
    main()