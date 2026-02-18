import os
import smtplib
from email.message import EmailMessage

def email_enabled() -> bool:
    return os.getenv("SEND_CREDS_EMAILS", "0") == "1"

def send_email(to_email: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_email = os.getenv("SMTP_FROM", user)

    if not host or not user or not password or not to_email:
        raise ValueError("SMTP config missing (SMTP_HOST/USER/PASS) or email missing")

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)
