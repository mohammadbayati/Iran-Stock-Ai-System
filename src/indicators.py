import os
import pandas as pd
import numpy as np
from datetime import datetime
from config.settings import HISTORY_DIR, STALE_HISTORY_DAYS

MINIMUM_BARS = 22


def load_history(symbol: str):
    path = os.path.join(HISTORY_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        if "close" not in df.columns:
            return None
        return df.dropna(subset=["close"]).reset_index(drop=True)
    except Exception:
        return None


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    return round(float(val), 2) if not (val != val) else None


def _macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return round(float(macd_line.iloc[-1]), 2), round(float(signal_line.iloc[-1]), 2), round(float(hist.iloc[-1]), 2)


def _bollinger(series, period=20):
    ma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    latest = series.iloc[-1]
    u = float(upper.iloc[-1])
    l = float(lower.iloc[-1])
    m = float(ma.iloc[-1])
    width = round((u - l) / m * 100, 2) if m > 0 else None
    position = round((latest - l) / (u - l) * 100, 1) if (u - l) > 0 else None
    return round(u, 2), round(m, 2), round(l, 2), width, position


def _trend_score(df):
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
        if ma20_series.iloc[-1] > ma20_series.iloc[-5]:
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
        "latest_close": None, "rsi": None, "macd": None,
        "macd_signal": None, "macd_hist": None, "trend_score": None,
        "volume_ratio_20": None, "return_5d_percent": None,
        "distance_to_20d_high_percent": None, "distance_to_20d_low_percent": None,
        "support": None, "resistance": None, "stop_loss": None,
        "target_1": None, "risk_reward": None, "stale": False,
        "bb_upper": None, "bb_mid": None, "bb_lower": None,
        "bb_width": None, "bb_position": None,
    }
    df = load_history(symbol)
    if df is None or len(df) < MINIMUM_BARS:
        return base

    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(dtype=float)
    latest_close = float(close.iloc[-1])
    latest_date_raw = df["date"].iloc[-1] if "date" in df.columns else None

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
    stop_loss = round(min(support * 0.97, latest_close * 0.95), 2)
    target_1 = resistance
    risk = latest_close - stop_loss
    reward = target_1 - latest_close
    risk_reward = round(reward / risk, 2) if risk > 0 and reward > 0 else None

    macd, macd_sig, macd_hist = _macd(close) if len(close) >= 26 else (None, None, None)
    bb_upper, bb_mid, bb_lower, bb_width, bb_position = _bollinger(close)

    return {
        "symbol": symbol, "missing": False,
        "latest_date": str(latest_date_raw) if latest_date_raw else None,
        "latest_close": round(latest_close, 2),
        "rsi": _rsi(close), "macd": macd, "macd_signal": macd_sig, "macd_hist": macd_hist,
        "trend_score": _trend_score(df), "volume_ratio_20": vol_ratio,
        "return_5d_percent": return_5d,
        "distance_to_20d_high_percent": dist_high,
        "distance_to_20d_low_percent": dist_low,
        "support": support, "resistance": resistance,
        "stop_loss": stop_loss, "target_1": target_1,
        "risk_reward": risk_reward, "stale": stale,
        "bb_upper": bb_upper, "bb_mid": bb_mid, "bb_lower": bb_lower,
        "bb_width": bb_width, "bb_position": bb_position,
    }