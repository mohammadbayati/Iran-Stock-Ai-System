import pandas as pd
from datetime import datetime


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
    positive_count = (changes > 0).sum()
    negative_count = (changes < 0).sum()
    breadth_pct = positive_count / len(df) * 100 if len(df) > 0 else 50

    retail_selling = avg_buyer_power < 0.9
    retail_buying = avg_buyer_power > 1.3
    money_entering = total_flow > 10e9
    money_leaving = total_flow < -10e9

    if money_entering and retail_selling:
        mood, mood_fa, mood_desc, emoji = "smart_accumulation", "🧠 تجمیع هوشمند", "حقیقی‌ها می‌فروشند، پول هوشمند وارد می‌شود", "🟢"
    elif money_entering and retail_buying and breadth_pct > 60:
        mood, mood_fa, mood_desc, emoji = "broad_rally", "🚀 رالی گسترده", "هم پول و هم خریدار وارد — روند صعودی قوی", "🟢"
    elif money_leaving and retail_buying:
        mood, mood_fa, mood_desc, emoji = "distribution", "⚠️ توزیع", "حقیقی‌ها می‌خرند، پول هوشمند خارج می‌شود — احتیاط", "🔴"
    elif money_leaving and retail_selling and breadth_pct < 40:
        mood, mood_fa, mood_desc, emoji = "broad_selloff", "🔻 فروش گسترده", "هم پول و هم فروشنده خارج — روند نزولی", "🔴"
    else:
        mood, mood_fa, mood_desc, emoji = "mixed", "⚖️ بازار خنثی", "سیگنال واضحی وجود ندارد — صبر کنید", "🟡"

    return {
        "mood": mood, "mood_fa": mood_fa, "mood_desc": mood_desc, "mood_emoji": emoji,
        "total_flow_billion": round(total_flow / 1e9, 1),
        "avg_buyer_power": round(avg_buyer_power, 2),
        "positive_count": int(positive_count),
        "negative_count": int(negative_count),
        "breadth_pct": round(breadth_pct, 1),
    }


def format_market_header(mood: dict, sector_heatmap: str = "") -> str:
    now = datetime.now().strftime("%Y-%m-%d  %H:%M")
    flow = mood["total_flow_billion"]
    flow_str = f"+{flow:.0f}" if flow >= 0 else f"{flow:.0f}"

    lines = [
        f"📊 *گزارش سیستم کمک‌تصمیم بورس تهران*",
        f"🕐 {now}",
        f"─────────────────────",
        f"{mood['mood_emoji']} *حالت بازار: {mood['mood_fa']}*",
        f"  {mood['mood_desc']}",
        f"",
        f"💰 جریان پول کل: {flow_str} میلیارد تومان",
        f"📈 مثبت: {mood['positive_count']} | 📉 منفی: {mood['negative_count']}",
        f"💪 قدرت خریدار: {mood['avg_buyer_power']}",
    ]

    if sector_heatmap:
        lines += ["", sector_heatmap]

    lines.append("─────────────────────")
    return "\n".join(lines)