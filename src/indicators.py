"""
Calculate technical indicators from historical OHLCV data.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

from config.settings import HISTORY_DIR, STALE_HISTORY_DAYS

MINIMUM_BARS = 15

_AR2FA = str.maketrans({"ك": "ک", "ي": "ی", "ة": "ه", "ى": "ی"})


def load_history(symbol: str) -> pd.DataFrame | None:
    normalized = symbol.translate(_AR2FA).strip()
    for name in [normalized, symbol]:
        path = os.path.join(HISTORY_DIR, f"{name}.csv")
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                df.columns = [c.lower().strip() for c in df.columns]
                if "close" not in df.columns:
                    return None
                df = df.dropna(subset=["close"]).reset_index(drop=True)
                return df
            except Exception:
                return None
    return None


def _rsi(series: pd.Series, period: int = 14) -> float | None:
    if len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def _atr(df: pd.DataFrame, period: int = 14) -> float | None:
    if "high" not in df.columns or "low" not in df.columns:
        return None
    if len(df) < period + 1:
        return None
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    return round(float(atr), 2) if not np.isnan(atr) else None


def _rsi_divergence(close: pd.Series, rsi_series: pd.Series, lookback: int = 10) -> str:
    if len(close) < lookback or len(rsi_series.dropna()) < lookback:
        return "none"
    price_recent = close.iloc[-lookback:]
    rsi_recent = rsi_series.iloc[-lookback:]
    half = lookback // 2
    price_low1 = price_recent.iloc[:half].min()
    price_low2 = price_recent.iloc[half:].min()
    rsi_low1 = rsi_recent.iloc[:half].min()
    rsi_low2 = rsi_recent.iloc[half:].min()
    price_high1 = price_recent.iloc[:half].max()
    price_high2 = price_recent.iloc[half:].max()
    rsi_high1 = rsi_recent.iloc[:half].max()
    rsi_high2 = rsi_recent.iloc[half:].max()
    if (price_low2 < price_low1 * 0.995) and (rsi_low2 > rsi_low1 + 2):
        return "bullish"
    if (price_high2 > price_high1 * 1.005) and (rsi_high2 < rsi_high1 - 2):
        return "bearish"
    return "none"


def _trend_score(df: pd.DataFrame) -> int:
    close = df["close"]
    n = min(20, len(close))
    score = 0
    ma20 = close.rolling(n).mean().iloc[-1]
    latest = close.iloc[-1]
    if latest > ma20:
        score += 1
    if len(close) >= 50:
        ma50 = close.rolling(50).mean().iloc[-1]
        if latest > ma50:
            score += 1
    ma20_series = close.rolling(n).mean()
    lb = min(5, len(ma20_series.dropna()))
    if lb >= 2:
        slope = ma20_series.iloc[-1] - ma20_series.iloc[-lb]
        if slope > 0:
            score += 1
    if len(close) >= 10:
        recent = close.iloc[-5:]
        prior = close.iloc[-10:-5]
        if recent.max() > prior.max():
            score += 1
        if recent.min() > prior.min():
            score += 1
    high_n = close.iloc[-n:].max()
    low_n = close.iloc[-n:].min()
    mid = (high_n + low_n) / 2
    if latest > mid:
        score += 1
    return score


def calculate_indicators(symbol: str) -> dict:
    base = {
        "symbol": symbol,
        "missing": True,
        "latest_date": None,
        "latest_close": None,
        "rsi": None,
        "rsi_divergence": "none",
        "trend_score": None,
        "volume_ratio_20": None,
        "return_5d_percent": None,
        "distance_to_20d_high_percent": None,
        "distance_to_20d_low_percent": None,
        "support": None,
        "resistance": None,
        "atr": None,
        "stop_loss": None,
        "target_1": None,
        "risk_reward": None,
        "stale": False,
    }

    df = load_history(symbol)
    if df is None or len(df) < MINIMUM_BARS:
        return base

    close = df["close"]
    volume = df.get("volume", pd.Series(dtype=float))

    latest_close = float(close.iloc[-1])
    latest_date_raw = df.get("date", pd.Series(dtype=str)).iloc[-1] if "date" in df.columns else None

    stale = False
    if latest_date_raw:
        try:
            ld = pd.to_datetime(str(latest_date_raw))
            if (datetime.now() - ld).days > STALE_HISTORY_DAYS:
                stale = True
        except Exception:
            pass

    n = min(20, len(close))
    high20 = float(close.iloc[-n:].max())
    low20 = float(close.iloc[-n:].min())
    close_5d_ago = float(close.iloc[-6]) if len(close) >= 6 else None

    vol_ratio = None
    if len(volume.dropna()) >= n:
        avg_vol = float(volume.iloc[-n:].mean())
        last_vol = float(volume.iloc[-1])
        vol_ratio = round(last_vol / avg_vol, 2) if avg_vol > 0 else None

    return_5d = round((latest_close / close_5d_ago - 1) * 100, 2) if close_5d_ago else None
    dist_high = round((high20 - latest_close) / high20 * 100, 2) if high20 else None
    dist_low = round((latest_close - low20) / low20 * 100, 2) if low20 else None

    support = round(low20, 2)
    resistance = round(high20, 2)

    atr_val = _atr(df)
    if atr_val and atr_val > 0:
        stop_loss = round(latest_close - 1.5 * atr_val, 2)
    else:
        stop_loss = round(support * 0.97, 2)

    range_20 = high20 - low20
    if resistance > latest_close * 1.01:
        target_1 = resistance
    else:
        target_1 = round(latest_close + range_20 * 0.618, 2)

    risk = latest_close - stop_loss
    reward = target_1 - latest_close
    risk_reward = round(reward / risk, 2) if risk > 0 and reward > 0 else None

    rsi_val = _rsi(close)
    divergence = "none"
    if rsi_val is not None and len(close) >= 20:
        period = min(14, len(close) - 1)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi_full = 100 - (100 / (1 + rs))
        divergence = _rsi_divergence(close, rsi_full)

    return {
        "symbol": symbol,
        "missing": False,
        "latest_date": str(latest_date_raw) if latest_date_raw else None,
        "latest_close": round(latest_close, 2),
        "rsi": rsi_val,
        "rsi_divergence": divergence,
        "trend_score": _trend_score(df),
        "volume_ratio_20": vol_ratio,
        "return_5d_percent": return_5d,
        "distance_to_20d_high_percent": dist_high,
        "distance_to_20d_low_percent": dist_low,
        "support": support,
        "resistance": resistance,
        "atr": atr_val,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "risk_reward": risk_reward,
        "stale": stale,
    }