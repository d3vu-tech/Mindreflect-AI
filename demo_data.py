"""
Synthetic demo data generator for MindReflect AI.

IMPORTANT: All data generated here is entirely synthetic/fictional.
It is clearly labelled as demo data and must never be mixed with real user data
without clear identification.

Generates approximately 75 days of realistic-looking wellness data.
"""

import random
import math
from datetime import date, timedelta
from typing import List, Dict

# Demo seed for reproducibility
DEMO_SEED = 42


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _round_to_int(value: float, lo: int, hi: int) -> int:
    return int(_clamp(round(value), lo, hi))


def generate_demo_checkins(user_id: int, days: int = 75) -> List[Dict]:
    """
    Generate `days` of synthetic daily check-in data.
    Uses a random walk with seasonal influence and behavioral correlations
    to produce plausible-looking wellness patterns.

    Returns a list of dicts ready for upsert_checkin().
    """
    random.seed(DEMO_SEED)
    checkins = []

    # Starting baselines
    mood = 3.5
    stress = 2.5
    sleep_hours = 7.2
    energy = 3.3

    # Inject a realistic "rough patch" around days 30-45
    rough_start = 28
    rough_end = 45

    # Inject a high-stress period around days 50-60
    stress_spike_start = 48
    stress_spike_end = 60

    today = date.today()

    for i in range(days, 0, -1):
        entry_date = today - timedelta(days=i)
        day_num = days - i  # 0-indexed

        # ── Simulate seasonal drift
        seasonal_mood = 0.2 * math.sin(2 * math.pi * day_num / 30)

        # ── Rough patch: mood drops, stress rises
        rough_effect_mood = -1.2 if rough_start <= day_num < rough_end else 0
        rough_effect_stress = 1.4 if rough_start <= day_num < rough_end else 0

        # ── Stress spike
        stress_spike = 1.5 if stress_spike_start <= day_num < stress_spike_end else 0

        # ── Random walk
        mood += random.gauss(0, 0.4) + seasonal_mood + rough_effect_mood * 0.15
        stress += random.gauss(0, 0.35) + rough_effect_stress * 0.15 + stress_spike * 0.12
        sleep_hours += random.gauss(0, 0.5)
        energy += random.gauss(0, 0.4)

        # ── Mean reversion
        mood += (3.4 - mood) * 0.08
        stress += (2.6 - stress) * 0.08
        sleep_hours += (7.0 - sleep_hours) * 0.08
        energy += (3.2 - energy) * 0.08

        # ── Clamp to valid ranges
        mood_val = _round_to_int(mood, 1, 5)
        stress_val = _round_to_int(stress, 1, 5)
        sleep_val = round(_clamp(sleep_hours, 3.0, 10.0), 1)
        sleep_quality = _round_to_int(sleep_hours / 2.2 + random.gauss(0, 0.3), 1, 5)
        energy_val = _round_to_int(energy, 1, 5)
        anxiety_val = _round_to_int(stress - 0.5 + random.gauss(0, 0.6), 1, 5)
        workload_val = _round_to_int(stress + random.gauss(0, 0.5), 1, 5)

        # ── Behavioral factors with probabilistic realism
        exercise = random.random() < 0.38         # ~38% days
        social = random.random() < 0.52           # ~52% days
        outdoor = random.random() < 0.45          # ~45% days
        relaxation = random.random() < 0.30       # ~30% days
        regular_meals = random.random() < 0.68    # ~68% days

        # Screen time correlated negatively with sleep
        screen_time = round(_clamp(
            (10 - sleep_val) * 1.1 + random.gauss(0, 1.2), 0.5, 12.0
        ), 1)

        # Skip some entries randomly (not every day has a check-in)
        if random.random() < 0.12:  # ~12% chance of missing entry
            continue

        # Reflections: a selection of demo phrases
        reflections = _get_demo_reflections(day_num, rough_start, rough_end,
                                             stress_spike_start, stress_spike_end,
                                             mood_val, stress_val)

        checkins.append({
            "entry_date": entry_date.isoformat(),
            "mood": mood_val,
            "stress": stress_val,
            "sleep_hours": sleep_val,
            "sleep_quality": sleep_quality,
            "energy": energy_val,
            "anxiety": anxiety_val,
            "exercise": exercise,
            "social_interaction": social,
            "outdoor_time": outdoor,
            "workload": workload_val,
            "screen_time": screen_time,
            "relaxation": relaxation,
            "regular_meals": regular_meals,
            "reflection": reflections,
            "is_demo": True,
            "created_at": f"{entry_date.isoformat()}T08:00:00",
        })

    return checkins


def _get_demo_reflections(day_num: int, rough_start: int, rough_end: int,
                           stress_start: int, stress_end: int,
                           mood: int, stress: int) -> str:
    """Return a contextual demo reflection phrase."""
    if rough_start <= day_num < rough_end:
        phrases = [
            "Feeling a bit off today, hard to pinpoint why.",
            "Low energy and motivation this week.",
            "Things felt heavier than usual today.",
            "Struggled to concentrate today.",
            "Not a great day overall, but getting through it.",
        ]
    elif stress_start <= day_num < stress_end:
        phrases = [
            "A lot on my plate with work deadlines.",
            "Pressure building up this week.",
            "Hard to switch off in the evenings.",
            "Busy period, feeling stretched.",
        ]
    elif mood >= 4:
        phrases = [
            "Good day overall, felt productive.",
            "Had a nice evening, feeling balanced.",
            "Energy was good today.",
            "Went for a walk, helped a lot.",
            "Caught up with a friend, lifted my mood.",
        ]
    elif stress >= 4:
        phrases = [
            "Busy and a bit stressed, but managing.",
            "Lots to do today, feeling it a bit.",
        ]
    else:
        phrases = [
            "Average day, nothing particular to note.",
            "Routine day.",
            "Felt okay, a bit tired.",
            "Normal day, reasonably productive.",
            "",  # Some entries have no reflection
        ]

    return random.choice(phrases)


def generate_demo_journal_entries(user_id: int) -> List[Dict]:
    """
    Generate a small set of synthetic journal entries.
    Content is realistic-sounding but entirely fictional.
    """
    random.seed(DEMO_SEED + 1)
    today = date.today()

    entries = [
        {
            "entry_date": (today - timedelta(days=68)).isoformat(),
            "title": "Starting this journal",
            "content": "Decided to start tracking how I feel each day. Hoping it helps me notice patterns I'd otherwise miss.",
            "mood_tag": 4,
            "tags": "start, reflection",
        },
        {
            "entry_date": (today - timedelta(days=55)).isoformat(),
            "title": "A difficult stretch",
            "content": "The last couple of weeks have felt heavier than usual. Hard to explain. Things are fine objectively, but I feel flat. Going to keep tracking and see if something shifts.",
            "mood_tag": 2,
            "tags": "difficult, reflection",
        },
        {
            "entry_date": (today - timedelta(days=40)).isoformat(),
            "title": "Starting to feel more like myself",
            "content": "The last week has been better. I noticed I slept more consistently and that seemed to help. Made a point of getting outside each day.",
            "mood_tag": 4,
            "tags": "improvement, sleep, outdoor",
        },
        {
            "entry_date": (today - timedelta(days=22)).isoformat(),
            "title": "Work pressure",
            "content": "Busy period at work. Finding it harder to switch off in the evenings. Screen time has crept up.",
            "mood_tag": 3,
            "tags": "work, stress",
        },
        {
            "entry_date": (today - timedelta(days=10)).isoformat(),
            "title": "Weekend reset",
            "content": "A quieter weekend. Went for a long walk, spent time with friends. Felt genuinely refreshed by Sunday evening.",
            "mood_tag": 5,
            "tags": "weekend, social, outdoor",
        },
        {
            "entry_date": (today - timedelta(days=3)).isoformat(),
            "title": "Reflecting on the month",
            "content": "Looking back at the data is interesting. I can see the rough patch clearly now. Sleep really does seem to matter for my mood — at least in my own data.",
            "mood_tag": 4,
            "tags": "reflection, patterns",
        },
    ]

    return entries
