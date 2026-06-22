"""
Layer 2 — Queue Intelligence (تحلیل صف)

In Iran market, buy/sell queues are critical signals that most screeners ignore.
Queue dynamics reveal supply/demand imbalance BEFORE price moves.
"""

import math
from dataclasses import dataclass


PRICE_LIMIT_PCT = 0.05  # Iran daily limit ±5%


def _safe(val, default=0.0) -> float:
    try:
        v = float(val or 0)
        return default if math.isnan(v) else v
    except (TypeError, ValueError):
        return default


@dataclass
class QueueSignal:
    signal: str
    description_fa: str
    confidence_bonus: int
    detail: str


def analyze_queue(row: dict) -> QueueSignal:
    best_buy_price  = _safe(row.get("best_buy_price"))
    best_sell_price = _safe(row.get("best_sell_price"))
    best_buy_vol    = _safe(row.get("best_buy_volume"))
    best_sell_vol   = _safe(row.get("best_sell_volume"))
    last_price      = _safe(row.get("last_price"))
    prev_close      = _safe(row.get("previous_close"))
    change_pct      = _safe(row.get("close_price_change_percent"))

    if prev_close <= 0 or last_price <= 0:
        if change_pct > 4.5:
            return QueueSignal("estimated_buy_limit", "احتمال صف خرید (تغییر قیمت: {:.1f}%)".format(change_pct), 12, "")
        if change_pct < -4.5:
            return QueueSignal("estimated_sell_limit", "احتمال صف فروش (تغییر قیمت: {:.1f}%)".format(change_pct), -12, "")
        if change_pct > 2.0:
            return QueueSignal("estimated_buy_pressure", "فشار خرید تخمینی (تغییر قیمت: {:.1f}%)".format(change_pct), 6, "")
        if change_pct < -2.0:
            return QueueSignal("estimated_sell_pressure", "فشار فروش تخمینی (تغییر قیمت: {:.1f}%)".format(change_pct), -6, "")
        return QueueSignal("unknown", "داده صف موجود نیست", 0, "")

    upper_limit = prev_close * (1 + PRICE_LIMIT_PCT)
    lower_limit = prev_close * (1 - PRICE_LIMIT_PCT)

    at_upper_limit = last_price >= upper_limit * 0.999
    at_lower_limit = last_price <= lower_limit * 1.001

    buy_sell_ratio = (best_buy_vol / best_sell_vol) if best_sell_vol > 0 else (10.0 if best_buy_vol > 0 else 1.0)

    if at_upper_limit and best_buy_vol > 0:
        return QueueSignal(
            "buy_queue_at_limit",
            "صف خرید در سقف روزانه — تقاضا بسیار قوی",
            15,
            f"حجم صف خرید: {int(best_buy_vol):,}",
        )

    if at_lower_limit and best_sell_vol > 0:
        return QueueSignal(
            "sell_queue_at_limit",
            "صف فروش در کف روزانه — عرضه بسیار قوی",
            -15,
            f"حجم صف فروش: {int(best_sell_vol):,}",
        )

    if buy_sell_ratio >= 3.0:
        return QueueSignal(
            "buy_queue_dominant",
            "تقاضا غالب — صف خرید قوی‌تر از عرضه",
            10,
            f"نسبت خریدار/فروشنده: {buy_sell_ratio:.1f}x",
        )

    if buy_sell_ratio <= 0.33:
        return QueueSignal(
            "sell_queue_dominant",
            "عرضه غالب — صف فروش قوی‌تر از تقاضا",
            -10,
            f"نسبت خریدار/فروشنده: {buy_sell_ratio:.1f}x",
        )

    if 0.8 <= buy_sell_ratio <= 1.2:
        return QueueSignal(
            "balanced",
            "تعادل عرضه و تقاضا",
            0,
            f"نسبت خریدار/فروشنده: {buy_sell_ratio:.1f}x",
        )

    if buy_sell_ratio > 1.2:
        return QueueSignal(
            "mild_buy_pressure",
            "فشار خرید ملایم",
            5,
            f"نسبت خریدار/فروشنده: {buy_sell_ratio:.1f}x",
        )

    return QueueSignal(
        "mild_sell_pressure",
        "فشار فروش ملایم",
        -5,
        f"نسبت خریدار/فروشنده: {buy_sell_ratio:.1f}x",
    )