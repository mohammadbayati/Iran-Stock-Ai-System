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
        buyer_power = 0.0

    try:
        flow = float(row.get("real_money_flow") or 0)
    except (ValueError, TypeError):
        flow = 0.0

    try:
        change_pct = float(row.get("close_price_change_percent") or 0)
    except (ValueError, TypeError):
        change_pct = 0.0

    try:
        trade_value = float(row.get("trade_value") or 0)
    except (ValueError, TypeError):
        trade_value = 0.0

    no_queue_data = (buyer_power == 0.0 or buyer_power == 1.0 or buyer_power == 2.0) and flow == 0.0

    if no_queue_data:
        if change_pct > 3.0 and trade_value > 5e9:
            return SmartMoneySignal(
                signal="price_volume_bullish",
                strength=60,
                description_fa="رشد با حجم بالا",
                is_bullish=True,
                confidence_bonus=8,
            )
        elif change_pct > 1.0 and trade_value > 10e9:
            return SmartMoneySignal(
                signal="price_volume_bullish",
                strength=50,
                description_fa="رشد با حجم بالا",
                is_bullish=True,
                confidence_bonus=5,
            )
        elif change_pct > 0.0 and trade_value > 20e9:
            return SmartMoneySignal(
                signal="price_volume_bullish",
                strength=40,
                description_fa="جریان مثبت با ارزش بالا",
                is_bullish=True,
                confidence_bonus=3,
            )
        elif change_pct < -3.0 and trade_value > 5e9:
            return SmartMoneySignal(
                signal="price_volume_bearish",
                strength=60,
                description_fa="افت با حجم بالا",
                is_bullish=False,
                confidence_bonus=-8,
            )
        elif change_pct < -1.0 and trade_value > 10e9:
            return SmartMoneySignal(
                signal="price_volume_bearish",
                strength=50,
                description_fa="افت با حجم بالا",
                is_bullish=False,
                confidence_bonus=-5,
            )
        elif abs(change_pct) < 0.5 and trade_value > 20e9:
            return SmartMoneySignal(
                signal="high_value_flat",
                strength=30,
                description_fa="حجم پول بالا، قیمت راکد",
                is_bullish=True,
                confidence_bonus=3,
            )
        elif trade_value > 5e9:
            return SmartMoneySignal(
                signal="no_queue_active",
                strength=20,
                description_fa="بدون داده صف — معامله فعال",
                is_bullish=change_pct >= 0,
                confidence_bonus=1,
            )
        return SmartMoneySignal(
            signal="no_data",
            strength=0,
            description_fa="داده کافی در دسترس نیست",
            is_bullish=False,
            confidence_bonus=0,
        )

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
            description_fa="تجمیع هوشمند",
            is_bullish=True,
            confidence_bonus=20,
        )

    if money_leaving and retail_buying and change_pct > 1.0:
        strength = min(100, int(abs(flow) / 1e9 * 20 + 40))
        return SmartMoneySignal(
            signal="hidden_distribution",
            strength=strength,
            description_fa="توزیع پنهان",
            is_bullish=False,
            confidence_bonus=-15,
        )

    if money_entering and retail_buying:
        strength = min(100, int(buyer_power * 20 + flow / 1e9 * 10))
        return SmartMoneySignal(
            signal="aligned_bullish",
            strength=strength,
            description_fa="هم‌راستای صعودی",
            is_bullish=True,
            confidence_bonus=10,
        )

    if money_leaving and retail_selling:
        strength = min(100, int((1 / max(buyer_power, 0.1)) * 15 + abs(flow) / 1e9 * 10))
        return SmartMoneySignal(
            signal="aligned_bearish",
            strength=strength,
            description_fa="هم‌راستای نزولی",
            is_bullish=False,
            confidence_bonus=-10,
        )

    if retail_buying:
        return SmartMoneySignal(
            signal="retail_driven_up",
            strength=30,
            description_fa="رشد حقیقی‌محور",
            is_bullish=True,
            confidence_bonus=-5,
        )

    if retail_selling:
        return SmartMoneySignal(
            signal="retail_driven_down",
            strength=30,
            description_fa="افت حقیقی‌محور",
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