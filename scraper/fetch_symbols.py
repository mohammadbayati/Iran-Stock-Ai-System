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
    except Exception as e:
        print(f"[fetch_symbols] TSETMC error: {e}")

    try:
        df_fb = _fetch_fallback()
        if len(df_fb) >= 50:
            return df_fb
        print(f"[fetch_symbols] Fallback only returned {len(df_fb)} symbols — trying cache")
    except Exception as e:
        print(f"[fetch_symbols] Fallback error: {e}")
        df_fb = pd.DataFrame()

    # Use cached symbols.csv if available and has enough data
    if os.path.exists(SYMBOLS_CSV):
        df_cache = pd.read_csv(SYMBOLS_CSV)
        if len(df_cache) > 100:
            print(f"[fetch_symbols] Using cached symbols: {len(df_cache)} symbols")
            # Merge live fallback data into cache for fresh prices
            if len(df_fb) > 0 and "symbol" in df_fb.columns and "symbol" in df_cache.columns:
                df_cache = df_cache[~df_cache["symbol"].isin(df_fb["symbol"])]
                df_cache = pd.concat([df_fb, df_cache], ignore_index=True)
                print(f"[fetch_symbols] Merged: {len(df_fb)} live + {len(df_cache)} cached = {len(df_cache)} total")
            return df_cache

    print(f"[fetch_symbols] No cache available, using fallback data only")
    return df_fb