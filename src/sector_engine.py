import pandas as pd
from dataclasses import dataclass

SECTOR_MAP = {
    "شپنا": "پتروشیمی", "شبندر": "پتروشیمی", "شپدیس": "پتروشیمی",
    "نوری": "پتروشیمی", "فارس": "پتروشیمی", "جم": "پتروشیمی",
    "خودرو": "خودرو", "خساپا": "خودرو", "خبهمن": "خودرو",
    "خپارس": "خودرو", "خکاوه": "خودرو",
    "فملی": "فلزات", "کچاد": "فلزات", "فخوز": "فلزات",
    "ذوب": "فلزات", "فولاد": "فلزات",
    "وبصادر": "بانک", "وبملت": "بانک", "وتجارت": "بانک",
    "وپارس": "بانک", "وشهر": "بانک",
    "شستا": "سرمایه‌گذاری", "وغدیر": "سرمایه‌گذاری",
    "وصندوق": "سرمایه‌گذاری", "ومعادن": "سرمایه‌گذاری",
    "اهرم": "ETF", "نارنج اهرم": "ETF", "کمند": "ETF",
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


def calculate_sector_strengths(df: pd.DataFrame) -> dict:
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

        if avg_flow > 5e9 and avg_bp >= 1.2 and avg_chg > 0:
            status, status_fa, bonus = "leading", "🟢 پیشرو", 10
        elif avg_flow < -5e9 or avg_bp < 0.8 or avg_chg < -1.5:
            status, status_fa, bonus = "lagging", "🔴 عقب‌مانده", -10
        else:
            status, status_fa, bonus = "neutral", "🟡 خنثی", 0

        results[sector] = SectorStrength(
            sector=sector, symbol_count=len(group),
            avg_flow=avg_flow, avg_buyer_power=avg_bp,
            avg_change_pct=avg_chg, total_flow=total_flow,
            status=status, status_fa=status_fa, confidence_bonus=bonus,
        )

    return results


def format_sector_heatmap(sector_strengths: dict) -> str:
    lines = ["🗺 نقشه گردش سکتور:"]
    all_sectors = sorted(sector_strengths.values(), key=lambda x: x.total_flow, reverse=True)
    for s in all_sectors:
        flow_b = s.total_flow / 1e9
        lines.append(f"  {s.status_fa} {s.sector} | جریان: {flow_b:+.0f}B | قدرت خریدار: {s.avg_buyer_power:.1f}")
    return "\n".join(lines)