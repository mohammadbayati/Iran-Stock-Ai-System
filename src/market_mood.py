"""
Layer 7 — Daily Market Mood + Fear & Greed Index
"""

import pandas as pd
from datetime import datetime, timezone, timedelta


def _tehran_now() -> str:
    tehran = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    return tehran.strftime("%Y-%m-%d  %H:%M")


def calculate_market_mood(df: pd.DataFrame) -> dict:
    def safe_float(val):
        try:
            return float(val or 0)
        except (ValueError, TypeError):
            return 0.0

    flows = df["real_money_flow"].apply(safe_float)
    buyer_powers = df["buyer_power"].apply(safe_float)
    changes = df["close_price_change_percent"].apply(safe_float)

    total_flow = flows.sum()
    avg_buyer_power = buyer_powers.mean()
    avg_change = changes.mean()
    positive_count = int((changes > 0).sum())
    negative_count = int((changes < 0).sum())
    total_symbols = len(df)

    breadth_pct = positive_count / total_symbols * 100 if total_symbols > 0 else 50

    # اگه همه buyer_power یکسان بود → از A/D ratio استفاده کن
    if buyer_powers.std() < 0.05:
        avg_buyer_power = round(positive_count / max(negative_count, 1), 2)

    # اگه flow همه صفر بود → estimated از change * value
    if abs(total_flow) < 1e9 and "trade_value" in df.columns:
        vals = df["trade_value"].apply(safe_float)
        total_flow = (changes * vals / 100).sum()

    # --- Fear & Greed Index (0-100) ---
    # A/D breadth score
    ad_score = breadth_pct  # 0-100

    # Buyer power score
    bp_score = min(avg_buyer_power / 2.0 * 100, 100)  # 1.0 → 50, 2.0 → 100

    # Avg change score
    chg_score = max(0.0, min(100.0, 50.0 + avg_change * 10))

    # Flow score
    if total_flow > 50e9:
        flow_score = 80.0
    elif total_flow > 10e9:
        flow_score = 65.0
    elif total_flow > 0:
        flow_score = 55.0
    elif total_flow > -10e9:
        flow_score = 45.0
    elif total_flow > -50e9:
        flow_score = 35.0
    else:
        flow_score = 20.0

    fear_greed = round(
        ad_score * 0.35 +
        bp_score * 0.25 +
        chg_score * 0.30 +
        flow_score * 0.10
    )
    fear_greed = max(0, min(100, int(fear_greed)))

    if fear_greed >= 80:
        fg_label = "🤑 طمع شدید"
        fg_action = "احتیاط — بازار بیش از حد خوش‌بین است"
    elif fear_greed >= 60:
        fg_label = "😊 طمع"
        fg_action = "شرایط مناسب — با احتیاط وارد شوید"
    elif fear_greed >= 40:
        fg_label = "😐 خنثی"
        fg_action = "بازار بی‌جهت — منتظر سیگنال بمانید"
    elif fear_greed >= 20:
        fg_label = "😨 ترس"
        fg_action = "ریسک بالا — از ورود جدید خودداری کنید"
    else:
        fg_label = "😱 ترس شدید"
        fg_action = "خروج گسترده — ورود جدید توصیه نمی‌شود"

    # Mood classification
    retail_selling = avg_buyer_power < 0.9
    retail_buying = avg_buyer_power > 1.3
    money_entering = total_flow > 10e9
    money_leaving = total_flow < -10e9

    if money_entering and retail_selling:
        mood = "smart_accumulation"
        mood_fa = "تجمیع هوشمند"
        mood_desc = "حقیقی‌ها می‌فروشند، پول هوشمند وارد می‌شود"
        mood_emoji = "🟢"
    elif money_entering and retail_buying and breadth_pct > 60:
        mood = "broad_rally"
        mood_fa = "رالی گسترده"
        mood_desc = "هم پول و هم خریدار وارد بازار — روند صعودی قوی"
        mood_emoji = "🟢"
    elif money_leaving and retail_buying:
        mood = "distribution"
        mood_fa = "توزیع"
        mood_desc = "حقیقی‌ها می‌خرند، پول هوشمند خارج می‌شود — احتیاط"
        mood_emoji = "🔴"
    elif money_leaving or (breadth_pct < 40 and avg_change < -1.0):
        mood = "broad_selloff"
        mood_fa = "فروش گسترده"
        mood_desc = "خروج گسترده پول و اکثر نمادها منفی"
        mood_emoji = "🔴"
    else:
        mood = "mixed"
        mood_fa = "بازار خنثی"
        mood_desc = "سیگنال واضحی وجود ندارد — صبر کنید"
        mood_emoji = "🟡"

    return {
        "mood": mood,
        "mood_fa": mood_fa,
        "mood_desc": mood_desc,
        "mood_emoji": mood_emoji,
        "total_flow_billion": round(total_flow / 1e9, 1),
        "avg_buyer_power": round(avg_buyer_power, 2),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "breadth_pct": round(breadth_pct, 1),
        "avg_change": round(avg_change, 2),
        "fear_greed": fear_greed,
        "fg_label": fg_label,
        "fg_action": fg_action,
    }


def format_market_header(mood: dict, sector_heatmap: str = "") -> str:
    flow = mood["total_flow_billion"]
    flow_str = f"+{flow:.0f}" if flow >= 0 else f"{flow:.0f}"
    fg = mood["fear_greed"]
    fg_bar = "█" * (fg // 10) + "░" * (10 - fg // 10)

    lines = [
        f"📊 *گزارش سیستم کمک‌تصمیم بورس تهران*",
        f"🕐 {_tehran_now()}",
        f"─────────────────────",
        f"{mood['mood_emoji']} *حالت بازار: {mood['mood_fa']}*",
        f"  {mood['mood_desc']}",
        f"",
        f"🧠 ترس و طمع: {fg}/100 {mood['fg_label']}",
        f"  [{fg_bar}]",
        f"  {mood['fg_action']}",
        f"",
        f"💰 جریان پول: {flow_str} میلیارد",
        f"📈 مثبت: {mood['positive_count']} | 📉 منفی: {mood['negative_count']} | 💪 خریدار: {mood['avg_buyer_power']}",
    ]

    if sector_heatmap:
        lines.append("")
        lines.append(sector_heatmap)

    lines.append("─────────────────────")
    return "\n".join(lines)