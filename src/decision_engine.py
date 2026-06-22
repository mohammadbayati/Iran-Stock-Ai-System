"""
Deterministic decision engine.

Rules are explicit and documented. No heuristic guessing.
If technical data is missing → Missing Technical Data, always.
"""

import math

from config.settings import (
    ENTRY_CANDIDATE_SCORE,
    ENTRY_CANDIDATE_TREND,
    ENTRY_CANDIDATE_RSI_LOW,
    ENTRY_CANDIDATE_RSI_HIGH,
    ENTRY_CANDIDATE_VOL_RATIO,
    OVERBOUGHT_RSI,
    PULLBACK_RSI_LOW,
    PULLBACK_RSI_HIGH,
)

LABEL_ENTRY_CANDIDATE = "Entry Candidate"
LABEL_TECH_WATCH = "Technical Entry Watch"
LABEL_PULLBACK = "Wait for Pullback"
LABEL_OVERBOUGHT = "Avoid Entry Now - Overbought"
LABEL_VOLUME = "Watch - Needs Volume Confirmation"
LABEL_WATCH = "Watch Only"
LABEL_MISSING = "Missing Technical Data"


def _is_missing(val) -> bool:
    if val is None:
        return True
    try:
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return False


def classify(row: dict) -> tuple[str, list[str]]:
    reasons = []

    trend_raw = row.get("trend_score")

    # اگه کاملاً فاقد داده باشیم
    if row.get("missing") or _is_missing(trend_raw):
        return LABEL_MISSING, ["داده تاریخچه یا اندیکاتور در دسترس نیست"]

    trend = float(trend_raw)
    rsi_raw = row.get("rsi")
    rsi_available = not _is_missing(rsi_raw)
    rsi = float(rsi_raw) if rsi_available else None

    vol_ratio = row.get("volume_ratio_20")
    score = row.get("initial_score", 0) or 0
    return_5d = row.get("return_5d_percent")
    dist_high = row.get("distance_to_20d_high_percent")
    stale = row.get("stale", False)

    if stale:
        reasons.append("⚠️ داده تاریخچه قدیمی است")

    # --- بررسی RSI فقط اگه موجود باشه ---
    if rsi_available:
        if rsi >= OVERBOUGHT_RSI:
            reasons.append(f"RSI={rsi} ≥ {OVERBOUGHT_RSI} → اشباع خرید")
            return LABEL_OVERBOUGHT, reasons

        near_20d_high = dist_high is not None and not _is_missing(dist_high) and float(dist_high) < 2.0
        strong_5d = return_5d is not None and not _is_missing(return_5d) and float(return_5d) > 5.0
        if rsi >= PULLBACK_RSI_LOW and near_20d_high and strong_5d:
            reasons.append(f"RSI={rsi} ≥ {PULLBACK_RSI_LOW}، قیمت نزدیک سقف ۲۰ روزه، بازده ۵ روزه {return_5d}%")
            return LABEL_OVERBOUGHT, reasons

        if PULLBACK_RSI_LOW <= rsi < PULLBACK_RSI_HIGH:
            reasons.append(f"RSI={rsi} در محدوده {PULLBACK_RSI_LOW}-{PULLBACK_RSI_HIGH} → صبر برای پولبک")
            return LABEL_PULLBACK, reasons

        rsi_healthy = ENTRY_CANDIDATE_RSI_LOW <= rsi < ENTRY_CANDIDATE_RSI_HIGH
        if not rsi_healthy:
            reasons.append(f"RSI={rsi} خارج از محدوده ایده‌آل ({ENTRY_CANDIDATE_RSI_LOW}-{ENTRY_CANDIDATE_RSI_HIGH})")
            return LABEL_WATCH, reasons
    else:
        reasons.append("RSI نامشخص — بر اساس روند و حجم طبقه‌بندی شد")

    # --- روند ---
    trend_ok = trend >= ENTRY_CANDIDATE_TREND
    vol_ok = vol_ratio is not None and not _is_missing(vol_ratio) and float(vol_ratio) >= ENTRY_CANDIDATE_VOL_RATIO

    if not trend_ok:
        reasons.append(f"trend_score={trend} < {ENTRY_CANDIDATE_TREND} → روند ضعیف")
        if vol_ok:
            return LABEL_WATCH, reasons
        reasons.append(f"حجم نسبی={vol_ratio} → نیاز به تایید حجم")
        return LABEL_VOLUME, reasons

    if not vol_ok:
        v_str = f"{float(vol_ratio):.1f}" if vol_ratio is not None else "N/A"
        reasons.append(f"volume_ratio={v_str} < {ENTRY_CANDIDATE_VOL_RATIO} → نیاز به تایید حجم")
        return LABEL_VOLUME, reasons

    if score >= ENTRY_CANDIDATE_SCORE:
        reasons.append(f"score={score}, trend={trend}" + (f", RSI={rsi}" if rsi_available else ", RSI=N/A"))
        return LABEL_ENTRY_CANDIDATE, reasons

    reasons.append(f"score={score} < {ENTRY_CANDIDATE_SCORE} ولی اندیکاتورهای تکنیکال مثبت → بررسی دستی")
    return LABEL_TECH_WATCH, reasons


def rsi_status(rsi) -> str:
    if _is_missing(rsi):
        return "نامشخص"
    rsi = float(rsi)
    if rsi >= 80:
        return "اشباع خرید شدید"
    if rsi >= 70:
        return "اشباع خرید"
    if rsi >= 60:
        return "بالاتر از میانه"
    if rsi >= 50:
        return "میانه"
    if rsi >= 45:
        return "محدوده ایده‌آل"
    if rsi >= 30:
        return "ضعیف"
    return "اشباع فروش"