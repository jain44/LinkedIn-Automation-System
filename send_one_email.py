#!/usr/bin/env python3
"""
send_one_email.py - Send a targeted email to a specific recruiter / company.
Usage:
  python send_one_email.py <email> [job_role] [company_or_recruiter_name] [--dry-run]
"""

import sys
import io
import argparse
import logging
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

from config import (
    CANDIDATE,
    SENDER_EMAIL,
    GMAIL_APP_PASSWORD,
    SENDER_NAME,
    DEFAULT_RESUME_PATH,
    SENT_LOG_CSV,
)
from src.csv_manager import log_sent_email
from src.email_template import generate_subject, generate_email_body, generate_email_html_body
from src.gmail_sender import send_email, test_smtp_connection


def main():
    parser = argparse.ArgumentParser(description="Send a single outreach email with resume attached")
    parser.add_argument("email", type=str, help="Recipient email address")
    parser.add_argument("role", type=str, nargs="?", default="Web Developer Intern", help="Job role")
    parser.add_argument("recruiter", type=str, nargs="?", default="Hiring Team", help="Recruiter or Company Name")
    parser.add_argument("--subject", type=str, default="", help="Custom subject line")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not send")
    args = parser.parse_args()

    to_email = args.email.strip()
    job_role = args.role.strip()
    recruiter_name = args.recruiter.strip()
    custom_subject = args.subject.strip()
    is_dry_run = args.dry_run

    logger.info(f"Target Recipient: {to_email}")
    logger.info(f"Role: {job_role}")
    logger.info(f"Recruiter/Company: {recruiter_name}")
    logger.info(f"Resume: {DEFAULT_RESUME_PATH}")
    logger.info(f"Mode: {'DRY RUN' if is_dry_run else 'LIVE SEND'}")

    if not is_dry_run:
        ok, msg = test_smtp_connection(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        if not ok:
            logger.error(f"SMTP Connection check failed: {msg}")
            sys.exit(1)
        logger.info("SMTP Credentials verified.")

    lead = {
        "email": to_email,
        "recruiter_name": recruiter_name,
        "job_role": job_role,
        "score": 100,
    }

    subject = custom_subject if custom_subject else generate_subject(lead, CANDIDATE)
    body_text = generate_email_body(lead, CANDIDATE)
    body_html = generate_email_html_body(plain_body=body_text, lead=lead, candidate=CANDIDATE)

    success, msg = send_email(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        resume_path=DEFAULT_RESUME_PATH,
        sender_email=SENDER_EMAIL,
        sender_name=SENDER_NAME,
        app_password=GMAIL_APP_PASSWORD,
        dry_run=is_dry_run,
    )

    if success:
        if not is_dry_run:
            log_sent_email(
                lead=lead,
                subject=subject,
                sent_log_path=SENT_LOG_CSV,
                status="sent",
            )
            logger.info(f"✅ Email successfully sent to {to_email} and logged to {SENT_LOG_CSV.name}!")
        else:
            logger.info(f"✅ [DRY RUN SUCCESS] Email generated and ready to send to {to_email}.")
    else:
        logger.error(f"❌ Failed to send email to {to_email}: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
