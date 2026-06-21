import pandas as pd


def detect_patterns(df: pd.DataFrame) -> dict:
    if df is None or len(df) < 3:
        return {"patterns": [], "signal": "neutral", "bonus": 0}

    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return {"patterns": [], "signal": "neutral", "bonus": 0}

    o = df["open"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)

    patterns = []
    total_bonus = 0

    # --- کندل آخر ---
    o1, h1, l1, c1 = o.iloc[-1], h.iloc[-1], l.iloc[-1], c.iloc[-1]
    body1 = abs(c1 - o1)
    range1 = h1 - l1
    upper_shadow1 = h1 - max(c1, o1)
    lower_shadow1 = min(c1, o1) - l1

    # --- کندل قبلی ---
    o2, h2, l2, c2 = o.iloc[-2], h.iloc[-2], l.iloc[-2], c.iloc[-2]
    body2 = abs(c2 - o2)

    # --- کندل دو روز قبل ---
    o3, c3 = o.iloc[-3], c.iloc[-3]

    # دوجی — بدنه خیلی کوچک
    if range1 > 0 and body1 / range1 < 0.1:
        patterns.append("دوجی")
        total_bonus += 5

    # چکش — سایه پایین بلند، بدنه کوچک بالا
    if (range1 > 0 and lower_shadow1 >= 2 * body1 and
            upper_shadow1 <= body1 * 0.3 and body1 > 0):
        patterns.append("چکش 🔨")
        total_bonus += 15

    # مرد آویزان — چکش ولی در روند صعودی
    if (range1 > 0 and lower_shadow1 >= 2 * body1 and
            upper_shadow1 <= body1 * 0.3 and body1 > 0 and c2 > o2):
        patterns.append("مرد آویزان ⚠️")
        total_bonus -= 10

    # ستاره تیرانداز — سایه بالا بلند، بدنه پایین
    if (range1 > 0 and upper_shadow1 >= 2 * body1 and
            lower_shadow1 <= body1 * 0.3 and body1 > 0):
        patterns.append("ستاره تیرانداز 🔻")
        total_bonus -= 15

    # انگلفینگ صعودی
    if (c1 > o1 and c2 < o2 and
            c1 > o2 and o1 < c2):
        patterns.append("انگلفینگ صعودی 🟢")
        total_bonus += 20

    # انگلفینگ نزولی
    if (c1 < o1 and c2 > o2 and
            c1 < o2 and o1 > c2):
        patterns.append("انگلفینگ نزولی 🔴")
        total_bonus -= 20

    # ستاره صبح — سه کندل: نزولی، دوجی/کوچک، صعودی
    if (c3 < o3 and body2 < body1 * 0.3 and c1 > o1 and
            c1 > (o3 + c3) / 2):
        patterns.append("ستاره صبح ⭐")
        total_bonus += 25

    # ستاره عصر
    if (c3 > o3 and body2 < body1 * 0.3 and c1 < o1 and
            c1 < (o3 + c3) / 2):
        patterns.append("ستاره عصر 🌆")
        total_bonus -= 25

    # سه سرباز سفید — سه کندل صعودی متوالی
    if (c1 > o1 and c2 > o2 and c3 > o3 and
            c1 > c2 > c3):
        patterns.append("سه سرباز سفید 💪")
        total_bonus += 15

    # سه کلاغ سیاه
    if (c1 < o1 and c2 < o2 and c3 < o3 and
            c1 < c2 < c3):
        patterns.append("سه کلاغ سیاه 🐦‍⬛")
        total_bonus -= 15

    # پین بار صعودی
    if (lower_shadow1 >= 3 * body1 and body1 > 0 and
            upper_shadow1 <= body1):
        patterns.append("پین بار صعودی 📍")
        total_bonus += 18

    total_bonus = max(-30, min(30, total_bonus))

    if total_bonus >= 10:
        signal = "bullish"
    elif total_bonus <= -10:
        signal = "bearish"
    else:
        signal = "neutral"

    return {
        "patterns": patterns,
        "signal": signal,
        "bonus": total_bonus,
        "patterns_fa": " | ".join(patterns) if patterns else "بدون الگو",
    }