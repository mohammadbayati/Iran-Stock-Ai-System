from pathlib import Path

import pandas as pd


TOP10_FILE = Path("output") / "top10_initial.csv"
INDICATORS_FILE = Path("data") / "indicators.csv"
OUTPUT_FILE = Path("output") / "decision_report.csv"


def classify_decision(row) -> tuple[str, str]:
    initial_score = float(row.get("initial_score", 0))
    trend_score = float(row.get("trend_score", 0))
    rsi = float(row.get("rsi_14", 0))
    volume_ratio = float(row.get("volume_ratio_20", 0))
    distance_to_high = float(row.get("distance_to_20d_high_percent", 0))
    return_5d = float(row.get("return_5d_percent", 0))

    reasons = []

    if trend_score >= 4:
        reasons.append("روند تکنیکال قوی است")
    elif trend_score == 3:
        reasons.append("روند قابل پیگیری است اما هنوز کامل نیست")
    else:
        reasons.append("روند تکنیکال ضعیف است")

    if volume_ratio >= 1.2:
        reasons.append("حجم بالاتر از میانگین ۲۰ روزه است")
    else:
        reasons.append("حجم هنوز تأییدکننده نیست")

    if rsi >= 80:
        reasons.append("RSI بسیار بالا است؛ ریسک ورود مستقیم زیاد است")
    elif rsi >= 70:
        reasons.append("RSI وارد محدوده اشباع خرید شده است")
    elif 45 <= rsi < 70:
        reasons.append("RSI در محدوده سالم‌تر قرار دارد")
    else:
        reasons.append("مومنتوم ضعیف یا نامطمئن است")

    if distance_to_high >= -1:
        reasons.append("قیمت نزدیک سقف ۲۰ روزه است")
    elif distance_to_high <= -5:
        reasons.append("قیمت کمی از سقف فاصله گرفته و برای پولبک قابل بررسی است")

    if return_5d >= 15:
        reasons.append("رشد ۵ روزه شدید بوده؛ احتمال اصلاح کوتاه‌مدت بالاتر است")

    if initial_score >= 80 and trend_score >= 4 and volume_ratio >= 1.2 and 45 <= rsi < 70:
        decision = "Entry Candidate"
    elif initial_score >= 75 and trend_score >= 4 and volume_ratio >= 1.2 and rsi >= 70:
        decision = "Wait for Pullback"
    elif trend_score >= 3 and 45 <= rsi < 70 and volume_ratio < 1.2:
        decision = "Watch - Needs Volume Confirmation"
    elif rsi >= 80 and distance_to_high >= -3:
        decision = "Avoid Entry Now - Overbought"
    else:
        decision = "Watch Only"

    return decision, " | ".join(reasons)


def main():
    if not TOP10_FILE.exists():
        raise FileNotFoundError(f"Top 10 file not found: {TOP10_FILE}")

    if not INDICATORS_FILE.exists():
        raise FileNotFoundError(f"Indicators file not found: {INDICATORS_FILE}")

    top10 = pd.read_csv(TOP10_FILE, encoding="utf-8-sig")
    indicators = pd.read_csv(INDICATORS_FILE, encoding="utf-8-sig")

    merged = top10.merge(indicators, on="symbol", how="left")

    decisions = merged.apply(classify_decision, axis=1)
    merged["decision_label"] = [item[0] for item in decisions]
    merged["decision_reasons"] = [item[1] for item in decisions]

    decision_rank = {
        "Entry Candidate": 1,
        "Wait for Pullback": 2,
        "Watch - Needs Volume Confirmation": 3,
        "Watch Only": 4,
        "Avoid Entry Now - Overbought": 5,
    }

    merged["decision_rank"] = merged["decision_label"].map(decision_rank).fillna(99)

    merged = merged.sort_values(
        by=["decision_rank", "initial_score", "trend_score", "volume_ratio_20"],
        ascending=[True, False, False, False],
    )

    selected_columns = [
        "symbol",
        "initial_score",
        "initial_label",
        "trend_score",
        "rsi_14",
        "rsi_status",
        "volume_ratio_20",
        "return_5d_percent",
        "distance_to_20d_high_percent",
        "distance_to_20d_low_percent",
        "technical_label",
        "decision_label",
        "decision_reasons",
    ]

    existing_columns = [col for col in selected_columns if col in merged.columns]
    output = merged[existing_columns]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Decision report saved: {OUTPUT_FILE}")
    print(output[["symbol", "initial_score", "trend_score", "rsi_14", "volume_ratio_20", "decision_label"]])


if __name__ == "__main__":
    main()