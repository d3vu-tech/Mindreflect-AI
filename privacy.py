"""
Privacy utilities for MindReflect AI.
Provides safety keyword detection and consent management helpers.
"""

import re
from typing import List, Tuple

# ──────────────────────────────────────────────
# Safety keyword detection
# ──────────────────────────────────────────────

# Patterns that may indicate the user is in severe distress.
# Used to trigger a safety message ONLY — not a diagnosis.
_SAFETY_PATTERNS = [
    r"\bsuicid\w*\b",
    r"\bself[-\s]?harm\w*\b",
    r"\bkill\s+(my)?self\b",
    r"\bwant\s+to\s+die\b",
    r"\bend\s+my\s+life\b",
    r"\bself[-\s]?injur\w*\b",
    r"\bcutting\s+myself\b",
    r"\boverdos\w*\b",
    r"\bno\s+reason\s+to\s+live\b",
    r"\bcan'?t\s+go\s+on\b",
]

_SAFETY_RE = re.compile("|".join(_SAFETY_PATTERNS), re.IGNORECASE)


def contains_safety_keywords(text: str) -> bool:
    """Return True if the text may contain crisis-level language."""
    if not text:
        return False
    return bool(_SAFETY_RE.search(text))


SAFETY_MESSAGE = """
---
### 🆘 If you are in immediate danger

Please reach out for support right away:

- **Emergency services:** Call your local emergency number (e.g. 911, 999, 112)
- **Crisis text line:** Text HOME to 741741 (US) or check your country's equivalent
- **National Suicide Prevention Lifeline (US):** Call or text **988**
- **International Association for Suicide Prevention:** https://www.iasp.info/resources/Crisis_Centres/
- **Talk to someone you trust** — a friend, family member, or colleague

---
MindReflect AI is a wellness reflection tool and cannot provide emergency assistance.
You deserve real support from a qualified professional.
---
"""


# ──────────────────────────────────────────────
# Consent / permission helpers
# ──────────────────────────────────────────────

DEFAULT_PERMISSIONS = {
    "mood_trends": False,
    "stress_trends": False,
    "sleep_data": False,
    "energy_data": False,
    "behavioral_patterns": False,
    "weekly_reports": False,
    "monthly_reports": False,
    "journal_entries": False,
}

PERMISSION_LABELS = {
    "mood_trends": "Mood Trends",
    "stress_trends": "Stress Trends",
    "sleep_data": "Sleep Data",
    "energy_data": "Energy Data",
    "behavioral_patterns": "Behavioral Patterns",
    "weekly_reports": "Weekly Reports",
    "monthly_reports": "Monthly Reports",
    "journal_entries": "Selected Journal Entries",
}


def describe_permissions(permissions_dict: dict) -> List[str]:
    """Return a human-readable list of enabled permissions."""
    return [
        PERMISSION_LABELS.get(k, k)
        for k, v in permissions_dict.items()
        if v
    ]


# ──────────────────────────────────────────────
# Privacy notices (shown in UI)
# ──────────────────────────────────────────────

PRIVACY_NOTICE = """
**MindReflect AI — Data Handling Summary**

- All data is stored locally on your device in a SQLite database.
- Journal entries are encrypted at rest using your account password.
- Nothing is shared automatically. Sharing requires explicit opt-in.
- When you use AI Reflection features, selected summary statistics
  (not your full journal) are sent to the Google Gemini API.
- Gemini API data handling is subject to Google's privacy policy.
- You can export or permanently delete your data at any time.
- This is a prototype application, not a certified healthcare service.
"""

DISCLAIMER = (
    "MindReflect AI is a wellness reflection and behavioral pattern awareness tool. "
    "Its insights are based on self-reported information and statistical patterns. "
    "It does not diagnose mental-health conditions, provide medical advice, "
    "or replace a qualified healthcare professional."
)
