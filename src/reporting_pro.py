"""
Pro Persian Telegram Report Builder — Clean Professional Format
"""

import os
import pandas as pd
from datetime import datetime
from config.settings import DECISION_REPORT_CSV, DATA_DIR, TELEGRAM_MAX_CHARS
from src.decision_engine import (
    LABEL_ENTRY_CANDIDATE, LABEL_TECH_WATCH, LABEL_PULLBACK,
    LABEL_OVERBOUGHT, LABEL_VOLUME, LABEL_WATCH, LABEL_MISSING,
)

ORDER = [
    LABEL_ENTRY_CANDIDATE, LABEL_TECH_WATCH, LABEL_PULLBACK,
    LABEL_VOLUME, LABEL_WATCH, LABEL_OVERBOUGHT, LABEL_MISSING,
]

GRADE_STARS = {"A": "★★★", "B": "★★☆", "C": "★☆☆", "D": "☆☆☆", "F": "✗"}

LABEL_FA_SHORT = {
    LABEL_ENTRY_CANDIDATE: "🟢 کاندید ورود",
    LABEL_TECH_WATCH:      "🟡 واچ تکنیکال",
    LABEL_PULLBACK:        "🟠 صبر — پولبک",
    LABEL_OVERBOUGHT:      "🔴 اشباع خرید",
    LABEL_VOLUME:          "🔵 نیاز به حجم",
    LABEL_WATCH:           "⚪ فقط رصد",
    LABEL_MISSING:         "⚫ داده ناقص",
}


def _to_jalali(dt: datetime) -> str:
    try:
        import jdatetime
        jdt = jdatetime.datetime.fromgregorian(datetime=dt)
        months = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                  "مهر","آبان","آذر","دی","بهمن","اسفند"]
        return f"{jdt.day} {months[jdt.month-1]} {jdt.year}"
    except ImportError:
        return dt.strftime("%Y-%m-%d")


def _weekday_fa(dt: datetime) -> str:
    days = {0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه",
            3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"}
    return days.get(dt.weekday(), "")


def _fmt(val, suffix="", fmt=".0f") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    try:
        return f"{float(val):{fmt}}{suffix}"
    except Exception:
        return str(val)


def _smart_money_short(sm_fa: str) -> str:
    sm_fa = str(sm_fa)
    replacements = {
        "تجمیع هوشمند: حقیقی می‌فروشد، پول هوشمند وارد می‌شود": "تجمیع هوشمند",
        "توزیع پنهان: حقیقی می‌خرد، پول هوشمند خارج می‌شود": "توزیع پنهان",
        "افت حقیقی‌محور: ممکن است اغراق‌آمیز باشد": "افت حقیقی‌محور",
        "هم‌راستای صعودی: خریدار و پول هر دو وارد": "هم‌راستای صعودی",
        "هم‌راستای نزولی: فروشنده و خروج پول هر دو تایید": "هم‌راستای نزولی",
        "رشد حقیقی‌محور: بدون پشتوانه پول هوشمند": "رشد حقیقی‌محور",
        "بدون سیگنال واضح": "خنثی",
    }
    for k, v in replacements.items():
        sm_fa = sm_fa.replace(k, v)
    return sm_fa


def _entry_block(row: pd.Series) -> str:
    grade = str(row.get("confidence_grade", ""))
    stars = GRADE_STARS.get(grade, "")
    score = int(row.get("confidence_score", 0))
    symbol = row.get("symbol", "?")
    rsi = _fmt(row.get("rsi"), fmt=".0f")
    trend = _fmt(row.get("trend_score"), fmt=".0f")
    vol = _fmt(row.get("volume_ratio_20"), fmt=".1f")
    ret5 = _fmt(row.get("return_5d_percent"), suffix="%", fmt=".1f")
    sl = _fmt(row.get("stop_loss"), fmt=",.0f")
    tp = _fmt(row.get("target_1"), fmt=",.0f")

    rr_raw = row.get("risk_reward")
    try:
        rr = f"{float(rr_raw):.1f}" if rr_raw and not pd.isna(rr_raw) and float(rr_raw) > 0.1 else "—"
    except Exception:
        rr = "—"

    sm = _smart_money_short(row.get("smart_money_fa", ""))
    sector = str(row.get("sector", ""))
    sec_status = str(row.get("sector_status", ""))

    lines = [
        f"┌──────────────────────────────┐",
        f"│ 🟢 {symbol}  {grade} {stars}  امتیاز {score}",
        f"│ RSI {rsi} | روند {trend}/6 | حجم {vol}x | بازده {ret5}",
        f"│ 🧠 {sm}",
        f"│ 🏭 {sector} {sec_status}",
        f"│ 🛑 {sl}  🎯 {tp}  ⚖️ {rr}",
        f"└──────────────────────────────┘",
    ]
    return "\n".join(lines)


def _summary_line(row: pd.Series) -> str:
    symbol = row.get("symbol", "?")
    score = int(row.get("confidence_score", 0))
    grade = str(row.get("confidence_grade", ""))
    label = LABEL_FA_SHORT.get(str(row.get("decision_label", "")), "")
    sector = str(row.get("sector", ""))
    return f"  {label} | {symbol} | {grade} | {score} | {sector}"


def build_pro_report(df: pd.DataFrame, market_header: str = "") -> list[str]:
    now = datetime.now()
    weekday = _weekday_fa(now)
    jalali_date = _to_jalali(now)
    time_str = now.strftime("%H:%M")

    mood_line = ""
    flow_line = ""
    if market_header:
        for line in market_header.split("\n"):
            if "حالت بازار" in line:
                mood_line = line.strip()
            if "جریان پول کل" in line:
                flow_line = line.strip()

    header = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 بورس تهران | {weekday} {jalali_date}\n"
        f"🕐 {time_str} | {mood_line}\n"
        f"{flow_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    entries = df[df["decision_label"] == LABEL_ENTRY_CANDIDATE].sort_values("confidence_score", ascending=False)
    entry_section = ""
    if not entries.empty:
        entry_section = f"\n🏆 کاندید ورود ({len(entries)} نماد)\n"
        entry_section += "\n".join(_entry_block(row) for _, row in entries.iterrows())

    watches = df[df["decision_label"] == LABEL_TECH_WATCH].sort_values("confidence_score", ascending=False)
    watch_section = ""
    if not watches.empty:
        watch_section = f"\n🟡 واچ تکنیکال ({len(watches)} نماد)\n"
        watch_section += "\n".join(_entry_block(row) for _, row in watches.iterrows())

    rest_labels = [LABEL_PULLBACK, LABEL_VOLUME, LABEL_WATCH, LABEL_OVERBOUGHT, LABEL_MISSING]
    rest_rows = df[df["decision_label"].isin(rest_labels)].sort_values("confidence_score", ascending=False)
    rest_section = ""
    if not rest_rows.empty:
        rest_section = "\n─────────────────────────\n"
        rest_section += "\n".join(_summary_line(row) for _, row in rest_rows.iterrows())

    entry_count = len(entries)
    high_conf = len(df[df["confidence_score"] >= 70]) if "confidence_score" in df.columns else 0
    stats = (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 {len(df)} نماد | {entry_count} کاندید | {high_conf} امتیاز بالا\n"
        f"⚠️ کمک‌تصمیم — مسئولیت با شماست"
    )

    try:
        from src.signal_tracker import get_accuracy_summary
        acc = get_accuracy_summary()
        if "هنوز" not in acc:
            stats += f"\n{acc}"
    except Exception:
        pass

    full = header + entry_section + watch_section + rest_section + stats

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