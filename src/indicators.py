"""
Calculate technical indicators from historical OHLCV data.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

from config.settings import HISTORY_DIR, STALE_HISTORY_DAYS

MINIMUM_BARS = 15


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
    if np.isnan(val):
        return None
    return round(float(val), 2)


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
    price_low1  = price_recent.iloc[:half].min()
    price_low2  = price_recent.iloc[half:].min()
    rsi_low1    = rsi_recent.iloc[:half].min()
    rsi_low2    = rsi_recent.iloc[half:].min()

    price_high1 = price_recent.iloc[:half].max()
    price_high2 = price_recent.iloc[half:].max()
    rsi_high1   = rsi_recent.iloc[:half].max()
    rsi_high2   = rsi_recent.iloc[half:].max()

    bullish = (price_low2 < price_low1 * 0.995) and (rsi_low2 > rsi_low1 + 2)
    bearish = (price_high2 > price_high1 * 1.005) and (rsi_high2 < rsi_high1 - 2)

    if bullish:
        return "bullish"
    if bearish:
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
    lookback = min(5, len(ma20_series.dropna()))
    if lookback >= 2:
        if ma20_series.iloc[-1] > ma20_series.iloc[-lookback]:
            score += 1

    if len(close) >= 10:
        recent = close.iloc[-5:]
        prior  = close.iloc[-10:-5]
        if recent.max() > prior.max():
            score += 1
        if recent.min() > prior.min():
            score += 1

    high_n = close.iloc[-n:].max()
    low_n  = close.iloc[-n:].min()
    if latest > (high_n + low_n) / 2:
        score += 1

    return score


def _volume_profile(df: pd.DataFrame, bins: int = 20, value_area_pct: float = 0.70):
    """Returns (poc, vah, val, poc_position). Uses last 60 bars only."""
    try:
        if "high" not in df.columns or "low" not in df.columns or len(df) < 5:
            return None, None, None, "unknown"

        price_min = float(df["low"].min())
        price_max = float(df["high"].max())
        if price_min >= price_max:
            return None, None, None, "unknown"

        bin_edges = np.linspace(price_min, price_max, bins + 1)
        vol_per_bin = np.zeros(bins)

        for _, row in df.iterrows():
            lo  = float(row.get("low",  row["close"]))
            hi  = float(row.get("high", row["close"]))
            vol = float(row.get("volume", 0) or 0)
            if hi <= lo or vol <= 0:
                continue
            for i in range(bins):
                overlap_lo = max(lo, bin_edges[i])
                overlap_hi = min(hi, bin_edges[i + 1])
                if overlap_hi > overlap_lo:
                    vol_per_bin[i] += vol * (overlap_hi - overlap_lo) / (hi - lo)

        total_vol = vol_per_bin.sum()
        if total_vol <= 0:
            return None, None, None, "unknown"

        poc_bin = int(np.argmax(vol_per_bin))
        poc = round(float((bin_edges[poc_bin] + bin_edges[poc_bin + 1]) / 2), 2)

        target_vol = total_vol * value_area_pct
        sorted_indices = list(np.argsort(vol_per_bin)[::-1])
        included = []
        captured = 0.0
        for idx in sorted_indices:
            included.append(idx)
            captured += vol_per_bin[idx]
            if captured >= target_vol:
                break

        lo_bin = min(included)
        hi_bin = max(included)
        val = round(float(bin_edges[lo_bin]), 2)
        vah = round(float(bin_edges[min(hi_bin + 1, bins)]), 2)

        latest_close = float(df["close"].iloc[-1])
        if latest_close > poc * 1.005:
            poc_position = "above"
        elif latest_close < poc * 0.995:
            poc_position = "below"
        else:
            poc_position = "at"

        return poc, vah, val, poc_position

    except Exception:
        return None, None, None, "unknown"


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
        "poc": None,
        "vah": None,
        "val": None,
        "poc_position": "unknown",
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
    low20  = float(close.iloc[-n:].min())
    close_5d_ago = float(close.iloc[-6]) if len(close) >= 6 else None

    vol_ratio = None
    if len(volume.dropna()) >= n:
        avg_vol  = float(volume.iloc[-n:].mean())
        last_vol = float(volume.iloc[-1])
        vol_ratio = round(last_vol / avg_vol, 2) if avg_vol > 0 else None

    return_5d = round((latest_close / close_5d_ago - 1) * 100, 2) if close_5d_ago else None
    dist_high = round((high20 - latest_close) / high20 * 100, 2) if high20 else None
    dist_low  = round((latest_close - low20) / low20 * 100, 2) if low20 else None

    support    = round(low20, 2)
    resistance = round(high20, 2)

    atr_val = _atr(df)
    if atr_val and atr_val > 0:
        atr_stop = round(latest_close - 1.5 * atr_val, 2)
    else:
        atr_stop = round(support * 0.97, 2)

    # Volume profile — فقط ۶۰ روز اخیر
    df_vp = df.tail(60) if len(df) > 60 else df
    poc, vah, val, poc_position = _volume_profile(df_vp)

    if val is not None and val > atr_stop and val < latest_close:
        stop_loss = val
    else:
        stop_loss = atr_stop

    range_20 = high20 - low20
    if vah is not None and vah > latest_close * 1.01:
        target_1 = vah
    elif resistance > latest_close * 1.01:
        target_1 = resistance
    else:
        target_1 = round(latest_close + range_20 * 0.618, 2)

    risk   = latest_close - stop_loss
    reward = target_1 - latest_close
    if risk > 0 and reward > 0:
        risk_reward = round(min(reward / risk, 10.0), 2)
    else:
        risk_reward = None

    rsi_val = _rsi(close)
    divergence = "none"
    if rsi_val is not None and len(close) >= 20:
        period = min(14, len(close) - 1)
        delta    = close.diff()
        gain     = delta.clip(lower=0)
        loss     = (-delta).clip(lower=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi_series = 100 - (100 / (1 + rs))
        divergence = _rsi_divergence(close, rsi_series)

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
        "stop_loss": round(stop_loss, 2),
        "target_1": round(target_1, 2),
        "risk_reward": risk_reward,
        "poc": poc,
        "vah": vah,
        "val": val,
        "poc_position": poc_position,
        "stale": stale,
    }