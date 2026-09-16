"""
Descriptive and comparative statistics for MindReflect AI.
All computations are observational — not diagnostic.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from analytics.trends import checkins_to_df, compute_baseline, compute_recent_average, filter_by_days


def compare_to_baseline(recent: Dict[str, float],
                        baseline: Dict[str, float]) -> Dict[str, Dict]:
    """
    Compare recent averages against the personal 30-day baseline.
    Returns a dict of {metric: {recent, baseline, delta, direction}}.
    """
    comparisons = {}
    for metric in ["mood", "stress", "sleep_hours", "energy", "anxiety"]:
        if metric in recent and metric in baseline:
            r = recent[metric]
            b = baseline[metric]
            delta = round(r - b, 2)
            direction = "above" if delta > 0 else ("below" if delta < 0 else "equal")
            comparisons[metric] = {
                "recent": r,
                "baseline": b,
                "delta": delta,
                "direction": direction,
            }
    return comparisons


def day_to_day_changes(df: pd.DataFrame, col: str) -> pd.Series:
    """Return the day-over-day absolute change for a column."""
    if col not in df.columns or df.empty:
        return pd.Series(dtype=float)
    return df[col].diff().abs()


def streak_stats(df: pd.DataFrame) -> Dict[str, int]:
    """
    Return the current check-in streak and the longest streak in history.
    A streak is broken by any day without a logged check-in.
    """
    if df.empty or "date" not in df.columns:
        return {"current_streak": 0, "longest_streak": 0}

    dates = sorted(df["date"].dt.date.unique())
    if not dates:
        return {"current_streak": 0, "longest_streak": 0}

    import datetime
    today = datetime.date.today()

    # Current streak: count back from today
    current = 0
    check = today
    date_set = set(dates)
    while check in date_set:
        current += 1
        check -= datetime.timedelta(days=1)

    # Longest streak overall
    longest = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return {"current_streak": current, "longest_streak": longest}


def completion_rate(df: pd.DataFrame, days: int = 30) -> float:
    """Return fraction of days in the last `days` that had a check-in."""
    if df.empty:
        return 0.0
    recent = filter_by_days(df, days)
    return round(len(recent) / days, 2) if days > 0 else 0.0


def behavioral_summary(df: pd.DataFrame) -> Dict[str, float]:
    """
    Return percentage of days with each tracked behavioral factor.
    """
    result = {}
    bool_cols = {
        "exercise": "Exercise days",
        "social_interaction": "Social days",
        "outdoor_time": "Outdoor time days",
        "relaxation": "Relaxation/meditation days",
        "regular_meals": "Regular meals days",
    }
    for col, label in bool_cols.items():
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(values) > 0:
                result[label] = round(float(values.mean()) * 100, 1)
    return result


def top_reflection_words(checkins: List[Dict], n: int = 10) -> List[str]:
    """
    Return the most commonly used words in reflection entries.
    Filters stop words. Used only for the user's own overview — not sent to AI.
    """
    import re
    from collections import Counter

    stop_words = {
        "i", "me", "my", "we", "the", "a", "an", "and", "or", "but",
        "in", "on", "at", "to", "for", "of", "is", "was", "it", "that",
        "this", "with", "had", "have", "be", "been", "are", "were", "not",
        "so", "do", "did", "can", "will", "just", "about", "from", "up",
        "out", "as", "by", "very", "got", "get", "felt", "feel", "today",
        "day", "really", "bit", "lot", "still", "more", "some", "much",
    }

    words = []
    for entry in checkins:
        text = entry.get("reflection") or ""
        if text:
            words.extend(re.findall(r"\b[a-z]{4,}\b", text.lower()))

    filtered = [w for w in words if w not in stop_words]
    counter = Counter(filtered)
    return [w for w, _ in counter.most_common(n)]
