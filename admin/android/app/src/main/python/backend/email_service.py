"""SMTP email service — real delivery, no mocks.

Uses Python's stdlib smtplib. No external dependency.
Designed for Gmail App Password (smtp.gmail.com:465 SSL),
but works with any SMTP provider (SendGrid, Mailgun, Zoho...).

Configuration is read from Settings (env vars):
  FS_SMTP_HOST  — default smtp.gmail.com
  FS_SMTP_PORT  — default 465
  FS_SMTP_USER  — full email address
  FS_SMTP_PASS  — App Password (NOT your Gmail login password)
  FS_SMTP_FROM  — optional; defaults to FS_SMTP_USER

If FS_SMTP_USER/FS_SMTP_PASS are empty, `enabled` is False and
calls return False. The API layer must check `.enabled` first.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid

logger = logging.getLogger("familysafety.email")


class EmailService:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str = "",
        timeout_s: int = 15,
    ) -> None:
        self.host = host or "smtp.gmail.com"
        self.port = int(port) if port else 465
        self.user = (user or "").strip()
        self.password = (password or "").strip()
        self.from_addr = (from_addr or self.user).strip()
        self.timeout_s = timeout_s
        self._enabled = bool(self.user and self.password)

    @property
    def enabled(self) -> bool:
        return self._enabled

    # -----------------------------------------------------------------
    # Public
    # -----------------------------------------------------------------

    def send_verification_code(
        self,
        to_email: str,
        code: str,
        ttl_minutes: int = 15,
        app_name: str = "Family Guard",
    ) -> bool:
        """Send the 6-digit code. Returns True on success."""
        if not self._enabled:
            logger.warning(
                "email disabled (FS_SMTP_USER/FS_SMTP_PASS missing) — "
                "cannot send to %s",
                to_email,
            )
            return False

        subject = f"{app_name} — Password Reset Code"
        text_body, html_body = _render_code_email(
            code=code, ttl_minutes=ttl_minutes, app_name=app_name,
        )
        return self._send(to_email, subject, text_body, html_body)

    # -----------------------------------------------------------------
    # Low-level
    # -----------------------------------------------------------------

    def _send(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr(("Family Guard", self.from_addr))
            msg["To"] = to_email
            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain=self.from_addr.split("@")[-1])

            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                self.host, self.port, context=context, timeout=self.timeout_s,
            ) as server:
                server.login(self.user, self.password)
                server.sendmail(self.from_addr, [to_email], msg.as_string())

            logger.info("verification code email sent to %s", to_email)
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP auth failed (check FS_SMTP_USER/FS_SMTP_PASS): %s", e)
            return False
        except smtplib.SMTPException as e:
            logger.error("SMTP error sending to %s: %s", to_email, e)
            return False
        except (OSError, ssl.SSLError) as e:
            logger.error("network/SSL error sending to %s: %s", to_email, e)
            return False
        except Exception as e:
            logger.exception("unexpected email error: %s", e)
            return False


# ---------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------

def _render_code_email(code: str, ttl_minutes: int, app_name: str):
    text = (
        f"{app_name} — Password Reset\n"
        f"\n"
        f"Your verification code is:\n"
        f"\n"
        f"    {code}\n"
        f"\n"
        f"This code expires in {ttl_minutes} minutes.\n"
        f"If you did not request a PIN reset, ignore this email.\n"
        f"\n"
        f"— Family Safety"
    )

    html = f"""\
<!DOCTYPE html>
<html><body style="font-family:Arial,Helvetica,sans-serif;color:#111;">
  <div style="max-width:520px;margin:24px auto;padding:24px;
              border:1px solid #e0e0e0;border-radius:12px;">
    <h2 style="margin:0 0 8px 0;color:#1976d2;">{app_name}</h2>
    <p style="margin:0 0 16px 0;color:#666;">Password Reset</p>

    <p>Your verification code is:</p>
    <div style="font-size:32px;letter-spacing:8px;font-weight:bold;
                background:#f5f5f5;padding:16px;text-align:center;
                border-radius:8px;font-family:monospace;">{code}</div>

    <p style="margin-top:16px;">This code expires in
       <strong>{ttl_minutes} minutes</strong>.</p>

    <p style="color:#888;font-size:12px;margin-top:24px;">
      If you did not request a PIN reset, you can safely ignore this email.
    </p>
  </div>
</body></html>
"""
    return text, html


# ---------------------------------------------------------------------
# Factory — read from Settings
# ---------------------------------------------------------------------

def build_default_service() -> EmailService:
    """Build an EmailService from backend.config.settings."""
    from .config import settings
    return EmailService(
        host=getattr(settings, "smtp_host", "smtp.gmail.com"),
        port=getattr(settings, "smtp_port", 465),
        user=getattr(settings, "smtp_user", ""),
        password=getattr(settings, "smtp_pass", ""),
        from_addr=getattr(settings, "smtp_from", ""),
    )
