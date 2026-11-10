#!/usr/bin/env python3
"""
test_connection.py - Verifies Gmail SMTP Authentication and Resume File
"""

import sys
import io

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import SENDER_EMAIL, GMAIL_APP_PASSWORD, DEFAULT_RESUME_PATH
from src.gmail_sender import test_smtp_connection

print("=" * 60)
print("[TEST] TESTING JAINAM'S GMAIL CONNECTION & SETUP")
print("=" * 60)
print(f"Sender Email : {SENDER_EMAIL}")
print(f"App Password : {'*' * (len(GMAIL_APP_PASSWORD) - 4) + GMAIL_APP_PASSWORD[-4:] if len(GMAIL_APP_PASSWORD) > 4 else 'Not Set'}")
print(f"Resume Path  : {DEFAULT_RESUME_PATH}")
print(f"Resume Exists: {DEFAULT_RESUME_PATH.exists()}")
print("-" * 60)

ok, msg = test_smtp_connection(SENDER_EMAIL, GMAIL_APP_PASSWORD)
if ok:
    print(f"[SUCCESS] {msg}")
    print("\nYour Gmail is completely set up and authenticated to send outreach emails!")
else:
    print(f"[ERROR] {msg}")
    print("\nPlease verify your Gmail 2-Step Verification and 16-character App Password.")

print("=" * 60)
