"""
Pro Persian Telegram Report Builder.
"""

import os
import pandas as pd
from config.settings import DECISION_REPORT_CSV, DATA_DIR, TELEGRAM_MAX_CHARS
from src.decision_engine import (
    LABEL_ENTRY_CANDIDATE, LABEL_TECH_WATCH, LABEL_PULLBACK,
    LABEL_OVERBOUGHT, LABEL_VOLUME, LABEL_WATCH, LABEL_MISSING,
)

EMOJI_MAP = {
    LABEL_ENTRY_CANDIDATE: "🟢",
    LABEL_TECH_WATCH:      "🟡",
    LABEL_PULLBACK:        "🟠",
    LABEL_OVERBOUGHT:      "🔴",
    LABEL_VOLUME:          "🔵",
    LABEL_WATCH:           "⚪",
    LABEL_MISSING:         "⚫",
}

LABEL_FA = {
    LABEL_ENTRY_CANDIDATE: "کاندید ورود",
    LABEL_TECH_WATCH:      "واچ تکنیکال",
    LABEL_PULLBACK:        "صبر برای پولبک",
    LABEL_OVERBOUGHT:      "عدم ورود — اشباع خرید",
    LABEL_VOLUME:          "نیاز به تایید حجم",
    LABEL_WATCH:           "فقط رصد",
    LABEL_MISSING:         "داده تکنیکال ناقص",
}

GRADE_EMOJI = {"A": "🏆", "B": "🥈", "C": "🥉", "D": "⚠️", "F": "❌"}

ORDER = [
    LABEL_ENTRY_CANDIDATE, LABEL_TECH_WATCH, LABEL_PULLBACK,
    LABEL_VOLUME, LABEL_WATCH, LABEL_OVERBOUGHT, LABEL_MISSING,
]

POC_FA = {
    "above": "بالای POC ✅",
    "below": "زیر POC ⚠️",
    "at":    "روی POC 🎯",
}


def _fmt(val, suffix="", fmt=".1f") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        return f"{float(val):{fmt}}{suffix}"
    except Exception:
        return str(val)


def _symbol_block(row: pd.Series) -> str:
    label = row.get("decision_label", "")
    emoji = EMOJI_MAP.get(label, "⚪")
    label_fa = LABEL_FA.get(label, label)
    grade = str(row.get("confidence_grade", ""))
    grade_emoji = GRADE_EMOJI.get(grade, "")
    score = row.get("confidence_score", "")
    missing = str(row.get("missing", "True")).lower() == "true"

    lines = [
        f"{emoji} *{row.get('symbol', '?')}*  {grade_emoji} درجه {grade} (امتیاز: {score})",
        f"  📌 {label_fa}",
    ]

    if not missing:
        lines += [
            f"  📊 RSI: {_fmt(row.get('rsi'))} — {row.get('rsi_status', '')}",
            f"  📈 روند: {_fmt(row.get('trend_score'), fmt='.0f')}/6  |  💧 حجم: {_fmt(row.get('volume_ratio_20'))}x",
            f"  📉 بازده ۵ روزه: {_fmt(row.get('return_5d_percent'), suffix='%')}",
        ]

        # Volume Profile
        poc = row.get("poc")
        vah = row.get("vah")
        val = row.get("val")
        poc_pos = row.get("poc_position", "unknown")
        if poc and not pd.isna(poc):
            poc_txt = POC_FA.get(poc_pos, "")
            lines.append(
                f"  📦 POC: {_fmt(poc, fmt='.0f')}  |  VAH: {_fmt(vah, fmt='.0f')}  |  VAL: {_fmt(val, fmt='.0f')}  {poc_txt}"
            )

        rr_raw = row.get("risk_reward")
        rr = f"{float(rr_raw):.1f}" if rr_raw and not pd.isna(rr_raw) and float(rr_raw) > 0.05 else "—"
        atr = row.get("atr")
        div = row.get("rsi_divergence", "none")

        lines += [
            f"  ─",
            f"  🛑 حد ضرر: {_fmt(row.get('stop_loss'), fmt='.0f')}  |  🎯 هدف: {_fmt(row.get('target_1'), fmt='.0f')}",
            f"  ⚖️ ریسک/ریوارد: {rr}" + (f"  |  ATR: {_fmt(atr, fmt='.0f')}" if atr and not pd.isna(atr) else ""),
        ]

        if div == "bullish":
            lines.append("  📐 واگرایی مثبت RSI (سیگنال برگشت صعودی)")
        elif div == "bearish":
            lines.append("  📐 واگرایی منفی RSI (سیگنال برگشت نزولی)")

        sm = row.get("smart_money_fa", "")
        if sm and str(sm) != "nan":
            lines.append(f"  🧠 {sm}")

        q = row.get("queue_fa", "")
        qd = row.get("queue_detail", "")
        if q and str(q) != "nan":
            detail = f" ({qd})" if qd and str(qd) != "nan" else ""
            lines.append(f"  📋 {q}{detail}")

        sector = row.get("sector", "")
        sec_status = row.get("sector_status", "")
        if sector and str(sector) != "nan":
            lines.append(f"  🏭 سکتور: {sector} {sec_status}")

        factors = row.get("confidence_factors", "")
        if factors and str(factors) != "nan":
            lines.append(f"  💡 {factors}")

        if row.get("stale"):
            lines.append("  ⚠️ داده تاریخچه قدیمی")

    reasons = row.get("decision_reasons", "")
    if reasons and str(reasons) != "nan":
        lines.append(f"  💬 {reasons}")

    return "\n".join(lines)


def build_pro_report(df: pd.DataFrame, market_header: str = "") -> list[str]:
    sections = [market_header] if market_header else []

    for label in ORDER:
        group = df[df["decision_label"] == label]
        if group.empty:
            continue
        group = group.sort_values("confidence_score", ascending=False)
        emoji = EMOJI_MAP.get(label, "⚪")
        label_fa = LABEL_FA.get(label, label)
        section = f"\n{emoji} *{label_fa}* ({len(group)} نماد)\n"
        section += "\n\n".join(_symbol_block(row) for _, row in group.iterrows())
        sections.append(section)

    entry_count = len(df[df["decision_label"] == LABEL_ENTRY_CANDIDATE])
    missing_count = len(df[df["missing"].astype(str).str.lower() == "true"])
    high_conf = len(df[df["confidence_score"] >= 70]) if "confidence_score" in df.columns else 0

    stats = (
        f"\n─────────────────────\n"
        f"📊 خلاصه: {len(df)} نماد | {entry_count} کاندید | "
        f"{high_conf} امتیاز بالا | {missing_count} فاقد داده"
    )

    try:
        from src.signal_tracker import get_accuracy_summary
        acc = get_accuracy_summary()
        stats += f"\n{acc}"
    except Exception:
        pass

    disclaimer = (
        "\n─────────────────────\n"
        "⚠️ *این گزارش توصیه خرید/فروش نیست.*\n"
        "خروجی سیستم کمک‌تصمیم است. تصمیم نهایی با شماست."
    )

    full = "\n".join(sections) + stats + disclaimer

    chunks = []
    while len(full) > TELEGRAM_MAX_CHARS:
        split_at = full.rfind("\n", 0, TELEGRAM_MAX_CHARS)
        if split_at == -1:
            split_at = TELEGRAM_MAX_CHARS
        chunks.append(full[:split_at])
        full = full[split_at:].lstrip()
    chunks.append(full)
    return chunks


def build_pro_report_from_csv() -> list[str]:
    market_header = ""
    header_path = os.path.join(DATA_DIR, "market_header.txt")
    if os.path.exists(header_path):
        with open(header_path, encoding="utf-8") as f:
            market_header = f.read()

    if not os.path.exists(DECISION_REPORT_CSV):
        return ["[reporting_pro] decision_report.csv not found"]

    df = pd.read_csv(DECISION_REPORT_CSV)
    return build_pro_report(df, market_header)