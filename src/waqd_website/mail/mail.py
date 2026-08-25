import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from waqd.base.file_logger import Logger

# Email configuration
EMAIL_SERVER = os.getenv("WAQD_EMAIL_SERVER", "")
EMAIL_LOGIN = os.getenv("WAQD_EMAIL_LOGIN", "")
EMAIL_PW = os.getenv("WAQD_EMAIL_PASSWORD", "")
EMAIL_PORT = int(os.getenv("WAQD_EMAIL_PORT", "587"))


def send_email(
    receiver_email: str, subject: str, body: str, sender_email="noreply@waqd.de"
) -> bool:
    """Send an email and report whether SMTP accepted it for delivery."""
    if not EMAIL_SERVER or not EMAIL_LOGIN or not EMAIL_PW:
        Logger().error("Email delivery is not configured; refusing to send email")
        return False

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_LOGIN, EMAIL_PW)
            server.sendmail(sender_email, receiver_email, message.as_string())
            Logger().debug("Email sent to receiver_email: %s", receiver_email)
            return True
    except Exception as e:
        Logger().error("Failed to send email to %s: %s", receiver_email, e)
        return False


def send_reset_email(receiver_email: str, reset_url: str):
    subject = "WAQD Password Reset"
    body = (
        f"You requested a password reset for your WAQD account.\n\n"
        f"Click the link below to set a new password (valid for 30 minutes):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email."
    )
    return send_email(receiver_email, subject, body)


def send_verification_email(receiver_email: str, verification_url: str):
    subject = "WAQD Email Verification"
    body = (
        "Please verify your WAQD account by clicking the link below (valid for 30 minutes):\n\n"
        f"{verification_url}\n\n"
        "If you did not create this account, you can safely ignore this email."
    )
    return send_email(receiver_email, subject, body)
