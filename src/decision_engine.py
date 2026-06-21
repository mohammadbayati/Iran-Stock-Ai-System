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


def _bb_signal(row: dict) -> tuple:
    """
    Returns (bonus_score, label_hint)
    bb_position: 0=at lower band, 100=at upper band
    bb_width: باریکی باند — عدد کم = squeeze = انتظار breakout
    """
    try:
        bb_pos = float(row.get("bb_position") or -1)
        bb_width = float(row.get("bb_width") or -1)
    except (ValueError, TypeError):
        return 0, None

    if bb_pos < 0:
        return 0, None

    bonus = 0
    hint = None

    # قیمت نزدیک باند پایین → فرصت خرید
    if bb_pos <= 20:
        bonus += 15
        hint = "bb_oversold"
    # قیمت نزدیک باند بالا → احتیاط
    elif bb_pos >= 80:
        bonus -= 10
        hint = "bb_overbought"
    # قیمت در ناحیه میانی پایین → خوب
    elif 20 < bb_pos <= 45:
        bonus += 8
        hint = "bb_good_zone"

    # Squeeze → احتمال breakout قوی
    if 0 < bb_width < 5:
        bonus += 10
        hint = "bb_squeeze"

    return bonus, hint


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

    bb_bonus, bb_hint = _bb_signal(row)
    score = score + bb_bonus

    # اشباع خرید شدید
    if rsi >= 80:
        reasons.append(f"RSI={rsi:.0f} ≥ 80 → اشباع خرید شدید")
        return LABEL_OVERBOUGHT, reasons

    # RSI بالا — بررسی BB
    if rsi >= 70:
        if bb_hint == "bb_oversold":
            # RSI بالا ولی BB پایین → احتمال pullback کوتاه
            reasons.append(f"RSI={rsi:.0f} بالا ولی BB در کف → صبر برای پولبک")
            return LABEL_PULLBACK, reasons
        try:
            dist_high = float(row.get("distance_to_20d_high_percent") or 999)
            ret5 = float(row.get("return_5d_percent") or 0)
        except (ValueError, TypeError):
            dist_high, ret5 = 999, 0
        if dist_high < 2.0 and ret5 > 5.0:
            reasons.append(f"RSI={rsi:.0f} + نزدیک سقف + بازده {ret5:.1f}%")
            return LABEL_OVERBOUGHT, reasons
        reasons.append(f"RSI={rsi:.0f} در محدوده ۷۰-۸۰ → صبر برای پولبک")
        return LABEL_PULLBACK, reasons

    rsi_ok = 45 <= rsi < 70
    trend_ok = trend >= 4

    try:
        vol_ok = vol_ratio is not None and float(vol_ratio) >= 1.2
    except (ValueError, TypeError):
        vol_ok = False

    # BB squeeze → حتی بدون حجم کافی در نظر بگیر
    if bb_hint == "bb_squeeze" and rsi_ok and trend_ok:
        reasons.append(f"BB Squeeze + RSI={rsi:.0f} + trend={trend} → انتظار breakout")
        return LABEL_ENTRY_CANDIDATE, reasons

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
        # BB در ناحیه خوب → کمتر سخت‌گیری کن
        if bb_hint in ("bb_oversold", "bb_good_zone"):
            reasons.append(f"BB در ناحیه خوب، حجم={vol_ratio} کم ولی قابل قبول")
            return LABEL_TECH_WATCH, reasons
        reasons.append(f"حجم نسبی={vol_ratio} → نیاز به تایید حجم")
        return LABEL_VOLUME, reasons

    if score >= 70:
        if bb_hint:
            reasons.append(f"امتیاز={score}, trend={trend}, RSI={rsi:.0f}, BB={bb_hint}")
        else:
            reasons.append(f"امتیاز={score}, trend={trend}, RSI={rsi:.0f}, حجم={vol_ratio:.1f}x")
        return LABEL_ENTRY_CANDIDATE, reasons

    reasons.append(f"امتیاز={score} — اندیکاتورها مثبت ولی نیاز به بررسی دستی")
    return LABEL_TECH_WATCH, reasons