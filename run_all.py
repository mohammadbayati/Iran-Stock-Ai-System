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


def main():
    python_exe = sys.executable

    run([python_exe, "scraper/fetch_symbols.py"])
    run([python_exe, "scraper/screen_top10.py"])
    run([python_exe, "scraper/send_telegram_report.py"])

    print("\nDONE.")
    print("Output files:")
    print("output/top10_initial.csv")
    print("Telegram report sent.")


if __name__ == "__main__":
    main()
