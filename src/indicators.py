"""
Calculate technical indicators from historical OHLCV data.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config.settings import HISTORY_DIR, STALE_HISTORY_DAYS

MINIMUM_BARS = 22


def load_history(symbol: str) -> pd.DataFrame | None:
    path = os.path.join(HISTORY_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        if "close" not in df.columns:
            return None
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        return df
    except Exception:
        return None


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def _trend_score(df: pd.DataFrame) -> int:
    close = df["close"]
    score = 0
    ma20 = close.rolling(20).mean().iloc[-1]
    latest = close.iloc[-1]

    if latest > ma20:
        score += 1
    if len(close) >= 50:
        ma50 = close.rolling(50).mean().iloc[-1]
        if latest > ma50:
            score += 1

    ma20_series = close.rolling(20).mean()
    if len(ma20_series.dropna()) >= 5:
        if ma20_series.iloc[-1] - ma20_series.iloc[-5] > 0:
            score += 1

    if len(close) >= 10:
        recent = close.iloc[-5:]
        prior = close.iloc[-10:-5]
        if recent.max() > prior.max():
            score += 1
        if recent.min() > prior.min():
            score += 1

    high20 = close.iloc[-20:].max()
    low20 = close.iloc[-20:].min()
    if latest > (high20 + low20) / 2:
        score += 1

    return score


def calculate_indicators(symbol: str) -> dict:
    base = {
        "symbol": symbol, "missing": True, "latest_date": None,
        "latest_close": None, "rsi": None, "trend_score": None,
        "volume_ratio_20": None, "return_5d_percent": None,
        "distance_to_20d_high_percent": None, "distance_to_20d_low_percent": None,
        "support": None, "resistance": None, "stop_loss": None,
        "target_1": None, "risk_reward": None, "stale": False,
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

    high20 = float(close.iloc[-20:].max())
    low20 = float(close.iloc[-20:].min())
    close_5d_ago = float(close.iloc[-6]) if len(close) >= 6 else None

    vol_ratio = None
    if len(volume.dropna()) >= 20:
        avg_vol = float(volume.iloc[-20:].mean())
        last_vol = float(volume.iloc[-1])
        vol_ratio = round(last_vol / avg_vol, 2) if avg_vol > 0 else None

    return_5d = round((latest_close / close_5d_ago - 1) * 100, 2) if close_5d_ago else None
    dist_high = round((high20 - latest_close) / high20 * 100, 2) if high20 else None
    dist_low = round((latest_close - low20) / low20 * 100, 2) if low20 else None

    support = round(low20, 2)
    resistance = round(high20, 2)
    stop_loss = round(support * 0.97, 2)
    target_1 = resistance
    risk = latest_close - stop_loss
    reward = target_1 - latest_close
    risk_reward = round(reward / risk, 2) if risk > 0 else None

    return {
        "symbol": symbol, "missing": False,
        "latest_date": str(latest_date_raw) if latest_date_raw else None,
        "latest_close": round(latest_close, 2),
        "rsi": _rsi(close), "trend_score": _trend_score(df),
        "volume_ratio_20": vol_ratio, "return_5d_percent": return_5d,
        "distance_to_20d_high_percent": dist_high,
        "distance_to_20d_low_percent": dist_low,
        "support": support, "resistance": resistance,
        "stop_loss": stop_loss, "target_1": target_1,
        "risk_reward": risk_reward, "stale": stale,
    }