"""
MindReflect AI — Mental Wellness Reflection & Behavioral Pattern Awareness
Main Streamlit application entry point.

Run: streamlit run app.py

IMPORTANT DISCLAIMER:
MindReflect AI is a wellness reflection and behavioral pattern awareness tool.
Its insights are based on self-reported information and statistical patterns.
It does not diagnose mental-health conditions, provide medical advice,
or replace a qualified healthcare professional.
"""

import sys
import os

# Add project root to path so all modules resolve correctly
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime, timedelta
import json

# ── Internal modules ──────────────────────────────────────────────────────────
from database.db import (
    init_database, create_user, get_user_by_username, get_user_by_id,
    upsert_checkin, get_checkin_for_date, get_checkins, get_all_checkins,
    delete_demo_checkins,
    create_journal_entry, update_journal_entry, get_journal_entries,
    get_journal_entry_by_id, delete_journal_entry, delete_demo_journal_entries,
    delete_journal_all,
    save_pattern_insights, get_pattern_insights,
    create_sharing_token, get_sharing_tokens, get_all_sharing_tokens,
    revoke_sharing_token, get_sharing_audit_log,
    export_user_data, delete_all_user_data,
    update_user_settings, update_password_hash,
)
from security.encryption import (
    hash_password, verify_password, encrypt_journal_content,
    decrypt_journal_content, generate_sharing_token as gen_token,
    is_crypto_available, is_safe_username, sanitize_text,
)
from security.privacy import (
    contains_safety_keywords, SAFETY_MESSAGE, DISCLAIMER, PRIVACY_NOTICE,
    DEFAULT_PERMISSIONS, PERMISSION_LABELS, describe_permissions,
)
from analytics.trends import (
    checkins_to_df, filter_by_days, compute_baseline,
    compute_recent_average, weekly_summary, monthly_summary, build_ai_summary,
)
from analytics.patterns import run_all_patterns
from analytics.statistics import (
    compare_to_baseline, streak_stats, completion_rate,
    behavioral_summary, top_reflection_words,
)
from ai.gemini_client import (
    is_ai_available, get_weekly_reflection, get_monthly_reflection,
    get_journal_reflection, explain_pattern, get_ai_status,
)
from data.demo_data import generate_demo_checkins, generate_demo_journal_entries
from reports.pdf_report import generate_wellness_report, is_pdf_available
from utils.helpers import (
    mood_label, stress_label, energy_label, sleep_quality_label,
    today_str, format_date, format_date_short, delta_arrow, confidence_badge,
    export_to_json, checkins_to_csv_string,
    CHART_LAYOUT, YAXIS_STYLE, COLOR_MOOD, COLOR_STRESS, COLOR_SLEEP, COLOR_ENERGY,
    COLOR_ANXIETY, COLOR_BASELINE,
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="MindReflect AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE INIT
# ══════════════════════════════════════════════════════════════════════════════

init_database()

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _init_session():
    defaults = {
        "authenticated": False,
        "user_id": None,
        "username": None,
        "display_name": None,
        "password": None,   # held in session for journal decryption (not persisted)
        "page": "🏠 Home",
        "demo_loaded": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()


def _login(user_id: int, username: str, display_name: str, password: str):
    st.session_state.authenticated = True
    st.session_state.user_id = user_id
    st.session_state.username = username
    st.session_state.display_name = display_name
    st.session_state.password = password


def _logout():
    for k in ["authenticated", "user_id", "username", "display_name", "password", "demo_loaded"]:
        st.session_state[k] = None if k not in ("authenticated", "demo_loaded") else False
    st.rerun()


def _uid() -> int:
    return st.session_state.user_id


def _upass() -> str:
    return st.session_state.password or ""

# ══════════════════════════════════════════════════════════════════════════════
# CHART HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _empty_chart(msg: str, height: int = 180) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=13, color="#6b7280"),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=20, b=10), height=height,
    )
    return fig


def _line_chart(df: pd.DataFrame, col: str, title: str, color: str,
                y_range=None, baseline_val=None) -> go.Figure:
    fig = go.Figure()
    valid = df[["date", col]].dropna() if not df.empty else pd.DataFrame()
    if valid.empty:
        return _empty_chart(f"No {col} data available yet")

    fig.add_trace(go.Scatter(
        x=valid["date"], y=valid[col],
        mode="lines+markers", name=title,
        line=dict(color=color, width=2.5),
        marker=dict(size=6, color=color),
        hovertemplate="%{x|%b %d}<br>" + title + ": %{y}<extra></extra>",
    ))
    if len(valid) >= 5:
        roll = valid[col].rolling(7, min_periods=3).mean()
        fig.add_trace(go.Scatter(
            x=valid["date"], y=roll,
            mode="lines", name="7-day avg",
            line=dict(color=color, width=1.5, dash="dot"),
            hoverinfo="skip",
        ))
    if baseline_val is not None:
        fig.add_hline(
            y=baseline_val, line_dash="dash", line_color=COLOR_BASELINE,
            annotation_text=f"Baseline {baseline_val:.1f}",
            annotation_position="bottom right",
        )
    layout = dict(title=title, **CHART_LAYOUT)
    # Merge YAXIS_STYLE with any caller-supplied range so grid lines are preserved
    layout["yaxis"] = dict(**YAXIS_STYLE, **(dict(range=y_range) if y_range else {}))
    fig.update_layout(**layout)
    return fig


def _scatter_chart(df: pd.DataFrame, x_col: str, y_col: str,
                   x_label: str, y_label: str, title: str, color: str) -> go.Figure:
    if df.empty:
        return _empty_chart("No data available")
    valid = df[[x_col, y_col]].dropna()
    if len(valid) < 5:
        return _empty_chart(f"Not enough data yet\n(need at least 5 paired entries)")
    fig = px.scatter(
        valid, x=x_col, y=y_col,
        labels={x_col: x_label, y_col: y_label},
        color_discrete_sequence=[color],
        opacity=0.65,
        trendline="ols" if len(valid) >= 10 else None,
    )
    fig.update_layout(title=title, yaxis=dict(**YAXIS_STYLE), **CHART_LAYOUT)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_auth():
    st.markdown("## 🧠 MindReflect AI")
    st.markdown(
        "_A private wellness reflection and behavioral pattern awareness journal._"
    )
    st.info(DISCLAIMER, icon="ℹ️")
    st.divider()

    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter your username and password.")
                return
            user = get_user_by_username(username.strip().lower())
            if user and verify_password(password, user["password_hash"]):
                _login(user["id"], user["username"],
                       user.get("display_name") or user["username"], password)
                st.rerun()
            else:
                st.error("Username or password is incorrect.")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("Choose a username",
                                          help="3–50 characters: letters, numbers, _ - .")
            new_display = st.text_input("Display name (optional)")
            new_email = st.text_input("Email (optional)")
            new_pw = st.text_input("Password", type="password")
            new_pw2 = st.text_input("Confirm password", type="password")
            agree = st.checkbox(
                "I understand this is a wellness reflection tool, not a medical service."
            )
            reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

        if reg_submitted:
            err = []
            if not new_username:
                err.append("Username is required.")
            elif not is_safe_username(new_username.strip()):
                err.append("Username must be 3–50 characters using letters, numbers, _ - . only.")
            if not new_pw:
                err.append("Password is required.")
            elif len(new_pw) < 6:
                err.append("Password must be at least 6 characters.")
            elif new_pw != new_pw2:
                err.append("Passwords do not match.")
            if not agree:
                err.append("Please acknowledge the tool's purpose before continuing.")

            if err:
                for e in err:
                    st.error(e)
            else:
                uid = create_user(
                    username=new_username.strip().lower(),
                    password_hash=hash_password(new_pw),
                    email=new_email.strip() if new_email else "",
                    display_name=new_display.strip() if new_display else new_username.strip(),
                )
                if uid is None:
                    st.error("That username is already taken. Please choose another.")
                else:
                    st.success("Account created! You can now sign in.")


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════

PAGES = [
    "🏠 Home",
    "📝 Daily Check-In",
    "📔 Private Journal",
    "📊 Wellness Trends",
    "🔎 Behavioral Patterns",
    "🤖 AI Reflection",
    "📄 Reports",
    "👩‍⚕️ Therapist Sharing",
    "🔐 Privacy & Consent",
    "⚙️ Settings",
]


def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 🧠 MindReflect AI")
        st.markdown(f"_Hello, **{st.session_state.display_name}** 👋_")
        st.divider()

        for page in PAGES:
            if st.button(page, key=f"nav_{page}", use_container_width=True):
                st.session_state.page = page
                st.rerun()

        st.divider()

        # Demo data button
        if not st.session_state.demo_loaded:
            if st.button("📦 Load Demo Data", use_container_width=True,
                         help="Load synthetic example data to explore the app"):
                _load_demo_data()
        else:
            if st.button("🗑️ Remove Demo Data", use_container_width=True):
                delete_demo_checkins(_uid())
                delete_demo_journal_entries(_uid())
                st.session_state.demo_loaded = False
                st.success("Demo data removed.")
                st.rerun()

        st.divider()
        if st.button("Sign Out", use_container_width=True):
            _logout()

        st.divider()
        st.caption(DISCLAIMER[:160] + "…")


def _load_demo_data():
    uid = _uid()
    checkins = generate_demo_checkins(uid)
    for c in checkins:
        upsert_checkin(uid, c["entry_date"], c)

    journals = generate_demo_journal_entries(uid)
    for j in journals:
        encrypted = encrypt_journal_content(j["content"], "demo_password")
        create_journal_entry(
            user_id=uid,
            entry_date=j["entry_date"],
            title=j["title"],
            encrypted_content=encrypted,
            mood_tag=j.get("mood_tag"),
            tags=j.get("tags", ""),
            is_demo=True,
        )
    st.session_state.demo_loaded = True
    st.success("✅ Demo data loaded! Explore the app with 75 days of synthetic data.")
    st.info("⚠️ DEMO DATA — Synthetic data for demonstration only.", icon="ℹ️")
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_home():
    st.header("🏠 Home")

    if st.session_state.demo_loaded:
        st.warning("⚠️ DEMO DATA — Synthetic data for demonstration only.", icon="⚠️")

    today = today_str()
    checkin_today = get_checkin_for_date(_uid(), today)

    # ── Today's status ──
    st.subheader("Today's Status")
    if not checkin_today:
        st.info(
            "✨ **Take a moment to check in with yourself.**\n\n"
            "Your first check-in starts your personal wellness timeline.",
            icon="💬",
        )
        if st.button("▶️ Start Today's Check-In", type="primary"):
            st.session_state.page = "📝 Daily Check-In"
            st.rerun()
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mood", mood_label(checkin_today.get("mood")))
        c2.metric("Stress", stress_label(checkin_today.get("stress")))
        c3.metric("Sleep", f"{checkin_today.get('sleep_hours', '—')}h")
        c4.metric("Energy", energy_label(checkin_today.get("energy")))
        st.success("✅ Today's check-in is complete.")

    st.divider()

    # ── Recent overview (7 days) ──
    all_checkins = get_all_checkins(_uid())
    df = checkins_to_df(all_checkins)

    st.subheader("Recent Overview — Last 7 Days")
    if len(all_checkins) < 2:
        st.info(
            "Keep checking in. After several entries, you'll start seeing personal patterns.",
            icon="📈",
        )
    else:
        recent7 = compute_recent_average(df, days=7)
        baseline30 = compute_baseline(df, window_days=30)
        streaks = streak_stats(df)
        comp_rate = completion_rate(df, days=30)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "Avg Mood (7d)",
            f"{recent7.get('mood', '—')}/5" if recent7.get('mood') else "—",
        )
        m2.metric(
            "Avg Stress (7d)",
            f"{recent7.get('stress', '—')}/5" if recent7.get('stress') else "—",
        )
        m3.metric(
            "Avg Sleep (7d)",
            f"{recent7.get('sleep_hours', '—')}h" if recent7.get('sleep_hours') else "—",
        )
        m4.metric(
            "Avg Energy (7d)",
            f"{recent7.get('energy', '—')}/5" if recent7.get('energy') else "—",
        )

        s1, s2, s3 = st.columns(3)
        s1.metric("Check-in Streak", f"{streaks['current_streak']} days")
        s2.metric("Longest Streak", f"{streaks['longest_streak']} days")
        s3.metric("30-day Completion", f"{int(comp_rate * 100)}%")

        # ── Recent pattern preview ──
        st.divider()
        st.subheader("Recent Patterns")

        if len(all_checkins) < 7:
            st.info(
                "Keep checking in for a few more days before looking for meaningful patterns.",
                icon="🔎",
            )
        else:
            patterns = run_all_patterns(all_checkins)
            if patterns:
                for p in patterns[:2]:
                    with st.container(border=True):
                        st.markdown(f"**{p['pattern_name']}**")
                        st.write(p["description"])
                        st.caption(
                            f"Confidence: {confidence_badge(p['confidence'])} | "
                            f"Data points: {p['data_points']}"
                        )
                st.caption(
                    "These are observational patterns from your logged data, "
                    "not medical conclusions. [View all →](#)"
                )
                if st.button("View All Patterns →"):
                    st.session_state.page = "🔎 Behavioral Patterns"
                    st.rerun()
            else:
                # Baseline comparison instead
                if baseline30 and recent7:
                    comp = compare_to_baseline(recent7, baseline30)
                    mood_comp = comp.get("mood", {})
                    stress_comp = comp.get("stress", {})
                    if mood_comp:
                        d = mood_comp["delta"]
                        direction = "above" if d > 0 else "below"
                        st.info(
                            f"Your average mood over the last 7 days was "
                            f"**{mood_comp['recent']}/5** compared with your "
                            f"recent baseline of **{mood_comp['baseline']}/5** "
                            f"({direction} baseline by {abs(d):.1f}).",
                            icon="📊",
                        )
                else:
                    st.info("No notable patterns detected yet. Keep logging!")


# ══════════════════════════════════════════════════════════════════════════════
# DAILY CHECK-IN PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_checkin():
    st.header("📝 Daily Check-In")

    today = today_str()
    existing = get_checkin_for_date(_uid(), today)  # dict or None

    # ── Show today's summary when already checked in (and not editing) ──
    if existing and "edit_checkin" not in st.session_state:
        st.success(f"✅ You've already checked in today ({format_date(today)}).")
        col1, col2 = st.columns(2)
        col1.metric("Mood", mood_label(existing.get("mood")))
        col2.metric("Stress", stress_label(existing.get("stress")))
        c1, c2 = st.columns(2)
        c1.metric("Sleep", f"{existing.get('sleep_hours', '—')}h")
        c2.metric("Energy", energy_label(existing.get("energy")))
        if st.button("✏️ Edit Today's Entry"):
            st.session_state.edit_checkin = True
            st.rerun()
        # Return here — no form is rendered, so no "missing submit button" warning.
        return

    if existing:
        st.info("Editing today's existing check-in.", icon="✏️")

    # ── Safe defaults: use existing values when editing, fresh defaults otherwise ──
    # Using `ex` (always a dict) means every .get() below is safe regardless of
    # whether the user has a previous entry or is filling in for the first time.
    ex = existing if existing is not None else {}

    def _int(key, default):
        """Return existing int value clamped to valid range, or default."""
        v = ex.get(key)
        try:
            return int(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    def _float(key, default):
        """Return existing float value, or default."""
        v = ex.get(key)
        try:
            return float(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    def _bool(key):
        """Return existing boolean behavioral flag, or False."""
        v = ex.get(key)
        return bool(v) if v is not None else False

    # ── Form ──
    with st.form("checkin_form"):
        st.markdown("### How are you feeling today?")
        st.caption(f"*{format_date(today)}*")

        # ── Core metrics ──
        st.subheader("Core Wellbeing")
        col_a, col_b = st.columns(2)
        with col_a:
            mood = st.select_slider(
                "Mood",
                options=[1, 2, 3, 4, 5],
                value=_int("mood", 3),
                format_func=lambda x: {
                    1: "1 — Very Low", 2: "2 — Low", 3: "3 — Neutral",
                    4: "4 — Good", 5: "5 — Very Good"
                }[x],
            )
            stress = st.select_slider(
                "Stress",
                options=[1, 2, 3, 4, 5],
                value=_int("stress", 2),
                format_func=lambda x: {
                    1: "1 — Very Low", 2: "2 — Low", 3: "3 — Moderate",
                    4: "4 — High", 5: "5 — Very High"
                }[x],
            )
        with col_b:
            energy = st.select_slider(
                "Energy",
                options=[1, 2, 3, 4, 5],
                value=_int("energy", 3),
                format_func=lambda x: {
                    1: "1 — Very Low", 2: "2 — Low", 3: "3 — Moderate",
                    4: "4 — Good", 5: "5 — High"
                }[x],
            )
            anxiety = st.select_slider(
                "Anxiety / Tension (optional)",
                options=[0, 1, 2, 3, 4, 5],
                value=_int("anxiety", 0),
                format_func=lambda x: "— Skip" if x == 0 else {
                    1: "1 — Very Low", 2: "2 — Low", 3: "3 — Moderate",
                    4: "4 — High", 5: "5 — Very High"
                }[x],
            )

        # ── Sleep ──
        st.subheader("Sleep")
        sc1, sc2 = st.columns(2)
        with sc1:
            sleep_hours = st.number_input(
                "Hours slept",
                min_value=0.0, max_value=24.0, step=0.5,
                value=_float("sleep_hours", 7.0),
            )
        with sc2:
            sleep_quality = st.select_slider(
                "Sleep quality",
                options=[1, 2, 3, 4, 5],
                value=_int("sleep_quality", 3),
                format_func=lambda x: {
                    1: "1 — Very Poor", 2: "2 — Poor", 3: "3 — Fair",
                    4: "4 — Good", 5: "5 — Excellent"
                }[x],
            )

        # ── Behavioral factors ──
        st.subheader("Today's Activities (optional)")
        st.caption("Check anything that applied to your day.")
        bc1, bc2, bc3 = st.columns(3)
        exercise      = bc1.checkbox("🏃 Exercise",              value=_bool("exercise"))
        social        = bc1.checkbox("🤝 Social interaction",    value=_bool("social_interaction"))
        outdoor       = bc2.checkbox("🌿 Outdoor time",          value=_bool("outdoor_time"))
        relaxation    = bc2.checkbox("🧘 Relaxation / meditation", value=_bool("relaxation"))
        regular_meals = bc3.checkbox("🍽️ Regular meals",         value=_bool("regular_meals"))

        workload = st.select_slider(
            "Study / work load today (optional)",
            options=[0, 1, 2, 3, 4, 5],
            value=_int("workload", 0),
            format_func=lambda x: "— Skip" if x == 0 else str(x),
        )
        screen_time = st.number_input(
            "Screen time (hours, optional)",
            min_value=0.0, max_value=24.0, step=0.5,
            value=_float("screen_time", 0.0),
        )

        # ── Reflection ──
        st.subheader("Reflection (optional)")
        reflection_text = st.text_area(
            "What influenced your day today?",
            value=ex.get("reflection") or "",
            max_chars=2000,
            placeholder="Write freely. This is for your personal reflection only.",
        )

        submitted = st.form_submit_button(
            "💾 Save Check-In", type="primary", use_container_width=True
        )

    # ── Handle submission (outside form block, submitted is still in scope) ──
    if submitted:
        # Safety check on free-text reflection
        if reflection_text and contains_safety_keywords(reflection_text):
            st.warning(SAFETY_MESSAGE)

        data = {
            "mood": int(mood),
            "stress": int(stress),
            "sleep_hours": float(sleep_hours),
            "sleep_quality": int(sleep_quality),
            "energy": int(energy),
            "anxiety": int(anxiety) if anxiety > 0 else None,
            "exercise": exercise,
            "social_interaction": social,
            "outdoor_time": outdoor,
            "relaxation": relaxation,
            "regular_meals": regular_meals,
            "workload": int(workload) if workload > 0 else None,
            "screen_time": float(screen_time) if screen_time > 0 else None,
            "reflection": sanitize_text(reflection_text) if reflection_text else None,
        }

        upsert_checkin(_uid(), today, data)

        # Clear edit flag so the summary view is shown again after saving
        st.session_state.pop("edit_checkin", None)

        st.success("✅ Check-in saved!")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE JOURNAL PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_journal():
    st.header("📔 Private Journal")
    st.info(
        "🔒 **Private Journal** — Your entries are not shared automatically. "
        "Journal content is encrypted at rest.",
        icon="🔒",
    )

    if st.session_state.demo_loaded:
        st.warning("Some entries are synthetic demo data.", icon="⚠️")

    tab_new, tab_view = st.tabs(["✍️ New Entry", "📚 View Entries"])

    with tab_new:
        with st.form("journal_form"):
            j_date = st.date_input("Date", value=date.today())
            j_title = st.text_input("Title", max_chars=200,
                                     placeholder="Give your entry a title…")
            j_content = st.text_area(
                "Your thoughts",
                height=250,
                max_chars=10000,
                placeholder="Write freely. This is your private space.",
            )
            j_mood = st.select_slider(
                "Mood tag (optional)",
                options=[0, 1, 2, 3, 4, 5],
                value=0,
                format_func=lambda x: "— No tag" if x == 0 else {
                    1: "😔 Very Low", 2: "😕 Low", 3: "😐 Neutral",
                    4: "🙂 Good", 5: "😊 Very Good"
                }[x],
            )
            j_tags = st.text_input(
                "Tags (optional, comma-separated)",
                placeholder="e.g. stress, work, family",
                max_chars=200,
            )
            j_submit = st.form_submit_button("💾 Save Entry", type="primary",
                                              use_container_width=True)

        if j_submit:
            if not j_title.strip():
                st.error("Please add a title to your entry.")
            elif not j_content.strip():
                st.error("Please write something in your entry.")
            else:
                if contains_safety_keywords(j_content):
                    st.warning(SAFETY_MESSAGE)

                encrypted = encrypt_journal_content(
                    sanitize_text(j_content), _upass()
                )
                create_journal_entry(
                    user_id=_uid(),
                    entry_date=j_date.isoformat(),
                    title=sanitize_text(j_title, 200),
                    encrypted_content=encrypted,
                    mood_tag=int(j_mood) if j_mood > 0 else None,
                    tags=sanitize_text(j_tags, 200),
                )
                st.success("✅ Journal entry saved.")
                st.rerun()

    with tab_view:
        entries = get_journal_entries(_uid())
        if not entries:
            st.info(
                "Your journal is empty. Your first entry starts your story.",
                icon="📝",
            )
            return

        # Decrypt and display
        for entry in entries:
            demo_badge = " 🔬 *Demo*" if entry.get("is_demo") else ""
            with st.expander(
                f"📅 {format_date_short(entry['entry_date'])} — {entry['title']}{demo_badge}"
            ):
                # Decrypt
                content = decrypt_journal_content(
                    entry["encrypted_content"],
                    "demo_password" if entry.get("is_demo") else _upass(),
                )
                if content is None:
                    st.error("⚠️ This entry could not be decrypted. "
                             "If you changed your password, older entries may be unreadable.")
                else:
                    st.write(content)

                meta_cols = st.columns(3)
                if entry.get("mood_tag"):
                    meta_cols[0].caption(f"Mood tag: {mood_label(entry['mood_tag'])}")
                if entry.get("tags"):
                    meta_cols[1].caption(f"Tags: {entry['tags']}")
                meta_cols[2].caption(
                    f"Updated: {format_date_short(entry['updated_at'][:10])}"
                )

                if not entry.get("is_demo"):
                    if st.button("🗑️ Delete", key=f"del_journal_{entry['id']}"):
                        delete_journal_entry(entry["id"], _uid())
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# WELLNESS TRENDS PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_trends():
    st.header("📊 Wellness Trends")

    all_checkins = get_all_checkins(_uid())
    df = checkins_to_df(all_checkins)

    if df.empty:
        st.info(
            "Your first check-in starts your personal wellness timeline. "
            "Come back after a few entries to see your trends.",
            icon="📈",
        )
        return

    # Period selector
    period_options = {"7 days": 7, "30 days": 30, "90 days": 90,
                      "6 months": 180, "1 year": 365}
    period_label = st.selectbox("View period", list(period_options.keys()),
                                 index=1)
    days = period_options[period_label]
    df_period = filter_by_days(df, days)
    baseline = compute_baseline(df, window_days=30)

    if df_period.empty:
        st.info(f"No data for the last {period_label}. "
                f"Try a wider period or continue checking in.")
        return

    tab_main, tab_weekly, tab_monthly, tab_scatter = st.tabs(
        ["📈 Trends", "📅 Weekly", "🗓️ Monthly", "🔍 Comparisons"]
    )

    with tab_main:
        st.plotly_chart(
            _line_chart(df_period, "mood", "Mood", COLOR_MOOD,
                        y_range=[0.5, 5.5], baseline_val=baseline.get("mood")),
            use_container_width=True,
            key="trends_mood_chart",
        )
        st.plotly_chart(
            _line_chart(df_period, "stress", "Stress", COLOR_STRESS,
                        y_range=[0.5, 5.5], baseline_val=baseline.get("stress")),
            use_container_width=True,
            key="trends_stress_chart",
        )

        col1, col2 = st.columns(2)
        with col1:
            # Sleep bar + quality line
            sleep_fig = go.Figure()
            sv = df_period[["date", "sleep_hours"]].dropna()
            if not sv.empty:
                sleep_fig.add_trace(go.Bar(
                    x=sv["date"], y=sv["sleep_hours"], name="Hours slept",
                    marker_color=COLOR_SLEEP, opacity=0.75,
                ))
            sq = df_period[["date", "sleep_quality"]].dropna()
            if not sq.empty:
                sleep_fig.add_trace(go.Scatter(
                    x=sq["date"], y=sq["sleep_quality"], name="Sleep quality",
                    yaxis="y2", line=dict(color="#0ea5e9", width=2),
                    mode="lines+markers",
                ))
            sleep_fig.update_layout(
                title="Sleep",
                yaxis=dict(**YAXIS_STYLE, title="Hours", range=[0, 12]),
                yaxis2=dict(
                    title="Quality", range=[0.5, 5.5],
                    overlaying="y", side="right",
                    **YAXIS_STYLE,
                ),
                **CHART_LAYOUT,
            )
            if not sv.empty:
                st.plotly_chart(sleep_fig, use_container_width=True,
                                key="trends_sleep_chart")
            else:
                st.plotly_chart(_empty_chart("No sleep data available"),
                                use_container_width=True,
                                key="trends_sleep_empty_chart")

        with col2:
            st.plotly_chart(
                _line_chart(df_period, "energy", "Energy", COLOR_ENERGY,
                            y_range=[0.5, 5.5]),
                use_container_width=True,
                key="trends_energy_chart",
            )

        if "anxiety" in df_period.columns and df_period["anxiety"].notna().sum() >= 3:
            st.plotly_chart(
                _line_chart(df_period, "anxiety", "Anxiety / Tension", COLOR_ANXIETY,
                            y_range=[0.5, 5.5]),
                use_container_width=True,
                key="trends_anxiety_chart",
            )

    with tab_weekly:
        wsummary = weekly_summary(df_period)
        if wsummary.empty:
            st.info("Not enough data for weekly summary yet.")
        else:
            fig_w = go.Figure()
            for col, color, label in [
                ("mood", COLOR_MOOD, "Mood"),
                ("stress", COLOR_STRESS, "Stress"),
                ("energy", COLOR_ENERGY, "Energy"),
            ]:
                if col in wsummary.columns:
                    fig_w.add_trace(go.Bar(
                        x=wsummary["week_starting"], y=wsummary[col],
                        name=label, marker_color=color, opacity=0.8,
                    ))
            fig_w.update_layout(
                title="Weekly Averages", barmode="group",
                yaxis=dict(**YAXIS_STYLE, range=[0, 6]),
                **CHART_LAYOUT,
            )
            st.plotly_chart(fig_w, use_container_width=True,
                            key="trends_weekly_chart")
            st.dataframe(wsummary, use_container_width=True, hide_index=True)

    with tab_monthly:
        msummary = monthly_summary(df_period)
        if msummary.empty:
            st.info("Not enough data for monthly summary yet.")
        else:
            fig_m = go.Figure()
            for col, color, label in [
                ("mood", COLOR_MOOD, "Mood"),
                ("stress", COLOR_STRESS, "Stress"),
                ("energy", COLOR_ENERGY, "Energy"),
            ]:
                if col in msummary.columns:
                    fig_m.add_trace(go.Bar(
                        x=msummary["month"], y=msummary[col],
                        name=label, marker_color=color, opacity=0.8,
                    ))
            fig_m.update_layout(
                title="Monthly Averages", barmode="group",
                yaxis=dict(**YAXIS_STYLE, range=[0, 6]),
                **CHART_LAYOUT,
            )
            st.plotly_chart(fig_m, use_container_width=True,
                            key="trends_monthly_chart")
            st.dataframe(msummary, use_container_width=True, hide_index=True)

    with tab_scatter:
        st.subheader("Comparative Views")
        st.caption(
            "These scatter plots show associations between variables in your logged data. "
            "They do not show causation."
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.plotly_chart(
                _scatter_chart(df_period, "sleep_hours", "mood",
                               "Sleep Duration (hrs)", "Mood (1–5)",
                               "Sleep vs Mood", COLOR_MOOD),
                use_container_width=True,
                key="trends_sleep_mood_scatter",
            )
        with col_s2:
            st.plotly_chart(
                _scatter_chart(df_period, "stress", "mood",
                               "Stress (1–5)", "Mood (1–5)",
                               "Stress vs Mood", COLOR_STRESS),
                use_container_width=True,
                key="trends_stress_mood_scatter",
            )

        if "screen_time" in df_period.columns and df_period["screen_time"].notna().sum() >= 5:
            st.plotly_chart(
                _scatter_chart(df_period, "screen_time", "sleep_hours",
                               "Screen Time (hrs)", "Sleep Duration (hrs)",
                               "Screen Time vs Sleep", "#7c5cd8"),
                use_container_width=True,
                key="trends_screen_sleep_scatter",
            )


# ══════════════════════════════════════════════════════════════════════════════
# BEHAVIORAL PATTERNS PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_patterns():
    st.header("🔎 Behavioral Patterns")
    st.info(
        "The patterns below are observational — they describe associations in your "
        "self-reported data. They are **not** clinical diagnoses or medical conclusions.",
        icon="ℹ️",
    )

    all_checkins = get_all_checkins(_uid())

    if len(all_checkins) < 5:
        st.info(
            "Keep checking in for a few more days before looking for meaningful patterns. "
            "At least 5–7 entries are needed for the first observations.",
            icon="🔎",
        )
        return

    df = checkins_to_df(all_checkins)
    baseline = compute_baseline(df, window_days=30)
    patterns = run_all_patterns(all_checkins)

    # Save for report use
    if patterns:
        save_pattern_insights(_uid(), patterns)

    if not patterns:
        st.success(
            "No notable statistical patterns detected in your current data. "
            "Continue logging to build a more complete picture.",
            icon="✅",
        )

    for p in patterns:
        with st.container(border=True):
            conf_color = {"high": "🟢", "medium": "🟡", "low": "🔵"}.get(
                p.get("confidence", "low"), "🔵"
            )
            st.markdown(f"### {p['pattern_name']}")
            st.write(p["description"])

            with st.expander("📋 Evidence & Detail"):
                st.caption(f"**Evidence:** {p['evidence']}")
                st.caption(
                    f"**Confidence:** {conf_color} {p['confidence'].capitalize()} — "
                    f"based on {p['data_points']} logged data points"
                )
                if p.get("time_period_days"):
                    st.caption(f"**Time period:** {p['time_period_days']} days")

                # Baseline context
                metric_map = {
                    "sustained_low_mood": "mood",
                    "sustained_high_stress": "stress",
                    "mood_variability": "mood",
                }
                metric = metric_map.get(p["pattern_type"])
                if metric and metric in baseline:
                    st.caption(f"**Your 30-day baseline {metric}:** {baseline[metric]}/5")

            st.caption(
                "💡 More consistent entries can make this pattern easier to interpret."
            )

    # ── Personal baseline comparison ──
    st.divider()
    st.subheader("📏 Personal Baseline Comparison")
    st.caption(
        "Comparing your recent averages to your personal 30-day baseline — "
        "not to any general population standard."
    )

    recent7 = compute_recent_average(df, days=7)
    comparisons = compare_to_baseline(recent7, baseline)

    if not comparisons:
        st.info("Not enough data yet for baseline comparison.")
    else:
        label_map = {
            "mood": "Mood", "stress": "Stress",
            "sleep_hours": "Sleep (hrs)", "energy": "Energy", "anxiety": "Anxiety",
        }
        cols = st.columns(min(len(comparisons), 4))
        for i, (metric, comp) in enumerate(comparisons.items()):
            col = cols[i % len(cols)]
            delta_str = f"{comp['delta']:+.2f}" if comp["delta"] != 0 else "—"
            col.metric(
                label=label_map.get(metric, metric),
                value=f"{comp['recent']}/5" if metric != "sleep_hours" else f"{comp['recent']}h",
                delta=f"{delta_str} vs baseline",
            )
        st.caption(
            "These are statistical observations from your own data. "
            "They do not indicate any medical condition."
        )


# ══════════════════════════════════════════════════════════════════════════════
# AI REFLECTION PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_ai_reflection():
    st.header("🤖 AI Reflection")
    st.info(
        "The AI reflection assistant uses **aggregate statistics** from your "
        "check-ins to provide wellness observations and reflection prompts. "
        "**Journal content is never sent to the AI automatically.** "
        "The AI does not diagnose any condition.",
        icon="🤖",
    )

    ai_status = get_ai_status()
    if not ai_status["ai_ready"]:
        st.warning(
            "AI reflection is not available. "
            + ("Install the `google-generativeai` package. " if ai_status["missing_sdk"] else "")
            + ("Configure your `GEMINI_API_KEY` in `.streamlit/secrets.toml` or as an environment variable." if ai_status["missing_key"] else ""),
            icon="⚠️",
        )
        with st.expander("How to configure the Gemini API key"):
            st.code(
                "# .streamlit/secrets.toml\nGEMINI_API_KEY = \"your-key-here\"",
                language="toml",
            )
            st.code("# Or environment variable\nexport GEMINI_API_KEY=your-key-here",
                    language="bash")
        return

    all_checkins = get_all_checkins(_uid())
    if len(all_checkins) < 5:
        st.info(
            "You need at least 5 check-ins before AI reflection is meaningful. "
            "Keep checking in!",
            icon="📝",
        )
        return

    df = checkins_to_df(all_checkins)
    patterns = run_all_patterns(all_checkins)

    tab_week, tab_month, tab_journal = st.tabs(
        ["📅 Reflect on My Week", "🗓️ Monthly Summary", "📔 Journal Reflection"]
    )

    with tab_week:
        st.subheader("Reflect on My Week")
        st.caption(
            "The AI will receive a summary of your last 7 days' averages and "
            "detected patterns — no raw text, no journal content."
        )
        if st.button("✨ Generate Weekly Reflection", type="primary"):
            summary = build_ai_summary(df, days=7)
            with st.spinner("Generating your reflection…"):
                result = get_weekly_reflection(summary, patterns)
            if result:
                st.markdown(result)
                st.divider()
                st.caption(
                    "_This reflection is based on statistical patterns in your "
                    "self-reported data. It is a wellness observation, not a "
                    "medical or clinical assessment._"
                )
            else:
                st.error(
                    "Could not generate a reflection right now. "
                    "Please check your API key and try again."
                )

    with tab_month:
        st.subheader("Monthly Summary")
        st.caption("Reflects on patterns over your last 30 days.")
        if len(all_checkins) < 14:
            st.info("You need at least 14 check-ins for a meaningful monthly reflection.")
        else:
            if st.button("✨ Generate Monthly Summary", type="primary"):
                summary = build_ai_summary(df, days=30)
                with st.spinner("Generating monthly summary…"):
                    result = get_monthly_reflection(summary, patterns)
                if result:
                    st.markdown(result)
                    st.divider()
                    st.caption(
                        "_This summary is observational only. It does not diagnose "
                        "any medical or psychiatric condition._"
                    )
                else:
                    st.error("Could not generate summary. Check your API key.")

    with tab_journal:
        st.subheader("Journal Reflection")
        st.info(
            "You can choose to share your journal entry **titles** (never content) "
            "to help the AI generate reflection questions. "
            "This is entirely optional and explicit.",
            icon="📔",
        )
        entries = get_journal_entries(_uid())
        if not entries:
            st.info("No journal entries yet.")
        else:
            entry_options = {
                f"{e['entry_date']}: {e['title']}": e["title"]
                for e in entries[:20]
            }
            selected_keys = st.multiselect(
                "Select journal entry titles to include (optional)",
                options=list(entry_options.keys()),
                default=[],
                help="Only titles are shared with the AI, never the content.",
            )
            selected_titles = [entry_options[k] for k in selected_keys]

            if st.button("✨ Generate Journal Reflection", type="primary"):
                summary = build_ai_summary(df, days=14)
                with st.spinner("Generating reflection questions…"):
                    result = get_journal_reflection(
                        selected_titles, len(entries), summary
                    )
                if result:
                    st.markdown(result)
                    st.caption(
                        "_Reflection questions generated from titles and statistics only. "
                        "No journal content was sent to the AI._"
                    )
                else:
                    st.error("Could not generate reflection. Check your API key.")


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_reports():
    st.header("📄 Reports")
    st.info(
        "Generate a wellness summary report for your own records or to share with "
        "a healthcare professional. Private journal content is **never** included "
        "unless you explicitly select entries.",
        icon="📄",
    )

    all_checkins = get_all_checkins(_uid())
    if not all_checkins:
        st.info("No data to report yet. Complete some check-ins first.")
        return

    user = get_user_by_id(_uid()) or {}
    display_name = user.get("display_name", st.session_state.display_name)
    df = checkins_to_df(all_checkins)

    # Period selection
    col1, col2 = st.columns(2)
    with col1:
        report_start = st.date_input(
            "Report start date",
            value=date.today() - timedelta(days=30),
        )
    with col2:
        report_end = st.date_input("Report end date", value=date.today())

    if report_start >= report_end:
        st.error("Start date must be before end date.")
        return

    # Filter check-ins for period
    df_report = df[
        (df["date"].dt.date >= report_start) &
        (df["date"].dt.date <= report_end)
    ]
    checkins_in_range = [
        c for c in all_checkins
        if report_start.isoformat() <= c["entry_date"] <= report_end.isoformat()
    ]

    st.metric("Check-ins in this period", len(checkins_in_range))

    # Optional AI summary
    include_ai = st.checkbox("Include AI-generated wellness summary", value=True)
    ai_summary_text = None

    # Optional journal titles
    entries = get_journal_entries(_uid())
    entries_in_range = [
        e for e in entries
        if report_start.isoformat() <= e["entry_date"] <= report_end.isoformat()
    ]
    selected_titles = []
    if entries_in_range:
        st.subheader("Optional: Include Journal Entry Titles")
        st.caption("Select which entry titles to reference in the report (no content included).")
        for e in entries_in_range:
            if not e.get("is_demo") and st.checkbox(
                f"{e['entry_date']}: {e['title']}", key=f"rep_j_{e['id']}"
            ):
                selected_titles.append(e["title"])

    st.divider()

    if st.button("📄 Generate Report", type="primary", use_container_width=True):
        patterns = run_all_patterns(checkins_in_range)
        recent = compute_recent_average(df_report, days=len(checkins_in_range) + 1)
        baseline = compute_baseline(df, window_days=30)
        date_range_str = f"{report_start.strftime('%d %b %Y')} – {report_end.strftime('%d %b %Y')}"

        if include_ai and is_ai_available() and len(checkins_in_range) >= 3:
            summary = build_ai_summary(df_report, days=len(checkins_in_range) + 1)
            with st.spinner("Generating AI wellness summary…"):
                ai_summary_text = get_weekly_reflection(summary, patterns)

        if is_pdf_available():
            pdf_bytes = generate_wellness_report(
                user_display_name=display_name,
                date_range=date_range_str,
                checkins=checkins_in_range,
                patterns=patterns,
                ai_summary=ai_summary_text,
                selected_journal_titles=selected_titles if selected_titles else None,
                baseline=baseline,
                recent_averages=recent,
            )
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"mindreflect_report_{today_str()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success("Report generated successfully.")
            else:
                st.error("PDF generation failed.")
        else:
            st.warning(
                "PDF generation requires the `reportlab` package. "
                "Showing report as text below.",
                icon="⚠️",
            )
            # Text fallback
            st.markdown(f"## Wellness Report — {date_range_str}")
            st.markdown(f"**Prepared for:** {display_name}")
            st.markdown(f"**Check-ins:** {len(checkins_in_range)}")
            if patterns:
                st.subheader("Behavioral Pattern Observations")
                for p in patterns:
                    st.markdown(f"**{p['pattern_name']}:** {p['description']}")
            if ai_summary_text:
                st.subheader("AI Wellness Summary")
                st.markdown(ai_summary_text)
            st.caption(
                "⚠️ " + 
                "This report contains self-reported wellness information and statistical "
                "observations. It is not a medical diagnosis."
            )

    # CSV export
    st.divider()
    st.subheader("Export Check-In Data")
    csv_data = checkins_to_csv_string(checkins_in_range)
    if csv_data:
        st.download_button(
            label="⬇️ Download Check-In CSV",
            data=csv_data,
            file_name=f"mindreflect_checkins_{today_str()}.csv",
            mime="text/csv",
        )


# ══════════════════════════════════════════════════════════════════════════════
# THERAPIST SHARING PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_sharing():
    st.header("👩‍⚕️ Therapist Sharing")
    st.success(
        "🔒 **Nothing is shared unless you explicitly choose to share it.** "
        "Sharing is OFF by default.",
        icon="🔒",
    )

    uid = _uid()
    tab_create, tab_manage = st.tabs(["Create Sharing Token", "Manage Tokens"])

    with tab_create:
        st.subheader("Create a New Sharing Token")
        st.caption(
            "Generate a token to share selected wellness data with your therapist "
            "or healthcare provider. You control exactly what is included."
        )

        with st.form("sharing_form"):
            label = st.text_input(
                "Token label (e.g. 'Dr. Smith — June 2025')",
                max_chars=100,
            )
            st.markdown("**Select what to share:**")
            perm_cols = st.columns(2)
            permissions = {}
            perm_items = list(PERMISSION_LABELS.items())
            for i, (key, plabel) in enumerate(perm_items):
                col = perm_cols[i % 2]
                permissions[key] = col.checkbox(plabel, value=False)

            expiry_days = st.selectbox(
                "Token expires in",
                [7, 14, 30, 60, 90, 180],
                index=2,
                format_func=lambda x: f"{x} days",
            )
            create_submitted = st.form_submit_button(
                "🔗 Create Sharing Token", type="primary", use_container_width=True
            )

        if create_submitted:
            if not label.strip():
                st.error("Please provide a label for this token.")
            elif not any(permissions.values()):
                st.error("Please select at least one data category to share.")
            else:
                token = gen_token()
                expires = (datetime.utcnow() + timedelta(days=expiry_days)).isoformat()
                create_sharing_token(uid, token, label.strip(), permissions, expires)
                st.success("✅ Sharing token created.")
                with st.container(border=True):
                    st.markdown("**Share this token with your healthcare provider:**")
                    st.code(token)
                    st.caption(
                        f"Expires: {(date.today() + timedelta(days=expiry_days)).strftime('%d %b %Y')} | "
                        f"Shared: {', '.join(describe_permissions(permissions))}"
                    )
                    st.warning(
                        "Store this token securely. It grants access to the selected data.",
                        icon="⚠️",
                    )
                st.rerun()

    with tab_manage:
        st.subheader("Active Tokens")
        active_tokens = get_sharing_tokens(uid)
        all_tokens = get_all_sharing_tokens(uid)

        if not all_tokens:
            st.info("You have no sharing tokens. Create one above.")
        else:
            for t in all_tokens:
                perms = json.loads(t.get("permissions", "{}"))
                revoked = bool(t.get("revoked_at"))
                expired = (
                    t.get("expires_at") and
                    t["expires_at"] < datetime.utcnow().isoformat()
                )
                status = "🔴 Revoked" if revoked else ("🟠 Expired" if expired else "🟢 Active")

                with st.expander(f"{t['label']}  —  {status}"):
                    st.caption(f"Created: {format_date_short(t['created_at'][:10])}")
                    if t.get("expires_at"):
                        st.caption(f"Expires: {format_date_short(t['expires_at'][:10])}")
                    if t.get("last_accessed"):
                        st.caption(f"Last accessed: {format_date_short(t['last_accessed'][:10])}")
                    st.caption(f"Shared data: {', '.join(describe_permissions(perms)) or 'None'}")

                    if not revoked and not expired:
                        if st.button(f"🚫 Revoke Access", key=f"rev_{t['id']}"):
                            revoke_sharing_token(t["id"], uid)
                            st.success("Token revoked.")
                            st.rerun()

        # Audit log
        st.divider()
        st.subheader("Sharing History")
        audit = get_sharing_audit_log(uid)
        if audit:
            for a in audit[:20]:
                st.caption(
                    f"• {a['action'].capitalize()} — "
                    f"{a.get('label', 'Token')} — "
                    f"{format_date_short(a['timestamp'][:10])}"
                )
        else:
            st.caption("No sharing activity recorded.")


# ══════════════════════════════════════════════════════════════════════════════
# PRIVACY & CONSENT PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_privacy():
    st.header("🔐 Privacy & Consent")

    st.markdown(PRIVACY_NOTICE)
    st.divider()

    st.subheader("AI Processing")
    st.info(
        "When you use AI Reflection features, **only aggregate statistics** are sent "
        "to the Google Gemini API — not your journal content, not raw reflections. "
        "You explicitly trigger each AI request. Nothing is sent automatically.",
        icon="🤖",
    )

    st.subheader("Journal Privacy")
    st.info(
        "Journal entries are encrypted at rest using your account password. "
        + ("Full Fernet (AES) encryption is active. " if is_crypto_available()
           else "⚠️ Cryptography package not installed — basic obfuscation only. Install `cryptography` for full encryption. ")
        + "Journal content is never sent to the AI automatically.",
        icon="🔒",
    )

    st.divider()

    # Export
    st.subheader("Export My Data")
    if st.button("⬇️ Export Data (JSON)"):
        data = export_user_data(_uid())
        st.download_button(
            label="📥 Download my data",
            data=export_to_json(data),
            file_name=f"mindreflect_data_{today_str()}.json",
            mime="application/json",
        )

    st.divider()

    # Danger zone
    st.subheader("⚠️ Danger Zone")

    with st.expander("Delete Journal Entries"):
        st.warning(
            "This will permanently delete **all** your journal entries. "
            "This cannot be undone.",
            icon="⚠️",
        )
        confirm_journal = st.text_input(
            "Type DELETE to confirm journal deletion",
            key="confirm_del_journal",
        )
        if st.button("🗑️ Delete All Journal Entries"):
            if confirm_journal == "DELETE":
                deleted = delete_journal_all(_uid())
                st.success(f"Deleted {deleted} journal entries.")
            else:
                st.error("Type DELETE to confirm.")

    with st.expander("Delete Account & All Data"):
        st.error(
            "This will permanently delete your account and **all** associated data. "
            "This cannot be undone.",
            icon="🚨",
        )
        confirm_account = st.text_input(
            "Type DELETE MY ACCOUNT to confirm",
            key="confirm_del_account",
        )
        if st.button("🚨 Delete My Account"):
            if confirm_account == "DELETE MY ACCOUNT":
                delete_all_user_data(_uid())
                st.success("Your account and all data have been deleted.")
                _logout()
            else:
                st.error("Type DELETE MY ACCOUNT exactly to confirm.")

    st.divider()
    st.caption(
        "MindReflect AI is a prototype/educational application and not an official "
        "healthcare service. See README for full data-handling documentation."
    )


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_settings():
    st.header("⚙️ Settings")

    user = get_user_by_id(_uid()) or {}
    ai_status = get_ai_status()

    tab_profile, tab_remind, tab_ai, tab_security = st.tabs(
        ["Profile", "Reminders", "AI Status", "Security"]
    )

    with tab_profile:
        st.subheader("Profile")
        with st.form("profile_form"):
            new_display = st.text_input(
                "Display name",
                value=user.get("display_name", ""),
            )
            new_email = st.text_input(
                "Email (optional)",
                value=user.get("email", ""),
            )
            new_tz = st.text_input(
                "Timezone (e.g. Europe/London)",
                value=user.get("timezone", "UTC"),
            )
            if st.form_submit_button("💾 Save Profile"):
                update_user_settings(
                    _uid(),
                    display_name=new_display.strip(),
                    email=new_email.strip(),
                    timezone=new_tz.strip(),
                )
                st.session_state.display_name = new_display.strip()
                st.success("Profile updated.")

    with tab_remind:
        st.subheader("Daily Reminder")
        st.info(
            "MindReflect AI is a Streamlit web application and does not support "
            "native mobile/browser push notifications in the prototype deployment. "
            "Your reminder preference is saved and shown as a prompt when you open the app.",
            icon="ℹ️",
        )
        with st.form("reminder_form"):
            rem_enabled = st.checkbox(
                "Show daily reminder prompt when I open the app",
                value=bool(user.get("reminder_enabled", False)),
            )
            rem_time = st.text_input(
                "Preferred time (HH:MM, for display only)",
                value=user.get("reminder_time", "09:00"),
            )
            if st.form_submit_button("💾 Save Reminder Settings"):
                update_user_settings(
                    _uid(),
                    reminder_enabled=int(rem_enabled),
                    reminder_time=rem_time.strip(),
                )
                st.success("Reminder settings saved.")

        # Show reminder if enabled and no checkin today
        if user.get("reminder_enabled"):
            today_ci = get_checkin_for_date(_uid(), today_str())
            if not today_ci:
                st.info(
                    f"🔔 **Daily Reminder** — Don't forget your check-in today! "
                    f"_(Your preferred time: {user.get('reminder_time', '09:00')})_"
                )

    with tab_ai:
        st.subheader("AI (Gemini) Status")
        if ai_status["ai_ready"]:
            st.success(
                f"✅ Gemini AI is configured and ready. Model: `{ai_status['model']}`",
                icon="✅",
            )
        else:
            st.warning("⚠️ AI reflection is not fully configured.", icon="⚠️")
            if ai_status["missing_sdk"]:
                st.info("Install `google-generativeai`: `pip install google-generativeai`")
            if ai_status["missing_key"]:
                st.info(
                    "Add your API key to `.streamlit/secrets.toml`:\n"
                    "```toml\nGEMINI_API_KEY = \"your-key-here\"\n```"
                )

        st.caption(
            "The AI model is Gemini 2.5 Flash. Only aggregate statistics are sent — "
            "never journal content or raw personal text."
        )

    with tab_security:
        st.subheader("Change Password")
        st.caption(
            "Changing your password will re-encrypt new journal entries with the new password. "
            "Older entries will use the previous password for decryption."
        )
        with st.form("pw_form"):
            current_pw = st.text_input("Current password", type="password")
            new_pw = st.text_input("New password", type="password")
            new_pw2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("🔑 Change Password"):
                if not verify_password(current_pw, user["password_hash"]):
                    st.error("Current password is incorrect.")
                elif len(new_pw) < 6:
                    st.error("New password must be at least 6 characters.")
                elif new_pw != new_pw2:
                    st.error("Passwords do not match.")
                else:
                    update_password_hash(_uid(), hash_password(new_pw))
                    st.session_state.password = new_pw
                    st.success(
                        "Password changed. Note: existing journal entries were "
                        "encrypted with your previous password."
                    )

        st.subheader("Encryption Status")
        if is_crypto_available():
            st.success("✅ Full Fernet (AES-128) encryption is active for journal entries.")
        else:
            st.warning(
                "⚠️ The `cryptography` package is not installed. "
                "Journal entries are using basic obfuscation only. "
                "Install `cryptography` for full encryption: `pip install cryptography`",
                icon="⚠️",
            )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.authenticated:
        page_auth()
        return

    render_sidebar()

    # Daily reminder banner
    user = get_user_by_id(_uid()) or {}
    if user.get("reminder_enabled") and st.session_state.page == "🏠 Home":
        today_ci = get_checkin_for_date(_uid(), today_str())
        if not today_ci:
            st.toast(
                f"🔔 Reminder: Don't forget your daily check-in!",
                icon="🔔",
            )

    page_fn = {
        "🏠 Home": page_home,
        "📝 Daily Check-In": page_checkin,
        "📔 Private Journal": page_journal,
        "📊 Wellness Trends": page_trends,
        "🔎 Behavioral Patterns": page_patterns,
        "🤖 AI Reflection": page_ai_reflection,
        "📄 Reports": page_reports,
        "👩‍⚕️ Therapist Sharing": page_sharing,
        "🔐 Privacy & Consent": page_privacy,
        "⚙️ Settings": page_settings,
    }

    current = st.session_state.page
    fn = page_fn.get(current, page_home)
    fn()

    # Persistent disclaimer footer
    st.divider()
    st.caption(
        "🛡️ " + DISCLAIMER
    )


if __name__ == "__main__":
    main()


    
