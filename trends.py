"""
Trend calculation utilities for MindReflect AI.
Converts raw check-in rows into Pandas DataFrames suitable for charting.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Optional


# ──────────────────────────────────────────────
# DataFrame construction
# ──────────────────────────────────────────────

def checkins_to_df(checkins: List[Dict]) -> pd.DataFrame:
    """
    Convert a list of check-in dicts (from the DB) into a clean DataFrame.
    Columns are cast to correct dtypes; entry_date becomes a datetime index.
    """
    if not checkins:
        return pd.DataFrame()

    df = pd.DataFrame(checkins)

    # Normalise column names
    if "entry_date" in df.columns:
        df["date"] = pd.to_datetime(df["entry_date"])
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    numeric_cols = ["mood", "stress", "sleep_hours", "sleep_quality",
                    "energy", "anxiety", "workload", "screen_time"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    bool_cols = ["exercise", "social_interaction", "outdoor_time",
                 "relaxation", "regular_meals"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("boolean")

    df = df.sort_values("date").reset_index(drop=True)
    return df


# ──────────────────────────────────────────────
# Period filtering
# ──────────────────────────────────────────────

def filter_by_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Return rows within the last `days` calendar days."""
    if df.empty:
        return df
    cutoff = pd.Timestamp(date.today() - timedelta(days=days))
    return df[df["date"] >= cutoff].copy()


# ──────────────────────────────────────────────
# Rolling averages
# ──────────────────────────────────────────────

def rolling_average(df: pd.DataFrame, col: str, window: int = 7) -> pd.Series:
    """Return a rolling mean Series for `col` with the given window."""
    if col not in df.columns or df.empty:
        return pd.Series(dtype=float)
    return df[col].rolling(window=window, min_periods=1).mean()


# ──────────────────────────────────────────────
# Baseline statistics
# ──────────────────────────────────────────────

def compute_baseline(df: pd.DataFrame, window_days: int = 30) -> Dict[str, float]:
    """
    Compute personal baseline averages over the last `window_days`.
    Returns a dict of {metric: mean_value}.
    """
    if df.empty:
        return {}

    baseline_df = filter_by_days(df, window_days)
    if baseline_df.empty:
        baseline_df = df

    metrics = ["mood", "stress", "sleep_hours", "sleep_quality", "energy", "anxiety"]
    result = {}
    for m in metrics:
        if m in baseline_df.columns:
            val = baseline_df[m].dropna().mean()
            if not np.isnan(val):
                result[m] = round(float(val), 2)
    return result


def compute_recent_average(df: pd.DataFrame, days: int = 7) -> Dict[str, float]:
    """Compute averages over the last `days`."""
    recent = filter_by_days(df, days)
    if recent.empty:
        return {}
    metrics = ["mood", "stress", "sleep_hours", "sleep_quality", "energy", "anxiety"]
    result = {}
    for m in metrics:
        if m in recent.columns:
            val = recent[m].dropna().mean()
            if not np.isnan(val):
                result[m] = round(float(val), 2)
    return result


# ──────────────────────────────────────────────
# Weekly / Monthly aggregates
# ──────────────────────────────────────────────

def weekly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return mean values grouped by ISO week."""
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()
    numeric_cols = ["mood", "stress", "sleep_hours", "energy"]
    available = [c for c in numeric_cols if c in df.columns]
    if not available:
        return pd.DataFrame()
    df = df.copy()
    df["week"] = df["date"].dt.to_period("W").apply(lambda r: str(r.start_time.date()))
    summary = df.groupby("week")[available].mean().round(2)
    summary.index.name = "week_starting"
    return summary.reset_index()


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return mean values grouped by calendar month."""
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()
    numeric_cols = ["mood", "stress", "sleep_hours", "energy"]
    available = [c for c in numeric_cols if c in df.columns]
    if not available:
        return pd.DataFrame()
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    summary = df.groupby("month")[available].mean().round(2)
    summary.index.name = "month"
    return summary.reset_index()


# ──────────────────────────────────────────────
# Summary statistics for AI context
# ──────────────────────────────────────────────

def build_ai_summary(df: pd.DataFrame, days: int = 7) -> Dict:
    """
    Build a lightweight statistics summary suitable for passing to Gemini.
    Only includes aggregate statistics — not raw entries or personal text.
    """
    if df.empty:
        return {"error": "No data available"}

    recent = filter_by_days(df, days)
    baseline_stats = compute_baseline(df, window_days=30)
    recent_stats = compute_recent_average(df, days=days)

    checkin_count = len(recent)
    total_entries = len(df)

    # Mood trend direction
    mood_trend = "stable"
    if "mood" in df.columns and len(df) >= 3:
        last_half = df["mood"].dropna().tail(len(df) // 2)
        first_half = df["mood"].dropna().head(len(df) // 2)
        if last_half.mean() < first_half.mean() - 0.3:
            mood_trend = "declining"
        elif last_half.mean() > first_half.mean() + 0.3:
            mood_trend = "improving"

    # Stress trend direction
    stress_trend = "stable"
    if "stress" in df.columns and len(df) >= 3:
        last_half = df["stress"].dropna().tail(len(df) // 2)
        first_half = df["stress"].dropna().head(len(df) // 2)
        if last_half.mean() > first_half.mean() + 0.3:
            stress_trend = "increasing"
        elif last_half.mean() < first_half.mean() - 0.3:
            stress_trend = "decreasing"

    return {
        "period_days": days,
        "checkins_in_period": checkin_count,
        "total_checkins": total_entries,
        "recent_averages": recent_stats,
        "baseline_averages_30d": baseline_stats,
        "mood_trend_direction": mood_trend,
        "stress_trend_direction": stress_trend,
    }
