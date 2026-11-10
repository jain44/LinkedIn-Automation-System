#!/usr/bin/env python3
"""
dashboard_server.py - Live Analytics & Outreach Control Server for Jainam Jain
Serves the web dashboard frontend and provides real-time JSON API for outreach stats,
delivered emails, discovered leads, auto-commented posts, and application forms.

Usage:
    python dashboard_server.py           # Starts server on port 5050
    python dashboard_server.py --port 5055
"""

import os
import sys
import json
import csv
import io
import mimetypes
import subprocess
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Set UTF-8 output encoding
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DASHBOARD_DIR = BASE_DIR / "dashboard"
LEADS_CSV = DATA_DIR / "leads.csv"
SENT_LOG_CSV = DATA_DIR / "sent_log.csv"
COMMENTED_JSON = DATA_DIR / "commented_posts.json"
APP_LINKS_CSV = DATA_DIR / "application_links.csv"
APP_LINKS_MD = DATA_DIR / "application_links.md"
REMINDER_LOG_CSV = DATA_DIR / "reminder_log.csv"
CANDIDATE_JSON = BASE_DIR / "candidate_data.json"
LOG_FILE = BASE_DIR / "internship_automation.log"

DEFAULT_PORT = 5050



def is_engine_running() -> bool:
    """Checks if the LinkedIn outreach scraper or sender is actively running."""
    try:
        if os.name == "nt":
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Process python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            # If more than 1 python process (this server is 1, scraper is another)
            pids = [p.strip() for p in res.stdout.strip().splitlines() if p.strip()]
            return len(pids) > 1
        return False
    except Exception:
        return False


def load_candidate_data() -> dict:
    if CANDIDATE_JSON.exists():
        try:
            with open(CANDIDATE_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "full_name": "Jainam Jain",
        "cgpa": "9.92 / 10",
        "college": "Thakur College of Engineering and Technology (TCET), Mumbai",
        "degree": "B.Tech IT + Minor in AI, 2024-2028",
        "email": "jainamjain1116@gmail.com",
        "phone": "+91 79779 63474",
        "github": "https://github.com/jain44",
        "linkedin": "https://www.linkedin.com/in/jainam-jain-746188263",
    }


def load_sent_log() -> list:
    if not SENT_LOG_CSV.exists():
        return []
    
    # Map recruiter phone numbers and WhatsApp links by email from leads.csv
    lead_phone_map = {}
    if LEADS_CSV.exists():
        try:
            with open(LEADS_CSV, "r", encoding="utf-8", errors="replace") as lf:
                reader = csv.DictReader(lf)
                for r in reader:
                    e = r.get("email", "").strip().lower()
                    p = r.get("phone_number", "").strip()
                    if e and p:
                        lead_phone_map[e] = {
                            "phone_number": p,
                            "whatsapp_link": r.get("whatsapp_link", "").strip(),
                        }
        except Exception:
            pass

    rows = []
    try:
        with open(SENT_LOG_CSV, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("email"):
                    email_key = r.get("email", "").strip().lower()
                    if email_key in lead_phone_map:
                        r["phone_number"] = lead_phone_map[email_key]["phone_number"]
                        r["whatsapp_link"] = lead_phone_map[email_key]["whatsapp_link"]
                    rows.append(r)
    except Exception:
        pass
    return rows


def load_leads() -> list:
    if not LEADS_CSV.exists():
        return []
    rows = []
    sent_emails = {r.get("email", "").strip().lower() for r in load_sent_log() if r.get("email")}
    try:
        with open(LEADS_CSV, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                email_clean = r.get("email", "").strip().lower()
                phone = r.get("phone_number", "").strip()
                if email_clean or phone:
                    from src.post_filter import is_blacklisted, is_location_allowed
                    is_b, _ = is_blacklisted(
                        email=email_clean,
                        text=r.get("post_snippet", ""),
                        recruiter=r.get("recruiter_name", ""),
                        company=r.get("company_name", ""),
                    )
                    loc_ok, _ = is_location_allowed(r.get("post_snippet", ""))
                    if is_b or r.get("status") == "blacklisted":
                        r["status"] = "blacklisted"
                    elif not loc_ok or r.get("status") == "location_excluded":
                        r["status"] = "location_excluded"
                    elif email_clean and email_clean in sent_emails:
                        r["status"] = "sent"
                    elif not email_clean and phone:
                        r["status"] = r.get("status") or "whatsapp_pending"
                    else:
                        r["status"] = "pending"
                    rows.append(r)
    except Exception:
        pass
    return rows


def load_commented_posts() -> list:
    if not COMMENTED_JSON.exists():
        return []
    unique_posts = []
    seen_identifiers = set()
    try:
        with open(COMMENTED_JSON, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
            for key, entry in data.items():
                if not isinstance(entry, dict):
                    continue
                # Unique key preference: fingerprint, then post_snippet, then post_key
                fp = entry.get("fingerprint") or entry.get("post_key") or key
                snippet = (entry.get("post_snippet") or "")[:80]
                ident = fp if fp else snippet
                if ident and ident in seen_identifiers:
                    continue
                seen_identifiers.add(ident)
                unique_posts.append(entry)
    except Exception:
        pass
    # Sort latest first
    unique_posts.sort(key=lambda x: x.get("commented_at", ""), reverse=True)
    return unique_posts


def load_application_links() -> list:
    if not APP_LINKS_CSV.exists():
        return []
    rows = []
    try:
        with open(APP_LINKS_CSV, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("apply_link"):
                    rows.append(r)
    except Exception:
        pass
    # Sort latest first
    rows.sort(key=lambda x: x.get("discovered_at", ""), reverse=True)
    return rows


def get_recent_logs(max_lines: int = 40) -> list:
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-max_lines:] if line.strip()]
    except Exception:
        return []


def load_reminder_log() -> list:
    if not REMINDER_LOG_CSV.exists():
        return []
    rows = []
    try:
        with open(REMINDER_LOG_CSV, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("email"):
                    rows.append(r)
    except Exception:
        pass
    rows.sort(key=lambda x: x.get("reminder_sent_at", ""), reverse=True)
    return rows


def build_full_stats() -> dict:
    candidate = load_candidate_data()
    sent_log = load_sent_log()
    leads = load_leads()
    commented_posts = load_commented_posts()
    app_links = load_application_links()
    reminders = load_reminder_log()
    engine_running = is_engine_running()
    recent_logs = get_recent_logs(35)

    pending_leads = [lead for lead in leads if lead.get("status") in ("pending", "whatsapp_pending")]

    # Calculate due reminders count (sent >= 3 days ago, not in reminder_log)
    now = datetime.now()
    reminded_emails = {r.get("email", "").strip().lower() for r in reminders if r.get("email")}
    due_reminders_count = 0
    for s in sent_log:
        em = s.get("email", "").strip().lower()
        if em and em not in reminded_emails:
            sent_at_str = s.get("sent_at", "")
            if sent_at_str:
                try:
                    sent_dt = datetime.strptime(sent_at_str, "%Y-%m-%d %H:%M:%S")
                    if (now - sent_dt).total_seconds() >= 3 * 86400:
                        due_reminders_count += 1
                except Exception:
                    pass

    # Metrics
    metrics = {
        "total_leads": len(leads),
        "sent_emails": len(sent_log),
        "commented_posts": len(commented_posts),
        "application_links": len(app_links),
        "pending_leads": len(pending_leads),
        "due_reminders": due_reminders_count,
        "reminders_sent": sum(1 for r in reminders if r.get("status") == "sent"),
        "replies_detected": sum(1 for r in reminders if r.get("status") == "replied"),
        "success_rate": "100%",
        "engine_active": engine_running,
        "high_match_count": sum(1 for lead in leads if int(lead.get("score") or 0) >= 95),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return {
        "candidate": candidate,
        "metrics": metrics,
        "leads": list(reversed(leads)),
        "sent_log": list(reversed(sent_log)),
        "reminders": reminders,
        "commented_posts": commented_posts,
        "application_links": app_links,
        "recent_logs": recent_logs,
    }


def render_email_preview_html(target_email: str) -> str:
    """Renders HTML email preview for a specific email or sample."""
    leads = load_leads()
    sent_log = load_sent_log()
    candidate = load_candidate_data()

    # Find matching record
    rec = None
    target_clean = target_email.strip().lower() if target_email else ""
    for r in sent_log + leads:
        if r.get("email", "").strip().lower() == target_clean:
            rec = r
            break

    if not rec:
        rec = {
            "email": target_email or "recruiter@company.com",
            "recruiter_name": "Hiring Team",
            "job_role": "Full Stack & GenAI Developer Intern",
            "post_snippet": "We are hiring tech interns with experience in React, Node.js, FastAPI, and GenAI.",
            "post_url": "https://www.linkedin.com/jobs/"
        }

    try:
        from src.email_template import generate_email_body, generate_email_html_body
        plain = generate_email_body(rec, candidate)
        return generate_email_html_body(plain, lead=rec, candidate=candidate)
    except Exception as e:
        sample_path = DATA_DIR / "sample_email_preview.html"
        if sample_path.exists():
            with open(sample_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"<h3>Email Preview for {target_email}</h3><p>Role: {rec.get('job_role')}</p><p>Recruiter: {rec.get('recruiter_name')}</p>"


class DashboardHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_HEAD(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/stats":
            data = build_full_stats()
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/email_preview":
            query = parse_qs(parsed.query)
            email = query.get("email", [""])[0]
            html_content = render_email_preview_html(email).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(html_content)))
            self.end_headers()
            self.wfile.write(html_content)
            return

        # Static files serving
        if path == "/" or path == "/index.html":
            file_path = DASHBOARD_DIR / "index.html"
        else:
            rel = path.lstrip("/")
            file_path = DASHBOARD_DIR / rel

        if file_path.exists() and file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "application/octet-stream"
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # Fallback 404
        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/links/status":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len).decode("utf-8")
                req_data = json.loads(post_body)
                apply_link = req_data.get("apply_link", "").strip()
                new_status = req_data.get("status", "applied").strip()

                if APP_LINKS_CSV.exists() and apply_link:
                    from src.csv_manager import APPLICATION_LINK_FIELDNAMES, sync_application_links_markdown
                    rows = []
                    fieldnames = APPLICATION_LINK_FIELDNAMES
                    with open(APP_LINKS_CSV, "r", encoding="utf-8", errors="replace") as f:
                        reader = csv.DictReader(f)
                        if reader.fieldnames:
                            fieldnames = reader.fieldnames
                        for r in reader:
                            if r.get("apply_link", "").strip() == apply_link:
                                r["status"] = new_status
                            rows.append(r)
                    with open(APP_LINKS_CSV, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    if APP_LINKS_MD.exists():
                        sync_application_links_markdown(APP_LINKS_CSV, APP_LINKS_MD)

                resp = json.dumps({"success": True, "link": apply_link, "status": new_status}).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            return

        if path == "/api/trigger_send":
            # Run send_emails.py --send in background
            try:
                subprocess.Popen(
                    [sys.executable, str(BASE_DIR / "send_emails.py"), "--send", "--limit", "5"],
                    cwd=str(BASE_DIR),
                )
                resp = json.dumps({"success": True, "message": "Email outreach process initiated for pending leads."}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            return

        if path == "/api/trigger_reminders":
            try:
                subprocess.Popen(
                    [sys.executable, str(BASE_DIR / "send_reminders.py"), "--send"],
                    cwd=str(BASE_DIR),
                )
                resp = json.dumps({
                    "success": True, 
                    "message": "Follow-up reminders & IMAP reply detection initiated in background."
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            return

        if path == "/api/send_single_lead":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len).decode("utf-8")
                req_data = json.loads(post_body)
                target_email = req_data.get("email", "").strip().lower()
                if not target_email:
                    raise ValueError("Target email address is required.")

                subprocess.Popen(
                    [sys.executable, str(BASE_DIR / "send_emails.py"), "--send", "--email", target_email],
                    cwd=str(BASE_DIR),
                )
                resp = json.dumps({
                    "success": True, 
                    "message": f"Personalized email outreach initiated for {target_email}."
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            return

        if path == "/api/preview_custom_email":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len).decode("utf-8")
                req_data = json.loads(post_body)
                candidate = load_candidate_data()

                lead = {
                    "email": req_data.get("email", "").strip(),
                    "recruiter_name": req_data.get("recruiter_name") or req_data.get("company_name") or "Hiring Team",
                    "job_role": req_data.get("job_role", "Software Engineer Intern"),
                    "company_name": req_data.get("company_name", ""),
                    "post_url": req_data.get("apply_link") or req_data.get("post_url") or "",
                    "post_snippet": f"{req_data.get('overview', '')} | Requirements: {req_data.get('requirements', '')}".strip(" |"),
                }

                from src.email_template import generate_subject, generate_email_body, generate_email_html_body
                custom_subject = req_data.get("subject", "").strip()
                subject = custom_subject if custom_subject else generate_subject(lead, candidate)
                plain_body = generate_email_body(lead, candidate)
                html_body = generate_email_html_body(plain_body, lead=lead, candidate=candidate)

                resp = json.dumps({
                    "success": True,
                    "subject": subject,
                    "plain_body": plain_body,
                    "html_body": html_body
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            return

        if path == "/api/send_custom_email":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len).decode("utf-8")
                req_data = json.loads(post_body)
                to_email = req_data.get("email", "").strip().lower()

                if not to_email or "@" not in to_email or "." not in to_email:
                    resp = json.dumps({"success": False, "error": "Please enter a valid email address."}).encode("utf-8")
                    self.send_response(400)
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(resp)
                    return

                candidate = load_candidate_data()
                company = req_data.get("company_name", "").strip()
                role = req_data.get("job_role", "").strip() or "Software Engineer Intern"
                apply_link = req_data.get("apply_link", "").strip()
                post_url = req_data.get("post_url", "").strip() or apply_link
                overview = req_data.get("overview", "").strip()
                requirements = req_data.get("requirements", "").strip()
                recruiter = req_data.get("recruiter_name", "").strip() or company or "Hiring Team"

                from src.post_filter import is_blacklisted
                blacklisted, b_reason = is_blacklisted(
                    email=to_email,
                    text=f"{overview} {requirements}",
                    company=company,
                    recruiter=recruiter,
                    url=apply_link or post_url,
                )
                if blacklisted:
                    resp = json.dumps({"success": False, "error": f"Outreach blocked: Recipient is blacklisted ({b_reason})."}).encode("utf-8")
                    self.send_response(400)
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(resp)
                    return

                from src.post_filter import is_location_allowed
                loc_ok, loc_reason = is_location_allowed(f"{overview} {requirements}")
                if not loc_ok:
                    resp = json.dumps({"success": False, "error": f"Outreach blocked: Location constraint violated ({loc_reason})."}).encode("utf-8")
                    self.send_response(400)
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(resp)
                    return

                lead = {
                    "email": to_email,
                    "recruiter_name": recruiter,
                    "job_role": role,
                    "company_name": company,
                    "post_url": post_url,
                    "post_snippet": f"{overview} | Requirements: {requirements}".strip(" |"),
                }

                from src.email_template import generate_subject, generate_email_body, generate_email_html_body
                from src.gmail_sender import send_email
                from config import SENDER_EMAIL, GMAIL_APP_PASSWORD, SENDER_NAME, DEFAULT_RESUME_PATH

                custom_subject = req_data.get("subject", "").strip()
                subject = custom_subject if custom_subject else generate_subject(lead, candidate)
                plain_body = generate_email_body(lead, candidate)
                html_body = generate_email_html_body(plain_body, lead=lead, candidate=candidate)

                success, msg = send_email(
                    to_email=to_email,
                    subject=subject,
                    body_text=plain_body,
                    body_html=html_body,
                    resume_path=DEFAULT_RESUME_PATH,
                    sender_email=SENDER_EMAIL,
                    sender_name=SENDER_NAME,
                    app_password=GMAIL_APP_PASSWORD,
                    dry_run=False,
                )

                if not success:
                    resp = json.dumps({"success": False, "error": msg}).encode("utf-8")
                    self.send_response(500)
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(resp)
                    return

                # 1. Update application_links.csv if apply_link or company matches
                if APP_LINKS_CSV.exists() and (apply_link or company):
                    from src.csv_manager import APPLICATION_LINK_FIELDNAMES, sync_application_links_markdown
                    rows = []
                    fieldnames = APPLICATION_LINK_FIELDNAMES
                    with open(APP_LINKS_CSV, "r", encoding="utf-8", errors="replace") as f:
                        reader = csv.DictReader(f)
                        if reader.fieldnames:
                            fieldnames = reader.fieldnames
                        for r in reader:
                            r_link = r.get("apply_link", "").strip()
                            r_comp = r.get("company_name", "").strip().lower()
                            if (apply_link and r_link == apply_link) or (company and r_comp == company.lower()):
                                r["status"] = "applied"
                            rows.append(r)
                    with open(APP_LINKS_CSV, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    if APP_LINKS_MD.exists():
                        sync_application_links_markdown(APP_LINKS_CSV, APP_LINKS_MD)

                # 2. Append to sent_log.csv
                from src.csv_manager import log_sent_email
                log_sent_email(lead, subject, "sent", SENT_LOG_CSV)

                # 3. Upsert into leads.csv
                from src.csv_manager import save_leads
                lead_to_save = dict(lead)
                lead_to_save["status"] = "sent"
                save_leads([lead_to_save], LEADS_CSV)

                resp = json.dumps({
                    "success": True,
                    "message": f"Tailored application email with resume successfully sent to {to_email}!",
                    "subject": subject
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(resp)
            return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()


def run_server(port: int = DEFAULT_PORT):
    # Ensure data/application_links.csv exists with header
    if not APP_LINKS_CSV.exists():
        APP_LINKS_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(APP_LINKS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["job_role", "recruiter_name", "apply_link", "post_url", "overview", "discovered_at", "status"])

    server_address = ("0.0.0.0", port)
    try:
        httpd = HTTPServer(server_address, DashboardHandler)
        print(f"===============================================================")
        print(f"🚀  JAINAM JAIN - OUTREACH COMMAND CENTER SERVER")
        print(f"===============================================================")
        print(f"📡  Dashboard URL: http://localhost:{port}")
        print(f"📊  API Endpoint : http://localhost:{port}/api/stats")
        print(f"🌐  Open in browser: http://localhost:{port}")
        print(f"===============================================================")
        httpd.serve_forever()
    except OSError as e:
        if port < 5060:
            print(f"Port {port} busy, attempting {port + 1}...")
            run_server(port + 1)
        else:
            raise e


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Jainam Outreach Dashboard Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind server")
    args = parser.parse_args()
    run_server(args.port)
