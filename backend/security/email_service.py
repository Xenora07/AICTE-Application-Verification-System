"""
backend/security/email_service.py - Safe Email Dispatcher for Password Resets.
Transmits password-reset links using SMTP when configured, or routes to an isolated
debug sink in local development without exposing tokens in public logs or API responses.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger("aicte.auth.email")


def send_password_reset_email(
    to_email: str,
    raw_token: str,
    recipient_name: str,
    frontend_origin: Optional[str] = None,
) -> bool:
    """
    Dispatches a password reset link to the user.
    Uses SMTP if credentials are provided; otherwise logs a private debug notice.
    """
    base_url = frontend_origin or os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
    reset_link = f"{base_url}?view=reset-password&token={raw_token}"

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@aicte-india.org")
    use_tls = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "AICTE Application Verification System — Password Reset Request"
            msg["From"] = f"AICTE Compliance Portal <{from_email}>"
            msg["To"] = to_email

            text_content = (
                f"Hello {recipient_name},\n\n"
                f"A password reset was requested for your AICTE Application Verification System account.\n"
                f"To set a new password, click the link below (valid for 15 minutes):\n\n"
                f"{reset_link}\n\n"
                f"If you did not request this, please disregard this email.\n"
            )

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 580px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #452c1e; margin-bottom: 8px;">Password Reset Request</h2>
                <p style="color: #475569; font-size: 14px;">Hello <strong>{recipient_name}</strong>,</p>
                <p style="color: #475569; font-size: 14px;">A password reset was requested for your AICTE Application Verification System auditor account.</p>
                <div style="margin: 24px 0;">
                    <a href="{reset_link}" style="background-color: #452c1e; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; display: inline-block;">Reset Password</a>
                </div>
                <p style="color: #94a3b8; font-size: 12px;">This link will expire in 15 minutes and can only be used once.</p>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 16px;">If the button does not work, copy and paste this URL into your browser:<br/><span style="color: #64748b; word-break: break-all;">{reset_link}</span></p>
            </div>
            """

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if use_tls:
                    server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info(f"Password reset email dispatched to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch reset email via SMTP: {e}")
            return False
    else:
        # Development fallback notice: SMTP is not configured
        is_production = os.getenv("ENVIRONMENT", "").lower() in ("production", "prod") or os.getenv("AICTE_ENV", "").lower() in ("production", "prod")
        if is_production:
            logger.warning(
                f"Password reset requested for {to_email}, but SMTP email delivery is unconfigured. "
                "Token suppressed for production security."
            )
        else:
            logger.info(
                f"[LOCAL DEV NOTICE] Password reset token generated for {to_email}. "
                f"SMTP not configured; local test link: {reset_link}"
            )
        return False
