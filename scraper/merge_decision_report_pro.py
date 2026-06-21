import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.decision_engine import classify, rsi_status
from src.smart_money import analyze_smart_money
from src.queue_analyzer import analyze_queue
from src.sector_engine import get_sector, calculate_sector_strengths, format_sector_heatmap
from src.confidence_score import calculate_confidence
from src.market_mood import calculate_market_mood, format_market_header
from src.signal_tracker import log_signals, update_outcomes, get_accuracy_summary

INDICATORS_CSV = "data/indicators.csv"
SYMBOLS_CSV = "data/symbols.csv"
DECISION_REPORT_CSV = "output/decision_report.csv"
DATA_DIR = "data"


def run():
    if not os.path.exists(INDICATORS_CSV):
        print(f"[pro_decision] {INDICATORS_CSV} not found")
        return None, ""

    if not os.path.exists(SYMBOLS_CSV):
        print(f"[pro_decision] {SYMBOLS_CSV} not found")
        return None, ""

    indicators = pd.read_csv(INDICATORS_CSV)
    symbols_df = pd.read_csv(SYMBOLS_CSV)

    # ستون missing ممکنه در indicators قدیمی نباشه
    if "missing" not in indicators.columns:
        indicators["missing"] = False
    else:
        indicators["missing"] = indicators["missing"].astype(str).str.lower() == "true"

    # sector و mood از کل بازار
    sector_strengths = calculate_sector_strengths(symbols_df)
    sector_heatmap = format_sector_heatmap(sector_strengths)
    mood = calculate_market_mood(symbols_df)
    market_header = format_market_header(mood, sector_heatmap)

    # لوکاپ نمادها از داده لایو
    sym_lookup = {str(r["symbol"]): r.to_dict() for _, r in symbols_df.iterrows()}

    rows = []
    for _, ind_row in indicators.iterrows():
        symbol = str(ind_row["symbol"])
        live = sym_lookup.get(symbol, {})

        # Layer 1 — پول هوشمند
        sm = analyze_smart_money(live)

        # Layer 2 — صف
        q = analyze_queue(live)

        # Layer 4 — سکتور
        sector = get_sector(symbol)
        sec = sector_strengths.get(sector)
        sector_bonus = sec.confidence_bonus if sec else 0

        missing = bool(ind_row["missing"])

        # خواندن ستون‌های اندیکاتور با نام‌های موجود در indicators.csv
        rsi_val = None
        for col in ["rsi", "rsi_14"]:
            if col in ind_row and pd.notna(ind_row[col]):
                rsi_val = float(ind_row[col])
                break

        trend_val = None
        if "trend_score" in ind_row and pd.notna(ind_row["trend_score"]):
            trend_val = int(ind_row["trend_score"])

        vol_val = None
        if "volume_ratio_20" in ind_row and pd.notna(ind_row["volume_ratio_20"]):
            vol_val = float(ind_row["volume_ratio_20"])

        rr_val = None
        if "risk_reward" in ind_row and pd.notna(ind_row.get("risk_reward")):
            rr_val = float(ind_row["risk_reward"])

        # Layer 5 — امتیاز اعتماد
        conf = calculate_confidence(
            smart_money_bonus=sm.confidence_bonus,
            queue_bonus=q.confidence_bonus,
            rsi=rsi_val if not missing else None,
            trend_score=trend_val if not missing else None,
            volume_ratio=vol_val if not missing else None,
            sector_bonus=sector_bonus,
            risk_reward=rr_val if not missing else None,
            missing=missing,
        )

        ind_dict = ind_row.to_dict()
        ind_dict["initial_score"] = conf.score
        ind_dict["rsi"] = rsi_val

        # تصمیم نهایی
        label, reasons = classify(ind_dict)

        rows.append({
            **ind_dict,
            "sector": sector,
            "smart_money_signal": sm.signal,
            "smart_money_fa": sm.description_fa,
            "queue_signal": q.signal,
            "queue_fa": q.description_fa,
            "queue_detail": q.detail,
            "sector_status": sec.status_fa if sec else "نامشخص",
            "confidence_score": conf.score,
            "confidence_grade": conf.grade,
            "confidence_factors": " | ".join(conf.factors),
            "decision_label": label,
            "decision_reasons": " | ".join(reasons),
            "rsi_status": rsi_status(rsi_val),
        })

    result = pd.DataFrame(rows)
    os.makedirs("output", exist_ok=True)
    result.to_csv(DECISION_REPORT_CSV, index=False, encoding="utf-8-sig")
    print(f"[pro_decision] {len(result)} نماد پردازش شد → {DECISION_REPORT_CSV}")

    log_signals(result)
    update_outcomes(result)

    print("\n--- Pro Decision Summary ---")
    cols = ["symbol", "confidence_score", "confidence_grade", "decision_label", "smart_money_signal"]
    print(result[cols].sort_values("confidence_score", ascending=False).to_string(index=False))
    print()
    print(get_accuracy_summary())

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "market_header.txt"), "w", encoding="utf-8") as f:
        f.write(market_header)

    return result, market_header


if __name__ == "__main__":
    run()