# MindReflect AI — Privacy & Data Handling

> **This is an educational/prototype application and not an official healthcare service.**
> It has not been certified as a medical device, clinical decision-support system, or
> regulated health application under any jurisdiction.

---

## 1. What Data Is Collected

MindReflect AI collects only the data you explicitly enter:

- **Account information:** Username, optional email address, display name, hashed password
- **Daily check-in data:** Mood, stress, sleep duration, sleep quality, energy, anxiety, behavioral factors (exercise, social interaction, etc.), and free-text reflections
- **Journal entries:** Title and body text you write, mood tags, personal tags
- **Settings:** Reminder preferences, timezone, display name
- **Sharing activity:** Non-sensitive audit records of sharing token creation and access

---

## 2. Why It Is Collected

Data is collected solely to provide the wellness reflection and pattern-awareness features of MindReflect AI:

- Daily check-in data is used to compute trends, statistics, and behavioral patterns
- Journal entries are your private record, stored for your access only
- Account data is used for authentication
- Sharing activity is logged to provide transparency and enable revocation

---

## 3. How Data Is Stored

- All data is stored **locally** in a SQLite database file (`mindreflect.db`) on the device running the application
- Journal entries are **encrypted at rest** using AES-128 (Fernet) symmetric encryption, with keys derived from your password using PBKDF2-HMAC-SHA256
- Passwords are stored as salted hashes and never in plaintext

---

## 4. Journal Data Protection

- Journal content is encrypted using a key derived from your account password
- Each journal entry uses a unique random salt
- Encrypted content cannot be read without the correct password
- **Limitation:** In this prototype, the encryption key is derived from your login password. If you change your password, existing entries remain encrypted with the previous key. Full re-encryption on password change is a known improvement item.
- If the `cryptography` package is not installed, a basic XOR obfuscation is used instead — this is clearly documented in the Settings page.

---

## 5. When Gemini Receives Data

The Google Gemini API is called **only when you explicitly request an AI reflection**. When you do:

- Only **aggregate statistics** are sent (e.g., average mood, stress, sleep over a period)
- **No raw check-in text** (reflection notes) is sent
- **No journal content** is sent
- **No personally identifying information** is sent
- Data sent is summarised in `ai/prompts.py` before transmission

Google's handling of API data is subject to [Google's privacy policy](https://policies.google.com/privacy).

---

## 6. Therapist Sharing

- Sharing is **OFF by default**
- You create a sharing token explicitly, choosing exactly what categories of data to include
- Tokens have a configurable expiry date
- Tokens can be revoked at any time
- A non-sensitive audit log records when tokens were created, accessed, and revoked
- Journal content is **never** automatically included in shared data
- The audit log does not contain journal content

---

## 7. User Consent

- Creating an account requires acknowledging that MindReflect AI is a wellness tool and not a medical service
- Each AI reflection request is explicitly triggered by the user
- Therapist sharing requires explicit token creation with permission selection
- No data is shared with any third party without explicit user action

---

## 8. Data Deletion

You can delete your data at any time via the **Privacy & Consent** page:

- **Delete journal entries:** Permanently removes all journal content
- **Delete account:** Permanently removes your account, all check-ins, journal entries, patterns, sharing tokens, and audit records
- Deleted data is not recoverable

---

## 9. Data Export

You can export your data in JSON format from the **Privacy & Consent** page.

The export includes:
- Account metadata (no password hash)
- All check-in data
- Journal entry metadata (dates, titles, tags — no encrypted content)

Check-in data can also be exported as CSV from the **Reports** page.

---

## 10. Third-Party Sharing

MindReflect AI does **not** share your data with any third party except:

- **Google Gemini API** — aggregate statistics only, when you explicitly use AI features
- Data is not sold, rented, or shared for advertising purposes

---

## 11. Security Limitations

This is a prototype application. Known limitations include:

- Password hashing uses SHA-256 with a random salt (adequate for prototype; bcrypt or Argon2 recommended for production)
- SQLite is used for local storage (no server-side encryption at the database level)
- There is no audit trail for local file system access — if an attacker gains access to the device running the app, they could copy the database file
- The encryption described here protects journal content within the database file from casual inspection, but is not a substitute for device-level security

---

## 12. Contact and Corrections

This application is provided for educational and demonstration purposes. It is not a certified healthcare service. If you have concerns about mental health, please consult a qualified healthcare professional.
