"""
Pro Decision Engine — merges all 7 intelligence layers into final decision report.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    INDICATORS_CSV, DECISION_REPORT_CSV, SYMBOLS_CSV, OUTPUT_DIR, DATA_DIR
)
from src.decision_engine import classify, rsi_status
from src.smart_money import analyze_smart_money
from src.queue_analyzer import analyze_queue
from src.sector_engine import get_sector, calculate_sector_strengths, format_sector_heatmap
from src.confidence_score import calculate_confidence
from src.market_mood import calculate_market_mood, format_market_header
from src.signal_tracker import log_signals, update_outcomes, get_accuracy_summary


def run():
    if not os.path.exists(INDICATORS_CSV):
        print(f"[pro_decision] {INDICATORS_CSV} not found")
        return
    if not os.path.exists(SYMBOLS_CSV):
        print(f"[pro_decision] {SYMBOLS_CSV} not found")
        return

    indicators = pd.read_csv(INDICATORS_CSV)
    symbols_df = pd.read_csv(SYMBOLS_CSV)
    indicators["missing"] = indicators["missing"].astype(str).str.lower() == "true"

    sector_strengths = calculate_sector_strengths(symbols_df)
    sector_heatmap = format_sector_heatmap(sector_strengths)

    mood = calculate_market_mood(symbols_df)
    market_header = format_market_header(mood, sector_heatmap)

    sym_lookup = {str(r["symbol"]): r.to_dict() for _, r in symbols_df.iterrows()}

    rows = []
    for _, ind_row in indicators.iterrows():
        symbol = str(ind_row["symbol"])
        live = sym_lookup.get(symbol, {})

        sm = analyze_smart_money(live)
        q = analyze_queue(live)

        sector = get_sector(symbol)
        sec = sector_strengths.get(sector)
        sector_bonus = sec.confidence_bonus if sec else 0

        not_missing = not ind_row["missing"]
        poc_pos = str(ind_row.get("poc_position", "unknown")) if not_missing else "unknown"
        macd_x = str(ind_row.get("macd_crossover", "none")) if not_missing else "none"
        bb_sq = bool(ind_row.get("bb_squeeze", False)) if not_missing else False
        bb_p = float(ind_row["bb_pct"]) if not_missing and pd.notna(ind_row.get("bb_pct")) else None
        w_trend = str(ind_row.get("weekly_trend")) if not_missing and pd.notna(ind_row.get("weekly_trend")) else None
        w_rsi = float(ind_row["weekly_rsi"]) if not_missing and pd.notna(ind_row.get("weekly_rsi")) else None

        conf = calculate_confidence(
            smart_money_bonus=sm.confidence_bonus,
            queue_bonus=q.confidence_bonus,
            rsi=ind_row.get("rsi") if not_missing else None,
            trend_score=int(ind_row["trend_score"]) if not_missing and pd.notna(ind_row.get("trend_score")) else None,
            volume_ratio=ind_row.get("volume_ratio_20") if not_missing else None,
            sector_bonus=sector_bonus,
            risk_reward=ind_row.get("risk_reward") if not_missing else None,
            missing=bool(ind_row["missing"]),
            rsi_divergence=str(ind_row.get("rsi_divergence", "none")) if not_missing else "none",
            poc_position=poc_pos,
            macd_crossover=macd_x,
            bb_squeeze=bb_sq,
            bb_pct=bb_p,
            weekly_trend=w_trend,
            weekly_rsi=w_rsi,
        )

        ind_dict = ind_row.to_dict()
        ind_dict["initial_score"] = conf.score

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
            "rsi_status": rsi_status(ind_row.get("rsi")),
        })

    result = pd.DataFrame(rows)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result.to_csv(DECISION_REPORT_CSV, index=False, encoding="utf-8-sig")
    print(f"[pro_decision] Saved to {DECISION_REPORT_CSV}")

    log_signals(result)
    update_outcomes(result)

    print("\n--- Pro Decision Summary ---")
    cols = ["symbol", "confidence_score", "confidence_grade", "decision_label", "smart_money_signal", "queue_signal"]
    print(result[cols].sort_values("confidence_score", ascending=False).to_string(index=False))
    print()
    print(get_accuracy_summary())

    header_path = os.path.join(DATA_DIR, "market_header.txt")
    with open(header_path, "w", encoding="utf-8") as f:
        f.write(market_header)

    return result, market_header


if __name__ == "__main__":
    run()