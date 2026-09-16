"""
Encryption and security utilities for MindReflect AI.
Journal content is encrypted at rest using symmetric encryption.

NOTE: This is a prototype/educational application.
In production, use a proper key-management service.
The encryption key derived from the user's password is only as strong
as the user's password and the local storage security.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional

# Attempt to use cryptography library; fall back to a basic XOR obfuscation
# if not available so the app still runs in minimal environments.
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes as crypto_hashes
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


# ──────────────────────────────────────────────
# Password hashing
# ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Return a salted SHA-256 hash of the password (bcrypt preferred in prod)."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{pw_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against the stored salted hash."""
    try:
        salt, pw_hash = stored_hash.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == pw_hash
    except Exception:
        return False


# ──────────────────────────────────────────────
# Journal encryption
# ──────────────────────────────────────────────

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet-compatible key from a password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=crypto_hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def _simple_obfuscate(text: str) -> str:
    """
    Minimal XOR obfuscation used ONLY when cryptography is not installed.
    This is NOT encryption — it only prevents casual viewing.
    Clearly documented as a fallback.
    """
    key = b"mindreflect_obs_key_v1"
    encoded = text.encode("utf-8")
    obfuscated = bytes(b ^ key[i % len(key)] for i, b in enumerate(encoded))
    return "OBF:" + base64.b64encode(obfuscated).decode()


def _simple_deobfuscate(text: str) -> str:
    """Reverse of _simple_obfuscate."""
    if not text.startswith("OBF:"):
        return text
    key = b"mindreflect_obs_key_v1"
    obfuscated = base64.b64decode(text[4:])
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(obfuscated)).decode("utf-8")


def encrypt_journal_content(plaintext: str, user_password: str) -> str:
    """
    Encrypt journal content using the user's password.

    Returns a string in the format: ENC:<salt_b64>:<ciphertext_b64>
    If cryptography is unavailable, falls back to obfuscation (documented).
    """
    if not plaintext:
        return ""

    if not _CRYPTO_AVAILABLE:
        return _simple_obfuscate(plaintext)

    salt = os.urandom(16)
    key = _derive_key(user_password, salt)
    f = Fernet(key)
    ciphertext = f.encrypt(plaintext.encode("utf-8"))
    salt_b64 = base64.urlsafe_b64encode(salt).decode()
    cipher_b64 = ciphertext.decode()
    return f"ENC:{salt_b64}:{cipher_b64}"


def decrypt_journal_content(ciphertext_str: str, user_password: str) -> Optional[str]:
    """
    Decrypt journal content encrypted with encrypt_journal_content().

    Returns None on failure (wrong password, corrupted data).
    """
    if not ciphertext_str:
        return ""

    if ciphertext_str.startswith("OBF:"):
        try:
            return _simple_deobfuscate(ciphertext_str)
        except Exception:
            return None

    if not ciphertext_str.startswith("ENC:"):
        # Plain text stored without encryption (legacy/demo)
        return ciphertext_str

    if not _CRYPTO_AVAILABLE:
        return "[Decryption unavailable — install the 'cryptography' package]"

    try:
        _, salt_b64, cipher_b64 = ciphertext_str.split(":", 2)
        salt = base64.urlsafe_b64decode(salt_b64)
        key = _derive_key(user_password, salt)
        f = Fernet(key)
        return f.decrypt(cipher_b64.encode()).decode("utf-8")
    except Exception:
        return None


def is_crypto_available() -> bool:
    """Return whether the cryptography library is installed."""
    return _CRYPTO_AVAILABLE


# ──────────────────────────────────────────────
# Sharing token generation
# ──────────────────────────────────────────────

def generate_sharing_token() -> str:
    """Generate a cryptographically secure random sharing token."""
    return secrets.token_urlsafe(32)


# ──────────────────────────────────────────────
# Input sanitisation
# ──────────────────────────────────────────────

def sanitize_text(text: str, max_length: int = 10_000) -> str:
    """Trim and limit text to prevent oversized inputs."""
    if not text:
        return ""
    return text.strip()[:max_length]


def is_safe_username(username: str) -> bool:
    """Return True if username only contains safe characters."""
    import re
    return bool(re.match(r"^[a-zA-Z0-9_\-\.]{3,50}$", username))
