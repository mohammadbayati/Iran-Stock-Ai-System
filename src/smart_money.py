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

    retail_buying = buyer_power >= 1.3
    retail_selling = buyer_power <= 0.8
    money_entering = flow > 0
    money_leaving = flow < 0
    price_falling = change_pct < -1.0

    if money_entering and retail_selling and (price_falling or abs(change_pct) < 1.0):
        strength = min(100, int(abs(flow) / 1e9 * 20 + 40))
        return SmartMoneySignal(
            signal="hidden_accumulation",
            strength=strength,
            description_fa="تجمیع هوشمند: حقیقی می‌فروشد، پول هوشمند وارد می‌شود",
            is_bullish=True,
            confidence_bonus=20,
        )

    if money_leaving and retail_buying and change_pct > 1.0:
        strength = min(100, int(abs(flow) / 1e9 * 20 + 40))
        return SmartMoneySignal(
            signal="hidden_distribution",
            strength=strength,
            description_fa="توزیع پنهان: حقیقی می‌خرد، پول هوشمند خارج می‌شود",
            is_bullish=False,
            confidence_bonus=-15,
        )

    if money_entering and retail_buying:
        strength = min(100, int(buyer_power * 20 + flow / 1e9 * 10))
        return SmartMoneySignal(
            signal="aligned_bullish",
            strength=strength,
            description_fa="هم‌راستای صعودی: خریدار و پول هر دو وارد",
            is_bullish=True,
            confidence_bonus=10,
        )

    if money_leaving and retail_selling:
        strength = min(100, int((1 / max(buyer_power, 0.1)) * 15 + abs(flow) / 1e9 * 10))
        return SmartMoneySignal(
            signal="aligned_bearish",
            strength=strength,
            description_fa="هم‌راستای نزولی: فروشنده و خروج پول هر دو تایید",
            is_bullish=False,
            confidence_bonus=-10,
        )

    if retail_buying and not money_entering:
        return SmartMoneySignal(
            signal="retail_driven_up",
            strength=30,
            description_fa="رشد حقیقی‌محور: بدون پشتوانه پول هوشمند",
            is_bullish=True,
            confidence_bonus=-5,
        )

    if retail_selling and not money_leaving:
        return SmartMoneySignal(
            signal="retail_driven_down",
            strength=30,
            description_fa="افت حقیقی‌محور: ممکن است اغراق‌آمیز باشد",
            is_bullish=False,
            confidence_bonus=5,
        )

    return SmartMoneySignal(
        signal="neutral",
        strength=0,
        description_fa="بدون سیگنال واضح",
        is_bullish=False,
        confidence_bonus=0,
    )