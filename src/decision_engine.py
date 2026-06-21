LABEL_ENTRY_CANDIDATE = "Entry Candidate"
LABEL_TECH_WATCH = "Technical Entry Watch"
LABEL_PULLBACK = "Wait for Pullback"
LABEL_OVERBOUGHT = "Avoid Entry Now - Overbought"
LABEL_VOLUME = "Watch - Needs Volume Confirmation"
LABEL_WATCH = "Watch Only"
LABEL_MISSING = "Missing Technical Data"


def rsi_status(rsi) -> str:
    if rsi is None:
        return "نامشخص"
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


def classify(row: dict) -> tuple:
    reasons = []
    missing = row.get("missing", False)
    if isinstance(missing, str):
        missing = missing.lower() == "true"

    rsi = row.get("rsi")
    trend = row.get("trend_score")
    vol_ratio = row.get("volume_ratio_20")
    score = row.get("initial_score", 0) or 0

    if missing or rsi is None or trend is None:
        return LABEL_MISSING, ["داده تاریخچه یا اندیکاتور در دسترس نیست"]

    try:
        rsi = float(rsi)
        trend = int(trend)
    except (ValueError, TypeError):
        return LABEL_MISSING, ["خطا در خواندن داده‌های تکنیکال"]

    if rsi >= 80:
        reasons.append(f"RSI={rsi:.0f} ≥ 80 → اشباع خرید شدید")
        return LABEL_OVERBOUGHT, reasons

    if rsi >= 70:
        try:
            dist_high = float(row.get("distance_to_20d_high_percent") or 999)
            ret5 = float(row.get("return_5d_percent") or 0)
        except (ValueError, TypeError):
            dist_high, ret5 = 999, 0
        if dist_high < 2.0 and ret5 > 5.0:
            reasons.append(f"RSI={rsi:.0f} + نزدیک سقف + بازده ۵ روزه {ret5:.1f}%")
            return LABEL_OVERBOUGHT, reasons
        reasons.append(f"RSI={rsi:.0f} در محدوده ۷۰-۸۰ → صبر برای پولبک")
        return LABEL_PULLBACK, reasons

    rsi_ok = 45 <= rsi < 70
    trend_ok = trend >= 4

    try:
        vol_ok = vol_ratio is not None and float(vol_ratio) >= 1.2
    except (ValueError, TypeError):
        vol_ok = False

    if not rsi_ok:
        reasons.append(f"RSI={rsi:.0f} خارج از محدوده ایده‌آل")
        return LABEL_WATCH, reasons

    if not trend_ok:
        if not vol_ok:
            reasons.append(f"trend={trend} ضعیف + حجم ناکافی")
            return LABEL_VOLUME, reasons
        reasons.append(f"trend={trend} ضعیف")
        return LABEL_WATCH, reasons

    if not vol_ok:
        reasons.append(f"حجم نسبی={vol_ratio} → نیاز به تایید حجم")
        return LABEL_VOLUME, reasons

    if score >= 70:
        reasons.append(f"امتیاز={score}, trend={trend}, RSI={rsi:.0f}, حجم={vol_ratio:.1f}x")
        return LABEL_ENTRY_CANDIDATE, reasons

    reasons.append(f"امتیاز={score} — اندیکاتورها مثبت ولی نیاز به بررسی دستی")
    return LABEL_TECH_WATCH, reasons