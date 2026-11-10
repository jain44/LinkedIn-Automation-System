"""
reminder_manager.py - Manages follow-up reminder emails and automated reply detection.

Capabilities:
1. IMAP Reply Detection: Automatically connects to Gmail via IMAP to check if the recruiter
   has responded in your inbox. If they replied, the reminder is skipped and logged as 'replied'.
2. Elapsed Time Threshold: Identifies outreach emails sent X or more days ago (default: 3 days).
3. Thread Continuation: Follows up using 'Re: <original subject>' in the exact same email thread.
4. Professional Follow-up Content: Courteous reminder highlighting candidate credentials,
   projects, 9.92 CGPA, and re-attaching the 1-page PDF resume.
5. Deduplication: Tracks sent reminders in data/reminder_log.csv so no recruiter receives
   more than one follow-up.
"""

import csv
import logging
import imaplib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

REMINDER_FIELDNAMES = [
    "email",
    "recruiter_name",
    "job_role",
    "original_subject",
    "original_sent_at",
    "reminder_sent_at",
    "days_elapsed",
    "status",
    "notes",
]


def _ensure_file(path: Path, fieldnames: List[str]) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def load_reminder_log(reminder_log_path: Path) -> List[Dict[str, Any]]:
    if not reminder_log_path.exists():
        return []
    rows = []
    try:
        with open(reminder_log_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("email"):
                    rows.append(r)
    except Exception as e:
        logger.warning(f"Could not load reminder log: {e}")
    return rows


def check_gmail_inbox_replies(
    sender_email: str,
    app_password: str,
    emails_to_check: List[str],
) -> Dict[str, bool]:
    """
    Connects to Gmail via IMAP to check if any emails from `emails_to_check`
    exist in the INBOX (indicating the recruiter has replied).
    Returns a dict mapping {email: True (replied) / False (no reply)}.
    """
    results = {e.lower(): False for e in emails_to_check}
    clean_pw = app_password.replace(" ", "").strip()
    if not sender_email or not clean_pw or not emails_to_check:
        return results

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=15)
        mail.login(sender_email.strip(), clean_pw)
        status, _ = mail.select("INBOX", readonly=True)
        if status != "OK":
            mail.logout()
            return results

        for target in emails_to_check:
            clean_target = target.strip().lower()
            try:
                # Search for messages received FROM the recruiter
                search_status, data = mail.search(None, f'(FROM "{clean_target}")')
                if search_status == "OK" and data and data[0]:
                    msg_ids = data[0].split()
                    if len(msg_ids) > 0:
                        results[clean_target] = True
                        logger.info(f"📬 Reply detected in inbox from {clean_target} ({len(msg_ids)} message(s))")
            except Exception as search_err:
                logger.debug(f"IMAP search error for {clean_target}: {search_err}")

        mail.logout()
    except Exception as e:
        logger.warning(f"Could not check Gmail inbox for replies via IMAP: {e}")

    return results


def get_eligible_reminders(
    sent_log_path: Path,
    reminder_log_path: Path,
    min_days: float = 3.0,
    check_replies: bool = True,
    sender_email: str = "",
    app_password: str = "",
    target_email: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Reads sent_log.csv, checks eligibility based on days elapsed, checks for inbox replies,
    and returns:
    (eligible_list, reasons_dict)
    """
    if not sent_log_path.exists():
        return [], {}

    # Already reminded emails
    already_reminded = {
        r.get("email", "").strip().lower()
        for r in load_reminder_log(reminder_log_path)
        if r.get("email") and r.get("status") in ("sent", "replied")
    }

    now = datetime.now()
    eligible = []
    reasons = {}

    sent_rows = []
    with open(sent_log_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("email"):
                sent_rows.append(r)

    # Filter by target_email if specified
    if target_email:
        target_norm = target_email.strip().lower()
        sent_rows = [r for r in sent_rows if r.get("email", "").strip().lower() == target_norm]

    # Batch check inbox replies if enabled
    emails_to_check = [r.get("email", "").strip().lower() for r in sent_rows]
    reply_status_map = {}
    if check_replies and sender_email and app_password:
        logger.info(f"🔍 Checking Gmail inbox for replies from {len(emails_to_check)} candidate emails...")
        reply_status_map = check_gmail_inbox_replies(sender_email, app_password, emails_to_check)

    for r in sent_rows:
        email = r.get("email", "").strip().lower()
        if not email:
            continue

        if email in already_reminded:
            reasons[email] = "Reminder already sent previously"
            continue

        if reply_status_map.get(email, False):
            reasons[email] = "Recruiter has already replied! (Skipping reminder)"
            # Log as replied so it's tracked
            log_sent_reminder(
                reminder_log_path=reminder_log_path,
                lead=r,
                subject=r.get("subject", ""),
                status="replied",
                notes="Response detected in Gmail inbox",
            )
            already_reminded.add(email)
            continue

        sent_at_str = r.get("sent_at", "")
        days_elapsed = 0.0
        if sent_at_str:
            try:
                sent_dt = datetime.strptime(sent_at_str, "%Y-%m-%d %H:%M:%S")
                days_elapsed = (now - sent_dt).total_seconds() / 86400.0
            except Exception:
                try:
                    sent_dt = datetime.fromisoformat(sent_at_str)
                    days_elapsed = (now - sent_dt).total_seconds() / 86400.0
                except Exception:
                    pass

        # If targeting a specific email, bypass the min_days threshold
        if target_email or days_elapsed >= min_days:
            r["days_elapsed"] = round(days_elapsed, 1)
            eligible.append(r)
        else:
            reasons[email] = f"Only {days_elapsed:.1f} days elapsed (threshold: {min_days} days)"

    return eligible, reasons


def log_sent_reminder(
    reminder_log_path: Path,
    lead: Dict[str, Any],
    subject: str,
    status: str = "sent",
    notes: str = "",
) -> None:
    """
    Logs sent reminder to data/reminder_log.csv.
    """
    _ensure_file(reminder_log_path, REMINDER_FIELDNAMES)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(reminder_log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REMINDER_FIELDNAMES)
        writer.writerow({
            "email": lead.get("email", "").strip().lower(),
            "recruiter_name": lead.get("recruiter_name", ""),
            "job_role": lead.get("job_role", ""),
            "original_subject": lead.get("subject", ""),
            "original_sent_at": lead.get("sent_at", ""),
            "reminder_sent_at": now_str,
            "days_elapsed": lead.get("days_elapsed", ""),
            "status": status,
            "notes": notes,
        })


def generate_reminder_subject(lead: Dict[str, Any]) -> str:
    """
    Keeps email in the exact same conversation thread using 'Re: <subject>'.
    """
    orig_sub = lead.get("subject", "").strip()
    if not orig_sub:
        role = lead.get("job_role", "Developer Intern")
        return f"Following up: {role} Application - Jainam Jain"
    if orig_sub.lower().startswith("re:"):
        return orig_sub
    return f"Re: {orig_sub}"


def generate_reminder_body(lead: Dict[str, Any], candidate: Dict[str, Any]) -> Tuple[str, str]:
    """
    Generates plain-text and rich HTML body for a polite, value-driven follow-up.
    """
    recruiter = lead.get("recruiter_name", "").strip()
    # Filter placeholder recruiter names
    if not recruiter or recruiter.lower() in ("hiring team", "n/a", "none", "unknown"):
        salutation = "Dear Hiring Team,"
    else:
        # Take first name if personal name
        first = recruiter.split()[0]
        salutation = f"Hi {first},"

    role = lead.get("job_role", "Developer Intern")
    name = candidate.get("full_name", "Jainam Jain")
    cgpa = candidate.get("cgpa", "9.92 / 10")
    college = candidate.get("college", "TCET Mumbai")
    phone = candidate.get("phone", "+91 79779 63474")
    email = candidate.get("email", "jainamjain1116@gmail.com")
    github = candidate.get("github", "https://github.com/jain44")
    linkedin = candidate.get("linkedin", "https://www.linkedin.com/in/jainam-jain-746188263")
    resume_drive_link = candidate.get("resume_drive_link") or "https://drive.google.com/file/d/1K_q0i7hr_CFEbV4ec5Y3pS_ts-fLi5zs/view?usp=drivesdk"

    body_text = f"""{salutation}

I hope you're having a productive week!

I wanted to briefly follow up on my previous application regarding the {role} position. 

I remain genuinely excited about the opportunity to contribute to your engineering initiatives. As a quick recap:
- 🎓 B.Tech IT (Minor in AI) at {college} with a {cgpa} CGPA.
- 💻 Hands-on experience across React, Next.js, Node.js, Python, FastAPI, and GenAI / LLM agent architectures.
- 🚀 Built and deployed live systems: Financial Crime Agent, GrowthOS, Kavach (Sentinel), JusticeAI, Samyak.
- ⚡ Available for immediate full-time or part-time internship (Remote or Mumbai).

I have re-attached my 1-page resume for your convenience. Please feel free to check out my code and live projects on GitHub ({github}) and LinkedIn ({linkedin}).

I would welcome the chance to speak with you or complete any preliminary technical assessment. Thank you again for your time!

Warm regards,
{name}
{phone} | {email}
GitHub: {github}
LinkedIn: {linkedin}
"""

    body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px; }}
    .container {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .header {{ background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: #ffffff; padding: 24px; }}
    .header h2 {{ margin: 0 0 6px 0; font-size: 20px; font-weight: 600; letter-spacing: -0.01em; }}
    .header p {{ margin: 0; font-size: 13px; opacity: 0.9; }}
    .content {{ padding: 28px 24px; }}
    .salutation {{ font-size: 15px; font-weight: 600; margin-bottom: 16px; color: #0f172a; }}
    .p {{ font-size: 14px; margin-bottom: 16px; color: #334155; line-height: 1.65; }}
    .card {{ background: #f1f5f9; border-left: 4px solid #2563eb; border-radius: 6px; padding: 14px 16px; margin: 18px 0; }}
    .card-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; color: #475569; margin-bottom: 8px; }}
    .card ul {{ margin: 0; padding-left: 18px; font-size: 13px; color: #334155; }}
    .card li {{ margin-bottom: 5px; }}
    .links-bar {{ display: flex; gap: 12px; margin: 20px 0; }}
    .btn {{ display: inline-block; background: #2563eb; color: #ffffff !important; text-decoration: none; font-size: 13px; font-weight: 600; padding: 8px 16px; border-radius: 6px; }}
    .btn-secondary {{ display: inline-block; background: #f1f5f9; color: #0f172a !important; text-decoration: none; font-size: 13px; font-weight: 600; padding: 8px 16px; border-radius: 6px; border: 1px solid #cbd5e1; margin-left: 8px; }}
    .footer {{ border-top: 1px solid #e2e8f0; padding: 20px 24px; background: #fafafa; font-size: 12px; color: #64748b; }}
    .footer strong {{ color: #0f172a; font-size: 13px; display: block; margin-bottom: 2px; }}
    .badge {{ display: inline-block; background: #dbeafe; color: #1e40af; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; margin-top: 4px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>Following Up: {role} Application</h2>
      <p>Quick status check & application recap</p>
    </div>
    <div class="content">
      <div class="salutation">{salutation}</div>
      <p class="p">I hope you're having a productive week!</p>
      <p class="p">I wanted to briefly follow up on my previous application regarding the <strong>{role}</strong> position. I remain genuinely excited about the opportunity to contribute to your engineering initiatives.</p>
      
      <div class="card">
        <div class="card-title">Quick Candidate Recap</div>
        <ul>
          <li><strong>Education:</strong> B.Tech IT (Minor in AI) at {college} • <span style="color: #2563eb; font-weight: 600;">{cgpa} CGPA</span></li>
          <li><strong>Technical Stack:</strong> React, Next.js, Node.js, Python, FastAPI, Groq LLMs & Autonomous Agents</li>
          <li><strong>Key Builds:</strong> Financial Crime Agent, GrowthOS, Kavach (Sentinel), JusticeAI, Samyak</li>
          <li><strong>Availability:</strong> Immediate • Remote or Mumbai Hybrid</li>
        </ul>
      </div>

      <p class="p">I've re-attached my 1-page resume for your convenience. Please let me know if you would like to schedule a brief introductory call or if there's any technical assessment I can complete.</p>

      <div style="margin: 22px 0;">
        <a href="{resume_drive_link}" class="btn" style="background-color: #2563eb; margin-right: 8px;">View Resume (Drive)</a>
        <a href="{github}" class="btn" style="margin-right: 8px;">View GitHub Portfolio</a>
        <a href="{linkedin}" class="btn-secondary">View LinkedIn Profile</a>
      </div>
    </div>
    
    <div class="footer">
      <strong>{name}</strong>
      <span>{phone} • {email}</span><br>
      <span class="badge">📎 1-Page Resume Attached (PDF)</span>
    </div>
  </div>
</body>
</html>"""

    return body_text.strip(), body_html.strip()
