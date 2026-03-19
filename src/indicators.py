from __future__ import annotations

import numpy as np
import pandas as pd


def add_technical_indicators(df: pd.DataFrame, rsi_window: int = 14, bb_window: int = 20) -> pd.DataFrame:
    out = df.copy()
    out["close"] = pd.to_numeric(out["close"], errors="coerce")

    delta = out["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / rsi_window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / rsi_window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["rsi"] = 100 - (100 / (1 + rs))
    out["rsi"] = out["rsi"].fillna(50.0).clip(0, 100)

    out["sma_20"] = out["close"].rolling(bb_window, min_periods=1).mean()
    rolling_std = out["close"].rolling(bb_window, min_periods=1).std().fillna(0.0)
    out["bb_upper"] = out["sma_20"] + 2 * rolling_std
    out["bb_lower"] = out["sma_20"] - 2 * rolling_std
    out["sma_50"] = out["close"].rolling(50, min_periods=1).mean()

    return out
