"""
Layer 5 — Unified Confidence Score (0-100)

Score breakdown (max 100):
  Smart money signal      → up to +20 / down to -15
  Queue intelligence      → up to +15 / down to -15
  RSI zone                → up to +15
  Trend score             → up to +20
  Volume ratio            → up to +10
  Sector alignment        → up to +10
  Risk/Reward ratio       → up to +10
  RSI Divergence          → up to +8 / down to -8
"""

from dataclasses import dataclass, field


@dataclass
class ConfidenceResult:
    score: int
    factors: list[str] = field(default_factory=list)
    grade: str = ""


def calculate_confidence(
    smart_money_bonus: int,
    queue_bonus: int,
    rsi: float | None,
    trend_score: int | None,
    volume_ratio: float | None,
    sector_bonus: int,
    risk_reward: float | None,
    missing: bool = False,
    rsi_divergence: str = "none",
) -> ConfidenceResult:

    if missing:
        return ConfidenceResult(score=0, factors=["داده تکنیکال موجود نیست"], grade="F")

    score = 50
    factors = []

    score += smart_money_bonus
    if smart_money_bonus >= 15:
        factors.append(f"پول هوشمند: +{smart_money_bonus} (تجمیع پنهان)")
    elif smart_money_bonus > 0:
        factors.append(f"پول هوشمند: +{smart_money_bonus}")
    elif smart_money_bonus < 0:
        factors.append(f"پول هوشمند: {smart_money_bonus} (توزیع پنهان)")

    score += queue_bonus
    if queue_bonus > 0:
        factors.append(f"تحلیل صف: +{queue_bonus}")
    elif queue_bonus < 0:
        factors.append(f"تحلیل صف: {queue_bonus}")

    if rsi is not None:
        if 45 <= rsi < 60:
            rsi_pts = 15
            factors.append(f"RSI={rsi:.0f}: +{rsi_pts} (ایده‌آل)")
        elif 60 <= rsi < 70:
            rsi_pts = 8
            factors.append(f"RSI={rsi:.0f}: +{rsi_pts} (مناسب)")
        elif 40 <= rsi < 45:
            rsi_pts = 5
            factors.append(f"RSI={rsi:.0f}: +{rsi_pts} (کمی پایین)")
        elif rsi >= 70:
            rsi_pts = -10
            factors.append(f"RSI={rsi:.0f}: {rsi_pts} (اشباع خرید)")
        elif rsi < 30:
            rsi_pts = -5
            factors.append(f"RSI={rsi:.0f}: {rsi_pts} (اشباع فروش)")
        else:
            rsi_pts = 0
        score += rsi_pts

    if trend_score is not None:
        trend_pts = min(trend_score * 3, 20)
        score += trend_pts
        factors.append(f"روند {trend_score}/6: +{trend_pts}")

    if volume_ratio is not None:
        if volume_ratio >= 2.0:
            vol_pts = 10
        elif volume_ratio >= 1.5:
            vol_pts = 7
        elif volume_ratio >= 1.2:
            vol_pts = 4
        elif volume_ratio < 0.8:
            vol_pts = -5
        else:
            vol_pts = 0
        score += vol_pts
        if vol_pts != 0:
            factors.append(f"حجم نسبی {volume_ratio:.1f}x: {'+' if vol_pts > 0 else ''}{vol_pts}")

    score += sector_bonus
    if sector_bonus > 0:
        factors.append(f"سکتور پیشرو: +{sector_bonus}")
    elif sector_bonus < 0:
        factors.append(f"سکتور عقب‌مانده: {sector_bonus}")

    if risk_reward is not None and risk_reward > 0:
        if risk_reward >= 3.0:
            rr_pts = 10
        elif risk_reward >= 2.0:
            rr_pts = 7
        elif risk_reward >= 1.5:
            rr_pts = 4
        else:
            rr_pts = 0
        score += rr_pts
        if rr_pts > 0:
            factors.append(f"ریسک/ریوارد {risk_reward:.1f}: +{rr_pts}")

    if rsi_divergence == "bullish":
        score += 8
        factors.append("واگرایی مثبت RSI: +8")
    elif rsi_divergence == "bearish":
        score -= 8
        factors.append("واگرایی منفی RSI: -8")

    score = max(0, min(100, score))

    if score >= 80:
        grade = "A"
    elif score >= 65:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "D"

    return ConfidenceResult(score=score, factors=factors, grade=grade)