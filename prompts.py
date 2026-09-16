"""
Gemini API prompts for MindReflect AI.

SAFETY: All prompts enforce the non-diagnostic, wellness-reflection-only constraint.
"""

# ──────────────────────────────────────────────
# System instruction
# ──────────────────────────────────────────────

SYSTEM_INSTRUCTION = """You are MindReflect — a mental wellness reflection assistant embedded in a private journaling application.

Your purpose:
- Help users understand observable patterns in their self-reported wellness data.
- Summarize statistical trends using clear, non-clinical language.
- Suggest reflection questions to help users explore their own experiences.
- Encourage consistency in tracking and self-awareness.

Strict boundaries you must NEVER cross:
- Never diagnose any psychiatric or medical condition.
- Never use clinical diagnostic labels (depression, anxiety disorder, ADHD, bipolar disorder, BPD, PTSD, etc.).
- Never imply the user has or may have a mental health disorder.
- Never assign clinical risk scores or severity ratings.
- Never prescribe or recommend medications.
- Never replace or simulate professional therapy or clinical assessment.
- Never make causal claims — only describe observed correlations in the user's own data.
- Never make definitive psychological claims.

Language guidelines:
- Use: "Your mood has been lower than your recent average."
- Use: "Stress appears to have remained elevated across several recent entries."
- Use: "Lower-sleep days have tended to coincide with lower mood in your data."
- Avoid: "You are depressed." / "You have anxiety." / "This suggests a disorder."
- Use neutral, warm, non-judgmental language.
- When persistent difficulties appear, gently suggest: "You might find it useful to speak with a qualified professional."
- Always note that insights are based on self-reported data and statistical patterns.

If the user mentions self-harm, suicidal thoughts, or immediate danger:
- Do NOT attempt to provide therapy or crisis intervention.
- Clearly direct the user to emergency services and appropriate crisis-support resources.
- State that MindReflect cannot provide emergency assistance.
"""


# ──────────────────────────────────────────────
# Prompt builders
# ──────────────────────────────────────────────

def weekly_reflection_prompt(summary: dict, patterns: list) -> str:
    """Build a weekly reflection prompt from statistics and detected patterns."""
    patterns_text = ""
    if patterns:
        patterns_text = "\n\nDetected statistical patterns in this period:\n"
        for p in patterns[:5]:  # Limit to 5 to avoid token excess
            patterns_text += (
                f"- {p.get('pattern_name', 'Pattern')}: "
                f"{p.get('description', '')} "
                f"[Confidence: {p.get('confidence', 'low')}, "
                f"Data points: {p.get('data_points', 0)}]\n"
            )

    recent = summary.get("recent_averages", {})
    baseline = summary.get("baseline_averages_30d", {})
    period = summary.get("period_days", 7)
    checkins = summary.get("checkins_in_period", 0)
    mood_trend = summary.get("mood_trend_direction", "stable")
    stress_trend = summary.get("stress_trend_direction", "stable")

    return f"""The user has requested a wellness reflection for the past {period} days.
They completed {checkins} check-ins during this period.

Recent averages (past {period} days):
{_format_averages(recent)}

Personal baseline (30-day averages):
{_format_averages(baseline)}

Mood trend direction: {mood_trend}
Stress trend direction: {stress_trend}
{patterns_text}

Please provide a thoughtful wellness reflection with these sections:

1. **What I noticed** — Briefly describe the key trends from the data above, comparing recent values to the personal baseline where relevant. Keep it factual and observational.

2. **Possible connections** — If the data shows any associations (e.g., sleep and mood, stress and energy), describe them as observations only. Clearly note that these are correlations, not causes.

3. **Reflection questions** — Offer 2–3 open-ended questions the user can reflect on. These should relate to what the data showed.

4. **A gentle next step** — One non-clinical, practical suggestion related to the patterns observed (e.g., track one more week, experiment with consistent sleep times, try noting what was different on higher-mood days).

Important: Base your response only on the data provided. Do not diagnose or imply any mental health condition. Use warm, supportive language."""


def monthly_reflection_prompt(summary: dict, patterns: list) -> str:
    """Build a monthly reflection prompt."""
    patterns_text = ""
    if patterns:
        patterns_text = "\n\nStatistical patterns observed:\n"
        for p in patterns[:6]:
            patterns_text += (
                f"- {p.get('pattern_name')}: {p.get('description')} "
                f"[{p.get('confidence')} confidence]\n"
            )

    recent = summary.get("recent_averages", {})
    baseline = summary.get("baseline_averages_30d", {})

    return f"""The user has requested a monthly wellness summary.

30-day averages:
{_format_averages(recent)}

Overall baseline averages:
{_format_averages(baseline)}
{patterns_text}

Please provide a monthly wellness summary covering:

1. **Month in Review** — A brief, data-grounded summary of how this month compared to the user's baseline. Note any trends that persisted or changed.

2. **Notable Observations** — 2–3 specific, data-supported observations. For example: average sleep, stress variation, energy patterns. All framed as observations of the logged data.

3. **Reflection prompts** — 2–3 questions to help the user reflect on what happened this month.

4. **Looking ahead** — One gentle, practical suggestion for the coming period.

Important: Only use the statistics provided. Do not diagnose. Do not label any pattern as a medical condition. Frame everything as personal wellness observations."""


def journal_reflection_prompt(entry_titles: list, entry_count: int,
                               summary: dict) -> str:
    """
    Build a prompt for reflecting on journal entries.
    Only titles are sent — full content is NEVER sent to the AI.
    """
    titles_text = ""
    if entry_titles:
        titles_text = "Journal entry titles the user chose to share (content is private):\n"
        titles_text += "\n".join(f"- {t}" for t in entry_titles[:10])

    recent = summary.get("recent_averages", {})

    return f"""The user would like some help reflecting on a recent period of journaling.

They have written {entry_count} journal entries.
{titles_text}

Their recent wellness averages:
{_format_averages(recent)}

Please offer:
1. **Reflection prompts** — 3–4 open, exploratory questions based on their wellness data and the themes suggested by their journal titles. These questions should help the user explore their own experiences, not interpret them for the user.
2. **A supportive observation** — One gentle, non-judgmental observation about what this period may have felt like, based only on the data provided.

Important: Do not interpret the journal titles as symptoms. Do not diagnose. Do not make assumptions about the user's mental health. Treat the titles as neutral topic hints only."""


def pattern_explanation_prompt(pattern: dict, baseline: dict) -> str:
    """Build a prompt to explain a single detected pattern in plain language."""
    return f"""Explain the following wellness observation to a non-technical user in 2–3 simple sentences.

Pattern: {pattern.get('pattern_name', 'Pattern')}
Description: {pattern.get('description', '')}
Evidence: {pattern.get('evidence', '')}
Confidence: {pattern.get('confidence', 'low')}
Data points: {pattern.get('data_points', 0)}

User's personal baseline:
{_format_averages(baseline)}

Instructions:
- Use simple, clear language a non-technical person will understand.
- Frame this as an observation about their logged data, not a diagnosis.
- End with one question the user might find useful to reflect on.
- Keep the total response under 80 words."""


def safety_check_prompt(text_excerpt: str) -> str:
    """
    Prompt used if a reflection or journal entry triggers safety keywords.
    The AI should respond ONLY with a safety message — no analysis.
    """
    return f"""A user has written text that may contain expressions of distress.

Excerpt (for context only — do not analyse or interpret):
"{text_excerpt[:200]}"

Respond ONLY with the following safety message, word for word:
---
It sounds like you may be going through a very difficult time. MindReflect is a wellness reflection tool and is not able to provide crisis support or emergency assistance.

If you are in immediate danger, please call your local emergency services (e.g. 911, 999, or 112).

In the US, you can call or text 988 (Suicide & Crisis Lifeline) for free, confidential support.
Internationally, https://www.iasp.info/resources/Crisis_Centres/ lists crisis centres by country.

Please reach out to someone you trust or a qualified professional. You deserve real support.
---"""


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _format_averages(averages: dict) -> str:
    """Format an averages dict as readable text lines."""
    if not averages:
        return "  No data available."
    labels = {
        "mood": "Mood",
        "stress": "Stress",
        "sleep_hours": "Sleep duration (hours)",
        "sleep_quality": "Sleep quality",
        "energy": "Energy",
        "anxiety": "Anxiety/tension",
    }
    lines = []
    for key, label in labels.items():
        if key in averages:
            val = averages[key]
            suffix = "/5" if key not in ("sleep_hours",) else "h"
            lines.append(f"  {label}: {val}{suffix}")
    return "\n".join(lines) if lines else "  No data available."
