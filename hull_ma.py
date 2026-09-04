"""
Hull Moving Average (HMA) calculation + 10/21/50 dual-cross detection.

This is Step 1 of the quant signal pipeline:
    10 crosses above 21  -> early warning (watch)
    21 crosses above 50  -> uptrend confirmed (entry candidate)

Both crosses must occur in the correct sequence (10/21 first, then 21/50)
within a configurable lookback window to count as a valid "golden cross" setup.
"""

import pandas as pd
import numpy as np


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted moving average — building block for Hull MA."""
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def hull_ma(series: pd.Series, period: int) -> pd.Series:
    """
    Hull Moving Average.
    HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
    Less lag than SMA/EMA — reacts faster to trend changes.
    """
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))

    wma_half = wma(series, half_period)
    wma_full = wma(series, period)
    raw_hma = 2 * wma_half - wma_full
    return wma(raw_hma, sqrt_period)


def detect_dual_cross(df: pd.DataFrame, lookback: int = 10) -> dict:
    """
    df must have a 'close' column, sorted oldest -> newest.

    Returns dict with:
        hull10, hull21, hull50 (latest values)
        cross_10_21_date: date the 10>21 cross happened (or None)
        cross_21_50_date: date the 21>50 cross happened (or None)
        sequence_valid: True if 10/21 cross happened BEFORE 21/50 cross,
                        both within `lookback` bars of "now"
        stage: 'none' | 'early_warning' | 'uptrend_confirmed'
    """
    df = df.copy()
    df["hull10"] = hull_ma(df["close"], 10)
    df["hull21"] = hull_ma(df["close"], 21)
    df["hull50"] = hull_ma(df["close"], 50)

    df["diff_10_21"] = df["hull10"] - df["hull21"]
    df["diff_21_50"] = df["hull21"] - df["hull50"]

    # a "cross above" = diff flips from <=0 to >0
    df["cross_10_21"] = (df["diff_10_21"] > 0) & (df["diff_10_21"].shift(1) <= 0)
    df["cross_21_50"] = (df["diff_21_50"] > 0) & (df["diff_21_50"].shift(1) <= 0)

    recent = df.tail(lookback)

    cross_10_21_dates = recent.index[recent["cross_10_21"]].tolist()
    cross_21_50_dates = recent.index[recent["cross_21_50"]].tolist()

    cross_10_21_date = cross_10_21_dates[-1] if cross_10_21_dates else None
    cross_21_50_date = cross_21_50_dates[-1] if cross_21_50_dates else None

    sequence_valid = False
    if cross_10_21_date is not None and cross_21_50_date is not None:
        sequence_valid = cross_10_21_date <= cross_21_50_date

    if cross_21_50_date is not None and sequence_valid:
        stage = "uptrend_confirmed"
    elif cross_10_21_date is not None:
        stage = "early_warning"
    else:
        stage = "none"

    latest = df.iloc[-1]

    return {
        "hull10": round(latest["hull10"], 2) if pd.notna(latest["hull10"]) else None,
        "hull21": round(latest["hull21"], 2) if pd.notna(latest["hull21"]) else None,
        "hull50": round(latest["hull50"], 2) if pd.notna(latest["hull50"]) else None,
        "cross_10_21_date": str(cross_10_21_date) if cross_10_21_date is not None else None,
        "cross_21_50_date": str(cross_21_50_date) if cross_21_50_date is not None else None,
        "sequence_valid": sequence_valid,
        "stage": stage,
    }
