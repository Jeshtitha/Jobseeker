"""
database.py — User Authentication Database
Supabase-backed user store for the JobSeeker AI platform.

Tables (create in Supabase SQL editor):
  users    — registered accounts (id, username, email, password_hash, salt, full_name, role, created_at, last_login)
  sessions — active login sessions  (token, user_id, created_at, expires_at)

Usage:
  from database import Database
  db = Database()
  db.create_user("alice", "a@x.com", "pass123")
  user = db.authenticate("alice", "pass123")
"""

import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional

from supabase import create_client, Client
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────

SESSION_HOURS = 24        # sessions expire after this many hours
PBKDF2_ITERS  = 260_000   # NIST-recommended minimum for PBKDF2-SHA256


def _get_supabase() -> Client:
    """Create a Supabase client using Streamlit secrets."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


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
    return secrets.token_hex(32)       # 256-bit random salt


def _new_token() -> str:
    return secrets.token_urlsafe(48)   # 384-bit session token


# ── Database class ────────────────────────────────────────────────────────────

class Database:
    def __init__(self):
        self.sb: Client = _get_supabase()

    def _refresh(self):
        """Re-create client (guards against connection drops)."""
        self.sb = _get_supabase()

    # ── User CRUD ──────────────────────────────────────────────────────────

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

        # Check for duplicates manually (Supabase raises on constraint violation)
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' is already taken.")
        if self.get_user_by_email(email):
            raise ValueError(f"Email '{email}' is already registered.")

        salt          = _new_salt()
        password_hash = _hash_password(password, salt)
        created_at    = datetime.utcnow().isoformat()

        self._refresh()
        resp = self.sb.table("users").insert({
            "username":      username.strip(),
            "email":         email.strip().lower(),
            "password_hash": password_hash,
            "salt":          salt,
            "full_name":     full_name.strip(),
            "role":          role,
            "created_at":    created_at,
        }).execute()

        if not resp.data:
            raise ValueError("Registration failed. Please try again.")

        return resp.data[0]

    def get_user_by_username(self, username: str) -> Optional[dict]:
        self._refresh()
        resp = self.sb.table("users") \
            .select("*") \
            .ilike("username", username) \
            .limit(1) \
            .execute()
        return resp.data[0] if resp.data else None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        self._refresh()
        resp = self.sb.table("users") \
            .select("*") \
            .ilike("email", email.lower()) \
            .limit(1) \
            .execute()
        return resp.data[0] if resp.data else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        self._refresh()
        resp = self.sb.table("users") \
            .select("*") \
            .eq("id", user_id) \
            .limit(1) \
            .execute()
        return resp.data[0] if resp.data else None

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
        now = datetime.utcnow().isoformat()
        self.sb.table("users").update({"last_login": now}).eq("id", user["id"]).execute()
        user["last_login"] = now
        return user

    def update_profile(self, user_id: int, full_name: str = None, email: str = None) -> bool:
        fields = {}
        if full_name is not None:
            fields["full_name"] = full_name.strip()
        if email is not None:
            if "@" not in email:
                raise ValueError("Invalid email address.")
            fields["email"] = email.strip().lower()
        if not fields:
            return False
        self._refresh()
        self.sb.table("users").update(fields).eq("id", user_id).execute()
        return True

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        if _hash_password(old_password, user["salt"]) != user["password_hash"]:
            raise ValueError("Current password is incorrect.")
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters.")
        salt     = _new_salt()
        new_hash = _hash_password(new_password, salt)
        self._refresh()
        self.sb.table("users").update({
            "password_hash": new_hash,
            "salt": salt,
        }).eq("id", user_id).execute()
        return True

    def list_users(self) -> list:
        """Admin helper — returns all users (without hashes)."""
        self._refresh()
        resp = self.sb.table("users") \
            .select("id, username, email, full_name, role, created_at, last_login") \
            .execute()
        return resp.data or []

    # ── Session management ─────────────────────────────────────────────────

    def create_session(self, user_id: int) -> str:
        """Create a new session token and return it."""
        token      = _new_token()
        now        = datetime.utcnow()
        expires_at = (now + timedelta(hours=SESSION_HOURS)).isoformat()
        self._refresh()
        self.sb.table("sessions").insert({
            "token":      token,
            "user_id":    user_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
        }).execute()
        return token

    def validate_session(self, token: str) -> Optional[dict]:
        """Return user dict if session is valid and not expired, else None."""
        if not token:
            return None
        self._refresh()
        resp = self.sb.table("sessions") \
            .select("*") \
            .eq("token", token) \
            .limit(1) \
            .execute()
        if not resp.data:
            return None
        row = resp.data[0]
        if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
            self.delete_session(token)
            return None
        return self.get_user_by_id(row["user_id"])

    def delete_session(self, token: str):
        self._refresh()
        self.sb.table("sessions").delete().eq("token", token).execute()

    def delete_all_sessions(self, user_id: int):
        """Log out all devices for a user."""
        self._refresh()
        self.sb.table("sessions").delete().eq("user_id", user_id).execute()

    def cleanup_expired_sessions(self):
        self._refresh()
        self.sb.table("sessions").delete() \
            .lt("expires_at", datetime.utcnow().isoformat()) \
            .execute()

    # ── Stats ──────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        self._refresh()
        users_resp = self.sb.table("users").select("id", count="exact").execute()
        sessions_resp = self.sb.table("sessions") \
            .select("token", count="exact") \
            .gt("expires_at", datetime.utcnow().isoformat()) \
            .execute()
        return {
            "total_users":     users_resp.count or 0,
            "active_sessions": sessions_resp.count or 0,
        }