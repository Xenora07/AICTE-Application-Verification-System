"""
backend/api/auth_routes.py - FastAPI Authentication Routes for AICTE Verification System.
Exposes endpoints for registration, login, session inspection, logout revocation, and password recovery.
"""

import uuid
import secrets
import datetime
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi import APIRouter, Depends, HTTPException, status, Request

from backend.database.auth_db import (
    create_user,
    get_user_by_email,
    revoke_token,
    store_password_reset_token,
    verify_and_consume_reset_token,
    update_user_password,
)
from backend.security.auth import (
    PasswordHasher,
    create_access_token,
    get_current_user,
    hash_token,
)
from backend.security.email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


# ------------------------------------------------------------------------------
# Request / Response Schemas
# ------------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email_format(v: str) -> str:
    cleaned = v.strip().lower()
    if not EMAIL_REGEX.match(cleaned):
        raise ValueError("Invalid email address format.")
    return cleaned

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full legal name of the reviewer")
    email: str = Field(..., description="Official institutional or reviewer email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)")
    consent_acknowledged: bool = Field(True, description="Acknowledgement of compliance terms")

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class LoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")
    remember_me: bool = Field(False, description="Whether to extend session duration")

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: str
    user: UserProfileResponse


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, description="Reset token from notification")
    new_password: str = Field(..., min_length=8, max_length=128, description="New account password")

    @model_validator(mode="before")
    @classmethod
    def populate_token(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "token" not in data and "reset_token" in data:
                data["token"] = data["reset_token"]
        return data


class GenericMessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


# ------------------------------------------------------------------------------
# Authentication Endpoints
# ------------------------------------------------------------------------------

@router.post(
    "/register",
    summary="Register New Auditor Account",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(payload: RegisterRequest):
    """
    Registers a new reviewer account.
    Enforces password strength policies, scrypt salting, and returns an initial access token.
    """
    clean_email = payload.email.strip().lower()

    # Verify duplicate email
    existing = get_user_by_email(clean_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An auditor account is already registered with this email address.",
        )

    # Validate password strength
    strength_err = PasswordHasher.validate_password_strength(payload.password)
    if strength_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=strength_err,
        )

    # Hash password with scrypt
    pwd_hash = PasswordHasher.hash_password(payload.password)
    user_id = str(uuid.uuid4())

    new_user = create_user(
        user_id=user_id,
        name=payload.name,
        email=clean_email,
        password_hash=pwd_hash,
        role="auditor",
    )

    # Generate initial session token
    token_data = create_access_token(
        user_id=new_user["id"],
        email=new_user["email"],
        name=new_user["name"],
        role=new_user["role"],
    )

    return TokenResponse(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        expires_in=token_data["expires_in"],
        expires_at=token_data["expires_at"],
        user=UserProfileResponse(**new_user),
    )


@router.post(
    "/login",
    summary="Auditor Authentication & Session Issuance",
    response_model=TokenResponse,
)
def login_user(payload: LoginRequest):
    """
    Authenticates an auditor by email and password using constant-time verification.
    Issues a signed JWT access token.
    """
    clean_email = payload.email.strip().lower()
    user = get_user_by_email(clean_email)

    # Defend against timing attacks: run a dummy hash check if user not found
    dummy_hash = "$scrypt$n=16384,r=8,p=1$0000000000000000000000000000000000000000000000000000000000000000$0000000000000000000000000000000000000000000000000000000000000000"
    target_hash = user["password_hash"] if user else dummy_hash

    is_valid = PasswordHasher.verify_password(payload.password, target_hash)

    if not user or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the administrator.",
        )

    # Calculate token duration (extended if remember_me is true)
    delta = datetime.timedelta(hours=24) if payload.remember_me else datetime.timedelta(minutes=60)

    token_data = create_access_token(
        user_id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        expires_delta=delta,
    )

    return TokenResponse(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        expires_in=token_data["expires_in"],
        expires_at=token_data["expires_at"],
        user=UserProfileResponse(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
            is_active=bool(user["is_active"]),
        ),
    )


@router.get(
    "/me",
    summary="Get Authenticated Auditor Profile",
    response_model=UserProfileResponse,
)
def get_authenticated_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return UserProfileResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"],
        is_active=bool(current_user["is_active"]),
    )


@router.post(
    "/logout",
    summary="Revoke Current Session Token",
    response_model=GenericMessageResponse,
)
def logout_user(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Terminates the session and revokes the token's JTI so it cannot be reused.
    """
    jti = current_user.get("_jti")
    exp_ts = current_user.get("_exp")
    if jti:
        if exp_ts:
            exp_iso = datetime.datetime.fromtimestamp(exp_ts, tz=datetime.timezone.utc).isoformat()
        else:
            exp_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        revoke_token(jti, current_user["id"], exp_iso)

    return GenericMessageResponse(message="Session successfully terminated and revoked.")


@router.post(
    "/forgot-password",
    summary="Request Password Reset Link",
    response_model=GenericMessageResponse,
)
def request_password_reset(payload: ForgotPasswordRequest, request: Request):
    """
    Issues a short-lived password reset token.
    Always returns a generic constant-time response to prevent user enumeration.
    """
    clean_email = payload.email.strip().lower()
    user = get_user_by_email(clean_email)

    if user and user.get("is_active"):
        # Generate 32-byte cryptographically secure token
        raw_token = secrets.token_urlsafe(32)
        token_digest = hash_token(raw_token)
        expires_iso = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
        ).isoformat()

        store_password_reset_token(token_digest, user["id"], expires_iso)

        # Dispatch reset email
        origin_header = request.headers.get("origin")
        send_password_reset_email(clean_email, raw_token, user["name"], frontend_origin=origin_header)

    return GenericMessageResponse(
        message="If an auditor account is registered with this email, password reset instructions have been issued."
    )


@router.post(
    "/reset-password",
    summary="Complete Password Reset",
    response_model=GenericMessageResponse,
)
def complete_password_reset(payload: ResetPasswordRequest):
    """
    Consumes a password reset token and sets a new account password.
    Enforces password strength policies.
    """
    token_digest = hash_token(payload.token.strip())
    user_id = verify_and_consume_reset_token(token_digest)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset link is invalid, expired, or has already been used.",
        )

    # Validate new password strength
    strength_err = PasswordHasher.validate_password_strength(payload.new_password)
    if strength_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=strength_err,
        )

    # Hash new password with scrypt
    new_hash = PasswordHasher.hash_password(payload.new_password)
    success = update_user_password(user_id, new_hash)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update account password.",
        )

    return GenericMessageResponse(message="Password successfully updated. You may now log in.")
