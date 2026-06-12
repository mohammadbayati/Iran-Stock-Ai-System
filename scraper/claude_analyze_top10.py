import csv
import os
from pathlib import Path

from anthropic import Anthropic


SKILL_FILE = Path("skills") / "iran-stock-super-strategy-engine" / "SKILL.md"
INPUT_FILE = Path("output") / "top10_initial.csv"
OUTPUT_FILE = Path("output") / "claude_strategy_report.txt"


def read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return path.read_text(encoding="utf-8")


def read_top10_csv() -> list[dict]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def format_rows_for_claude(rows: list[dict]) -> str:
    lines = []

    for index, row in enumerate(rows, start=1):
        lines.append(f"## Candidate {index}")
        lines.append(f"symbol: {row.get('symbol', '')}")
        lines.append(f"last_price: {row.get('last_price', '')}")
        lines.append(f"close_price: {row.get('close_price', '')}")
        lines.append(f"previous_close: {row.get('previous_close', '')}")
        lines.append(f"last_price_change_percent: {row.get('last_price_change_percent', '')}")
        lines.append(f"close_price_change_percent: {row.get('close_price_change_percent', '')}")
        lines.append(f"trade_value: {row.get('trade_value', '')}")
        lines.append(f"volume: {row.get('volume', '')}")
        lines.append(f"buyer_power: {row.get('buyer_power', '')}")
        lines.append(f"real_money_flow: {row.get('real_money_flow', '')}")
        lines.append(f"best_buy_price: {row.get('best_buy_price', '')}")
        lines.append(f"best_sell_price: {row.get('best_sell_price', '')}")
        lines.append(f"initial_score: {row.get('initial_score', '')}")
        lines.append(f"initial_label: {row.get('initial_label', '')}")
        lines.append(f"reasons: {row.get('reasons', '')}")
        lines.append("")

    return "\n".join(lines)


def build_prompt(skill_text: str, top10_text: str) -> str:
    return f"""
You are using the following Claude Skill instructions as the analysis framework.

<skill>
{skill_text}
</skill>

Now analyze the following Iranian stock market screener output.

Important constraints:
- The data below is an initial screener output, not a complete technical dataset.
- Missing data such as RSI, MACD, EMA, ADX, Bollinger Bands, support/resistance, P/E, sector index, and market regime must be explicitly disclosed.
- Do not give blind buy/sell recommendations.
- Do not claim a guaranteed success rate.
- Instead of "success percentage", provide "Setup Confidence" and "Estimated Probability Range" as a qualitative estimate based only on the available data.
- Keep the Telegram report concise and decision-oriented.
- Write the final answer in Persian.
- Rank the symbols into:
  1. قابل بررسی جدی
  2. واچ‌لیست
  3. پرریسک / نیازمند داده بیشتر
- For each symbol, provide:
  - Symbol Quality estimate
  - Entry Quality estimate
  - Setup Confidence
  - Estimated Probability Range
  - Expected upside cannot be calculated precisely unless resistance/target data exists; if missing, say so.
  - Key reason
  - Main risk
  - Final label

<screener_output>
{top10_text}
</screener_output>

Final output format:

# گزارش تحلیلی Claude برای Top 10

## هشدار مهم
یک پاراگراف کوتاه درباره محدودیت داده و اینکه این توصیه خرید/فروش نیست.

## خلاصه مدیریتی
۳ تا ۵ خط.

## رتبه‌بندی نهایی
برای هر نماد در یک ساختار کوتاه:

1. نماد:
- تصمیم:
- Symbol Quality:
- Entry Quality:
- Setup Confidence:
- Estimated Probability Range:
- دلیل اصلی:
- ریسک اصلی:
- اقدام پیشنهادی:
"""


def call_claude(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError("Missing ANTHROPIC_API_KEY environment variable")

    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return message.content[0].text


def save_report(report: str) -> Path:
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    OUTPUT_FILE.write_text(report, encoding="utf-8")
    return OUTPUT_FILE


def main():
    skill_text = read_file(SKILL_FILE)
    rows = read_top10_csv()
    top10_text = format_rows_for_claude(rows)
    prompt = build_prompt(skill_text, top10_text)

    report = call_claude(prompt)
    output_path = save_report(report)

    print("Claude analysis saved.")
    print(f"Output file: {output_path}")
    print("")
    print(report)


if __name__ == "__main__":
    main()