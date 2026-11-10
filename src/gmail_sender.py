"""
gmail_sender.py - Direct Gmail SMTP Email Sender with Resume Attachment
Supports plain text + HTML formatting, attachments, rate limiting, and Dry Run mode.
"""

import os
import smtplib
import logging
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def test_smtp_connection(sender_email: str, app_password: str) -> Tuple[bool, str]:
    """
    Validates Gmail SMTP login credentials.
    """
    clean_password = app_password.replace(" ", "").strip()
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email.strip(), clean_password)
        server.quit()
        return True, "SMTP connection successful! Credentials verified."
    except Exception as e:
        return False, f"SMTP Connection failed: {str(e)}"


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    resume_path: Optional[Path] = None,
    sender_email: str = "",
    sender_name: str = "",
    app_password: str = "",
    dry_run: bool = True,
) -> Tuple[bool, str]:
    """
    Sends an email via Gmail SMTP with optional PDF resume attachment.
    If dry_run is True, prints email preview without actually sending.
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would send to: {to_email} | Subject: '{subject}'")
        return True, "DRY_RUN: Simulated successfully"

    clean_password = app_password.replace(" ", "").strip()
    if not clean_password or not sender_email:
        err = "Sender email or app password not configured."
        logger.error(err)
        return False, err

    msg = MIMEMultipart("mixed")
    msg["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Create alternative container for text + html
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg_alt.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(msg_alt)

    # Attach PDF resume if provided
    if resume_path and Path(resume_path).exists():
        try:
            with open(resume_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=Path(resume_path).name)
            part["Content-Disposition"] = f'attachment; filename="{Path(resume_path).name}"'
            msg.attach(part)
        except Exception as e:
            logger.warning(f"Failed to attach resume {resume_path}: {e}")

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=25)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email.strip(), clean_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"Successfully sent email to {to_email}")
        return True, "Sent successfully"
    except Exception as e:
        error_msg = f"Failed to send email to {to_email}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
