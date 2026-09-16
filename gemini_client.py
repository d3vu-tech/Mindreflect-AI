"""
Google Gemini API client for MindReflect AI.
Uses the google-genai SDK (v2) with Gemini 2.5 Flash.

API key is loaded from Streamlit secrets or environment variable.
Never hard-coded.
"""

import os
from typing import Optional, Dict, List
from ai.prompts import (
    SYSTEM_INSTRUCTION,
    weekly_reflection_prompt,
    monthly_reflection_prompt,
    journal_reflection_prompt,
    pattern_explanation_prompt,
)

# ──────────────────────────────────────────────
# SDK import with graceful fallback
# ──────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

_client: Optional[object] = None


def _get_api_key() -> Optional[str]:
    """Load the Gemini API key from secrets or environment. Never hard-coded."""
    # 1. Environment variable
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key

    # 2. Streamlit secrets
    try:
        import streamlit as st
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass

    return None


def _get_client():
    """Return a configured Gemini client, creating it if necessary."""
    global _client
    if _client is not None:
        return _client

    if not _GENAI_AVAILABLE:
        return None

    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        _client = genai.Client(api_key=api_key)
        return _client
    except Exception:
        return None


def is_ai_available() -> bool:
    """Return True if the Gemini client can be configured."""
    return _GENAI_AVAILABLE and bool(_get_api_key())


def _call_gemini(prompt: str, max_tokens: int = 1024) -> Optional[str]:
    """
    Call Gemini 2.5 Flash and return the text response.
    Returns None on any failure — errors are never surfaced to the user.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=max_tokens,
                temperature=0.7,
            ),
        )
        if response and response.text:
            return response.text.strip()
        return None
    except Exception:
        # Do not surface raw exception details (may contain key material)
        return None


# ──────────────────────────────────────────────
# Public AI feature functions
# ──────────────────────────────────────────────

def get_weekly_reflection(summary: Dict, patterns: List[Dict]) -> Optional[str]:
    """
    Generate a weekly wellness reflection narrative.
    Only aggregate statistics are sent — no raw journal content.
    """
    prompt = weekly_reflection_prompt(summary, patterns)
    return _call_gemini(prompt, max_tokens=800)


def get_monthly_reflection(summary: Dict, patterns: List[Dict]) -> Optional[str]:
    """Generate a monthly wellness reflection narrative."""
    prompt = monthly_reflection_prompt(summary, patterns)
    return _call_gemini(prompt, max_tokens=900)


def get_journal_reflection(entry_titles: List[str], entry_count: int,
                            summary: Dict) -> Optional[str]:
    """
    Reflect on journal entries using titles only (never full content).
    The user must explicitly request this — no automatic processing.
    """
    prompt = journal_reflection_prompt(entry_titles, entry_count, summary)
    return _call_gemini(prompt, max_tokens=600)


def explain_pattern(pattern: Dict, baseline: Dict) -> Optional[str]:
    """Explain a single behavioral pattern in plain language."""
    prompt = pattern_explanation_prompt(pattern, baseline)
    return _call_gemini(prompt, max_tokens=200)


def get_safety_response(text_excerpt: str) -> str:
    """
    Return a safety-focused response for distress-related content.
    Always returns a hardcoded safety message — never an AI diagnosis.
    """
    from security.privacy import SAFETY_MESSAGE
    return SAFETY_MESSAGE


def get_ai_status() -> Dict:
    """Return a status dict for the AI feature (shown in settings/UI)."""
    has_key = bool(_get_api_key())
    has_sdk = _GENAI_AVAILABLE
    return {
        "sdk_available": has_sdk,
        "api_key_configured": has_key,
        "ai_ready": has_sdk and has_key,
        "model": "gemini-3.6-flash",
        "missing_sdk": not has_sdk,
        "missing_key": not has_key,
    }
