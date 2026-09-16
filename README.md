# MindReflect AI

**A private mental wellness reflection and behavioral pattern awareness application.**

> ⚠️ **Important Disclaimer:** MindReflect AI is a wellness reflection and behavioral
> pattern awareness tool. Its insights are based on self-reported information and
> statistical patterns. It does **not** diagnose mental-health conditions, provide
> medical advice, or replace a qualified healthcare professional.

---

## Overview

MindReflect AI helps you understand patterns in your own self-reported wellbeing data through:

- 📝 **Daily check-ins** — mood, stress, sleep, energy, behavioral factors
- 📔 **Private journaling** — encrypted entries, never shared automatically
- 📊 **Trend visualisations** — Plotly charts across 7 days to 1 year
- 🔎 **Behavioral pattern detection** — statistical observations from your own data
- 🤖 **AI-powered reflection** — Gemini 2.5 Flash generates wellness summaries
- 📄 **Report generation** — PDF wellness reports with your selected data
- 👩‍⚕️ **Therapist sharing** — explicit consent-based, token-based sharing
- 🔐 **Privacy controls** — data export, deletion, sharing management

---

## Features

| Feature | Description |
|---|---|
| Daily Check-In | Mood, stress, sleep, energy, anxiety, behavioral factors, free-text reflection |
| Personal Baseline | 30-day average comparison — your data vs your baseline, not a population norm |
| Pattern Detection | 9 statistical pattern types including mood variability, sleep associations, exercise correlations |
| AI Reflection | Gemini 2.5 Flash weekly/monthly reflections and journal prompts |
| Encrypted Journal | Journal content encrypted at rest using password-derived Fernet keys |
| Therapist Report | PDF with selected data, patterns, AI summary; never includes journal content automatically |
| Therapist Sharing | Secure tokens with expiry, explicit permission selection, revocable |
| Demo Data | 75 days of synthetic data for demonstration purposes |

---

## Architecture

```
mindreflect_ai/
├── app.py                  # Main Streamlit application
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example
├── database/
│   ├── db.py               # All SQLite CRUD operations
│   └── models.py           # Data models + DDL SQL
├── analytics/
│   ├── trends.py           # DataFrame construction, rolling averages, baselines
│   ├── patterns.py         # 9 behavioral pattern detectors
│   └── statistics.py       # Streaks, completion rate, behavioral summaries
├── ai/
│   ├── gemini_client.py    # Gemini 2.5 Flash API client
│   └── prompts.py          # System instruction + prompt builders
├── security/
│   ├── encryption.py       # Password hashing + journal encryption
│   └── privacy.py          # Safety detection + consent helpers
├── reports/
│   └── pdf_report.py       # ReportLab PDF generator
├── utils/
│   └── helpers.py          # Labels, chart config, export helpers
└── data/
    └── demo_data.py        # Synthetic demo data generator
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- A Google Gemini API key (for AI features)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/mindreflect-ai.git
cd mindreflect-ai/mindreflect_ai
```

### 2. Create a virtual environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Gemini API key

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and add your key:

```toml
GEMINI_API_KEY = "your-actual-gemini-api-key"
```

Alternatively, set an environment variable:

```bash
export GEMINI_API_KEY=your-actual-gemini-api-key
```

> **Never commit secrets.toml to version control.** The .gitignore already excludes it.

### 5. Run the application

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Streamlit Cloud Deployment

1. Push the repository to GitHub (ensure `secrets.toml` is **not** committed).
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud) and connect your repository.
3. Set the main file path to `mindreflect_ai/app.py`.
4. Add your `GEMINI_API_KEY` in the Streamlit Cloud Secrets settings.

---

## Database

MindReflect AI uses **SQLite** (`mindreflect.db`) stored locally alongside the application.

The database is created automatically on first run. Tables:

| Table | Purpose |
|---|---|
| `users` | Account credentials and settings |
| `daily_checkins` | Daily wellness check-in entries |
| `journal_entries` | Encrypted journal content |
| `pattern_insights` | Cached detected pattern results |
| `sharing_consents` | Therapist sharing tokens and permissions |
| `sharing_audit_log` | Non-sensitive audit trail of sharing activity |

**For production deployment**, replace SQLite with PostgreSQL and use a proper secret management service.

---

## Privacy Architecture

- **Journal encryption:** AES-128 (Fernet) encryption using PBKDF2-HMAC-SHA256 key derivation from the user's password. Each entry uses a unique salt. Requires the `cryptography` package.
- **Password hashing:** Salted SHA-256 (upgrade to bcrypt in production).
- **AI data minimisation:** Only aggregate statistics are sent to Gemini — never raw text, never journal content, never full check-in rows.
- **Sharing:** Explicit opt-in only. OFF by default. Tokens expire and are revocable. Audit log kept without sensitive content.
- **No automatic sharing:** Nothing leaves the local database without an explicit user action.

---

## Pattern Detection Methodology

All patterns are observational statistical rules applied to the user's own self-reported data. They are **not** clinical diagnostic criteria.

| Pattern | Detection Rule | Minimum Data |
|---|---|---|
| Sustained Low Mood | Mood ≤ 2.5 for ≥ 5 consecutive logged days | 5 days |
| Sustained High Stress | Stress ≥ 4.0 for ≥ 5 consecutive logged days | 5 days |
| Sleep–Mood Association | Pearson r ≥ 0.25 between sleep hours and mood | 14 paired observations |
| Stress–Sleep Association | Pearson r ≥ 0.25 between stress and sleep quality | 14 paired observations |
| Mood Variability | Recent SD ≥ 1.2 (higher than overall history) | 14 observations |
| Energy–Mood Association | Pearson r ≥ 0.25 between energy and mood | 10 paired observations |
| Exercise–Mood Association | Mean mood difference ≥ 0.3 (exercise vs non-exercise days) | 10 observations |
| Social–Mood Association | Mean mood difference ≥ 0.3 (social vs non-social days) | 10 observations |
| Screen Time–Sleep Association | Pearson r ≥ 0.25 between screen time and sleep hours | 10 paired observations |

**Thresholds are configurable** in `analytics/patterns.py` under the `THRESHOLDS` dictionary.

These thresholds are prototype analytical rules and are **not** clinical standards.

---

## AI Safety Limitations

The Gemini model is instructed via a system prompt to:

- Never diagnose any psychiatric or medical condition
- Never use clinical diagnostic labels
- Only describe observable statistical patterns
- Use neutral, non-judgmental language
- Encourage professional support where persistent difficulties are apparent
- Never replace or simulate therapy

The application also:

- Detects safety keywords (self-harm, suicidal language) in user text
- Responds with an immediate safety message and crisis resources
- Does **not** attempt to provide crisis intervention through the AI

---

## Known Limitations

1. **Local SQLite only** — Not suitable for multi-user production deployment without migration to PostgreSQL.
2. **Encryption key tied to password** — Password changes do not re-encrypt existing entries.
3. **No push notifications** — Streamlit does not support native push notifications; reminders are shown as UI prompts only.
4. **No real-time sync** — Data is stored locally; there is no cloud sync in this prototype.
5. **AI requires API key** — AI features are unavailable without a valid Gemini API key.
6. **Prototype security** — Password hashing uses SHA-256; upgrade to bcrypt or Argon2 in production.

---

## Future Improvements

- Migrate to PostgreSQL for multi-user deployment
- Upgrade to bcrypt/Argon2 password hashing
- Implement proper key management for journal encryption
- Add email-based daily reminder system
- Implement OAuth2 authentication
- Add time-of-day check-in patterns
- Multi-language support
- Accessibility improvements (screen reader compatibility)

---

## Privacy Policy

See [`PRIVACY.md`](PRIVACY.md) for the full data-handling document.

---

## Licence

This project is an educational/prototype application. Not for clinical use.
