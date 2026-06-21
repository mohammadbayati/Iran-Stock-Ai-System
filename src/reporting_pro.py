import os, pandas as pd

DECISION_REPORT_CSV = "output/decision_report.csv"
DATA_DIR = "data"
TELEGRAM_MAX_CHARS = 4000

LABEL_ENTRY = "Entry Candidate"
LABEL_TECH = "Technical Entry Watch"
LABEL_PULLBACK = "Wait for Pullback"
LABEL_OVERBOUGHT = "Avoid Entry Now - Overbought"
LABEL_VOLUME = "Watch - Needs Volume Confirmation"
LABEL_WATCH = "Watch Only"
LABEL_MISSING = "Missing Technical Data"

EMOJI_MAP = {LABEL_ENTRY:"🟢", LABEL_TECH:"🟡", LABEL_PULLBACK:"🟠",
             LABEL_OVERBOUGHT:"🔴", LABEL_VOLUME:"🔵", LABEL_WATCH:"⚪", LABEL_MISSING:"⚫"}
LABEL_FA = {LABEL_ENTRY:"کاندید ورود", LABEL_TECH:"واچ تکنیکال", LABEL_PULLBACK:"صبر برای پولبک",
            LABEL_OVERBOUGHT:"عدم ورود — اشباع خرید", LABEL_VOLUME:"نیاز به تایید حجم",
            LABEL_WATCH:"فقط رصد", LABEL_MISSING:"داده تکنیکال ناقص"}
GRADE_EMOJI = {"A":"🏆","B":"🥈","C":"🥉","D":"⚠️","F":"❌"}
ORDER = [LABEL_ENTRY, LABEL_TECH, LABEL_PULLBACK, LABEL_VOLUME, LABEL_WATCH, LABEL_OVERBOUGHT, LABEL_MISSING]


def _fmt(val, suffix="", fmt=".1f"):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        return f"{float(val):{fmt}}{suffix}"
    except Exception:
        return str(val)


def _symbol_block(row):
    label = row.get("decision_label", "")
    emoji = EMOJI_MAP.get(label, "⚪")
    grade = str(row.get("confidence_grade", ""))
    score = row.get("confidence_score", "")
    missing = str(row.get("missing", "True")).lower() == "true"

    lines = [
        f"{emoji} *{row.get('symbol','?')}*  {GRADE_EMOJI.get(grade,'')} درجه {grade} (امتیاز: {score})",
        f"  📌 {LABEL_FA.get(label, label)}",
    ]

    if not missing:
        rsi_col = row.get("rsi") or row.get("rsi_14")
        lines += [
            f"  📊 RSI: {_fmt(rsi_col)} — {row.get('rsi_status','')}",
            f"  📈 روند: {_fmt(row.get('trend_score'),fmt='.0f')}/6  |  💧 حجم: {_fmt(row.get('volume_ratio_20'))}x",
            f"  📉 بازده ۵ روزه: {_fmt(row.get('return_5d_percent') or row.get('return_5d'),suffix='%')}",
        ]
        rr = row.get("risk_reward")
        if rr and not pd.isna(float(rr if rr else 0)) and float(rr) > 0:
            lines += [
                f"  🛑 حد ضرر: {_fmt(row.get('stop_loss'),fmt='.0f')}  |  🎯 هدف: {_fmt(row.get('target_1'),fmt='.0f')}",
                f"  ⚖️ ریسک/ریوارد: {_fmt(rr)}",
            ]
        sm = row.get("smart_money_fa","")
        if sm and str(sm) != "nan":
            lines.append(f"  🧠 {sm}")
        q = row.get("queue_fa","")
        qd = row.get("queue_detail","")
        if q and str(q) != "nan":
            lines.append(f"  📋 {q}" + (f" ({qd})" if qd and str(qd) != "nan" else ""))
        sec = row.get("sector","")
        sec_s = row.get("sector_status","")
        if sec and str(sec) != "nan":
            lines.append(f"  🏭 سکتور: {sec} {sec_s}")
        factors = row.get("confidence_factors","")
        if factors and str(factors) != "nan":
            lines.append(f"  💡 {factors}")

    reasons = row.get("decision_reasons","")
    if reasons and str(reasons) != "nan":
        lines.append(f"  💬 {reasons}")

    return "\n".join(lines)


def build_pro_report(df, market_header=""):
    sections = [market_header] if market_header else []

    for label in ORDER:
        group = df[df["decision_label"] == label]
        if group.empty:
            continue
        group = group.sort_values("confidence_score", ascending=False)
        section = f"\n{EMOJI_MAP.get(label,'⚪')} *{LABEL_FA.get(label,label)}* ({len(group)} نماد)\n"
        section += "\n\n".join(_symbol_block(row) for _, row in group.iterrows())
        sections.append(section)

    missing_count = len(df[df["missing"].astype(str).str.lower() == "true"])
    high_conf = len(df[df["confidence_score"] >= 70]) if "confidence_score" in df.columns else 0

    stats = (f"\n─────────────────────\n"
             f"📊 خلاصه: {len(df)} نماد | {high_conf} امتیاز بالا | {missing_count} فاقد داده")

    disclaimer = ("\n─────────────────────\n"
                  "⚠️ *این گزارش توصیه خرید/فروش نیست.*\n"
                  "خروجی سیستم کمک‌تصمیم است. تصمیم نهایی با شماست.")

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


def build_pro_report_from_csv():
    market_header = ""
    header_path = os.path.join(DATA_DIR, "market_header.txt")
    if os.path.exists(header_path):
        with open(header_path, encoding="utf-8") as f:
            market_header = f.read()
    if not os.path.exists(DECISION_REPORT_CSV):
        return ["decision_report.csv not found"]
    df = pd.read_csv(DECISION_REPORT_CSV)
    return build_pro_report(df, market_header)