from dataclasses import dataclass

PRICE_LIMIT_PCT = 0.05


@dataclass
class QueueSignal:
    signal: str
    description_fa: str
    confidence_bonus: int
    detail: str


def analyze_queue(row: dict) -> QueueSignal:
    def sf(v):
        try:
            return float(v or 0)
        except (ValueError, TypeError):
            return 0.0

    best_buy_price = sf(row.get("best_buy_price"))
    best_sell_price = sf(row.get("best_sell_price"))
    best_buy_vol = sf(row.get("best_buy_volume") or row.get("buy_volume_or_count"))
    best_sell_vol = sf(row.get("best_sell_volume"))
    last_price = sf(row.get("last_price") or row.get("close_price"))
    prev_close = sf(row.get("previous_close"))
    buyer_power = sf(row.get("buyer_power"))
    buy_num = sf(row.get("buy_power_numerator"))
    sell_den = sf(row.get("sell_power_denominator"))
    change_pct = sf(row.get("close_price_change_percent"))

    # فرمت جدید TSETMC — بدون داده صف واقعی
    no_queue = (best_buy_vol == 0 and best_sell_vol == 0)

    if no_queue:
        # استفاده از buyer_power و تغییر قیمت
        if buyer_power > 0 and buyer_power not in (1.0, 2.0):
            ratio = buyer_power
        elif buy_num > 0 and sell_den > 0:
            ratio = round(buy_num / sell_den, 2)
        else:
            # برآورد از تغییر قیمت
            if change_pct >= 4.5:
                return QueueSignal("estimated_buy_queue", "احتمال صف خرید (برآورد از قیمت)", 12, f"تغییر: {change_pct:+.1f}%")
            elif change_pct >= 2.0:
                return QueueSignal("estimated_buy_pressure", "فشار خرید (برآورد)", 6, f"تغییر: {change_pct:+.1f}%")
            elif change_pct <= -4.5:
                return QueueSignal("estimated_sell_queue", "احتمال صف فروش (برآورد از قیمت)", -12, f"تغییر: {change_pct:+.1f}%")
            elif change_pct <= -2.0:
                return QueueSignal("estimated_sell_pressure", "فشار فروش (برآورد)", -6, f"تغییر: {change_pct:+.1f}%")
            return QueueSignal("no_queue_data", "داده صف موجود نیست", 0, "")

        if ratio >= 3.0:
            return QueueSignal("buy_queue_dominant", "تقاضا غالب — صف خرید قوی‌تر از عرضه", 10, f"نسبت خریدار/فروشنده: {ratio:.1f}x")
        elif ratio >= 1.5:
            return QueueSignal("mild_buy_pressure", "فشار خرید ملایم", 5, f"نسبت: {ratio:.1f}x")
        elif ratio <= 0.33:
            return QueueSignal("sell_queue_dominant", "عرضه غالب — صف فروش قوی‌تر از تقاضا", -10, f"نسبت خریدار/فروشنده: {ratio:.1f}x")
        elif ratio <= 0.7:
            return QueueSignal("mild_sell_pressure", "فشار فروش ملایم", -5, f"نسبت: {ratio:.1f}x")
        return QueueSignal("balanced", "تعادل عرضه و تقاضا", 0, f"نسبت: {ratio:.1f}x")

    # داده صف واقعی موجود است
    if prev_close <= 0 or last_price <= 0:
        return QueueSignal("unknown", "اطلاعات صف در دسترس نیست", 0, "")

    upper_limit = prev_close * (1 + PRICE_LIMIT_PCT)
    lower_limit = prev_close * (1 - PRICE_LIMIT_PCT)
    at_upper = last_price >= upper_limit * 0.999
    at_lower = last_price <= lower_limit * 1.001

    ratio = (best_buy_vol / best_sell_vol) if best_sell_vol > 0 else (10.0 if best_buy_vol > 0 else 1.0)

    if at_upper and best_buy_vol > 0:
        return QueueSignal("buy_queue_at_limit", "صف خرید در سقف روزانه — تقاضا بسیار قوی", 15, f"نسبت خریدار/فروشنده: {ratio:.1f}x")
    if at_lower and best_sell_vol > 0:
        return QueueSignal("sell_queue_at_limit", "صف فروش در کف روزانه — عرضه بسیار قوی", -15, f"نسبت خریدار/فروشنده: {ratio:.1f}x")
    if ratio >= 3.0:
        return QueueSignal("buy_queue_dominant", "تقاضا غالب — صف خرید قوی‌تر از عرضه", 10, f"نسبت خریدار/فروشنده: {ratio:.1f}x")
    if ratio <= 0.33:
        return QueueSignal("sell_queue_dominant", "عرضه غالب — صف فروش قوی‌تر از تقاضا", -10, f"نسبت خریدار/فروشنده: {ratio:.1f}x")
    if ratio > 1.2:
        return QueueSignal("mild_buy_pressure", "فشار خرید ملایم", 5, f"نسبت: {ratio:.1f}x")
    if ratio < 0.8:
        return QueueSignal("mild_sell_pressure", "فشار فروش ملایم", -5, f"نسبت: {ratio:.1f}x")

    return QueueSignal("balanced", "تعادل عرضه و تقاضا", 0, f"نسبت: {ratio:.1f}x")