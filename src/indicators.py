"""
Calculate technical indicators from historical OHLCV data.

Returns a dict of indicator values for a single symbol.
If history is unavailable or too short, returns an empty indicator dict
with missing=True so downstream can label it correctly.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

from config.settings import HISTORY_DIR, STALE_HISTORY_DAYS

MINIMUM_BARS = 15  # minimum bars needed for calculations


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
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if pd.isna(last_gain) or pd.isna(last_loss):
        return None
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
    if last_gain == 0:
        return 0.0
    rs = last_gain / last_loss
    return round(float(100 - (100 / (1 + rs))), 2)


def _rsi_series(series: pd.Series, period: int = 14) -> pd.Series:
    """Returns the full RSI series (for divergence detection)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """Average True Range — requires high/low/close columns."""
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


def _rsi_divergence(close: pd.Series, rsi_s: pd.Series, lookback: int = 10) -> str:
    if len(close) < lookback or len(rsi_s.dropna()) < lookback:
        return "none"
    price_recent = close.iloc[-lookback:]
    rsi_recent = rsi_s.iloc[-lookback:]
    price_first_half = price_recent.iloc[:lookback // 2]
    price_second_half = price_recent.iloc[lookback // 2:]
    rsi_first_half = rsi_recent.iloc[:lookback // 2]
    rsi_second_half = rsi_recent.iloc[lookback // 2:]
    price_low1 = price_first_half.min()
    price_low2 = price_second_half.min()
    rsi_low1 = rsi_first_half.min()
    rsi_low2 = rsi_second_half.min()
    price_high1 = price_first_half.max()
    price_high2 = price_second_half.max()
    rsi_high1 = rsi_first_half.max()
    rsi_high2 = rsi_second_half.max()
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
        slope = ma20_series.iloc[-1] - ma20_series.iloc[-lookback]
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


def _volume_profile(df: pd.DataFrame, bins: int = 10) -> dict:
    df_vp = df.tail(60) if len(df) > 60 else df
    if "volume" not in df_vp.columns or df_vp["volume"].isna().all():
        return {"poc": None, "vah": None, "val": None, "poc_position": "unknown"}
    close = df_vp["close"].dropna()
    volume = df_vp["volume"].dropna()
    if len(close) < 5 or len(volume) < 5:
        return {"poc": None, "vah": None, "val": None, "poc_position": "unknown"}
    price_min = close.min()
    price_max = close.max()
    if price_max <= price_min:
        return {"poc": None, "vah": None, "val": None, "poc_position": "unknown"}
    bin_edges = np.linspace(price_min, price_max, bins + 1)
    bin_vols = np.zeros(bins)
    bin_midpoints = (bin_edges[:-1] + bin_edges[1:]) / 2
    for price, vol in zip(close, volume):
        idx = min(int((price - price_min) / (price_max - price_min) * bins), bins - 1)
        bin_vols[idx] += vol
    poc_idx = int(np.argmax(bin_vols))
    poc = round(float(bin_midpoints[poc_idx]), 2)
    total_vol = bin_vols.sum()
    target_vol = total_vol * 0.70
    val_idx = poc_idx
    vah_idx = poc_idx
    captured = bin_vols[poc_idx]
    while captured < target_vol:
        can_go_low = val_idx > 0
        can_go_high = vah_idx < bins - 1
        if not can_go_low and not can_go_high:
            break
        add_low = bin_vols[val_idx - 1] if can_go_low else -1
        add_high = bin_vols[vah_idx + 1] if can_go_high else -1
        if add_low >= add_high and can_go_low:
            val_idx -= 1
            captured += bin_vols[val_idx]
        elif can_go_high:
            vah_idx += 1
            captured += bin_vols[vah_idx]
        else:
            break
    val = round(float(bin_midpoints[val_idx]), 2)
    vah = round(float(bin_midpoints[vah_idx]), 2)
    latest_close = float(close.iloc[-1])
    if latest_close > poc * 1.01:
        poc_position = "above"
    elif latest_close < poc * 0.99:
        poc_position = "below"
    else:
        poc_position = "at"
    return {"poc": poc, "vah": vah, "val": val, "poc_position": poc_position}


def _swing_points(df: pd.DataFrame, window: int = 5, lookback: int = 60) -> dict:
    df_s = df.tail(lookback).reset_index(drop=True) if len(df) > lookback else df.reset_index(drop=True)
    has_hl = "high" in df_s.columns and "low" in df_s.columns
    if has_hl:
        highs = df_s["high"]
        lows = df_s["low"]
    else:
        highs = df_s["close"]
        lows = df_s["close"]
    swing_highs = []
    swing_lows = []
    n = len(df_s)
    for i in range(window, n - window):
        left_h = highs.iloc[i - window:i]
        right_h = highs.iloc[i + 1:i + window + 1]
        if highs.iloc[i] >= left_h.max() and highs.iloc[i] >= right_h.max():
            swing_highs.append(float(highs.iloc[i]))
        left_l = lows.iloc[i - window:i]
        right_l = lows.iloc[i + 1:i + window + 1]
        if lows.iloc[i] <= left_l.min() and lows.iloc[i] <= right_l.min():
            swing_lows.append(float(lows.iloc[i]))
    latest_close = float(df_s["close"].iloc[-1])
    fallback_high = float(highs.max())
    fallback_low = float(lows.min())
    resistance_candidates = [p for p in swing_highs if p >= latest_close * 0.99]
    resistance = round(min(resistance_candidates), 2) if resistance_candidates else round(fallback_high, 2)
    support_candidates = [p for p in swing_lows if p <= latest_close * 1.01]
    support = round(max(support_candidates), 2) if support_candidates else round(fallback_low, 2)
    return {"support": support, "resistance": resistance}


def _bollinger_bands(close: pd.Series, period: int = 20, std_mult: float = 2.0) -> dict:
    if len(close) < period:
        return {"bb_upper": None, "bb_middle": None, "bb_lower": None, "bb_squeeze": False, "bb_pct": None}
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    bb_upper = round(float(upper.iloc[-1]), 2)
    bb_middle = round(float(sma.iloc[-1]), 2)
    bb_lower = round(float(lower.iloc[-1]), 2)
    bandwidth = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else None
    squeeze = bandwidth is not None and bandwidth < 0.10
    latest = float(close.iloc[-1])
    bb_pct = round((latest - bb_lower) / (bb_upper - bb_lower), 3) if (bb_upper - bb_lower) > 0 else None
    return {"bb_upper": bb_upper, "bb_middle": bb_middle, "bb_lower": bb_lower, "bb_squeeze": squeeze, "bb_pct": bb_pct}


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    if len(close) < slow + signal:
        return {"macd_line": None, "macd_signal": None, "macd_hist": None, "macd_crossover": "none"}
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    ml = round(float(macd_line.iloc[-1]), 4)
    sl = round(float(signal_line.iloc[-1]), 4)
    hl = round(float(hist.iloc[-1]), 4)
    if len(macd_line) >= 2:
        prev_diff = float(macd_line.iloc[-2]) - float(signal_line.iloc[-2])
        curr_diff = float(macd_line.iloc[-1]) - float(signal_line.iloc[-1])
        if prev_diff < 0 and curr_diff >= 0:
            crossover = "bullish"
        elif prev_diff > 0 and curr_diff <= 0:
            crossover = "bearish"
        else:
            crossover = "none"
    else:
        crossover = "none"
    return {"macd_line": ml, "macd_signal": sl, "macd_hist": hl, "macd_crossover": crossover}


def _candlestick_patterns(df: pd.DataFrame) -> dict:
    result = {"candle_pattern": "none", "candle_bullish": None}
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return result
    if len(df) < 3:
        return result
    df_c = df.tail(3).reset_index(drop=True)
    o = df_c["open"].astype(float)
    h = df_c["high"].astype(float)
    l = df_c["low"].astype(float)
    c = df_c["close"].astype(float)
    o0, h0, l0, c0 = o.iloc[-1], h.iloc[-1], l.iloc[-1], c.iloc[-1]
    o1, h1, l1, c1 = o.iloc[-2], h.iloc[-2], l.iloc[-2], c.iloc[-2]
    o2, h2, l2, c2 = o.iloc[-3], h.iloc[-3], l.iloc[-3], c.iloc[-3]
    body0 = abs(c0 - o0)
    body1 = abs(c1 - o1)
    range0 = h0 - l0 if h0 - l0 > 0 else 0.001
    range1 = h1 - l1 if h1 - l1 > 0 else 0.001
    upper_shadow0 = h0 - max(o0, c0)
    lower_shadow0 = min(o0, c0) - l0
    if body0 < 0.10 * range0:
        result["candle_pattern"] = "doji"
        result["candle_bullish"] = None
        return result
    if (lower_shadow0 >= 2 * body0 and upper_shadow0 <= 0.3 * body0 and min(o0, c0) > l0 + range0 * 0.5):
        result["candle_pattern"] = "hammer"
        result["candle_bullish"] = True
        return result
    if (upper_shadow0 >= 2 * body0 and lower_shadow0 <= 0.3 * body0 and max(o0, c0) < h0 - range0 * 0.5):
        result["candle_pattern"] = "inverted_hammer"
        result["candle_bullish"] = True
        return result
    prev_bearish = c1 < o1
    today_bullish = c0 > o0
    if prev_bearish and today_bullish and o0 < c1 and c0 > o1:
        result["candle_pattern"] = "bullish_engulfing"
        result["candle_bullish"] = True
        return result
    prev_bullish = c1 > o1
    today_bearish = c0 < o0
    if prev_bullish and today_bearish and o0 > c1 and c0 < o1:
        result["candle_pattern"] = "bearish_engulfing"
        result["candle_bullish"] = False
        return result
    bar2_bearish = c2 < o2 and abs(c2 - o2) > 0.5 * (h2 - l2)
    bar1_small = abs(c1 - o1) < 0.3 * (h1 - l1 if h1 - l1 > 0 else 0.001)
    bar0_bullish = c0 > o0 and abs(c0 - o0) > 0.5 * range0
    if bar2_bearish and bar1_small and bar0_bullish and c0 > (o2 + c2) / 2:
        result["candle_pattern"] = "morning_star"
        result["candle_bullish"] = True
        return result
    return result


def _weekly_trend(df: pd.DataFrame) -> dict:
    result = {"weekly_rsi": None, "weekly_trend": None}
    if "date" not in df.columns:
        return result
    try:
        dfw = df.copy()
        dfw["date"] = pd.to_datetime(dfw["date"])
        dfw = dfw.set_index("date")
        weekly = dfw["close"].resample("W").last().dropna()
        if len(weekly) < 15:
            return result
        w_rsi = _rsi(weekly)
        result["weekly_rsi"] = w_rsi
        if len(weekly) >= 5:
            slope = float(weekly.iloc[-1]) - float(weekly.iloc[-4])
            result["weekly_trend"] = "up" if slope > 0 else "down"
    except Exception:
        pass
    return result


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
        "poc": None,
        "vah": None,
        "val": None,
        "poc_position": "unknown",
        "bb_upper": None,
        "bb_middle": None,
        "bb_lower": None,
        "bb_squeeze": False,
        "bb_pct": None,
        "macd_line": None,
        "macd_signal": None,
        "macd_hist": None,
        "macd_crossover": "none",
        "weekly_rsi": None,
        "weekly_trend": None,
        "candle_pattern": "none",
        "candle_bullish": None,
        "close_20d": None,
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

    sp = _swing_points(df)
    support = sp["support"]
    resistance = sp["resistance"]

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
    if risk > 0 and reward > 0:
        risk_reward = min(round(reward / risk, 2), 10.0)
    else:
        risk_reward = None

    rsi_val = _rsi(close)
    divergence = "none"
    if len(close) >= 20:
        rsi_s = _rsi_series(close)
        divergence = _rsi_divergence(close, rsi_s)

    vp = _volume_profile(df)
    bb = _bollinger_bands(close)
    macd = _macd(close)
    weekly = _weekly_trend(df)
    candle = _candlestick_patterns(df)

    if vp["val"] and vp["val"] > stop_loss and vp["val"] < latest_close:
        stop_loss = round(vp["val"], 2)
        risk = latest_close - stop_loss
        if risk > 0 and reward > 0:
            risk_reward = min(round(reward / risk, 2), 10.0)

    close_20d = ",".join(str(int(round(float(v), 0))) for v in close.iloc[-20:].tolist())

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
        "poc": vp["poc"],
        "vah": vp["vah"],
        "val": vp["val"],
        "poc_position": vp["poc_position"],
        "bb_upper": bb["bb_upper"],
        "bb_middle": bb["bb_middle"],
        "bb_lower": bb["bb_lower"],
        "bb_squeeze": bb["bb_squeeze"],
        "bb_pct": bb["bb_pct"],
        "macd_line": macd["macd_line"],
        "macd_signal": macd["macd_signal"],
        "macd_hist": macd["macd_hist"],
        "macd_crossover": macd["macd_crossover"],
        "weekly_rsi": weekly["weekly_rsi"],
        "weekly_trend": weekly["weekly_trend"],
        "candle_pattern": candle["candle_pattern"],
        "candle_bullish": candle["candle_bullish"],
        "close_20d": close_20d,
    }