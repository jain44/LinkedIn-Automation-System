#!/usr/bin/env python3
"""
send_reminders.py - Automated Follow-Up & Reminder System with Reply Detection

Features:
1. IMAP Reply Detection: Automatically connects to your Gmail inbox via IMAP to check
   if any recruiter has replied. If they replied, the reminder is skipped and logged as 'replied'!
2. Days Threshold: Finds outreach emails sent X or more days ago (default: 3 days).
3. Thread Continuation: Keeps the conversation in the same thread using 'Re: <original subject>'.
4. Professional Template: Respectful recap with 9.92 CGPA, tech stack, and 1-page PDF attached.
5. Deduplication: Tracks sent reminders in data/reminder_log.csv so each recruiter receives
   at most 1 follow-up.

Usage:
  python send_reminders.py                   # Dry-run preview of leads eligible for reminders (>=3 days)
  python send_reminders.py --send            # Send live reminder emails via Gmail SMTP
  python send_reminders.py --days 2          # Check for emails sent >= 2 days ago
  python send_reminders.py --days 0 --send   # Send reminders immediately to all unreplied emails
  python send_reminders.py --email <address> # Send a targeted reminder to a specific recruiter
  python send_reminders.py --check-replies   # Only check Gmail inbox to see who replied
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
    SENT_LOG_CSV,
    REMINDER_LOG_CSV,
    EMAIL_SEND_DELAY_MIN,
    EMAIL_SEND_DELAY_MAX,
)
from src.gmail_sender import send_email, test_smtp_connection
from src.reminder_manager import (
    get_eligible_reminders,
    generate_reminder_subject,
    generate_reminder_body,
    log_sent_reminder,
    check_gmail_inbox_replies,
    load_reminder_log,
)


def main():
    parser = argparse.ArgumentParser(description="Follow-up & reminder system for previously sent outreach emails")
    parser.add_argument("--send", action="store_true", help="Send live reminder emails (default is dry-run preview)")
    parser.add_argument("--days", type=float, default=3.0, help="Minimum days elapsed since initial email (default: 3.0)")
    parser.add_argument("--email", type=str, default=None, help="Target a specific email address regardless of elapsed days")
    parser.add_argument("--check-replies", action="store_true", help="Only check Gmail inbox for replies and display status")
    parser.add_argument("--no-check-replies", action="store_true", help="Bypass IMAP inbox reply check")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of reminders to send in this batch")
    args = parser.parse_args()

    is_live = args.send
    min_days = args.days
    target_email = args.email.strip() if args.email else None
    check_replies = not args.no_check_replies

    print("=" * 70)
    print(" 📬 JAINAM JAIN — AUTOMATED OUTREACH REMINDER & FOLLOW-UP ENGINE ")
    print("=" * 70)
    print(f"• Mode: {'🔥 LIVE SEND' if is_live else '👀 DRY-RUN PREVIEW (No emails sent)'}")
    print(f"• Elapsed Threshold: {min_days} day(s)")
    if target_email:
        print(f"• Target Email: {target_email}")
    print(f"• IMAP Reply Check: {'Enabled (imap.gmail.com)' if check_replies else 'Disabled'}")
    print(f"• Resume Attachment: {DEFAULT_RESUME_PATH.name}")
    print(f"• Sent Log Source: {SENT_LOG_CSV}")
    print(f"• Reminder Log: {REMINDER_LOG_CSV}")
    print("-" * 70)

    # 1. Quick check if only checking replies
    if args.check_replies:
        print("🔍 Scanning Gmail inbox for replies from all contacted recruiters...")
        if not SENT_LOG_CSV.exists():
            print("No sent emails found in sent_log.csv.")
            return

        import csv
        emails = []
        with open(SENT_LOG_CSV, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                if row.get("email"):
                    emails.append(row.get("email").strip().lower())

        if not emails:
            print("No recipient emails found in sent_log.csv.")
            return

        reply_map = check_gmail_inbox_replies(SENDER_EMAIL, GMAIL_APP_PASSWORD, emails)
        print("\n📊 Inbox Reply Status Report:")
        for em, replied in reply_map.items():
            status_icon = "🎉 REPLIED!" if replied else "⏳ No reply yet"
            print(f"  • {em:35} : {status_icon}")
        return

    # 2. Check SMTP credentials if live send is requested
    if is_live:
        print("🔐 Verifying Gmail SMTP connection before dispatching...")
        ok, msg = test_smtp_connection(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        if not ok:
            logger.error(f"❌ SMTP Check failed: {msg}")
            sys.exit(1)
        print("✅ SMTP Credentials confirmed.")

    # 3. Find eligible leads
    eligible, reasons = get_eligible_reminders(
        sent_log_path=SENT_LOG_CSV,
        reminder_log_path=REMINDER_LOG_CSV,
        min_days=min_days,
        check_replies=check_replies,
        sender_email=SENDER_EMAIL,
        app_password=GMAIL_APP_PASSWORD,
        target_email=target_email,
    )

    # Print summary of skipped / ineligible leads
    if reasons:
        print("\nℹ️ Status of previously sent outreach:")
        for em, reason in reasons.items():
            print(f"  • {em:35} : {reason}")

    if not eligible:
        print("\n✨ No emails currently need a reminder based on your criteria.")
        print(f"   (Either emails were sent recently, already reminded, or replied).")
        print("=" * 70)
        return

    # Enforce batch limit
    to_process = eligible[: args.limit]
    print(f"\n🎯 Found {len(to_process)} lead(s) eligible for a follow-up reminder:\n")

    for i, lead in enumerate(to_process, 1):
        email = lead.get("email", "")
        role = lead.get("job_role", "")
        recruiter = lead.get("recruiter_name", "Hiring Team")
        days = lead.get("days_elapsed", 0)
        print(f"  [{i}/{len(to_process)}] {email} | {recruiter} | {role} ({days} days elapsed)")

    if not is_live:
        # Show a preview of the reminder email
        sample = to_process[0]
        sub = generate_reminder_subject(sample)
        body_text, _ = generate_reminder_body(sample, CANDIDATE)
        print("\n" + "-" * 70)
        print(f"📝 SAMPLE REMINDER PREVIEW (To: {sample.get('email')}):")
        print(f"Subject: {sub}")
        print("-" * 70)
        print(body_text[:400] + "...\n[Full message + resume will be attached]")
        print("-" * 70)
        print("\n💡 To send live follow-up reminders, re-run with the --send flag:")
        print("   python send_reminders.py --send")
        print("=" * 70)
        return

    # 4. Live sending loop
    print("\n🚀 Beginning live reminder dispatch...")
    sent_count = 0

    for i, lead in enumerate(to_process, 1):
        email = lead.get("email", "")
        recruiter = lead.get("recruiter_name", "Hiring Team")
        role = lead.get("job_role", "")
        subject = generate_reminder_subject(lead)
        body_text, body_html = generate_reminder_body(lead, CANDIDATE)

        print(f"\n[{i}/{len(to_process)}] Sending follow-up to {email} ({recruiter})...")

        success, err_msg = send_email(
            to_email=email,
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
            log_sent_reminder(
                reminder_log_path=REMINDER_LOG_CSV,
                lead=lead,
                subject=subject,
                status="sent",
                notes="Follow-up reminder sent successfully",
            )
            sent_count += 1
            logger.info(f"✅ Follow-up sent to {email} for role '{role}'")
        else:
            logger.error(f"❌ Failed to send follow-up to {email}: {err_msg}")

        # Human-like delay between emails if more remain
        if i < len(to_process):
            delay = random.uniform(EMAIL_SEND_DELAY_MIN, EMAIL_SEND_DELAY_MAX)
            print(f"⏳ Waiting {delay:.1f}s before next email to protect deliverability...")
            time.sleep(delay)

    print("\n" + "=" * 70)
    print(f"🏁 Reminder dispatch complete! Sent: {sent_count}/{len(to_process)}")
    print(f"📁 Logged to: {REMINDER_LOG_CSV}")
    print("=" * 70)


if __name__ == "__main__":
    main()
