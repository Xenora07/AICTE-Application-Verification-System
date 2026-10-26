"""
backend/database package initialization.
"""
from backend.database.auth_db import (
    init_auth_db,
    get_db_connection,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_password,
    revoke_token,
    is_token_revoked,
    store_password_reset_token,
    verify_and_consume_reset_token,
)

__all__ = [
    "init_auth_db",
    "get_db_connection",
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "update_user_password",
    "revoke_token",
    "is_token_revoked",
    "store_password_reset_token",
    "verify_and_consume_reset_token",
]
