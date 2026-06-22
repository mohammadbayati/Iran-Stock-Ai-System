"""
Layer 4 — Sector Rotation Intelligence
"""

import pandas as pd
from dataclasses import dataclass

SECTOR_MAP = {
    # پتروشیمی
    "شپنا": "پتروشیمی", "شبندر": "پتروشیمی", "شپدیس": "پتروشیمی",
    "نوری": "پتروشیمی", "فارس": "پتروشیمی", "جم": "پتروشیمی",
    "پتروفارس": "پتروشیمی",
    # نفت و گاز
    "پتروصبا": "نفت و گاز", "شتران": "نفت و گاز", "شسپا": "نفت و گاز",
    # خودرو
    "خودرو": "خودرو", "خساپا": "خودرو", "خبهمن": "خودرو",
    "خپارس": "خودرو", "خکاوه": "خودرو", "وساپا": "خودرو",
    "سایپا": "خودرو", "ورنا": "خودرو",
    # فلزات
    "فملی": "فلزات", "کچاد": "فلزات", "فخوز": "فلزات",
    "ذوب": "فلزات", "فولاد": "فلزات", "کهمدا": "فلزات",
    "فافق": "فلزات",
    # بانک
    "وبصادر": "بانک", "وبملت": "بانک", "وتجارت": "بانک",
    "وپارس": "بانک", "وشهر": "بانک", "وگردش": "بانک",
    # سرمایه‌گذاری
    "شستا": "سرمایه‌گذاری", "وغدیر": "سرمایه‌گذاری",
    "وصندوق": "سرمایه‌گذاری", "ومعادن": "سرمایه‌گذاری",
    "فرابورس": "سرمایه‌گذاری", "پایش": "سرمایه‌گذاری",
    # ETF
    "اهرم": "ETF", "نارنج اهرم": "ETF", "کمند": "ETF",
    # دارو
    "دارو": "دارو", "دجابر": "دارو", "دکوثر": "دارو",
    # سیمان
    "سصوفی": "سیمان", "سصوفي": "سیمان", "سمازن": "سیمان",
    # معدن
    "زبینا": "معدن", "زکوثر": "معدن", "کمینا": "معدن", "كمينا": "معدن",
    # غذایی
    "غشان": "غذایی",
    # کاغذ
    "چاپ": "کاغذ",
    # مخابرات
    "اخابر": "مخابرات",
}

DEFAULT_SECTOR = "سایر"


@dataclass
class SectorStrength:
    sector: str
    symbol_count: int
    avg_flow: float
    avg_buyer_power: float
    avg_change_pct: float
    total_flow: float
    status: str
    status_fa: str
    confidence_bonus: int


def get_sector(symbol: str) -> str:
    return SECTOR_MAP.get(symbol, DEFAULT_SECTOR)


def calculate_sector_strengths(df: pd.DataFrame) -> dict[str, SectorStrength]:
    df = df.copy()
    df["sector"] = df["symbol"].apply(get_sector)

    def safe_float(val):
        try:
            return float(val or 0)
        except (ValueError, TypeError):
            return 0.0

    df["_flow"] = df["real_money_flow"].apply(safe_float)
    df["_bp"] = df["buyer_power"].apply(safe_float)
    df["_chg"] = df["close_price_change_percent"].apply(safe_float)

    # اگه همه real_money_flow صفر بودن → estimated flow از تغییر قیمت × ارزش معامله
    if df["_flow"].abs().sum() < 1e9:
        def safe_val(v):
            try:
                return float(v or 0)
            except (ValueError, TypeError):
                return 0.0
        df["_val"] = df.get("trade_value", df.get("total_trade_value", pd.Series(0, index=df.index))).apply(safe_val)
        df["_flow"] = df["_chg"] * df["_val"] / 100

    # buyer_power همه 1.0 → از A/D ratio استفاده کن
    bp_vals = df["_bp"]
    if bp_vals.std() < 0.05:
        pos = (df["_chg"] > 0).sum()
        neg = (df["_chg"] < 0).sum()
        ad_ratio = round(pos / max(neg, 1), 2)
        df["_bp"] = df["_chg"].apply(lambda x: 1.3 if x > 0 else (0.7 if x < 0 else 1.0))

    results = {}
    for sector, group in df.groupby("sector"):
        avg_flow = group["_flow"].mean()
        avg_bp = group["_bp"].mean()
        avg_chg = group["_chg"].mean()
        total_flow = group["_flow"].sum()

        if avg_chg > 1.0 and avg_bp >= 1.1:
            status = "leading"
            status_fa = "🟢 پیشرو"
            bonus = 10
        elif avg_chg < -1.0 or avg_bp < 0.9:
            status = "lagging"
            status_fa = "🔴 عقب‌مانده"
            bonus = -10
        else:
            status = "neutral"
            status_fa = "🟡 خنثی"
            bonus = 0

        results[sector] = SectorStrength(
            sector=sector,
            symbol_count=len(group),
            avg_flow=avg_flow,
            avg_buyer_power=avg_bp,
            avg_change_pct=avg_chg,
            total_flow=total_flow,
            status=status,
            status_fa=status_fa,
            confidence_bonus=bonus,
        )

    return results


def format_sector_heatmap(sector_strengths: dict) -> str:
    lines = ["🗺 نقشه گردش سکتور امروز:"]

    leading = [s for s in sector_strengths.values() if s.status == "leading"]
    neutral = [s for s in sector_strengths.values() if s.status == "neutral"]
    lagging = [s for s in sector_strengths.values() if s.status == "lagging"]

    for s in sorted(leading, key=lambda x: x.total_flow, reverse=True):
        flow_b = s.total_flow / 1e9
        lines.append(f"  {s.status_fa} {s.sector} | جریان: {flow_b:+.0f}B | میانگین تغییر: {s.avg_change_pct:+.1f}%")

    for s in sorted(neutral, key=lambda x: x.total_flow, reverse=True):
        flow_b = s.total_flow / 1e9
        lines.append(f"  {s.status_fa} {s.sector} | جریان: {flow_b:+.0f}B | میانگین تغییر: {s.avg_change_pct:+.1f}%")

    for s in sorted(lagging, key=lambda x: x.total_flow):
        flow_b = s.total_flow / 1e9
        lines.append(f"  {s.status_fa} {s.sector} | جریان: {flow_b:+.0f}B | میانگین تغییر: {s.avg_change_pct:+.1f}%")

    return "\n".join(lines)