"""
Layer 3 — Market Mood Calculator
"""

import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class MarketMood:
    mood: str
    mood_fa: str
    emoji: str
    description_fa: str
    positive_count: int
    negative_count: int
    total_count: int
    buyer_power_avg: float
    total_flow: float
    advance_decline_ratio: float


def _safe_float(val) -> float:
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def _tehran_now() -> str:
    tehran = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    return tehran.strftime("%Y-%m-%d  %H:%M")


def calculate_market_mood(df: pd.DataFrame) -> MarketMood:
    if df.empty:
        return MarketMood("unknown", "نامشخص", "❓", "داده کافی نیست", 0, 0, 0, 1.0, 0.0, 1.0)

    df = df.copy()
    df["_chg"] = df["close_price_change_percent"].apply(_safe_float)
    df["_flow"] = df["real_money_flow"].apply(_safe_float)
    df["_bp"] = df["buyer_power"].apply(_safe_float)
    df["_val"] = df.get("trade_value", pd.Series(0, index=df.index)).apply(_safe_float)

    positive = (df["_chg"] > 0).sum()
    negative = (df["_chg"] < 0).sum()
    total = len(df)

    total_flow = df["_flow"].sum()
    if abs(total_flow) < 1e9:
        df["_estimated_flow"] = df["_chg"] * df["_val"] / 100
        total_flow = df["_estimated_flow"].sum()

    buyer_power_avg = df["_bp"].mean()
    if abs(buyer_power_avg - 1.0) < 0.05:
        buyer_power_avg = round(positive / max(negative, 1), 2)

    ad_ratio = positive / max(negative, 1)

    bullish = ad_ratio >= 1.5 and total_flow > 0
    bearish = ad_ratio <= 0.7 or total_flow < -50e9

    if bullish and total_flow > 100e9:
        mood, mood_fa, emoji, desc = "strong_bull", "بازار صعودی قوی", "🚀", "جریان پول مثبت و اکثر نمادها سبز"
    elif bullish:
        mood, mood_fa, emoji, desc = "bull", "بازار صعودی", "📈", "اکثر نمادها مثبت با جریان ورودی"
    elif bearish and total_flow < -100e9:
        mood, mood_fa, emoji, desc = "strong_bear", "بازار نزولی قوی", "🔴", "خروج گسترده پول و اکثر نمادها منفی"
    elif bearish:
        mood, mood_fa, emoji, desc = "bear", "بازار نزولی", "📉", "فشار فروش غالب است"
    else:
        mood, mood_fa, emoji, desc = "neutral", "بازار خنثی", "⚖️", "سیگنال واضحی وجود ندارد — صبر کنید"

    return MarketMood(
        mood=mood, mood_fa=mood_fa, emoji=emoji,
        description_fa=desc,
        positive_count=int(positive),
        negative_count=int(negative),
        total_count=total,
        buyer_power_avg=round(buyer_power_avg, 2),
        total_flow=total_flow,
        advance_decline_ratio=round(ad_ratio, 2),
    )


def format_market_header(mood: MarketMood, sector_heatmap: str = "") -> str:
    flow_b = mood.total_flow / 1e9
    flow_str = f"{flow_b:+.0f}"

    lines = [
        "📊 *گزارش سیستم کمک‌تصمیم بورس تهران*",
        f"🕐 {_tehran_now()}",
        "─────────────────────",
        f"{mood.emoji} *حالت بازار: {mood.mood_fa}*",
        f"  {mood.description_fa}",
        "",
        f"💰 جریان پول کل: {flow_str} میلیارد تومان",
        f"📈 مثبت: {mood.positive_count} | 📉 منفی: {mood.negative_count}",
        f"💪 قدرت خریدار: {mood.buyer_power_avg}",
    ]

    if sector_heatmap:
        lines.append("")
        lines.append(sector_heatmap)

    lines.append("─────────────────────")
    return "\n".join(lines)