"""
Layer 4 — Sector Rotation Intelligence

Groups symbols by sector, calculates sector-level strength,
and identifies leading vs lagging sectors for today.

Only recommends entry in leading sectors.
Symbols in lagging sectors are downgraded regardless of individual signals.
"""

import pandas as pd
from dataclasses import dataclass

# Sector mapping for common Iran market symbols
SECTOR_MAP = {
    # پتروشیمی
    "شپنا": "پتروشیمی", "شبندر": "پتروشیمی", "شپدیس": "پتروشیمی",
    "نوری": "پتروشیمی", "فارس": "پتروشیمی", "جم": "پتروشیمی",
    "پتروپارس": "پتروشیمی", "مارون": "پتروشیمی", "کرماشا": "پتروشیمی",
    "اروند": "پتروشیمی", "شفن": "پتروشیمی", "شکربن": "پتروشیمی",
    "پارسان": "پتروشیمی", "شاوان": "پتروشیمی", "شرانل": "پتروشیمی",
    "زاگرس": "پتروشیمی", "شزنگ": "پتروشیمی", "شگویا": "پتروشیمی",
    "شاملا": "پتروشیمی", "کیمیاتک": "پتروشیمی",
    # خودرو و قطعات
    "خودرو": "خودرو", "خساپا": "خودرو", "خبهمن": "خودرو",
    "خپارس": "خودرو", "خکاوه": "خودرو", "ختوقا": "خودرو",
    "خاور": "خودرو", "خریخت": "خودرو", "خزامیا": "خودرو",
    "خمحور": "خودرو", "خنصیر": "خودرو", "خشرق": "خودرو",
    "خلنت": "خودرو", "خمهر": "خودرو", "خکار": "خودرو",
    "خرینگ": "خودرو", "خفناور": "خودرو", "خاذین": "خودرو",
    # فلزات اساسی
    "فملی": "فلزات", "کچاد": "فلزات", "فخوز": "فلزات",
    "ذوب": "فلزات", "فولاد": "فلزات", "هرمز": "فلزات",
    "ارفع": "فلزات", "کاوه": "فلزات", "نوردلرستان": "فلزات",
    "فسپا": "فلزات", "فلوله": "فلزات", "فاسمین": "فلزات",
    "فنوال": "فلزات", "میدکو": "فلزات", "فافق": "فلزات",
    "فایرا": "فلزات", "فروس": "فلزات", "کرور": "فلزات",
    # بانک و اعتبار
    "وبصادر": "بانک", "وبملت": "بانک", "وتجارت": "بانک",
    "وپارس": "بانک", "وشهر": "بانک", "وسینا": "بانک",
    "وکار": "بانک", "ودی": "بانک", "واقتصاد": "بانک",
    "وآیند": "بانک", "وخاور": "بانک", "وخارزم": "بانک",
    "شبریز": "بانک", "وزمین": "بانک", "وسپه": "بانک",
    "وپاسار": "بانک", "وپست": "بانک",
    # سرمایه‌گذاری و هلدینگ
    "شستا": "سرمایه‌گذاری", "وغدیر": "سرمایه‌گذاری",
    "وصندوق": "سرمایه‌گذاری", "ومعادن": "سرمایه‌گذاری",
    "وامید": "سرمایه‌گذاری", "وبهمن": "سرمایه‌گذاری",
    "وتوس": "سرمایه‌گذاری", "وصنا": "سرمایه‌گذاری",
    "ونوین": "سرمایه‌گذاری", "فرابورس": "سرمایه‌گذاری",
    "بورس": "سرمایه‌گذاری", "وگستر": "سرمایه‌گذاری",
    "سرو": "سرمایه‌گذاری", "وسبحان": "سرمایه‌گذاری",
    "وتوکا": "سرمایه‌گذاری", "وصنعت": "سرمایه‌گذاری",
    # سیمان
    "سپاها": "سیمان", "سشرق": "سیمان", "سمازن": "سیمان",
    "سنوین": "سیمان", "سهگمت": "سیمان", "سکرما": "سیمان",
    "سرود": "سیمان", "سصفها": "سیمان", "سدشت": "سیمان",
    "سفارس": "سیمان", "سخاش": "سیمان", "سیلام": "سیمان",
    "ساراب": "سیمان", "سغرب": "سیمان", "سبهان": "سیمان",
    # دارو و بهداشت
    "دارو": "دارو", "دجابر": "دارو", "دکوثر": "دارو",
    "دشیمی": "دارو", "دلقما": "دارو", "وپخش": "دارو",
    "دامین": "دارو", "دروز": "دارو", "داور": "دارو",
    "دسبحا": "دارو", "دتماد": "دارو", "دفرا": "دارو",
    "شسپا": "دارو", "دعبید": "دارو", "درازک": "دارو",
    "دبالک": "دارو", "دحاوی": "دارو", "دیران": "دارو",
    # غذا و کشاورزی
    "غدشت": "غذا", "غگل": "غذا", "غپینو": "غذا",
    "غبشهر": "غذا", "غشاذر": "غذا", "غالبر": "غذا",
    "غمارگارین": "غذا", "غنوش": "غذا", "غمینو": "غذا",
    "غصینو": "غذا", "غویتا": "غذا", "غشان": "غذا",
    "غفارس": "غذا", "غزر": "غذا", "غمهر": "غذا",
    # چاپ و بسته‌بندی
    "چاپ": "چاپ و بسته‌بندی", "ممسنی": "چاپ و بسته‌بندی",
    "چکاوه": "چاپ و بسته‌بندی", "چکاپا": "چاپ و بسته‌بندی",
    "چافست": "چاپ و بسته‌بندی", "چخزر": "چاپ و بسته‌بندی",
    # بیمه
    "البرز": "بیمه", "آسیا": "بیمه", "بپاس": "بیمه",
    "ملت": "بیمه", "دانا": "بیمه", "سامان": "بیمه",
    "ما": "بیمه", "کوثر": "بیمه", "اتکام": "بیمه",
    # مخابرات
    "اخابر": "مخابرات", "همراه": "مخابرات", "رتاپ": "مخابرات",
    "ذتلیا": "مخابرات", "شتوسا": "مخابرات",
    # انرژی و نفت
    "شتران": "انرژی", "شنفت": "انرژی",
    "پالایش": "انرژی", "شپاس": "انرژی", "شرفا": "انرژی",
    # معدن
    "کگل": "معدن", "کمدور": "معدن", "کیسون": "معدن",
    "باما": "معدن", "کنور": "معدن", "کاما": "معدن",
    "کزنو": "معدن", "کسرا": "معدن",
    # مواد شیمیایی
    "شمواد": "شیمیایی", "شکلر": "شیمیایی", "شصفها": "شیمیایی",
    "شپترو": "شیمیایی", "شدوص": "شیمیایی", "شلرد": "شیمیایی",
    "شیران": "شیمیایی", "خرد": "شیمیایی",
    # صندوق ETF و اهرمی
    "اهرم": "ETF", "کمند": "ETF", "طلا": "ETF",
    "سکه": "ETF", "کیان": "ETF", "توان": "ETF",
    "فیروزه": "ETF", "امین": "ETF",
    # پیمانکاری و ساختمان
    "ثاباد": "ساختمان", "ثفارس": "ساختمان", "ثمسکن": "ساختمان",
    "ثنوسا": "ساختمان", "ثالوند": "ساختمان", "ثشاهد": "ساختمان",
    "ثعمرا": "ساختمان",
    # برق و الکترونیک
    "برق": "برق", "بترانس": "برق", "بکاب": "برق",
    "بمپنا": "برق", "بنو": "برق", "لپارس": "برق",
}

DEFAULT_SECTOR = "سایر"


@dataclass
class SectorStrength:
    sector: str
    symbol_count: int
    avg_flow: float          # average real_money_flow
    avg_buyer_power: float
    avg_change_pct: float
    total_flow: float
    status: str              # "leading" / "neutral" / "lagging"
    status_fa: str
    confidence_bonus: int    # applied to all symbols in this sector


def get_sector(symbol: str) -> str:
    return SECTOR_MAP.get(symbol, DEFAULT_SECTOR)


def calculate_sector_strengths(df: pd.DataFrame) -> dict[str, SectorStrength]:
    """
    df: full symbols dataframe with real_money_flow, buyer_power, close_price_change_percent
    Returns: dict of sector_name → SectorStrength
    """
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

    results = {}
    for sector, group in df.groupby("sector"):
        avg_flow = group["_flow"].mean()
        avg_bp = group["_bp"].mean()
        avg_chg = group["_chg"].mean()
        total_flow = group["_flow"].sum()

        # Classify sector
        if avg_flow > 5e9 and avg_bp >= 1.2 and avg_chg > 0:
            status = "leading"
            status_fa = "🟢 پیشرو"
            bonus = 10
        elif avg_flow < -5e9 or avg_bp < 0.8 or avg_chg < -1.5:
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
    """Returns a Persian text block for the Telegram report header."""
    lines = ["🗺 نقشه گردش سکتور امروز:"]

    leading = [s for s in sector_strengths.values() if s.status == "leading"]
    neutral = [s for s in sector_strengths.values() if s.status == "neutral"]
    lagging = [s for s in sector_strengths.values() if s.status == "lagging"]

    for s in sorted(leading, key=lambda x: x.total_flow, reverse=True):
        flow_b = s.total_flow / 1e9
        lines.append(f"  {s.status_fa} {s.sector} | جریان: {flow_b:+.0f}B | قدرت خریدار: {s.avg_buyer_power:.1f}")

    for s in sorted(neutral, key=lambda x: x.total_flow, reverse=True):
        flow_b = s.total_flow / 1e9
        lines.append(f"  {s.status_fa} {s.sector} | جریان: {flow_b:+.0f}B | قدرت خریدار: {s.avg_buyer_power:.1f}")

    for s in sorted(lagging, key=lambda x: x.total_flow):
        flow_b = s.total_flow / 1e9
        lines.append(f"  {s.status_fa} {s.sector} | جریان: {flow_b:+.0f}B | قدرت خریدار: {s.avg_buyer_power:.1f}")

    return "\n".join(lines)