"""
backend/tests/test_auth.py - Comprehensive Unit & Integration Tests for Authentication System.
Tests password hashing (scrypt), token issuance, route protection, token revocation, and password recovery.
"""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import create_application
from backend.database.auth_db import (
    init_auth_db,
    get_user_by_email,
    store_password_reset_token,
    verify_and_consume_reset_token,
)
from backend.security.auth import (
    PasswordHasher,
    create_access_token,
    hash_token,
)

# Test database isolation
TEST_DB_PATH = Path(__file__).resolve().parent / "test_auth_isolated.db"


@pytest.fixture(scope="module", autouse=True)
def setup_test_auth_environment():
    """Sets isolated test database path and cleans up before and after."""
    old_env = os.environ.get("AUTH_DB_PATH")
    os.environ["AUTH_DB_PATH"] = str(TEST_DB_PATH)
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    init_auth_db(TEST_DB_PATH)
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if old_env is not None:
        os.environ["AUTH_DB_PATH"] = old_env
    else:
        os.environ.pop("AUTH_DB_PATH", None)


@pytest.fixture(scope="module")
def client():
    """Initializes FastAPI test client."""
    app = create_application()
    return TestClient(app)


# ------------------------------------------------------------------------------
# 1. Password Hashing & Strength Tests
# ------------------------------------------------------------------------------

def test_password_hasher_scrypt():
    """Verifies that password hashing produces valid scrypt format and verifies correctly."""
    pwd = "Secur3AuditorPassword!"
    hashed = PasswordHasher.hash_password(pwd)
    assert hashed.startswith("$scrypt$")
    assert PasswordHasher.verify_password(pwd, hashed) is True
    assert PasswordHasher.verify_password("WrongPassword123!", hashed) is False
    assert PasswordHasher.verify_password("", hashed) is False


def test_password_policy_validation():
    """Ensures short or weak passwords violate policy."""
    assert PasswordHasher.validate_password_strength("short1") is not None
    assert PasswordHasher.validate_password_strength("allcharacters") is not None
    assert PasswordHasher.validate_password_strength("12345678") is not None
    assert PasswordHasher.validate_password_strength("ValidPassword123") is None


# ------------------------------------------------------------------------------
# 2. Registration & Login Flow Tests
# ------------------------------------------------------------------------------

def test_register_auditor_success(client):
    """Verifies successful registration of a new auditor."""
    payload = {
        "name": "Prof. Alok Sharma",
        "email": "alok.sharma@aicte.gov.in",
        "password": "CompliantPassword2026!",
        "consent_acknowledged": True,
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alok.sharma@aicte.gov.in"
    assert data["user"]["name"] == "Prof. Alok Sharma"


def test_register_duplicate_email_rejected(client):
    """Verifies that duplicate registration is rejected with 409 Conflict."""
    payload = {
        "name": "Duplicate User",
        "email": "alok.sharma@aicte.gov.in",
        "password": "AnotherPassword2026!",
        "consent_acknowledged": True,
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409
    assert "already registered" in res.json()["detail"]


def test_login_success_and_failure(client):
    """Verifies valid login generates token and invalid password returns 401."""
    # Successful login
    login_payload = {
        "email": "alok.sharma@aicte.gov.in",
        "password": "CompliantPassword2026!",
        "remember_me": True,
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alok.sharma@aicte.gov.in"

    # Failed login: wrong password
    bad_payload = {
        "email": "alok.sharma@aicte.gov.in",
        "password": "WrongPassword!",
    }
    bad_res = client.post("/api/v1/auth/login", json=bad_payload)
    assert bad_res.status_code == 401

    # Failed login: non-existent email
    ghost_payload = {
        "email": "ghost.auditor@aicte.gov.in",
        "password": "CompliantPassword2026!",
    }
    ghost_res = client.post("/api/v1/auth/login", json=ghost_payload)
    assert ghost_res.status_code == 401


# ------------------------------------------------------------------------------
# 3. Session & Route Protection Tests
# ------------------------------------------------------------------------------

def test_protected_route_rejection_without_token(client):
    """Verifies that protected verification endpoints reject unauthenticated access with 401."""
    # Attempting to verify sample without authorization header
    res = client.post("/api/v1/dataset/verify-sample/DOC_REAL_001")
    assert res.status_code == 401


def test_protected_route_success_with_valid_token(client):
    """Verifies that protected verification endpoints succeed with a valid Bearer token."""
    # Log in to get token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "alok.sharma@aicte.gov.in", "password": "CompliantPassword2026!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access /auth/me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alok.sharma@aicte.gov.in"

    # Access protected dataset sample verification
    verify_res = client.post("/api/v1/dataset/verify-sample/DOC_REAL_001", headers=headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["document_id"] == "DOC_REAL_001"


def test_logout_revokes_token(client):
    """Verifies that logging out revokes the token's JTI and prevents further access."""
    # Log in to get a fresh token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "alok.sharma@aicte.gov.in", "password": "CompliantPassword2026!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify active
    check_res = client.get("/api/v1/auth/me", headers=headers)
    assert check_res.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Subsequent access with revoked token must fail with 401
    revoked_res = client.get("/api/v1/auth/me", headers=headers)
    assert revoked_res.status_code == 401
    assert "terminated" in revoked_res.json()["detail"] or "expired" in revoked_res.json()["detail"]


# ------------------------------------------------------------------------------
# 4. Password Recovery Flow Tests
# ------------------------------------------------------------------------------

def test_forgot_password_generic_response(client):
    """Verifies that forgot password returns generic constant response without user enumeration."""
    # Existing email
    res1 = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "alok.sharma@aicte.gov.in"},
    )
    assert res1.status_code == 200
    assert "If an auditor account" in res1.json()["message"]

    # Non-existent email (must return identical generic message)
    res2 = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@aicte.gov.in"},
    )
    assert res2.status_code == 200
    assert res2.json()["message"] == res1.json()["message"]


def test_reset_password_execution(client):
    """Verifies complete password reset cycle with single-use token."""
    user = get_user_by_email("alok.sharma@aicte.gov.in", db_path=TEST_DB_PATH)
    assert user is not None

    # Create mock reset token directly in DB
    raw_token = "secure_test_reset_token_32_characters_long"
    token_hash = hash_token(raw_token)
    expires_iso = "2099-12-31T23:59:59+00:00"
    store_password_reset_token(token_hash, user["id"], expires_iso, db_path=TEST_DB_PATH)

    # Reset password with valid token
    reset_payload = {
        "token": raw_token,
        "new_password": "NewUpdatedPassword2026!",
    }
    reset_res = client.post("/api/v1/auth/reset-password", json=reset_payload)
    assert reset_res.status_code == 200
    assert "successfully updated" in reset_res.json()["message"]

    # Single-use: attempting to use the same token again must fail
    second_res = client.post("/api/v1/auth/reset-password", json=reset_payload)
    assert second_res.status_code == 400

    # Old password no longer works
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alok.sharma@aicte.gov.in", "password": "CompliantPassword2026!"},
    )
    assert old_login.status_code == 401

    # New password works
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alok.sharma@aicte.gov.in", "password": "NewUpdatedPassword2026!"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()
