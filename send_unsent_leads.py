#!/usr/bin/env python3
"""
send_unsent_leads.py - Dedicated script to reach out to all unsent / pending leads in leads.csv.

Usage:
  python send_unsent_leads.py --send             # Live send to all unsent leads
  python send_unsent_leads.py --dry-run          # Preview emails without sending
  python send_unsent_leads.py --send --limit 10  # Send to up to 10 unsent leads
"""

import sys
import io
import time
import random
import argparse
import logging
import csv
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
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from config import (
    CANDIDATE,
    SENDER_EMAIL,
    SENDER_NAME,
    LEADS_CSV,
    SENT_LOG_CSV,
    DEFAULT_RESUME_PATH,
    EMAIL_SEND_DELAY_MIN,
    EMAIL_SEND_DELAY_MAX,
    MAX_EMAILS_PER_SESSION,
)
from src.csv_manager import log_sent_email, load_sent_emails
from src.email_template import generate_subject, generate_email_body, generate_email_html_body
from src.gmail_sender import send_email, test_smtp_connection
from src.post_filter import is_blacklisted, is_location_allowed


def get_truly_unsent_leads(leads_path: Path, sent_log_path: Path) -> list:
    """Finds all leads in leads.csv that have not yet been emailed in sent_log.csv."""
    if not leads_path.exists():
        return []

    sent_emails = load_sent_emails(sent_log_path)
    unsent = []
    seen_in_batch = set()

    try:
        with open(leads_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email", "").strip().lower()
                status = row.get("status", "").strip().lower()

                if not email or "@" not in email:
                    continue
                if status == "blacklisted" or status == "location_excluded":
                    continue
                if email in sent_emails or email in seen_in_batch:
                    continue

                # Safety checks
                b_listed, b_reason = is_blacklisted(
                    email=email,
                    text=row.get("post_snippet", ""),
                    recruiter=row.get("recruiter_name", ""),
                    company=row.get("company_name", ""),
                )
                if b_listed:
                    continue

                loc_ok, _ = is_location_allowed(row.get("post_snippet", ""))
                if not loc_ok:
                    continue

                seen_in_batch.add(email)
                unsent.append(row)
    except Exception as e:
        logger.error(f"Error reading {leads_path}: {e}")

    return unsent


def main():
    parser = argparse.ArgumentParser(description="Send outreach emails to all unsent leads in leads.csv")
    parser.add_argument("--send", action="store_true", help="Send real emails (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode only")
    parser.add_argument("--limit", type=int, default=MAX_EMAILS_PER_SESSION, help="Max emails to send")
    args = parser.parse_args()

    is_live = args.send and not args.dry_run

    print("\n" + "=" * 65)
    print("🚀  JAINAM JAIN - UNSENT LEADS OUTREACH SENDER")
    print("=" * 65)
    print(f" Candidate  : {CANDIDATE['full_name']} ({CANDIDATE.get('degree', 'B.Tech IT')})")
    print(f" CGPA       : {CANDIDATE.get('cgpa', '9.92 / 10')} | {CANDIDATE.get('college', 'TCET Mumbai')}")
    print(f" Sender     : {SENDER_NAME} <{SENDER_EMAIL}>")
    print(f" Mode       : {'🔴 LIVE SEND' if is_live else '🟡 DRY RUN (Preview only)'}")
    print(f" Resume     : {DEFAULT_RESUME_PATH.name} (Exists: {DEFAULT_RESUME_PATH.exists()})")
    print("=" * 65 + "\n")

    if is_live:
        logger.info("Validating Gmail SMTP credentials...")
        ok, msg = test_smtp_connection()
        if not ok:
            logger.error(f"❌ Gmail SMTP verification failed: {msg}")
            return
        logger.info("✅ Gmail SMTP connection confirmed.\n")

    unsent_leads = get_truly_unsent_leads(LEADS_CSV, SENT_LOG_CSV)

    if not unsent_leads:
        print("=" * 65)
        print("✅ ALL LEADS HAVE ALREADY BEEN CONTACTED!")
        print("=" * 65)
        print("• There are 0 pending/unsent leads in data/leads.csv.")
        print(f"• Total emails already sent: {len(load_sent_emails(SENT_LOG_CSV))}")
        print("\n💡 What to do next:")
        print("  1. Run `python main.py --send` to scrape fresh LinkedIn posts & send immediately.")
        print("  2. Apply to new links in `data/application_links.csv`.")
        print("  3. Or paste any LinkedIn post here and I'll send an email right away!")
        print("=" * 65 + "\n")
        return

    batch = unsent_leads[:args.limit]
    logger.info(f"Found {len(unsent_leads)} unsent leads. Processing batch of {len(batch)}...\n")

    sent_count = 0
    failed_count = 0

    for i, lead in enumerate(batch, 1):
        to_email = lead.get("email", "").strip()
        job_role = lead.get("job_role", "Software Engineer Intern")
        recruiter = lead.get("recruiter_name", "Hiring Team")

        subject = generate_subject(lead, CANDIDATE)
        body_text = generate_email_body(lead, CANDIDATE)
        body_html = generate_email_html_body(body_text, lead=lead, candidate=CANDIDATE)

        print("-" * 65)
        print(f"[{i}/{len(batch)}] Target: {to_email} ({recruiter}) | Role: {job_role}")
        print(f"Subject: {subject}")

        if not is_live:
            print("Mode: [DRY RUN] Email not sent.")
            log_sent_email(lead, subject, "dry_run", SENT_LOG_CSV)
            sent_count += 1
            time.sleep(0.5)
        else:
            success, msg = send_email(
                to_email=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachment_path=DEFAULT_RESUME_PATH if DEFAULT_RESUME_PATH.exists() else None,
            )
            if success:
                logger.info(f"✅ Successfully sent email to {to_email}")
                log_sent_email(lead, subject, "sent", SENT_LOG_CSV)
                sent_count += 1
                if i < len(batch):
                    delay = random.uniform(EMAIL_SEND_DELAY_MIN, EMAIL_SEND_DELAY_MAX)
                    logger.info(f"Safe human pause of {delay:.1f}s before next email...")
                    time.sleep(delay)
            else:
                logger.error(f"❌ Failed to send to {to_email}: {msg}")
                log_sent_email(lead, subject, f"failed: {msg}", SENT_LOG_CSV)
                failed_count += 1

    print("\n" + "=" * 65)
    print("🎉  OUTREACH BATCH COMPLETE")
    print("=" * 65)
    print(f" Mode            : {'LIVE SEND' if is_live else 'DRY RUN'}")
    print(f" Sent / Processed: {sent_count}")
    print(f" Failed          : {failed_count}")
    print(f" Sent Log        : {SENT_LOG_CSV}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

