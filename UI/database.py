"""
database.py — User Authentication Database
SQLite-backed user store for the JobSeeker AI platform.

Tables:
  users         — registered accounts (id, username, email, password_hash, salt, created_at, last_login)
  sessions      — active login sessions  (token, user_id, created_at, expires_at)

Usage:
  from database import Database
  db = Database()                         # auto-creates jobseeker.db
  db.create_user("alice", "a@x.com", "pass123")
  user = db.authenticate("alice", "pass123")
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional


# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH        = os.environ.get("JOBSEEKER_DB", "jobseeker.db")
SESSION_HOURS  = 24          # sessions expire after this many hours
PBKDF2_ITERS   = 260_000     # NIST-recommended minimum for PBKDF2-SHA256


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    """Return a PBKDF2-SHA256 hex digest for (password, salt)."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERS,
    )
    return dk.hex()


def _new_salt() -> str:
    return secrets.token_hex(32)          # 256-bit random salt


def _new_token() -> str:
    return secrets.token_urlsafe(48)      # 384-bit session token


# ── Database class ────────────────────────────────────────────────────────────

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent Streamlit reruns
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT    NOT NULL,
                    salt          TEXT    NOT NULL,
                    full_name     TEXT    DEFAULT '',
                    role          TEXT    DEFAULT 'user',
                    created_at    TEXT    NOT NULL,
                    last_login    TEXT
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token         TEXT    PRIMARY KEY,
                    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at    TEXT    NOT NULL,
                    expires_at    TEXT    NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_users_email   ON users(email);
            """)

    # ── User CRUD ─────────────────────────────────────────────────────────────

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str = "",
        role: str = "user",
    ) -> dict:
        """
        Register a new user. Returns the created user dict.
        Raises ValueError if username or email already taken.
        """
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        if len(username.strip()) < 2:
            raise ValueError("Username must be at least 2 characters.")
        if "@" not in email:
            raise ValueError("Invalid email address.")

        salt          = _new_salt()
        password_hash = _hash_password(password, salt)
        created_at    = datetime.utcnow().isoformat()

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash, salt, full_name, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (username.strip(), email.strip().lower(), password_hash, salt,
                     full_name.strip(), role, created_at),
                )
            return self.get_user_by_username(username)
        except sqlite3.IntegrityError as e:
            msg = str(e).lower()
            if "username" in msg:
                raise ValueError(f"Username '{username}' is already taken.")
            if "email" in msg:
                raise ValueError(f"Email '{email}' is already registered.")
            raise ValueError("Registration failed. Please try again.")

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.lower(),)
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def authenticate(self, username_or_email: str, password: str) -> Optional[dict]:
        """
        Verify credentials. Returns user dict on success, None on failure.
        Accepts either username or email as the first argument.
        """
        user = self.get_user_by_username(username_or_email)
        if not user:
            user = self.get_user_by_email(username_or_email)
        if not user:
            return None

        expected = _hash_password(password, user["salt"])
        if not secrets.compare_digest(expected, user["password_hash"]):
            return None

        # Update last_login timestamp
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), user["id"]),
            )
        user["last_login"] = datetime.utcnow().isoformat()
        return user

    def update_profile(self, user_id: int, full_name: str = None, email: str = None) -> bool:
        fields, vals = [], []
        if full_name is not None:
            fields.append("full_name = ?"); vals.append(full_name.strip())
        if email is not None:
            if "@" not in email:
                raise ValueError("Invalid email address.")
            fields.append("email = ?"); vals.append(email.strip().lower())
        if not fields:
            return False
        vals.append(user_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", vals)
        return True

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        if _hash_password(old_password, user["salt"]) != user["password_hash"]:
            raise ValueError("Current password is incorrect.")
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters.")
        salt = _new_salt()
        new_hash = _hash_password(new_password, salt)
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (new_hash, salt, user_id),
            )
        return True

    def list_users(self) -> list:
        """Admin helper — returns all users (without hashes)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, username, email, full_name, role, created_at, last_login FROM users"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Session management ────────────────────────────────────────────────────

    def create_session(self, user_id: int) -> str:
        """Create a new session token and return it."""
        token      = _new_token()
        now        = datetime.utcnow()
        expires_at = (now + timedelta(hours=SESSION_HOURS)).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, now.isoformat(), expires_at),
            )
        return token

    def validate_session(self, token: str) -> Optional[dict]:
        """Return user dict if session is valid and not expired, else None."""
        if not token:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE token = ?", (token,)
            ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
            self.delete_session(token)
            return None
        return self.get_user_by_id(row["user_id"])

    def delete_session(self, token: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def delete_all_sessions(self, user_id: int):
        """Log out all devices for a user."""
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def cleanup_expired_sessions(self):
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (datetime.utcnow().isoformat(),),
            )

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._connect() as conn:
            total_users    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active_sessions= conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE expires_at > ?",
                (datetime.utcnow().isoformat(),)
            ).fetchone()[0]
        return {"total_users": total_users, "active_sessions": active_sessions}
