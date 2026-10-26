"""
backend/database/auth_db.py - SQLite Database Manager for AICTE Authentication & User Storage.
Implements parameterized SQL queries, foreign key enforcement, WAL mode, and token revocation.
"""

import os
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Optional, Any

# Default path for persistent SQLite database
DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "aicte_auth.db"


def get_db_path() -> Path:
    """Resolves database file path from environment or default."""
    custom_path = os.getenv("AUTH_DB_PATH")
    if custom_path:
        p = Path(custom_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    # On Vercel serverless (or any read-only container), filesystem outside /tmp is read-only
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        tmp_dir = Path("/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir / "aicte_auth.db"
    try:
        DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_DB_PATH
    except (OSError, PermissionError):
        tmp_dir = Path("/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir / "aicte_auth.db"


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Creates a sqlite3 connection with foreign keys and WAL mode enabled."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(str(target_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_auth_db(db_path: Optional[Path] = None) -> None:
    """Initializes tables for users, revoked tokens, and password reset tokens."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'auditor',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            """)

            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                revoked_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires ON revoked_tokens(expires_at);
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_expires ON password_reset_tokens(expires_at);
            """)
    finally:
        conn.close()


def create_user(
    user_id: str,
    name: str,
    email: str,
    password_hash: str,
    role: str = "auditor",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Registers a new user using parameterized SQL."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clean_email = email.strip().lower()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (id, name, email, password_hash, role, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (user_id, name.strip(), clean_email, password_hash, role, now_iso, now_iso),
            )
        return {
            "id": user_id,
            "name": name.strip(),
            "email": clean_email,
            "role": role,
            "created_at": now_iso,
            "is_active": True,
        }
    finally:
        conn.close()


def get_user_by_email(email: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves user record by email (case-insensitive) using parameterized SQL."""
    conn = get_db_connection(db_path)
    try:
        clean_email = email.strip().lower()
        cursor = conn.execute(
            "SELECT id, name, email, password_hash, role, created_at, updated_at, is_active FROM users WHERE email = ?",
            (clean_email,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def get_user_by_id(user_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves user record by ID using parameterized SQL."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, name, email, password_hash, role, created_at, updated_at, is_active FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def update_user_password(user_id: str, new_password_hash: str, db_path: Optional[Path] = None) -> bool:
    """Updates password hash for a user."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (new_password_hash, now_iso, user_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def revoke_token(jti: str, user_id: str, expires_at_iso: str, db_path: Optional[Path] = None) -> None:
    """Inserts token JTI into revoked_tokens blacklist."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO revoked_tokens (jti, user_id, revoked_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (jti, user_id, now_iso, expires_at_iso),
            )
    finally:
        conn.close()


def is_token_revoked(jti: str, db_path: Optional[Path] = None) -> bool:
    """Checks if a JTI has been recorded as revoked."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def store_password_reset_token(
    token_hash: str, user_id: str, expires_at_iso: str, db_path: Optional[Path] = None
) -> None:
    """Stores a hashed password reset token."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO password_reset_tokens (token_hash, user_id, expires_at, used)
                VALUES (?, ?, ?, 0)
                """,
                (token_hash, user_id, expires_at_iso),
            )
    finally:
        conn.close()


def verify_and_consume_reset_token(token_hash: str, db_path: Optional[Path] = None) -> Optional[str]:
    """
    Verifies that a password reset token exists, is unused, and has not expired.
    If valid, marks it used and returns user_id; otherwise returns None.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                SELECT user_id, expires_at, used
                FROM password_reset_tokens
                WHERE token_hash = ?
                """,
                (token_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if row["used"] != 0:
                return None
            if row["expires_at"] < now_iso:
                return None

            # Mark as consumed immediately (single-use)
            conn.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE token_hash = ?",
                (token_hash,),
            )
            return row["user_id"]
    finally:
        conn.close()
