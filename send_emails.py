#!/usr/bin/env python3
"""
send_emails.py - Dedicated Outreach Sender (Without LinkedIn Scraping)
Sends personalized cold application emails with 1-page resume attached directly to
pending leads in data/leads.csv without opening the Chrome browser or scraping.

Usage:
  python send_emails.py           # Dry-run preview of pending leads
  python send_emails.py --send    # Send real emails via Gmail SMTP
  python send_emails.py --limit 5 # Send to top 5 pending leads
"""

import sys
import io
import time
import random
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
        logging.FileHandler("email_outreach.log", encoding="utf-8"),
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
    LEADS_CSV,
    SENT_LOG_CSV,
    EMAIL_SEND_DELAY_MIN,
    EMAIL_SEND_DELAY_MAX,
)
from src.csv_manager import get_pending_leads, log_sent_email
from src.email_template import generate_subject, generate_email_body, generate_email_html_body
from src.gmail_sender import send_email, test_smtp_connection


def main():
    parser = argparse.ArgumentParser(description="Send outreach emails without scraping")
    parser.add_argument("--send", action="store_true", help="Send live emails (defaults to dry-run preview if omitted)")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of emails to send in this batch")
    args = parser.parse_args()

    live_mode = args.send

    print("=" * 68)
    print("📧  JAINAM JAIN - DIRECT EMAIL OUTREACH (NO SCRAPING)")
    print("=" * 68)
    print(f" Candidate  : {CANDIDATE.get('full_name')} ({CANDIDATE.get('degree')})")
    print(f" CGPA       : {CANDIDATE.get('cgpa')} | TCET Mumbai")
    print(f" Sender     : {SENDER_NAME} <{SENDER_EMAIL}>")
    print(f" Mode       : {'🔴 LIVE SEND (Sending real emails)' if live_mode else '🟢 DRY RUN (Simulation / Preview)'}")
    print(f" Resume     : {DEFAULT_RESUME_PATH.name} (Exists: {DEFAULT_RESUME_PATH.exists()})")
    print("=" * 68 + "\n")

    # Validate Gmail credentials if live
    if live_mode:
        logger.info("Validating Gmail SMTP credentials...")
        ok, msg = test_smtp_connection(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        if not ok:
            logger.error(f"SMTP Auth Failed: {msg}")
            print("\n❌ Cannot send emails: Check SENDER_EMAIL and GMAIL_APP_PASSWORD in .env")
            return
        logger.info("✅ Gmail SMTP connection confirmed.")

    # Read pending leads from data/leads.csv
    pending = get_pending_leads(LEADS_CSV, SENT_LOG_CSV)
    logger.info(f"Found {len(pending)} uncontacted pending lead(s) in {LEADS_CSV.name}")

    if not pending:
        print("\n✅ All leads in data/leads.csv have already been contacted!")
        print("To add new leads:")
        print(f"  1. Add rows to {LEADS_CSV}")
        print("  2. Run 'python main.py' to scrape fresh leads from LinkedIn.\n")
        return

    batch = pending[:args.limit]
    logger.info(f"Processing {len(batch)} lead(s) in this session (limit: {args.limit})...\n")

    sent_count = 0
    failed_count = 0

    for i, lead in enumerate(batch, 1):
        to_email = lead.get("email", "").strip()
        job_role = lead.get("job_role", "Full Stack Developer Intern")
        recruiter = lead.get("recruiter_name", "Hiring Team")

        # Airtight check: Never send emails to blacklisted entities (e.g. The GAO Group, GAO Tek)
        from src.post_filter import is_blacklisted
        blacklisted, b_reason = is_blacklisted(
            email=to_email,
            text=lead.get("post_snippet", ""),
            recruiter=recruiter,
            company=lead.get("company_name", ""),
        )
        if blacklisted:
            logger.warning(f"🚫 [SAFETY BLOCKED] Skipping blacklisted lead: {to_email} ({b_reason})")
            print(f"🚫 [SAFETY BLOCKED] Skipping blacklisted lead: {to_email} ({b_reason})")
            continue

        # Strict check for location constraints: Onsite ONLY in Mumbai, otherwise strictly Remote
        from src.post_filter import is_location_allowed
        loc_ok, loc_reason = is_location_allowed(lead.get("post_snippet", ""))
        if not loc_ok:
            logger.warning(f"🚫 [LOCATION BLOCKED] Skipping lead: {to_email} ({loc_reason})")
            print(f"🚫 [LOCATION BLOCKED] Skipping lead: {to_email} ({loc_reason})")
            continue

        subject = generate_subject(lead, CANDIDATE)
        body_text = generate_email_body(lead, CANDIDATE)
        body_html = generate_email_html_body(body_text, lead=lead, candidate=CANDIDATE)

        print("-" * 68)
        print(f"[{i}/{len(batch)}] TO: {to_email} ({recruiter}) | ROLE: {job_role}")
        print(f"SUBJECT: {subject}")

        if not live_mode:
            print("\n--- [EMAIL PREVIEW (TEXT)] ---")
            print(body_text[:400] + ("\n...[truncated preview]..." if len(body_text) > 400 else ""))
            print("-" * 68 + "\n")
            log_sent_email(lead, subject, "dry_run", SENT_LOG_CSV)
            sent_count += 1
            time.sleep(0.5)
        else:
            success, message = send_email(
                to_email=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                resume_path=DEFAULT_RESUME_PATH,
                sender_email=SENDER_EMAIL,
                sender_name=SENDER_NAME,
                app_password=GMAIL_APP_PASSWORD,
                dry_run=False,
            )

            if success:
                logger.info(f"✅ Successfully sent to {to_email}")
                log_sent_email(lead, subject, "sent", SENT_LOG_CSV)
                sent_count += 1
                if i < len(batch):
                    delay = random.uniform(EMAIL_SEND_DELAY_MIN, EMAIL_SEND_DELAY_MAX)
                    logger.info(f"Delivering safe pause of {delay:.1f}s before next email...")
                    time.sleep(delay)
            else:
                logger.error(f"❌ Failed sending to {to_email}: {message}")
                log_sent_email(lead, subject, f"failed: {message}", SENT_LOG_CSV)
                failed_count += 1

    print("\n" + "=" * 68)
    print("📊 BATCH SUMMARY")
    print("=" * 68)
    print(f" Total Processed : {len(batch)}")
    print(f" Successfully Sent: {sent_count}")
    print(f" Failed           : {failed_count}")
    print(f" Log File         : {SENT_LOG_CSV}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
