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

    run([python_exe, "scraper\\fetch_symbols.py"])
    run([python_exe, "scraper\\screen_top10.py"])

    print("\nDONE.")
    print("Output file:")
    print("output\\top10_initial.csv")


if __name__ == "__main__":
    main()