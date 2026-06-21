"""
Fetch all 700+ symbols from TSETMC old API (MarketWatchPlus).
Falls back to tradersarena if TSETMC fails.
"""

import os
import sys
import requests
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SYMBOLS_CSV, SYMBOLS_JSON, DATA_DIR

TSETMC_URL = "https://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx"
FALLBACK_URL = "https://tradersarena.ir/data/mainwatch/symbols"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _parse_tsetmc(text: str) -> pd.DataFrame:
    """
    Format: HEADER@@sym1;sym2;...
    Each symbol: ins_code,isin,symbol,name,unknown,prev_close,last,close,count,volume,value,close2,last2,high,low,unknown2,unknown3,unknown4,unknown5,unknown6,...
    """
    if "@@" not in text:
        return pd.DataFrame()

    _, symbols_part = text.split("@@", 1)
    # Queue data after second @@ if present
    if "@@" in symbols_part:
        symbols_part, queue_part = symbols_part.split("@@", 1)
        queue_map = _parse_queue(queue_part)
    else:
        queue_map = {}

    records = []
    for sym_str in symbols_part.split(";"):
        sym_str = sym_str.strip()
        if not sym_str:
            continue
        parts = sym_str.split(",")
        if len(parts) < 12:
            continue
        try:
            ins_code = parts[0]
            isin = parts[1]
            symbol = parts[2].strip()
            name = parts[3].strip() if len(parts) > 3 else ""
            prev_close = float(parts[5] or 0)
            last = float(parts[6] or 0)
            close = float(parts[7] or 0)
            count = int(parts[8] or 0)
            volume = float(parts[9] or 0)
            value = float(parts[10] or 0)
            high = float(parts[13] or 0) if len(parts) > 13 else 0
            low = float(parts[14] or 0) if len(parts) > 14 else 0

            change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0

            q = queue_map.get(ins_code, {})
            buy_vol = float(q.get("buy_vol", 0))
            sell_vol = float(q.get("sell_vol", 0))
            buyer_power = round(buy_vol / sell_vol, 2) if sell_vol > 0 else (2.0 if buy_vol > 0 else 1.0)
            flow = buy_vol - sell_vol

            records.append({
                "ins_code": ins_code,
                "isin": isin,
                "symbol": symbol,
                "name": name,
                "previous_close": prev_close,
                "last_price": last,
                "close_price": close,
                "close_price_change_percent": change_pct,
                "volume": volume,
                "trade_value": value,
                "high": high,
                "low": low,
                "buyer_power": buyer_power,
                "buy_power_numerator": buy_vol,
                "sell_power_denominator": sell_vol,
                "real_money_flow": flow,
                "best_buy_price": float(q.get("best_buy_price", 0)),
                "best_sell_price": float(q.get("best_sell_price", 0)),
                "best_buy_volume": float(q.get("best_buy_vol", 0)),
                "best_sell_volume": float(q.get("best_sell_vol", 0)),
            })
        except Exception:
            continue

    return pd.DataFrame(records)


def _parse_queue(queue_text: str) -> dict:
    """Parse queue section: ins_code,buy_vol,buy_price,sell_price,sell_vol,..."""
    result = {}
    for item in queue_text.split(";"):
        parts = item.strip().split(",")
        if len(parts) < 5:
            continue
        try:
            ins_code = parts[0]
            result[ins_code] = {
                "buy_vol": float(parts[1] or 0),
                "best_buy_price": float(parts[2] or 0),
                "best_sell_price": float(parts[3] or 0),
                "sell_vol": float(parts[4] or 0),
                "best_buy_vol": float(parts[1] or 0),
                "best_sell_vol": float(parts[4] or 0),
            }
        except Exception:
            continue
    return result


def _fetch_fallback() -> pd.DataFrame:
    print(f"[fetch_symbols] Trying fallback: {FALLBACK_URL}")
    resp = requests.get(FALLBACK_URL, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    rows = raw if isinstance(raw, list) else raw.get("data", [])
    COLS = [
        "ins_code", "isin", "symbol", "buy_volume_or_count", "trade_value",
        "last_price", "last_price_change_percent", "close_price",
        "close_price_change_percent", "buy_power_numerator", "sell_power_denominator",
        "buyer_power", "real_money_flow", "unknown_1", "unknown_2",
        "volume", "best_buy_price", "best_sell_price", "best_sell_volume", "previous_close",
    ]
    records = []
    for row in rows:
        if isinstance(row, (list, tuple)):
            records.append({COLS[i]: row[i] if i < len(row) else None for i in range(len(COLS))})
    df = pd.DataFrame(records)
    print(f"[fetch_symbols] {len(df)} symbols from fallback")
    return df


def fetch_symbols() -> pd.DataFrame:
    print(f"[fetch_symbols] Fetching all symbols from TSETMC...")
    try:
        resp = requests.get(TSETMC_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        df = _parse_tsetmc(resp.text)
        if len(df) > 50:
            print(f"[fetch_symbols] {len(df)} symbols fetched from TSETMC")
            return df
        print(f"[fetch_symbols] TSETMC returned {len(df)} symbols — market may be closed, using fallback")
        return _fetch_fallback()
    except Exception as e:
        print(f"[fetch_symbols] TSETMC error: {e}")
        return _fetch_fallback()


def save_symbols(df: pd.DataFrame):
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(SYMBOLS_CSV, index=False, encoding="utf-8-sig")
    df.to_json(SYMBOLS_JSON, orient="records", force_ascii=False, indent=2)
    print(f"[fetch_symbols] Saved {len(df)} symbols")


if __name__ == "__main__":
    df = fetch_symbols()
    save_symbols(df)
    print(df[["symbol", "close_price_change_percent", "volume", "buyer_power"]].head(20).to_string())