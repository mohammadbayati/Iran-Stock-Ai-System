def screen_top10(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df["has_history"] = df["symbol"].apply(_has_history)
    df["initial_score"] = df.apply(score_symbol, axis=1)
    df["initial_label"] = df["initial_score"].apply(initial_label)

    if IS_CI:
        # در CI: سمبل‌هایی که history دارن رو بدون فیلتر سخت نگه دار
        df_with_hist = df[df["has_history"] == True].copy()
        df_no_hist = df[df["has_history"] == False].copy()
        df_no_hist = df_no_hist[df_no_hist.apply(_is_valid_symbol, axis=1)]

        df_combined = pd.concat([df_with_hist, df_no_hist]).drop_duplicates(subset="symbol")
        df_combined = df_combined.sort_values("initial_score", ascending=False).reset_index(drop=True)

        result = df_combined.head(TOP_N).copy()
        print(f"[screen_top10] CI mode: {len(df_with_hist)} with history + {len(df_no_hist)} filtered = {len(result)} selected")
    else:
        df = df[df.apply(_is_valid_symbol, axis=1)].copy()
        print(f"[screen_top10] {before} → {len(df)} after liquidity filter")
        df = df.sort_values("initial_score", ascending=False).reset_index(drop=True)
        result = df.head(TOP_N).copy()

    with_hist = result["has_history"].sum()
    print(f"[screen_top10] Selected {len(result)} symbols ({with_hist} with cached history)")
    return result