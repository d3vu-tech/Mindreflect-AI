"""
Behavioral pattern detection engine for MindReflect AI.

IMPORTANT: These are observational statistical rules only.
They do NOT diagnose medical or psychiatric conditions.
All outputs must be interpreted as wellness observations, not clinical findings.

Detection thresholds are configurable at the top of this module.
They are analytical prototype rules, not clinical standards.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from analytics.trends import checkins_to_df, filter_by_days

# ──────────────────────────────────────────────
# Configurable thresholds (NOT clinical standards)
# ──────────────────────────────────────────────
THRESHOLDS = {
    # Pattern 1: Sustained low mood
    "low_mood_threshold": 2.5,
    "low_mood_consecutive_days": 5,

    # Pattern 2: Sustained high stress
    "high_stress_threshold": 4.0,
    "high_stress_consecutive_days": 5,

    # Pattern 3 & 4: Sleep associations
    "sleep_mood_min_pairs": 14,
    "sleep_stress_min_pairs": 14,
    "correlation_significance_threshold": 0.25,  # |r| above this = noteworthy

    # Pattern 5: Mood variability
    "mood_variability_min_obs": 14,
    "mood_variability_sd_threshold": 1.2,

    # Pattern 6: Energy-mood association
    "energy_mood_min_obs": 10,

    # Pattern 7: Exercise-mood association
    "exercise_mood_min_obs": 10,

    # Pattern 8: Social-mood association
    "social_mood_min_obs": 10,

    # Pattern 9: Screen time — sleep
    "screen_sleep_min_obs": 10,
}


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

def _confidence_from_n(n: int) -> str:
    """Map data-point count to a confidence label."""
    if n < 7:
        return "low"
    if n < 20:
        return "medium"
    return "high"


def _safe_correlation(s1: pd.Series, s2: pd.Series) -> Optional[float]:
    """Return Pearson r between two series or None if insufficient data."""
    combined = pd.concat([s1, s2], axis=1).dropna()
    if len(combined) < 5:
        return None
    try:
        r = combined.iloc[:, 0].corr(combined.iloc[:, 1])
        return float(r) if not np.isnan(r) else None
    except Exception:
        return None


def _max_consecutive(series: pd.Series, condition_fn) -> int:
    """Return the maximum run of consecutive rows satisfying condition_fn."""
    max_run = 0
    current_run = 0
    for val in series:
        if pd.notna(val) and condition_fn(val):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run


# ──────────────────────────────────────────────
# Individual pattern detectors
# ──────────────────────────────────────────────

def detect_sustained_low_mood(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 1: Sustained low mood over consecutive logged days."""
    if "mood" not in df.columns or df.empty:
        return None
    mood_series = df["mood"].dropna()
    if len(mood_series) < THRESHOLDS["low_mood_consecutive_days"]:
        return None

    recent = mood_series.tail(30)
    max_run = _max_consecutive(
        recent, lambda v: v <= THRESHOLDS["low_mood_threshold"]
    )

    if max_run < THRESHOLDS["low_mood_consecutive_days"]:
        return None

    avg_recent = round(float(recent.tail(max_run).mean()), 2)
    avg_all = round(float(mood_series.mean()), 2)

    return {
        "pattern_type": "sustained_low_mood",
        "pattern_name": "Lower Mood Period",
        "description": (
            f"Your mood has remained lower than usual across {max_run} "
            f"consecutive recent entries (average: {avg_recent}/5)."
        ),
        "evidence": (
            f"Average mood over this period: {avg_recent}/5. "
            f"Your overall logged average: {avg_all}/5."
        ),
        "confidence": _confidence_from_n(max_run),
        "data_points": int(max_run),
        "time_period_days": int(max_run),
    }


def detect_sustained_high_stress(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 2: Sustained elevated stress over consecutive logged days."""
    if "stress" not in df.columns or df.empty:
        return None
    stress_series = df["stress"].dropna()
    if len(stress_series) < THRESHOLDS["high_stress_consecutive_days"]:
        return None

    recent = stress_series.tail(30)
    max_run = _max_consecutive(
        recent, lambda v: v >= THRESHOLDS["high_stress_threshold"]
    )

    if max_run < THRESHOLDS["high_stress_consecutive_days"]:
        return None

    avg_recent = round(float(recent.tail(max_run).mean()), 2)
    avg_all = round(float(stress_series.mean()), 2)

    return {
        "pattern_type": "sustained_high_stress",
        "pattern_name": "Elevated Stress Period",
        "description": (
            f"Your stress levels have remained elevated across {max_run} "
            f"consecutive recent entries (average: {avg_recent}/5)."
        ),
        "evidence": (
            f"Average stress over this period: {avg_recent}/5. "
            f"Your overall logged average: {avg_all}/5."
        ),
        "confidence": _confidence_from_n(max_run),
        "data_points": int(max_run),
        "time_period_days": int(max_run),
    }


def detect_sleep_mood_association(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 3: Association between sleep duration and mood."""
    if "sleep_hours" not in df.columns or "mood" not in df.columns:
        return None

    min_pairs = THRESHOLDS["sleep_mood_min_pairs"]
    paired = df[["sleep_hours", "mood"]].dropna()
    if len(paired) < min_pairs:
        return None

    r = _safe_correlation(paired["sleep_hours"], paired["mood"])
    if r is None or abs(r) < THRESHOLDS["correlation_significance_threshold"]:
        return None

    direction = "more" if r > 0 else "fewer"
    mood_direction = "higher" if r > 0 else "lower"

    return {
        "pattern_type": "sleep_mood_association",
        "pattern_name": "Sleep & Mood Pattern",
        "description": (
            f"In your logged data, days with {direction} hours of sleep "
            f"have tended to coincide with {mood_direction} mood."
        ),
        "evidence": (
            f"Correlation between sleep and mood in your data: {r:.2f} "
            f"(based on {len(paired)} logged days). "
            "Correlation does not imply causation."
        ),
        "confidence": _confidence_from_n(len(paired)),
        "data_points": len(paired),
        "time_period_days": int((df["date"].max() - df["date"].min()).days) if "date" in df.columns else 0,
    }


def detect_stress_sleep_association(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 4: Association between stress and sleep quality/duration."""
    if "stress" not in df.columns:
        return None

    sleep_col = "sleep_quality" if "sleep_quality" in df.columns else "sleep_hours"
    if sleep_col not in df.columns:
        return None

    min_pairs = THRESHOLDS["sleep_stress_min_pairs"]
    paired = df[["stress", sleep_col]].dropna()
    if len(paired) < min_pairs:
        return None

    r = _safe_correlation(paired["stress"], paired[sleep_col])
    if r is None or abs(r) < THRESHOLDS["correlation_significance_threshold"]:
        return None

    sleep_label = "sleep quality" if sleep_col == "sleep_quality" else "sleep duration"
    direction = "lower" if r < 0 else "higher"

    return {
        "pattern_type": "stress_sleep_association",
        "pattern_name": "Stress & Sleep Pattern",
        "description": (
            f"Higher-stress days in your log have tended to coincide with "
            f"{direction} {sleep_label}."
        ),
        "evidence": (
            f"Correlation between stress and {sleep_label}: {r:.2f} "
            f"(based on {len(paired)} logged days)."
        ),
        "confidence": _confidence_from_n(len(paired)),
        "data_points": len(paired),
        "time_period_days": int((df["date"].max() - df["date"].min()).days) if "date" in df.columns else 0,
    }


def detect_mood_variability(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 5: Unusually high mood variability."""
    if "mood" not in df.columns or df.empty:
        return None

    mood = df["mood"].dropna()
    if len(mood) < THRESHOLDS["mood_variability_min_obs"]:
        return None

    overall_sd = float(mood.std())
    recent_mood = mood.tail(14)
    recent_sd = float(recent_mood.std())

    if recent_sd < THRESHOLDS["mood_variability_sd_threshold"]:
        return None

    return {
        "pattern_type": "mood_variability",
        "pattern_name": "Mood Variability",
        "description": (
            f"Your mood has fluctuated more than usual over the last "
            f"{len(recent_mood)} logged entries."
        ),
        "evidence": (
            f"Recent mood standard deviation: {recent_sd:.2f}. "
            f"Your overall standard deviation: {overall_sd:.2f}. "
            f"Recent range: {float(recent_mood.min()):.1f}–{float(recent_mood.max()):.1f}/5."
        ),
        "confidence": _confidence_from_n(len(recent_mood)),
        "data_points": len(recent_mood),
        "time_period_days": 14,
    }


def detect_energy_mood_association(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 6: Association between energy and mood."""
    if "energy" not in df.columns or "mood" not in df.columns:
        return None

    min_obs = THRESHOLDS["energy_mood_min_obs"]
    paired = df[["energy", "mood"]].dropna()
    if len(paired) < min_obs:
        return None

    r = _safe_correlation(paired["energy"], paired["mood"])
    if r is None or abs(r) < THRESHOLDS["correlation_significance_threshold"]:
        return None

    direction = "higher" if r > 0 else "lower"

    return {
        "pattern_type": "energy_mood_association",
        "pattern_name": "Energy & Mood Pattern",
        "description": (
            f"Lower-energy days in your log have tended to coincide with "
            f"{'lower' if r > 0 else 'higher'} mood."
        ),
        "evidence": (
            f"Correlation between energy and mood: {r:.2f} "
            f"(based on {len(paired)} logged days)."
        ),
        "confidence": _confidence_from_n(len(paired)),
        "data_points": len(paired),
        "time_period_days": int((df["date"].max() - df["date"].min()).days) if "date" in df.columns else 0,
    }


def detect_exercise_mood_association(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 7: Compare mood on exercise vs non-exercise days."""
    if "exercise" not in df.columns or "mood" not in df.columns:
        return None

    min_obs = THRESHOLDS["exercise_mood_min_obs"]
    sub = df[["exercise", "mood"]].dropna()
    if len(sub) < min_obs:
        return None

    exercise_days = sub[sub["exercise"] == 1]["mood"]
    no_exercise_days = sub[sub["exercise"] == 0]["mood"]

    if len(exercise_days) < 3 or len(no_exercise_days) < 3:
        return None

    ex_avg = round(float(exercise_days.mean()), 2)
    no_ex_avg = round(float(no_exercise_days.mean()), 2)
    diff = round(ex_avg - no_ex_avg, 2)

    if abs(diff) < 0.3:
        return None

    direction = "higher" if diff > 0 else "lower"

    return {
        "pattern_type": "exercise_mood_association",
        "pattern_name": "Exercise & Mood Pattern",
        "description": (
            f"Your logged mood was generally {direction} on days when "
            f"you recorded exercise."
        ),
        "evidence": (
            f"Average mood on exercise days: {ex_avg}/5 "
            f"({len(exercise_days)} days). "
            f"Average mood on non-exercise days: {no_ex_avg}/5 "
            f"({len(no_exercise_days)} days). "
            "This is an association, not a causal claim."
        ),
        "confidence": _confidence_from_n(len(sub)),
        "data_points": len(sub),
        "time_period_days": int((df["date"].max() - df["date"].min()).days) if "date" in df.columns else 0,
    }


def detect_social_mood_association(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 8: Compare mood on social vs non-social days."""
    if "social_interaction" not in df.columns or "mood" not in df.columns:
        return None

    min_obs = THRESHOLDS["social_mood_min_obs"]
    sub = df[["social_interaction", "mood"]].dropna()
    if len(sub) < min_obs:
        return None

    social_days = sub[sub["social_interaction"] == 1]["mood"]
    no_social_days = sub[sub["social_interaction"] == 0]["mood"]

    if len(social_days) < 3 or len(no_social_days) < 3:
        return None

    s_avg = round(float(social_days.mean()), 2)
    ns_avg = round(float(no_social_days.mean()), 2)
    diff = round(s_avg - ns_avg, 2)

    if abs(diff) < 0.3:
        return None

    direction = "higher" if diff > 0 else "lower"

    return {
        "pattern_type": "social_mood_association",
        "pattern_name": "Social Interaction & Mood Pattern",
        "description": (
            f"Your logged mood tended to be {direction} on days when "
            f"you recorded social interaction."
        ),
        "evidence": (
            f"Average mood on social days: {s_avg}/5 ({len(social_days)} days). "
            f"Average mood on non-social days: {ns_avg}/5 ({len(no_social_days)} days)."
        ),
        "confidence": _confidence_from_n(len(sub)),
        "data_points": len(sub),
        "time_period_days": int((df["date"].max() - df["date"].min()).days) if "date" in df.columns else 0,
    }


def detect_screen_sleep_association(df: pd.DataFrame) -> Optional[Dict]:
    """Pattern 9: Association between screen time and sleep."""
    if "screen_time" not in df.columns:
        return None

    sleep_col = "sleep_hours" if "sleep_hours" in df.columns else None
    if sleep_col is None:
        return None

    min_obs = THRESHOLDS["screen_sleep_min_obs"]
    paired = df[["screen_time", sleep_col]].dropna()
    if len(paired) < min_obs:
        return None

    r = _safe_correlation(paired["screen_time"], paired[sleep_col])
    if r is None or abs(r) < THRESHOLDS["correlation_significance_threshold"]:
        return None

    direction = "shorter" if r < 0 else "longer"

    return {
        "pattern_type": "screen_sleep_association",
        "pattern_name": "Screen Time & Sleep Pattern",
        "description": (
            f"Higher screen-time days in your log have tended to coincide "
            f"with {direction} sleep duration."
        ),
        "evidence": (
            f"Correlation between screen time and sleep hours: {r:.2f} "
            f"(based on {len(paired)} logged days). "
            "Correlation does not imply causation."
        ),
        "confidence": _confidence_from_n(len(paired)),
        "data_points": len(paired),
        "time_period_days": int((df["date"].max() - df["date"].min()).days) if "date" in df.columns else 0,
    }


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def run_all_patterns(checkins: List[Dict]) -> List[Dict]:
    """
    Run all pattern detectors on the provided check-in data.
    Returns a list of detected pattern dicts (may be empty).
    """
    df = checkins_to_df(checkins)
    if df.empty:
        return []

    detectors = [
        detect_sustained_low_mood,
        detect_sustained_high_stress,
        detect_sleep_mood_association,
        detect_stress_sleep_association,
        detect_mood_variability,
        detect_energy_mood_association,
        detect_exercise_mood_association,
        detect_social_mood_association,
        detect_screen_sleep_association,
    ]

    patterns = []
    for detector in detectors:
        try:
            result = detector(df)
            if result:
                patterns.append(result)
        except Exception:
            # Never surface raw errors to user; silently skip failed detector
            continue

    return patterns
