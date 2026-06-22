"""
Layer 1 — Smart Money Divergence Detector
"""

from dataclasses import dataclass


@dataclass
class SmartMoneySignal:
    signal: str
    strength: int
    description_fa: str
    is_bullish: bool
    confidence_bonus: int


def analyze_smart_money(row: dict) -> SmartMoneySignal:
    try:
        buyer_power = float(row.get("buyer_power") or 0)
    except (ValueError, TypeError):
        buyer_power = 1.0

    try:
        flow = float(row.get("real_money_flow") or 0)
    except (ValueError, TypeError):
        flow = 0.0

    try:
        change_pct = float(row.get("close_price_change_percent") or 0)
    except (ValueError, TypeError):
        change_pct = 0.0

    try:
        trade_value = float(row.get("trade_value") or row.get("total_trade_value") or 0)
    except (ValueError, TypeError):
        trade_value = 0.0

    # فرمت جدید TSETMC (2 قسمت @@) داده صف ندارد
    no_queue_data = (buyer_power in (0.0, 1.0, 2.0)) and flow == 0.0

    if no_queue_data:
        if change_pct > 3.0 and trade_value > 5e9:
            return SmartMoneySignal("price_volume_bullish", 60, "رشد با حجم بالا", True, 8)
        if change_pct > 1.0 and trade_value > 10e9:
            return SmartMoneySignal("price_volume_bullish", 50, "رشد با حجم بالا", True, 5)
        if change_pct > 0.0 and trade_value > 20e9:
            return SmartMoneySignal("price_volume_bullish", 40, "جریان مثبت با ارزش بالا", True, 3)
        if change_pct < -3.0 and trade_value > 5e9:
            return SmartMoneySignal("price_volume_bearish", 60, "افت با حجم بالا", False, -8)
        if change_pct < -1.0 and trade_value > 10e9:
            return SmartMoneySignal("price_volume_bearish", 50, "افت با حجم بالا", False, -5)
        if abs(change_pct) < 0.5 and trade_value > 20e9:
            return SmartMoneySignal("high_value_flat", 30, "حجم پول بالا، قیمت راکد", True, 3)
        if trade_value > 5e9:
            return SmartMoneySignal("no_queue_active", 20, "بدون داده صف — معامله فعال", change_pct >= 0, 1)
        return SmartMoneySignal("no_data", 0, "داده کافی در دسترس نیست", False, 0)

    retail_buying = buyer_power >= 1.3
    retail_selling = buyer_power <= 0.8
    money_entering = flow > 0
    money_leaving = flow < 0
    price_falling = change_pct < -1.0
    price_rising = change_pct > 1.0

    if money_entering and retail_selling and (price_falling or abs(change_pct) < 1.0):
        strength = min(100, int(abs(flow) / 1e9 * 20 + 40))
        return SmartMoneySignal("hidden_accumulation", strength,
            "تجمیع هوشمند: حقیقی می‌فروشد، پول هوشمند وارد می‌شود", True, 20)

    if money_leaving and retail_buying and price_rising:
        strength = min(100, int(abs(flow) / 1e9 * 20 + 40))
        return SmartMoneySignal("hidden_distribution", strength,
            "توزیع پنهان: حقیقی می‌خرد، پول هوشمند خارج می‌شود", False, -15)

    if money_entering and retail_buying:
        strength = min(100, int(buyer_power * 20 + flow / 1e9 * 10))
        return SmartMoneySignal("aligned_bullish", strength,
            "هم‌راستای صعودی: خریدار و پول هر دو وارد", True, 10)

    if money_leaving and retail_selling:
        strength = min(100, int((1 / max(buyer_power, 0.1)) * 15 + abs(flow) / 1e9 * 10))
        return SmartMoneySignal("aligned_bearish", strength,
            "هم‌راستای نزولی: فروشنده و خروج پول هر دو تایید", False, -10)

    if retail_buying and not money_entering:
        return SmartMoneySignal("retail_driven_up", 30,
            "رشد حقیقی‌محور: بدون پشتوانه پول هوشمند", True, -5)

    if retail_selling and not money_leaving:
        return SmartMoneySignal("retail_driven_down", 30,
            "افت حقیقی‌محور: ممکن است اغراق‌آمیز باشد", False, 5)

    return SmartMoneySignal("neutral", 0, "بدون سیگنال واضح", False, 0)