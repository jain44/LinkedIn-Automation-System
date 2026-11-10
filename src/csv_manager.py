"""
csv_manager.py - Lead and Sent Log Tracking for Jainam's Internship Outreach
Guarantees zero duplicate emails by tracking contacted recruiters.
"""

import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any

logger = logging.getLogger(__name__)

LEAD_FIELDNAMES = [
    "email",
    "phone_number",
    "whatsapp_link",
    "recruiter_name",
    "job_role",
    "post_url",
    "score",
    "search_keyword",
    "discovered_at",
    "status",
    "post_snippet",
]

SENT_FIELDNAMES = [
    "email",
    "recruiter_name",
    "job_role",
    "subject",
    "sent_at",
    "status",
    "post_url",
]

APPLICATION_LINK_FIELDNAMES = [
    "job_role",
    "company_name",
    "recruiter_name",
    "apply_link",
    "post_url",
    "overview",
    "requirements",
    "discovered_at",
    "status",
]



def _ensure_file(path: Path, fieldnames: List[str]) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def load_sent_emails(sent_log_path: Path) -> Set[str]:
    """
    Returns a set of all lowercased emails that have already been contacted.
    """
    if not sent_log_path.exists():
        return set()

    sent = set()
    try:
        with open(sent_log_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                em = row.get("email", "").strip().lower()
                status = row.get("status", "").strip().lower()
                if em and status == "sent":
                    sent.add(em)
    except Exception as e:
        logger.warning(f"Error reading sent log: {e}")
    return sent



def save_leads(leads: List[Dict[str, Any]], leads_path: Path) -> int:
    """
    Saves newly discovered leads, skipping duplicates.
    Returns number of new leads saved.
    """
    if not leads:
        return 0

    _ensure_file(leads_path, LEAD_FIELDNAMES)

    existing_emails = set()
    existing_phones = set()
    try:
        with open(leads_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                em = row.get("email", "").strip().lower()
                ph = re.sub(r"\D", "", row.get("phone_number", ""))
                if em:
                    existing_emails.add(em)
                if ph:
                    existing_phones.add(ph)
    except Exception:
        pass

    new_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(leads_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEAD_FIELDNAMES)
        for lead in leads:
            email = lead.get("email", "").strip().lower()
            phone = lead.get("phone_number", "").strip()
            digits = re.sub(r"\D", "", phone)

            # Lead must have either an email or a valid phone number
            if not email and not digits:
                continue

            # Strict check for blacklisted entities (e.g. The GAO Group, GAO Tek)
            from src.post_filter import is_blacklisted
            blacklisted, b_reason = is_blacklisted(
                email=email,
                text=lead.get("post_snippet", ""),
                recruiter=lead.get("recruiter_name", ""),
                company=lead.get("company_name", ""),
            )
            if blacklisted:
                logger.info(f"🚫 Rejecting blacklisted lead '{email or phone}': {b_reason}")
                continue

            # Strict check for location constraints: Onsite ONLY in Mumbai, otherwise strictly Remote
            from src.post_filter import is_location_allowed
            loc_ok, loc_reason = is_location_allowed(lead.get("post_snippet", ""))
            if not loc_ok:
                logger.info(f"🚫 Rejecting lead '{email or phone}' due to location constraint: {loc_reason}")
                continue

            # Duplicate check
            is_dup = False
            if email and email in existing_emails:
                is_dup = True
            if digits and digits in existing_phones:
                is_dup = True
            if is_dup:
                continue

            if email:
                existing_emails.add(email)
            if digits:
                existing_phones.add(digits)

            # Determine lead status
            default_status = "pending" if email else "whatsapp_pending"

            writer.writerow({
                "email": email,
                "phone_number": phone,
                "whatsapp_link": lead.get("whatsapp_link", ""),
                "recruiter_name": lead.get("recruiter_name", ""),
                "job_role": lead.get("job_role", "Software Engineer Intern"),
                "post_url": lead.get("post_url", ""),
                "score": lead.get("score", 70),
                "search_keyword": lead.get("search_keyword", ""),
                "discovered_at": lead.get("discovered_at") or now_str,
                "status": lead.get("status") or default_status,
                "post_snippet": lead.get("post_snippet", "")[:250],
            })
            new_count += 1

    if new_count > 0:
        logger.info(f"✨ Saved {new_count} new unique lead(s) to {leads_path.name}")
    return new_count


def get_pending_leads(leads_path: Path, sent_log_path: Path) -> List[Dict[str, Any]]:
    """
    Returns all leads from leads.csv that have not yet been emailed in sent_log.csv.
    """
    if not leads_path.exists():
        return []

    sent_emails = load_sent_emails(sent_log_path)
    pending = []

    from src.post_filter import is_blacklisted

    try:
        with open(leads_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email", "").strip().lower()
                status = row.get("status", "").strip().lower()
                if status == "blacklisted":
                    continue

                # Strict check against blacklisted entities (e.g. The GAO Group, GAO Tek)
                blacklisted, _ = is_blacklisted(
                    email=email,
                    text=row.get("post_snippet", ""),
                    recruiter=row.get("recruiter_name", ""),
                    company=row.get("company_name", ""),
                )
                if blacklisted:
                    continue

                # Strict check for location constraints: Onsite ONLY in Mumbai, otherwise strictly Remote
                from src.post_filter import is_location_allowed
                loc_ok, _ = is_location_allowed(row.get("post_snippet", ""))
                if not loc_ok:
                    continue

                if email and email not in sent_emails:
                    pending.append(row)
    except Exception as e:
        logger.error(f"Error reading leads: {e}")

    return pending


def log_sent_email(lead: Dict[str, Any], subject: str, status: str, sent_log_path: Path) -> None:
    """
    Appends a successfully sent or dry-run email to sent_log.csv.
    """
    _ensure_file(sent_log_path, SENT_FIELDNAMES)

    with open(sent_log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SENT_FIELDNAMES)
        writer.writerow({
            "email": lead.get("email", "").strip().lower(),
            "recruiter_name": lead.get("recruiter_name", ""),
            "job_role": lead.get("job_role", ""),
            "subject": subject,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "post_url": lead.get("post_url", ""),
        })

    # Also synchronize status in leads.csv so it reflects 'sent'
    if status == "sent":
        try:
            from config import LEADS_CSV
            target_email = lead.get("email", "").strip().lower()
            if target_email and LEADS_CSV.exists():
                with open(LEADS_CSV, "r", encoding="utf-8", errors="replace") as lf:
                    reader = csv.DictReader(lf)
                    fields = reader.fieldnames
                    rows = list(reader)
                modified = False
                for r in rows:
                    if r.get("email", "").strip().lower() == target_email and r.get("status", "").lower() != "sent":
                        r["status"] = "sent"
                        modified = True
                if modified:
                    with open(LEADS_CSV, "w", newline="", encoding="utf-8") as lf:
                        writer = csv.DictWriter(lf, fieldnames=fields)
                        writer.writeheader()
                        writer.writerows(rows)
        except Exception:
            pass


def get_post_fingerprint(text: str) -> str:
    """
    Creates an invariant, deterministic SHA-256 fingerprint from post text.
    Strips volatile UI prefixes, timestamps, and formatting so the exact same post
    always produces the identical fingerprint across any session, run, or search query.
    Uses an 80-character invariant window to match both live scraped posts and logged snippets.
    """
    if not text:
        return ""
    import re
    import hashlib
    t = text.lower()
    t = re.sub(r"feed\s*post", "", t)
    t = re.sub(r"\b\d+\s*[hdwm]\b(?:\s*•)?", "", t)
    t = re.sub(r"\bfollow\b", "", t)
    t = re.sub(r"•\s*edited\b", "", t)
    clean_chars = re.sub(r"[^a-z0-9]", "", t)
    core = clean_chars[:80] if len(clean_chars) >= 30 else clean_chars
    if not core:
        return ""
    return hashlib.sha256(core.encode("utf-8")).hexdigest()[:20]


def load_commented_keys(commented_log_path: Path) -> Set[str]:
    """
    Returns set of post keys, URLs, activity IDs, and deterministic content fingerprints
    that have already been commented on across all runs.
    """
    if not commented_log_path.exists():
        return set()
    keys: Set[str] = set()
    try:
        with open(commented_log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, entry in data.items():
                keys.add(k)
                if isinstance(entry, dict):
                    if entry.get("post_url"):
                        keys.add(entry["post_url"])
                    if entry.get("fingerprint"):
                        keys.add(entry["fingerprint"])
                    if entry.get("activity_id"):
                        keys.add(entry["activity_id"])
                    # Derive content fingerprint from post snippet for legacy entries
                    snippet = entry.get("post_snippet", "")
                    fp = get_post_fingerprint(snippet)
                    if fp:
                        keys.add(fp)
    except Exception as e:
        logger.warning(f"Error loading commented log: {e}")
    return keys


def record_comment(
    post_key: str,
    post_url: str,
    recruiter_name: str,
    post_snippet: str,
    comment_text: str,
    commented_log_path: Path,
    fingerprint: str = "",
    activity_id: str = "",
) -> None:
    """
    Persists a new commented post entry to disk immediately.
    Saves multiple identifiers (ephemeral key, URL, activity ID, and SHA-256 content fingerprint)
    so the post can NEVER be commented on twice across any run, session, or keyword.
    """
    data = {}
    if commented_log_path.exists():
        try:
            with open(commented_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    fp = fingerprint or get_post_fingerprint(post_snippet)
    entry = {
        "post_key": post_key,
        "post_url": post_url,
        "fingerprint": fp,
        "activity_id": activity_id,
        "recruiter_name": recruiter_name,
        "post_snippet": (post_snippet or "")[:250],
        "comment_text": comment_text,
        "commented_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Store under stable fingerprint if available, plus post_key
    storage_key = f"fp:{fp}" if fp else post_key
    data[storage_key] = entry
    if post_key and post_key != storage_key:
        data[post_key] = entry
    if activity_id and activity_id != storage_key:
        data[activity_id] = entry

    try:
        with open(commented_log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error writing to commented log: {e}")


def load_saved_apply_links(csv_path: Path) -> Set[str]:
    """
    Returns set of already saved application links to prevent duplicates.
    """
    if not csv_path.exists():
        return set()
    links = set()
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                link = row.get("apply_link", "").strip()
                if link:
                    links.add(link)
    except Exception as e:
        logger.warning(f"Error reading application links: {e}")
    return links


def save_application_link(
    job_role: str,
    recruiter_name: str,
    apply_link: str,
    post_url: str,
    overview: str,
    csv_path: Path,
    md_path: Path = None,
    company_name: str = "",
    requirements: str = "",
) -> bool:
    """
    Appends a new internship application link with structured role, company, overview,
    and requirements to application_links.csv, and syncs to application_links.md.
    """
    if not apply_link:
        return False

    _ensure_file(csv_path, APPLICATION_LINK_FIELDNAMES)
    saved_links = load_saved_apply_links(csv_path)

    clean_link = apply_link.strip()
    if clean_link in saved_links:
        return False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_overview = " ".join(str(overview or "").split())[:600]
    clean_requirements = " ".join(str(requirements or "").split())[:600]
    clean_company = str(company_name or "").strip() or "Tech Company"

    # Strict check against blacklisted entities (e.g. The GAO Group, GAO Tek)
    from src.post_filter import is_blacklisted
    blacklisted, b_reason = is_blacklisted(
        url=clean_link,
        text=f"{clean_overview} {clean_requirements}",
        company=clean_company,
        recruiter=recruiter_name,
    )
    if blacklisted:
        logger.info(f"🚫 Rejecting blacklisted application link '{clean_link}': {b_reason}")
        return False

    # Strict check for location constraints: Onsite ONLY in Mumbai, otherwise strictly Remote
    from src.post_filter import is_location_allowed
    loc_ok, loc_reason = is_location_allowed(f"{clean_overview} {clean_requirements}")
    if not loc_ok:
        logger.info(f"🚫 Rejecting application link '{clean_link}' due to location constraint: {loc_reason}")
        return False

    row = {
        "job_role": job_role or "Software Engineer Intern",
        "company_name": clean_company,
        "recruiter_name": recruiter_name or "Hiring Team",
        "apply_link": clean_link,
        "post_url": post_url or "",
        "overview": clean_overview,
        "requirements": clean_requirements,
        "discovered_at": now_str,
        "status": "new",
    }

    try:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=APPLICATION_LINK_FIELDNAMES)
            writer.writerow(row)
        logger.info(f"🔗 Saved application link: {clean_link} | Company: {clean_company} | Role: {job_role}")

        # Sync to Markdown dashboard if path provided
        if md_path:
            sync_application_links_markdown(csv_path, md_path)

        return True
    except Exception as e:
        logger.error(f"Error saving application link: {e}")
        return False


def sync_application_links_markdown(csv_path: Path, md_path: Path) -> None:
    """
    Generates a clean, readable Markdown dashboard with summary table and detailed cards
    in data/application_links.md.
    """
    if not csv_path.exists():
        return

    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("apply_link"):
                    rows.append(r)
    except Exception:
        return

    lines = [
        "# 📋 Curated Internship Application Links & Forms",
        "",
        f"> **Total Opportunities Tracked**: `{len(rows)}` | **Last Synced**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        "",
        "Quickly review verified internship openings with role titles, company overviews, technical requirements, and direct application links.",
        "",
        "## ⚡ Quick Application Table",
        "",
        "| # | Company | Specific Roles | Direct Apply Link | LinkedIn Post | Discovered |",
        "| :---: | :--- | :--- | :--- | :---: | :---: |",
    ]

    for idx, r in enumerate(reversed(rows), 1):
        role = r.get("job_role", "Tech Intern")
        company = r.get("company_name") or r.get("recruiter_name", "Tech Startup")
        apply_url = r.get("apply_link", "")
        post_url = r.get("post_url", "")
        date_str = r.get("discovered_at", "")[:16]

        apply_md = f"[👉 **Apply Here**]({apply_url})" if apply_url else "-"
        post_md = f"[🔗 View Post]({post_url})" if post_url else "-"

        lines.append(f"| {idx} | **{company}** | {role} | {apply_md} | {post_md} | {date_str} |")

    lines.extend([
        "",
        "---",
        "",
        "## 🔍 Detailed Opportunity Overviews & Requirements",
        "",
    ])

    for idx, r in enumerate(reversed(rows), 1):
        role = r.get("job_role", "Tech Intern")
        company = r.get("company_name") or r.get("recruiter_name", "Tech Startup")
        recruiter = r.get("recruiter_name", "Hiring Team")
        apply_url = r.get("apply_link", "")
        post_url = r.get("post_url", "")
        overview = r.get("overview") or "Internship program opportunity for technical roles."
        requirements = r.get("requirements") or "Software engineering, full stack, and problem-solving skills."
        date_str = r.get("discovered_at", "")[:16]
        status = r.get("status", "new")

        badge = "🟢 New Opportunity" if status != "applied" else "✅ Applied"

        lines.append(f"### {idx}. {company} — {role}")
        lines.append(f"> **Status**: {badge} | **Discovered**: `{date_str}` | **Posted by**: {recruiter}")
        lines.append("")
        lines.append(f"- 🔗 **Direct Application Link**: [{apply_url}]({apply_url})")
        if post_url:
            lines.append(f"- 📝 **LinkedIn Post Link**: [{post_url}]({post_url})")
        lines.append("")
        lines.append("**💡 What the Internship is About (Overview)**:")
        lines.append(f"{overview}")
        lines.append("")
        lines.append("**🛠️ Requirements & Key Details**:")
        lines.append(f"{requirements}")
        lines.append("")
        lines.append("---")
        lines.append("")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        logger.warning(f"Error updating markdown table: {e}")


