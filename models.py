"""
Database models for MindReflect AI.
Defines SQLite table schemas using dataclasses for type safety.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class User:
    """Represents an application user."""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    display_name: str = ""
    timezone: str = "UTC"
    reminder_enabled: bool = False
    reminder_time: str = "09:00"
    created_at: Optional[datetime] = None
    is_demo: bool = False


@dataclass
class DailyCheckIn:
    """Represents a daily wellness check-in entry."""
    id: Optional[int] = None
    user_id: int = 0
    entry_date: Optional[date] = None
    mood: Optional[int] = None          # 1-5
    stress: Optional[int] = None        # 1-5
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None # 1-5
    energy: Optional[int] = None        # 1-5
    anxiety: Optional[int] = None       # 1-5 (optional)
    exercise: Optional[bool] = None
    social_interaction: Optional[bool] = None
    outdoor_time: Optional[bool] = None
    workload: Optional[int] = None      # 1-5 (optional)
    screen_time: Optional[float] = None # hours
    relaxation: Optional[bool] = None
    regular_meals: Optional[bool] = None
    reflection: Optional[str] = None
    is_demo: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class JournalEntry:
    """Represents a private journal entry."""
    id: Optional[int] = None
    user_id: int = 0
    entry_date: Optional[date] = None
    title: str = ""
    encrypted_content: str = ""         # stored encrypted
    mood_tag: Optional[int] = None      # 1-5
    tags: str = ""                      # comma-separated
    is_demo: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PatternInsight:
    """Represents a detected behavioral pattern."""
    id: Optional[int] = None
    user_id: int = 0
    pattern_type: str = ""
    pattern_name: str = ""
    description: str = ""
    evidence: str = ""
    confidence: str = "low"             # low / medium / high
    data_points: int = 0
    time_period_days: int = 0
    detected_at: Optional[datetime] = None
    is_demo: bool = False


@dataclass
class SharingConsent:
    """Represents a therapist sharing token and permissions."""
    id: Optional[int] = None
    user_id: int = 0
    token: str = ""
    label: str = ""
    permissions: str = ""               # JSON string of permission flags
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None


@dataclass
class SharingAuditLog:
    """Audit log for sharing token access — no journal content stored."""
    id: Optional[int] = None
    user_id: int = 0
    token_id: int = 0
    action: str = ""                    # created / accessed / revoked
    timestamp: Optional[datetime] = None
    notes: str = ""                     # non-sensitive metadata only


# SQL DDL — kept alongside models for single-file reference
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    password_hash TEXT NOT NULL,
    display_name TEXT DEFAULT '',
    timezone TEXT DEFAULT 'UTC',
    reminder_enabled INTEGER DEFAULT 0,
    reminder_time TEXT DEFAULT '09:00',
    created_at TEXT NOT NULL,
    is_demo INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    entry_date TEXT NOT NULL,
    mood INTEGER,
    stress INTEGER,
    sleep_hours REAL,
    sleep_quality INTEGER,
    energy INTEGER,
    anxiety INTEGER,
    exercise INTEGER,
    social_interaction INTEGER,
    outdoor_time INTEGER,
    workload INTEGER,
    screen_time REAL,
    relaxation INTEGER,
    regular_meals INTEGER,
    reflection TEXT,
    is_demo INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, entry_date)
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    entry_date TEXT NOT NULL,
    title TEXT NOT NULL,
    encrypted_content TEXT NOT NULL,
    mood_tag INTEGER,
    tags TEXT DEFAULT '',
    is_demo INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS pattern_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pattern_type TEXT NOT NULL,
    pattern_name TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence TEXT NOT NULL,
    confidence TEXT NOT NULL,
    data_points INTEGER DEFAULT 0,
    time_period_days INTEGER DEFAULT 0,
    detected_at TEXT NOT NULL,
    is_demo INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sharing_consents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    label TEXT DEFAULT '',
    permissions TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    revoked_at TEXT,
    last_accessed TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sharing_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    notes TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""
