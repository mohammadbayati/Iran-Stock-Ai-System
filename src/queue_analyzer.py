from dataclasses import dataclass

PRICE_LIMIT_PCT = 0.05


@dataclass
class QueueSignal:
    signal: str
    description_fa: str
    confidence_bonus: int
    detail: str


def analyze_queue(row: dict) -> QueueSignal:
    try:
        best_buy_price = float(row.get("best_buy_price") or 0)
        best_sell_price = float(row.get("best_sell_price") or 0)
        best_buy_vol = float(row.get("buy_volume_or_count") or 0)
        best_sell_vol = float(row.get("best_sell_volume") or 0)
        last_price = float(row.get("last_price") or 0)
        prev_close = float(row.get("previous_close") or 0)
    except (ValueError, TypeError):
        return QueueSignal("unknown", "اطلاعات صف در دسترس نیست", 0, "")

    if prev_close <= 0 or last_price <= 0:
        return QueueSignal("unknown", "اطلاعات صف در دسترس نیست", 0, "")

    upper_limit = prev_close * (1 + PRICE_LIMIT_PCT)
    lower_limit = prev_close * (1 - PRICE_LIMIT_PCT)

    at_upper_limit = last_price >= upper_limit * 0.999
    at_lower_limit = last_price <= lower_limit * 1.001

    buy_sell_ratio = (best_buy_vol / best_sell_vol) if best_sell_vol > 0 else (10 if best_buy_vol > 0 else 1)

    if at_upper_limit and best_buy_vol > 0:
        return QueueSignal(
            signal="buy_queue_at_limit",
            description_fa="صف خرید در سقف روزانه — تقاضا بسیار قوی",
            confidence_bonus=15,
            detail=f"حجم صف خرید: {int(best_buy_vol):,}",
        )

    if at_lower_limit and best_sell_vol > 0:
        return QueueSignal(
            signal="sell_queue_at_limit",
            description_fa="صف فروش در کف روزانه — عرضه بسیار قوی",
            confidence_bonus=-15,
            detail=f"حجم صف فروش: {int(best_sell_vol):,}",
        )

    if buy_sell_ratio >= 3.0:
        return QueueSignal(
            signal="buy_queue_dominant",
            description_fa="تقاضا غالب — صف خرید قوی‌تر از عرضه",
            confidence_bonus=10,
            detail=f"نسبت خریدار/فروشنده: {buy_sell_ratio:.1f}x",
        )

    if buy_sell_ratio <= 0.33:
        return QueueSignal(
            signal="sell_queue_dominant",
            description_fa="عرضه غالب — صف فروش قوی‌تر از تقاضا",
            confidence_bonus=-10,
            detail=f"نسبت خریدار/فروشنده: {buy_sell_ratio:.1f}x",
        )

    if buy_sell_ratio > 1.2:
        return QueueSignal(
            signal="mild_buy_pressure",
            description_fa="فشار خرید ملایم",
            confidence_bonus=5,
            detail=f"نسبت: {buy_sell_ratio:.1f}x",
        )

    if buy_sell_ratio < 0.8:
        return QueueSignal(
            signal="mild_sell_pressure",
            description_fa="فشار فروش ملایم",
            confidence_bonus=-5,
            detail=f"نسبت: {buy_sell_ratio:.1f}x",
        )

    return QueueSignal(
        signal="balanced",
        description_fa="تعادل عرضه و تقاضا",
        confidence_bonus=0,
        detail=f"نسبت: {buy_sell_ratio:.1f}x",
    )