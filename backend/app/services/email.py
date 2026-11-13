# =============================================================================
# PROJECT NEXUS AI - Email Service
# =============================================================================
# SMTP-based transactional email service with professional templates.
# All email sending happens on the backend. Credentials never reach frontend.
# =============================================================================

import logging
from email.message import EmailMessage
from typing import Optional

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

ORG_NAME = settings.org_name
ORG_SUPPORT_EMAIL = settings.org_support_email
ORG_WEBSITE = settings.org_website or settings.app_base_url
APP_BASE_URL = settings.app_base_url


def _base_template(title: str, body: str, footer_note: str) -> str:
    """Wrap email content in a branded, responsive HTML template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    @media only screen and (max-width: 600px) {{
      .container {{ width: 100% !important; }}
      .content {{ padding: 15px !important; }}
    }}
    body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    .header {{ background: #1a1a2e; color: #fff; padding: 24px; text-align: center; border-radius: 8px 8px 0 0; }}
    .header h1 {{ margin: 0; font-size: 24px; }}
    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
    .button {{ display: inline-block; background: #4f46e5; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 16px 0; }}
    .button:hover {{ background: #4338ca; }}
    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }}
    .expiration {{ background: #fef3c7; border: 1px solid #f59e0b; color: #92400e; padding: 12px; border-radius: 6px; margin: 16px 0; font-size: 14px; }}
    .warning {{ background: #fecaca; border: 1px solid #ef4444; color: #991b1b; padding: 12px; border-radius: 6px; margin: 16px 0; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{ORG_NAME}</h1>
    </div>
    <div class="content">
      {body}
    </div>
    <div class="footer">
      <p>{ORG_NAME} | {ORG_SUPPORT_EMAIL}</p>
      <p>{footer_note}</p>
    </div>
  </div>
</body>
</html>
"""


def verification_email_template(user_name: str, verification_url: str, expires_hours: int) -> tuple[str, str]:
    subject = f"Verify your email address - {ORG_NAME}"
    body = f"""
    <h2>Welcome to {ORG_NAME}</h2>
    <p>Hello {user_name},</p>
    <p>Thank you for registering. Please verify your email address to activate your account.</p>
    <a href="{verification_url}" class="button">Verify Email Address</a>
    <div class="expiration">
      <strong>This verification link expires in {expires_hours} hours.</strong><br>
      If you did not create an account, please ignore this email.
    </div>
    <p>If the button above doesn't work, copy and paste this link into your browser:<br>
    <code>{verification_url}</code></p>
    """
    footer = f"This is a transactional security email from {ORG_NAME}. You are receiving this because you registered for an account."
    return subject, _base_template(subject, body, footer)


def password_reset_email_template(user_name: str, reset_url: str, expires_hours: int) -> tuple[str, str]:
    subject = f"Reset your password - {ORG_NAME}"
    body = f"""
    <h2>Password Reset Request</h2>
    <p>Hello {user_name},</p>
    <p>You requested a password reset for your {ORG_NAME} account.</p>
    <a href="{reset_url}" class="button">Reset Password</a>
    <div class="expiration">
      <strong>This reset link expires in {expires_hours} hour.</strong><br>
      If you did not request a password reset, please ignore this email and contact {ORG_SUPPORT_EMAIL} immediately.
    </div>
    <p>If the button above doesn't work, copy and paste this link into your browser:<br>
    <code>{reset_url}</code></p>
    """
    footer = f"This is a transactional security email from {ORG_NAME}. For support, contact {ORG_SUPPORT_EMAIL}."
    return subject, _base_template(subject, body, footer)


def account_deletion_confirmation_template(user_name: str, confirm_url: str, grace_days: int) -> tuple[str, str]:
    subject = f"Confirm account deletion - {ORG_NAME}"
    body = f"""
    <h2>Account Deletion Request</h2>
    <p>Hello {user_name},</p>
    <p>We received a request to delete your {ORG_NAME} account.</p>
    <p><strong>Important:</strong> This action is permanent and cannot be undone.</p>
    <a href="{confirm_url}" class="button">Confirm Account Deletion</a>
    <div class="expiration">
      <strong>You have {grace_days} days to cancel this request.</strong><br>
      If you did not request this, click the cancel link below or contact {ORG_SUPPORT_EMAIL} immediately.
    </div>
    <p>To cancel, visit your account settings or reply to this email.</p>
    """
    footer = f"This is a transactional security email from {ORG_NAME}."
    return subject, _base_template(subject, body, footer)


def security_notification_template(user_name: str, subject_line: str, message: str) -> tuple[str, str]:
    subject = f"Security Notice: {subject_line} - {ORG_NAME}"
    body = f"""
    <h2>Security Notice</h2>
    <p>Hello {user_name},</p>
    <p>{message}</p>
    <div class="warning">
      <strong>If you did not perform this action, please secure your account immediately.</strong><br>
      Contact {ORG_SUPPORT_EMAIL} if you need assistance.
    </div>
    """
    footer = f"This is a transactional security email from {ORG_NAME}."
    return subject, _base_template(subject, body, footer)


# ---------------------------------------------------------------------------
# Email sender
# ---------------------------------------------------------------------------

class EmailService:
    """Backend email service using SMTP. Never exposes credentials to frontend."""

    def __init__(self):
        self.configured = settings.is_email_configured()

    async def send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send an email via SMTP. Returns True on success."""
        if not self.configured:
            logger.warning(
                "Email not configured. SMTP credentials missing. "
                "Email to %s would be sent: %s", to_email, subject
            )
            return False

        try:
            message = EmailMessage()
            message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            message["To"] = to_email
            message["Subject"] = subject
            message.add_alternative(html_content, subtype="html")

            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                start_tls=True,
            )
            logger.info("Email sent successfully to %s", to_email)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to_email, type(exc).__name__)
            return False

    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_url: str,
    ) -> bool:
        subject, html = verification_email_template(
            user_name, verification_url, settings.email_verification_expire_hours
        )
        return await self.send(to_email, subject, html)

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_url: str,
    ) -> bool:
        subject, html = password_reset_email_template(
            user_name, reset_url, settings.password_reset_expire_hours
        )
        return await self.send(to_email, subject, html)

    async def send_account_deletion_confirmation(
        self,
        to_email: str,
        user_name: str,
        confirm_url: str,
    ) -> bool:
        subject, html = account_deletion_confirmation_template(
            user_name, confirm_url, settings.account_deletion_grace_period_days
        )
        return await self.send(to_email, subject, html)

    async def send_security_notification(
        self,
        to_email: str,
        user_name: str,
        subject_line: str,
        message: str,
    ) -> bool:
        subject, html = security_notification_template(user_name, subject_line, message)
        return await self.send(to_email, subject, html)


email_service = EmailService()