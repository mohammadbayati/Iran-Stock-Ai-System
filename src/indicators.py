def _volume_profile(df: pd.DataFrame, bins: int = 20, value_area_pct: float = 0.70):
    """
    Volume Profile over last 20 bars.
    Returns (poc, vah, val, poc_position).
    """
    try:
        if "volume" not in df.columns:
            return None, None, None, "unknown"

        last = df.tail(20).copy()
        last = last.dropna(subset=["close", "volume"])
        if len(last) < 5:
            return None, None, None, "unknown"

        price_min = float(last["close"].min())
        price_max = float(last["close"].max())
        if price_max <= price_min:
            return None, None, None, "unknown"

        bin_edges = np.linspace(price_min, price_max, bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        vol_per_bin = np.zeros(bins)
        for _, row in last.iterrows():
            idx = int((row["close"] - price_min) / (price_max - price_min) * bins)
            idx = max(0, min(idx, bins - 1))
            vol_per_bin[idx] += float(row["volume"])

        poc_idx = int(np.argmax(vol_per_bin))
        poc = round(float(bin_centers[poc_idx]), 2)

        total_vol = vol_per_bin.sum()
        if total_vol <= 0:
            return poc, None, None, "unknown"

        target_vol = total_vol * value_area_pct

        # Sort bins by volume descending, expand until 70% captured
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