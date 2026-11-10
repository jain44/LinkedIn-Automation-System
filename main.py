#!/usr/bin/env python3
"""
main.py - Main Runner for Jainam's Tech Internship Automation
Scrapes live LinkedIn internship postings and conducts personalized cold email outreach.
"""

import sys
import io
import os
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("internship_automation.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

from config import (
    CANDIDATE,
    SENDER_EMAIL,
    GMAIL_APP_PASSWORD,
    SENDER_NAME,
    DRY_RUN,
    DEFAULT_RESUME_PATH,
    DEFAULT_SEARCH_KEYWORDS,
    LEADS_CSV,
    SENT_LOG_CSV,
    EMAIL_SEND_DELAY_MIN,
    EMAIL_SEND_DELAY_MAX,
    MAX_EMAILS_PER_SESSION,
)
from src.linkedin_scraper import run_scraper
from src.csv_manager import save_leads, get_pending_leads, log_sent_email
from src.email_template import generate_subject, generate_email_body, generate_email_html_body
from src.gmail_sender import send_email, test_smtp_connection


def print_banner(live_mode: bool):
    print("=" * 65)
    print("🚀  JAINAM JAIN - TECH INTERNSHIP OUTREACH AUTOMATION")
    print("=" * 65)
    print(f" Candidate  : {CANDIDATE.get('full_name')} ({CANDIDATE.get('degree')})")
    print(f" CGPA       : {CANDIDATE.get('cgpa')} | TCET Mumbai")
    print(f" Sender     : {SENDER_NAME} <{SENDER_EMAIL}>")
    print(f" Mode       : {'🔴 LIVE SEND (Real emails will be sent)' if live_mode else '🟢 DRY RUN (Simulation only)'}")
    print(f" Resume     : {DEFAULT_RESUME_PATH.name} (Exists: {DEFAULT_RESUME_PATH.exists()})")
    print("=" * 65 + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Jainam Tech Internship LinkedIn Automation")
    parser.add_argument("--send", action="store_true", help="Send live emails (overrides DRY_RUN=true in .env)")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping and process existing pending leads")
    parser.add_argument("--keywords", nargs="+", help="Specific search keywords to use")
    parser.add_argument("--time-filter", choices=["past-24h", "past-week", "past-month"], default="past-week", help="Time filter for LinkedIn search")
    parser.add_argument("--limit", type=int, default=MAX_EMAILS_PER_SESSION, help="Max emails to send this session")
    return parser.parse_args()


def main():
    args = parse_args()
    live_send = args.send or (not DRY_RUN)
    dry_run = not live_send

    print_banner(live_mode=live_send)

    # 1. Test SMTP credentials
    if live_send:
        logger.info("Validating Gmail SMTP credentials...")
        ok, msg = test_smtp_connection(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        if not ok:
            logger.error(f"❌ Gmail SMTP verification failed: {msg}")
            print("\nPlease check your GMAIL_APP_PASSWORD in .env before running live send.")
            sys.exit(1)
        logger.info("✅ Gmail SMTP connection confirmed.")

    # 2. LinkedIn Scraping Phase
    if not args.skip_scrape:
        keywords = args.keywords if args.keywords else DEFAULT_SEARCH_KEYWORDS
        logger.info(f"Initiating scraping across {len(keywords)} internship keywords...")
        discovered_leads = run_scraper(keywords=keywords, time_filter=args.time_filter)
        new_count = save_leads(discovered_leads, LEADS_CSV)
        logger.info(f"Scrape step finished. {new_count} new leads added.")
    else:
        logger.info("Skipping scraping step (--skip-scrape). Reading existing leads...")

    # 3. Outreach Phase
    pending_leads = get_pending_leads(LEADS_CSV, SENT_LOG_CSV)
    logger.info(f"Found {len(pending_leads)} pending leads to reach out to.")

    if not pending_leads:
        from config import APPLICATION_LINKS_CSV, APPLICATION_LINKS_MD
        from src.csv_manager import load_saved_apply_links
        apply_links_count = len(load_saved_apply_links(APPLICATION_LINKS_CSV))
        print("\n" + "=" * 65)
        print("✅ SCRAPING & HARVESTING COMPLETE")
        print("=" * 65)
        if apply_links_count > 0:
            print(f"📋 Found & Saved {apply_links_count} Application Links / Google Forms!")
            print(f"👉 Clickable Dashboard : {APPLICATION_LINKS_MD}")
            print(f"👉 Full CSV Data File   : {APPLICATION_LINKS_CSV}")
        print("✉️  No uncontacted email leads pending in leads.csv.")
        print("=" * 65 + "\n")
        return

    leads_to_process = pending_leads[:args.limit]
    logger.info(f"Processing batch of {len(leads_to_process)} leads (Session limit: {args.limit})...\n")

    sent_count = 0
    failed_count = 0

    for i, lead in enumerate(leads_to_process, 1):
        to_email = lead.get("email", "").strip()
        job_role = lead.get("job_role", "Software Engineer Intern")
        recruiter = lead.get("recruiter_name", "Team")

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

        print("-" * 60)
        print(f"[{i}/{len(leads_to_process)}] Target: {to_email} ({recruiter}) | Role: {job_role}")
        print(f"Subject: {subject}")

        if dry_run:
            print("\n--- [PREVIEW BODY] ---")
            print(body_text[:350] + "\n...[truncated for preview]...\n")
            log_sent_email(lead, subject, "dry_run", SENT_LOG_CSV)
            sent_count += 1
            time.sleep(1.0)
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
                log_sent_email(lead, subject, "sent", SENT_LOG_CSV)
                sent_count += 1
                delay = random.uniform(EMAIL_SEND_DELAY_MIN, EMAIL_SEND_DELAY_MAX)
                logger.info(f"Delivering safe pause of {delay:.1f}s before next email...")
                time.sleep(delay)
            else:
                log_sent_email(lead, subject, f"failed: {message}", SENT_LOG_CSV)
                failed_count += 1

    print("\n" + "=" * 60)
    print("🎉  SESSION COMPLETED")
    print("=" * 60)
    print(f" Mode            : {'LIVE SEND' if live_send else 'DRY RUN'}")
    print(f" Emails Processed: {sent_count}")
    print(f" Failed          : {failed_count}")
    print(f" Sent Log        : {SENT_LOG_CSV}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
