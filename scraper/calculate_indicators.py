from pathlib import Path

import pandas as pd


HISTORY_DIR = Path("data") / "history"
OUTPUT_FILE = Path("data") / "indicators.csv"


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(series: pd.Series):
    ema_12 = series.ewm(span=12, adjust=False).mean()
    ema_26 = series.ewm(span=26, adjust=False).mean()

    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_histogram = macd - macd_signal

    return macd, macd_signal, macd_histogram


def calculate_indicators_for_file(file_path: Path) -> dict | None:
    df = pd.read_csv(file_path, encoding="utf-8-sig")

    if df.empty:
        return None

    required_columns = {"date", "open", "high", "low", "adjClose", "volume", "value", "symbol"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        print(f"Skipping {file_path.name}. Missing columns: {missing_columns}")
        return None

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    close = df["adjClose"].astype(float)
    volume = df["volume"].astype(float)

    df["ema_9"] = close.ewm(span=9, adjust=False).mean()
    df["ema_21"] = close.ewm(span=21, adjust=False).mean()
    df["ema_50"] = close.ewm(span=50, adjust=False).mean()
    df["ema_200"] = close.ewm(span=200, adjust=False).mean()

    df["rsi_14"] = calculate_rsi(close, 14)

    macd, macd_signal, macd_histogram = calculate_macd(close)
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_histogram"] = macd_histogram

    df["avg_volume_20"] = volume.rolling(window=20, min_periods=1).mean()
    df["volume_ratio_20"] = volume / df["avg_volume_20"]

    df["return_1d_percent"] = close.pct_change(periods=1) * 100
    df["return_5d_percent"] = close.pct_change(periods=5) * 100
    df["return_20d_percent"] = close.pct_change(periods=20) * 100

    df["rolling_high_20"] = df["high"].astype(float).rolling(window=20, min_periods=1).max()
    df["rolling_low_20"] = df["low"].astype(float).rolling(window=20, min_periods=1).min()

    df["distance_to_20d_high_percent"] = ((close - df["rolling_high_20"]) / df["rolling_high_20"]) * 100
    df["distance_to_20d_low_percent"] = ((close - df["rolling_low_20"]) / df["rolling_low_20"]) * 100

    latest = df.iloc[-1]
    symbol = latest["symbol"]

    trend_score = 0

    if latest["adjClose"] > latest["ema_21"]:
        trend_score += 1

    if latest["ema_9"] > latest["ema_21"]:
        trend_score += 1

    if latest["ema_21"] > latest["ema_50"]:
        trend_score += 1

    if latest["macd"] > latest["macd_signal"]:
        trend_score += 1

    if latest["volume_ratio_20"] > 1.2:
        trend_score += 1

    rsi = latest["rsi_14"]

    if pd.isna(rsi):
        rsi_status = "Unknown"
    elif rsi < 30:
        rsi_status = "Oversold"
    elif rsi <= 70:
        rsi_status = "Healthy"
    else:
        rsi_status = "Overbought"

    if trend_score >= 4 and rsi_status != "Overbought":
        technical_label = "Strong Technical Setup"
    elif trend_score >= 3:
        technical_label = "Watch Technical Setup"
    else:
        technical_label = "Weak Technical Setup"

    return {
        "symbol": symbol,
        "latest_date": latest["date"],
        "latest_adj_close": latest["adjClose"],
        "ema_9": latest["ema_9"],
        "ema_21": latest["ema_21"],
        "ema_50": latest["ema_50"],
        "ema_200": latest["ema_200"],
        "rsi_14": latest["rsi_14"],
        "rsi_status": rsi_status,
        "macd": latest["macd"],
        "macd_signal": latest["macd_signal"],
        "macd_histogram": latest["macd_histogram"],
        "avg_volume_20": latest["avg_volume_20"],
        "volume_ratio_20": latest["volume_ratio_20"],
        "return_1d_percent": latest["return_1d_percent"],
        "return_5d_percent": latest["return_5d_percent"],
        "return_20d_percent": latest["return_20d_percent"],
        "rolling_high_20": latest["rolling_high_20"],
        "rolling_low_20": latest["rolling_low_20"],
        "distance_to_20d_high_percent": latest["distance_to_20d_high_percent"],
        "distance_to_20d_low_percent": latest["distance_to_20d_low_percent"],
        "trend_score": trend_score,
        "technical_label": technical_label,
    }


def main():
    if not HISTORY_DIR.exists():
        raise FileNotFoundError(f"History directory not found: {HISTORY_DIR}")

    rows = []

    for file_path in HISTORY_DIR.glob("*.csv"):
        print(f"Calculating indicators for: {file_path.name}")

        result = calculate_indicators_for_file(file_path)

        if result:
            rows.append(result)

    if not rows:
        print("No indicator rows generated.")
        return

    output_df = pd.DataFrame(rows)
    output_df = output_df.sort_values(
        by=["trend_score", "volume_ratio_20", "return_5d_percent"],
        ascending=[False, False, False],
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Indicators saved: {OUTPUT_FILE}")
    print(output_df[["symbol", "trend_score", "rsi_14", "rsi_status", "volume_ratio_20", "technical_label"]])


if __name__ == "__main__":
    main()
