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


def send_email(receiver_email: str, subject: str, body: str, sender_email="noreply@waqd.de"):
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
    except Exception as e:
        Logger().debug("Failed to send email to %s: %s", receiver_email, e)


def send_reset_email(receiver_email: str, reset_url: str):
    subject = "WAQD Password Reset"
    body = (
        f"You requested a password reset for your WAQD account.\n\n"
        f"Click the link below to set a new password (valid for 30 minutes):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email."
    )
    send_email(receiver_email, subject, body)
