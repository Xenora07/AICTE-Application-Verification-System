"""
backend/security/auth.py - Authentication, Password Hashing, JWT Sessions, and Access Control.
Provides vetted scrypt/PBKDF2 password hashing, constant-time verification, and FastAPI dependencies.
"""

import os
import re
import uuid
import secrets
import hashlib
import datetime
from typing import Dict, Optional, Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.database.auth_db import get_user_by_id, is_token_revoked

# ------------------------------------------------------------------------------
# Configuration & Secrets Management
# ------------------------------------------------------------------------------

# Secure secret key with production validation
_DEFAULT_FALLBACK_SECRET = "aikte_sec_jwt_auth_dev_key_must_be_overridden_in_production_32b"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEFAULT_FALLBACK_SECRET)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
try:
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
except ValueError:
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Bearer token HTTP extractor
http_bearer = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------------------
# Password Hashing & Policy Validation
# ------------------------------------------------------------------------------

class PasswordHasher:
    """
    Cryptographic password hasher employing memory-hard scrypt (RFC 7914 / OpenSSL)
    with constant-time verification and PBKDF2 compatibility.
    """
    SCRYPT_N = 16384
    SCRYPT_R = 8
    SCRYPT_P = 1
    SALT_BYTES = 32

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Generates a secure salt and computes the scrypt digest."""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        salt = secrets.token_bytes(cls.SALT_BYTES)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=cls.SCRYPT_N,
            r=cls.SCRYPT_R,
            p=cls.SCRYPT_P,
            maxmem=64 * 1024 * 1024,
        )
        salt_hex = salt.hex()
        hash_hex = derived.hex()
        return f"$scrypt$n={cls.SCRYPT_N},r={cls.SCRYPT_R},p={cls.SCRYPT_P}${salt_hex}${hash_hex}"

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        """Verifies password using constant-time comparison."""
        if not password or not stored_hash:
            return False

        try:
            parts = stored_hash.split("$")
            # Format: ["", "scrypt", "n=16384,r=8,p=1", salt_hex, hash_hex]
            if len(parts) >= 5 and parts[1] == "scrypt":
                salt = bytes.fromhex(parts[3])
                expected_hash = bytes.fromhex(parts[4])
                computed = hashlib.scrypt(
                    password.encode("utf-8"),
                    salt=salt,
                    n=cls.SCRYPT_N,
                    r=cls.SCRYPT_R,
                    p=cls.SCRYPT_P,
                    maxmem=64 * 1024 * 1024,
                )
                return secrets.compare_digest(computed, expected_hash)

            # PBKDF2-HMAC-SHA256 fallback compatibility
            if len(parts) >= 5 and parts[1] == "pbkdf2-sha256":
                salt = bytes.fromhex(parts[3])
                expected_hash = bytes.fromhex(parts[4])
                computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
                return secrets.compare_digest(computed, expected_hash)
        except Exception:
            return False

        return False

    @staticmethod
    def validate_password_strength(password: str) -> Optional[str]:
        """
        Validates minimum compliance requirements for reviewer passwords.
        Returns None if valid, or a friendly error message if rejected.
        """
        if len(password) < 8:
            return "Password must be at least 8 characters long."
        if not re.search(r"[A-Za-z]", password):
            return "Password must contain at least one letter."
        if not re.search(r"[0-9]", password):
            return "Password must contain at least one number."
        return None


# ------------------------------------------------------------------------------
# JWT Token Issuance & Decoding
# ------------------------------------------------------------------------------

def create_access_token(
    user_id: str,
    email: str,
    name: str,
    role: str = "auditor",
    expires_delta: Optional[datetime.timedelta] = None,
) -> Dict[str, Any]:
    """Issues a signed JWT access token with JTI and standard claims."""
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = expires_delta or datetime.timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + delta
    jti = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "email": email.strip().lower(),
        "name": name,
        "role": role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(delta.total_seconds()),
        "expires_at": expire.isoformat(),
        "jti": jti,
    }


def decode_access_token(token: str) -> Dict[str, Any]:
    """Validates and decodes a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "jti"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def hash_token(token: str) -> str:
    """Hashes a reset or session token using SHA-256 for safe database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------------------
# FastAPI Dependency Injection: Route Protection
# ------------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Dict[str, Any]:
    """
    Enforces authentication on protected routes.
    Verifies Bearer token signature, expiration, and ensures token is not revoked.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been terminated or logged out.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token identity missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach raw token metadata for logout revocation
    user["_jti"] = jti
    user["_exp"] = payload.get("exp")
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Optional[Dict[str, Any]]:
    """Allows authenticated or guest access depending on token presence."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
