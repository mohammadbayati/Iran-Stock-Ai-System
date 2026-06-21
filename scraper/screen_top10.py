import csv
from pathlib import Path


INPUT_FILE = Path("data") / "symbols.csv"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "top10_initial.csv"


def to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return default


def score_symbol(row):
    """
    امتیازدهی اولیه فقط با داده‌های موجود در API اصلی.
    نسخه بعدی با RSI, MACD, EMA, Support/Resistance دقیق‌تر می‌شود.
    """

    buyer_power = to_float(row.get("buyer_power"))
    real_money_flow = to_float(row.get("real_money_flow"))
    close_change = to_float(row.get("close_price_change_percent"))
    last_change = to_float(row.get("last_price_change_percent"))
    trade_value = to_float(row.get("trade_value"))
    volume = to_float(row.get("volume"))
    last_price = to_float(row.get("last_price"))
    best_buy_price = to_float(row.get("best_buy_price"))
    best_sell_price = to_float(row.get("best_sell_price"))

    score = 0
    reasons = []

    # 1. قدرت خریدار
    if buyer_power >= 3:
        score += 25
        reasons.append("قدرت خریدار بسیار بالا")
    elif buyer_power >= 1.5:
        score += 18
        reasons.append("قدرت خریدار خوب")
    elif buyer_power >= 1:
        score += 10
        reasons.append("قدرت خریدار خنثی تا مثبت")
    else:
        score -= 10
        reasons.append("قدرت خریدار ضعیف")

    # 2. ورود پول حقیقی
    if real_money_flow > 1_000_000_000_000:
        score += 25
        reasons.append("ورود پول حقیقی بسیار قوی")
    elif real_money_flow > 100_000_000_000:
        score += 18
        reasons.append("ورود پول حقیقی قوی")
    elif real_money_flow > 0:
        score += 10
        reasons.append("ورود پول حقیقی مثبت")
    else:
        score -= 15
        reasons.append("خروج پول حقیقی")

    # 3. بازدهی روزانه
    if 0 < close_change <= 3:
        score += 12
        reasons.append("رشد روزانه مثبت")
    elif close_change > 3:
        score += 6
        reasons.append("رشد مثبت اما نزدیک به سقف مجاز")
    elif close_change < 0:
        score -= 8
        reasons.append("بازدهی روزانه منفی")

    # 4. اختلاف آخرین و پایانی
    if last_change > close_change:
        score += 8
        reasons.append("آخرین قیمت قوی‌تر از پایانی")
    elif last_change < close_change:
        score -= 5
        reasons.append("آخرین قیمت ضعیف‌تر از پایانی")

    # 5. ارزش معاملات
    if trade_value > 5_000_000_000_000:
        score += 15
        reasons.append("ارزش معاملات بسیار بالا")
    elif trade_value > 1_000_000_000_000:
        score += 10
        reasons.append("ارزش معاملات مناسب")
    elif trade_value > 100_000_000_000:
        score += 5
        reasons.append("ارزش معاملات قابل قبول")
    else:
        score -= 5
        reasons.append("ارزش معاملات پایین")

    # 6. حجم
    if volume > 1_000_000_000:
        score += 10
        reasons.append("حجم معاملات بالا")
    elif volume > 100_000_000:
        score += 5
        reasons.append("حجم معاملات مناسب")
    else:
        score -= 5
        reasons.append("حجم معاملات پایین")

    # 7. صف خرید احتمالی
    # اگر بهترین فروش صفر باشد و بهترین خرید نزدیک آخرین قیمت باشد، می‌تواند نشانه صف خرید باشد.
    if best_sell_price == 0 and best_buy_price >= last_price:
        score += 8
        reasons.append("احتمال صف خرید یا فشار تقاضا")
    elif best_sell_price > 0 and best_sell_price > last_price:
        score += 2
        reasons.append("عرضه بالاتر از قیمت آخرین")

    # محدودسازی امتیاز
    score = max(0, min(100, score))

    if score >= 80:
        label = "Strong Candidate"
    elif score >= 65:
        label = "Watch Candidate"
    elif score >= 50:
        label = "Weak Watch"
    else:
        label = "Avoid / Low Priority"

    row["initial_score"] = score
    row["initial_label"] = label
    row["reasons"] = " | ".join(reasons)

    return row


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    tradeable = [
        row for row in rows
        if to_float(row.get("last_price")) > 0
        and to_float(row.get("volume")) > 0
        and to_float(row.get("trade_value")) > 0
    ]

    skipped = len(rows) - len(tradeable)
    if skipped:
        print(f"Filtered out {skipped} non-trading/suspended symbols.")

    scored_rows = [score_symbol(row) for row in tradeable]

    scored_rows.sort(
        key=lambda x: float(x.get("initial_score", 0)),
        reverse=True
    )

    top10 = scored_rows[:10]

    fieldnames = list(top10[0].keys()) if top10 else []

    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(top10)

    print(f"Scored symbols: {len(scored_rows)}")
    print(f"Top 10 saved to: {OUTPUT_FILE}")

    print("\nTop 10:")
    for index, row in enumerate(top10, start=1):
        print(
            index,
            row["symbol"],
            row["initial_score"],
            row["initial_label"],
            row["reasons"]
        )


if __name__ == "__main__":
    main()