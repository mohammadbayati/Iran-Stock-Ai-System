from dataclasses import dataclass, field


@dataclass
class ConfidenceResult:
    score: int
    factors: list = field(default_factory=list)
    grade: str = ""


def calculate_confidence(smart_money_bonus, queue_bonus, rsi, trend_score,
                         volume_ratio, sector_bonus, risk_reward, missing=False):
    if missing:
        return ConfidenceResult(score=0, factors=["داده تکنیکال موجود نیست"], grade="F")

    score = 50
    factors = []

    score += smart_money_bonus
    if smart_money_bonus > 0:
        factors.append(f"پول هوشمند: +{smart_money_bonus}")
    elif smart_money_bonus < 0:
        factors.append(f"پول هوشمند: {smart_money_bonus}")

    score += queue_bonus
    if queue_bonus > 0:
        factors.append(f"تحلیل صف: +{queue_bonus}")
    elif queue_bonus < 0:
        factors.append(f"تحلیل صف: {queue_bonus}")

    if rsi is not None:
        if 45 <= rsi < 60:
            pts = 15
            factors.append(f"RSI={rsi:.0f}: +{pts} (ایده‌آل)")
        elif 60 <= rsi < 70:
            pts = 8
            factors.append(f"RSI={rsi:.0f}: +{pts} (مناسب)")
        elif 40 <= rsi < 45:
            pts = 5
            factors.append(f"RSI={rsi:.0f}: +{pts} (کمی پایین)")
        elif rsi >= 70:
            pts = -10
            factors.append(f"RSI={rsi:.0f}: {pts} (اشباع خرید)")
        elif rsi < 30:
            pts = -5
            factors.append(f"RSI={rsi:.0f}: {pts} (اشباع فروش)")
        else:
            pts = 0
        score += pts

    if trend_score is not None:
        pts = min(trend_score * 3, 20)
        score += pts
        factors.append(f"روند {trend_score}/6: +{pts}")

    if volume_ratio is not None:
        if volume_ratio >= 2.0:
            pts = 10
        elif volume_ratio >= 1.5:
            pts = 7
        elif volume_ratio >= 1.2:
            pts = 4
        elif volume_ratio < 0.8:
            pts = -5
        else:
            pts = 0
        score += pts
        if pts != 0:
            factors.append(f"حجم {volume_ratio:.1f}x: {'+' if pts>0 else ''}{pts}")

    score += sector_bonus
    if sector_bonus > 0:
        factors.append(f"سکتور پیشرو: +{sector_bonus}")
    elif sector_bonus < 0:
        factors.append(f"سکتور عقب‌مانده: {sector_bonus}")

    if risk_reward and risk_reward > 0:
        if risk_reward >= 3.0:
            pts = 10
        elif risk_reward >= 2.0:
            pts = 7
        elif risk_reward >= 1.5:
            pts = 4
        else:
            pts = 0
        score += pts
        if pts > 0:
            factors.append(f"R:R={risk_reward:.1f}: +{pts}")

    score = max(0, min(100, score))
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"

    return ConfidenceResult(score=score, factors=factors, grade=grade)