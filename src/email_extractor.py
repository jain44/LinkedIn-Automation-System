"""
email_extractor.py - Recruiter and Founder Email Extraction for Tech Internships
Extracts valid emails from LinkedIn posts including plain and obfuscated formats.
"""

import re
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

# Standard strict email pattern
EMAIL_REGEX = re.compile(
    r"(?<![A-Za-z0-9._%+\-])"
    r"[A-Za-z0-9][A-Za-z0-9._%+\-]{0,63}"
    r"@"
    r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)+"
    r"(?![A-Za-z0-9._%+\-])",
    re.IGNORECASE,
)

# Obfuscated email patterns
OBFUSCATED_PATTERNS = [
    # user [at] domain [dot] com or user (at) domain (dot) com
    re.compile(r"([A-Za-z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\bat\b)\s*([A-Za-z0-9.\-]+)\s*(?:\[dot\]|\(dot\)|\bdot\b)\s*([A-Za-z]{2,10})", re.IGNORECASE),
    # user @ domain [dot] com
    re.compile(r"([A-Za-z0-9._%+\-]+)\s*@\s*([A-Za-z0-9.\-]+)\s*(?:\[dot\]|\(dot\)|\bdot\b)\s*([A-Za-z]{2,10})", re.IGNORECASE),
]

# Domains that should NEVER receive automated cold emails
BLOCKED_DOMAINS = {
    "example.com", "test.com", "domain.com", "company.com", "email.com",
    "placeholder.com", "invalid.com", "localhost.com", "linkedin.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "github.com", "gitlab.com", "medium.com", "sentry.io", "wixpress.com"
}

# Generic help/support local parts that aren't hiring-related
BLOCKED_LOCAL_PARTS = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "support", "help",
    "webmaster", "privacy", "legal", "press", "billing", "account",
    "abuse", "security", "newsletter", "unsubscribe"
}

# Hiring & direct startup local parts that are ALWAYS valid
HIRING_LOCAL_PARTS = {
    "hiring", "careers", "jobs", "internship", "internships", "talent",
    "recruitment", "recruiter", "people", "hr", "apply", "work",
    "info", "contact", "hello", "team", "reach", "founder", "leads"
}

COMMON_BAD_TLDS = {"con", "comm", "cpm", "vom", "cim", "om", "cm", "coom", "come", "png", "jpg", "jpeg", "pdf"}

KNOWN_VALID_TLDS = {
    "com", "in", "org", "net", "io", "ai", "co", "tech", "dev", "app",
    "me", "de", "uk", "us", "ca", "fr", "au", "eu", "xyz", "online",
    "site", "space", "global", "biz", "info", "link", "club", "edu",
    "gov", "agency", "cc", "so", "cloud", "work", "to", "sg", "nl",
    "ch", "se", "no", "es", "it", "pl", "cz", "at", "dk", "fi", "ie",
    "co.in", "ac.in", "org.in", "net.in", "gov.in", "gen.in"
}

TRAILING_GLUED_WORDS = {
    "please", "pls", "plz", "share", "send", "drop", "apply", "contact",
    "reach", "dm", "note", "thank", "thanks", "regards", "or", "and",
    "with", "for", "interested", "urgent", "hiring", "subject", "sub",
    "resume", "cv", "portfolio", "email", "mail"
}


def sanitize_email(raw_email: str) -> str:
    """
    Cleans trailing English words accidentally glued to email domains on LinkedIn posts.
    e.g. info@elternsegen.aiPlease -> info@elternsegen.ai
         info@elternsegen.aiplease -> info@elternsegen.ai
         hr@company.comShare       -> hr@company.com
    """
    if not raw_email or "@" not in raw_email:
        return ""

    cleaned = raw_email.strip(" .,;:()[]{}<>\"'!?\n\r\t")
    parts = cleaned.split("@", 1)
    if len(parts) != 2:
        return ""
    local_part, domain = parts

    if "." not in domain:
        return ""

    domain_parts = domain.split(".")
    tld_raw = domain_parts[-1]
    domain_base = ".".join(domain_parts[:-1])

    # 1. Check CamelCase boundary (e.g. "aiPlease" -> "ai", "comShare" -> "com")
    camel_match = re.match(r"^([a-zA-Z]{2,6})([A-Z][a-zA-Z]*)$", tld_raw)
    if camel_match:
        tld_cand = camel_match.group(1).lower()
        if tld_cand in KNOWN_VALID_TLDS:
            return f"{local_part}@{domain_base}.{tld_cand}".lower()

    # 2. Check lowercase glued words (e.g. "aiplease", "comshare", "insend")
    tld_low = tld_raw.lower()
    for valid_tld in sorted(KNOWN_VALID_TLDS, key=len, reverse=True):
        if tld_low.startswith(valid_tld):
            remainder = tld_low[len(valid_tld):]
            if remainder in TRAILING_GLUED_WORDS or any(remainder.startswith(w) for w in TRAILING_GLUED_WORDS):
                return f"{local_part}@{domain_base}.{valid_tld}".lower()

    return f"{local_part}@{domain}".lower()


def is_valid_email(email: str) -> bool:
    email = str(email or "").strip().lower()
    if not email or "@" not in email:
        return False

    parts = email.split("@", 1)
    if len(parts) != 2:
        return False
    local_part, domain = parts

    if len(email) > 100 or len(local_part) < 2 or len(domain) < 4:
        return False

    if domain in BLOCKED_DOMAINS:
        return False

    tld = domain.split(".")[-1]
    if tld in COMMON_BAD_TLDS:
        return False

    # Block invalid TLDs that are ungrammatical or corrupt words
    if tld not in KNOWN_VALID_TLDS and not any(domain.endswith("." + kt) for kt in ["co.in", "ac.in", "org.in"]):
        return False

    # Block blacklisted domains and entities (e.g. GAO Group, GAO Tech)
    from src.post_filter import is_blacklisted
    blacklisted, _ = is_blacklisted(email=email)
    if blacklisted:
        return False

    return True


def deobfuscate_text(text: str) -> str:
    """
    Normalizes diverse email obfuscations commonly used by recruiters on LinkedIn:
    - user [at] domain.com, user (at) domain.com, user [@] domain.com
    - user AT domain DOT com
    - user @ domain . com
    - user [dot] com, user (dot) com
    """
    if not text:
        return ""
    cleaned = text
    # 1. Bracketed or parenthesized 'at': [at], (at), [@], (@)
    cleaned = re.sub(
        r'([A-Za-z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\[@\]|\(@\))\s*([A-Za-z0-9.\-]+)',
        r'\1@\2',
        cleaned,
        flags=re.IGNORECASE
    )
    # 2. Uppercase AT with surrounding spaces: user AT domain
    cleaned = re.sub(r'([A-Za-z0-9._%+\-]+)\s+AT\s+([A-Za-z0-9.\-]+)', r'\1@\2', cleaned)
    # 3. Spaced @: user @ domain.com
    cleaned = re.sub(r'([A-Za-z0-9._%+\-]+)\s*@\s*([A-Za-z0-9.\-]+)', r'\1@\2', cleaned)
    # 4. Bracketed or parenthesized 'dot': [dot], (dot), [.], (.)
    cleaned = re.sub(
        r'([A-Za-z0-9.\-]+)\s*(?:\[dot\]|\(dot\)|\[\.\]|\(\.\))\s*([A-Za-z]{2,10})',
        r'\1.\2',
        cleaned,
        flags=re.IGNORECASE
    )
    # 5. Uppercase DOT with space: domain DOT com
    cleaned = re.sub(r'([A-Za-z0-9.\-]+)\s+DOT\s+([A-Za-z]{2,10})', r'\1.\2', cleaned)
    # 6. Spaced dot before TLD: domain . com
    cleaned = re.sub(r'([A-Za-z0-9.\-]+)\s*\.\s*([A-Za-z]{2,10})\b', r'\1.\2', cleaned)

    return cleaned


def extract_emails(text: str) -> List[str]:
    """
    Extracts all unique, valid emails from text.
    Handles standard and obfuscated emails.
    Sanitizes glued trailing text from TLDs (e.g. .aiPlease -> .ai).
    """
    if not text:
        return []

    resolved_text = deobfuscate_text(text)
    raw_matches = EMAIL_REGEX.findall(resolved_text)

    valid_emails: List[str] = []
    seen: Set[str] = set()

    for raw in raw_matches:
        cleaned = sanitize_email(raw)
        if cleaned and cleaned not in seen and is_valid_email(cleaned):
            seen.add(cleaned)
            valid_emails.append(cleaned)

    return valid_emails


def extract_phone_numbers(text: str) -> List[str]:
    """
    Extracts genuine recruiter phone & WhatsApp numbers from post text.
    Handles Indian numbers (+91, 10-digit formats) and international numbers.
    Filters out dates, years (2025/2026), salary figures, and pincodes.
    """
    if not text:
        return []

    found = []

    # 1. Direct wa.me links: wa.me/919876543210
    for m in re.finditer(r"wa\.me\/(?:\+?(\d{10,14}))", text, re.IGNORECASE):
        num = m.group(1)
        found.append("+" + num if not num.startswith("+") else num)

    # 2. Numbers with explicit recruiter contact/WhatsApp prefixes
    prefixed_pattern = re.compile(
        r"(?:whatsapp|call|contact|ph(?:one)?|mobile|tel|ping|reach\s*out|connect|send\s*(?:your\s*)?(?:resume|cv))"
        r"(?:\s+(?:your\s+)?(?:resume|cv|at|on|to|details|us|here)){0,3}[\s:]+"
        r"(?:\+(\d{1,3})[\s.-]*)?"
        r"([\(]?\d{2,4}[\)]?[\s.-]?\d{3,4}[\s.-]?\d{3,5})",
        re.IGNORECASE
    )
    for m in prefixed_pattern.finditer(text):
        country = m.group(1) or ("91" if len(re.sub(r"\D", "", m.group(2))) == 10 else "")
        digits = re.sub(r"\D", "", m.group(2))
        if 8 <= len(digits) <= 12:
            full = f"+{country}{digits}" if country else f"+{digits}"
            if full not in found:
                found.append(full)

    # 3. Standard +91 Indian mobile formats: +91 98201 23456, +91-9820123456
    std_in = re.compile(r"(?:\+91[\s.-]*)([6-9]\d{9}|[6-9]\d{4}[\s.-]\d{5}|[6-9]\d{2}[\s.-]\d{3}[\s.-]\d{4})\b")
    for m in std_in.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        full = "+" + digits
        if full not in found:
            found.append(full)

    # Normalize to clean display format: +91 XXXXX XXXXX or +<country> <number>
    cleaned_res = []
    for f in found:
        d = re.sub(r"\D", "", f)
        if len(d) == 10 and d[0] in "6789":
            d = "91" + d
        if len(d) == 12 and d.startswith("91"):
            formatted = f"+91 {d[2:7]} {d[7:]}"
        else:
            formatted = f"+{d}"
        if formatted not in cleaned_res:
            cleaned_res.append(formatted)

    return cleaned_res


def generate_whatsapp_link(phone: str, role: str = "Developer Intern", candidate_name: str = "Jainam Jain") -> str:
    """
    Generates a direct WhatsApp click-to-chat URL with a personalized candidate intro.
    """
    import urllib.parse
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if len(digits) == 10 and digits[0] in "6789":
        digits = "91" + digits
    msg = (
        f"Hi! I came across your post regarding the {role} position. "
        f"I am {candidate_name} (B.Tech IT, 9.92 CGPA, TCET Mumbai) with 1+ year experience in React, Next.js, Node.js, and GenAI. "
        f"GitHub: https://github.com/jain44 | LinkedIn: https://www.linkedin.com/in/jainam-jain-746188263. "
        f"I have attached my 1-page resume for your review. Would love to discuss this opportunity!"
    )
    encoded_msg = urllib.parse.quote(msg)
    return f"https://wa.me/{digits}?text={encoded_msg}"


def unwrap_linkedin_url(url: str) -> str:
    """
    Unwraps LinkedIn safety redirects (e.g. https://www.linkedin.com/safety/go/?url=...)
    to recover the real destination link.
    """
    if "linkedin.com/safety/go" in url:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get("url", [""])[0]
            if target:
                return target.strip()
        except Exception:
            pass
    return url.strip()


BLOCKED_APPLY_DOMAINS = {
    "whatsapp.com", "instagram.com", "facebook.com", "twitter.com", "x.com",
    "youtube.com", "github.com", "gitlab.com", "medium.com", "reddit.com",
    "telegram.org", "t.me", "discord.gg", "discord.com",
    # Framework and language false-positive TLD matches
    "next.js", "node.js", "react.js", "vue.js", "express.js", "nest.js",
    "three.js", "chart.js", "nuxt.js", "d3.js", "electron.js",
    # Educational degrees mistakenly matched by .tech / .com / etc.
    "b.tech", "m.tech", "b.e", "m.e", "b.sc", "m.sc", "bca", "mca", "b.com", "m.com"
}


def is_genuine_apply_link(url: str) -> bool:
    """
    Validates whether a URL is a genuine job application / ATS / form link,
    rejecting LinkedIn internal company/profile/feed pages, social media, and tech buzzwords.
    """
    import urllib.parse
    clean = unwrap_linkedin_url(url).strip()
    if not clean.startswith("http://") and not clean.startswith("https://"):
        clean = "https://" + clean

    try:
        parsed = urllib.parse.urlparse(clean)
    except Exception:
        return False

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if not host or "." not in host:
        return False

    # Block internal LinkedIn domains (company pages, personal profiles, feed updates, etc.)
    # Exception: lnkd.in is LinkedIn's outbound shortlink redirecting to external portals!
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        return False

    # Block social networks and false-positive tech stack words
    if host in BLOCKED_APPLY_DOMAINS:
        return False

    # Block asset files
    path_low = parsed.path.lower()
    if any(path_low.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".pdf", ".css", ".js"]):
        return False

    VALID_TLDS = {
        "com", "in", "org", "net", "io", "co", "ai", "app", "dev", "site",
        "tech", "me", "ly", "gle", "link", "careers", "jobs", "hr", "is",
        "xyz", "online", "global", "space", "agency", "cc", "so", "cloud",
        "work", "to", "us", "uk", "ca", "de", "fr", "eu", "info"
    }
    tld = host.split(".")[-1].lower()
    if tld not in VALID_TLDS:
        return False

    # Block generic search engine roots without path
    if host in {"google.com", "bing.com", "yahoo.com", "wikipedia.org"} and (not parsed.path or parsed.path == "/"):
        return False

    # Block blacklisted domains and entities (e.g. GAO Tek, The GAO Group)
    from src.post_filter import is_blacklisted
    blacklisted, _ = is_blacklisted(url=clean)
    if blacklisted:
        return False

    return True


def extract_apply_links(text: str, element: Any = None) -> List[str]:
    """
    Extracts genuine external application URLs (Google Forms, lnkd.in, Notion, Lever,
    Greenhouse, Trakstar, Airtable, Typeform, career portals) from post text and post card anchor tags.
    Filters out internal LinkedIn company pages, profiles, and post links.
    """
    raw_urls = []
    text_clean = str(text or "")

    # 1. Targeted regex for explicit "apply link: ____", "registration link: ____", "google form: ____"
    label_patterns = [
        re.compile(r'(?:apply\s*(?:link|here|url|now|form)?|application\s*(?:link|form|url)?|registration\s*(?:link|url|form)?|google\s*form|form\s*link|link\s*to\s*apply|job\s*link)\s*[:\-–—>👉🔗]+\s*([^\s<>"\',;]+)', re.IGNORECASE),
        re.compile(r'\b(?:link|form)\s*[:\-–—>👉🔗]+\s*([^\s<>"\',;]+)', re.IGNORECASE),
    ]
    for pat in label_patterns:
        for match in pat.findall(text_clean):
            m_str = match.strip().rstrip(".,;:!?)'\"")
            if "." in m_str and len(m_str) > 4:
                raw_urls.append(m_str)

    # 2. Form portals, ATS, and outbound shortener domains (forms.gle, lnkd.in, bit.ly, etc.)
    shortener_pattern = re.compile(
        r'(?<![A-Za-z0-9.-])(?:forms\.gle|docs\.google\.com/forms|lnkd\.in|bit\.ly|tinyurl\.com|notion\.site|'
        r'airtable\.com|typeform\.com|lever\.co|greenhouse\.io|linktr\.ee|unstop\.com|cuvette\.tech|'
        r'wellfound\.com|ashbyhq\.com|trakstar\.com)/[^\s<>"\',;]+',
        re.IGNORECASE
    )
    for m in shortener_pattern.findall(text_clean):
        raw_urls.append(m)

    # 3. Standard http/https URL regex
    url_pattern = re.compile(r'https?://[A-Za-z0-9.\-_~:/?#\[\]@!$&\'()*+,;=%]+')
    raw_urls.extend(url_pattern.findall(text_clean))

    # 4. Extract from Selenium element link preview card & outbound anchor tags
    if element:
        try:
            from selenium.webdriver.common.by import By
            # Specifically target outbound article/preview cards and non-company anchors
            card_selectors = [
                ".//div[contains(@class, 'feed-shared-article')]//a[contains(@href, 'http')]",
                ".//div[contains(@class, 'update-components-article')]//a[contains(@href, 'http')]",
                ".//a[contains(@class, 'feed-shared-article__link')]",
                ".//a[contains(@class, 'update-components-article__meta-title-link')]",
                ".//a[contains(@href, 'lnkd.in')]",
                ".//a[contains(@href, 'safety/go')]",
                ".//a[contains(@href, 'http') and not(contains(@href, 'linkedin.com/in/')) and not(contains(@href, 'linkedin.com/company/')) and not(contains(@href, 'linkedin.com/school/')) and not(contains(@href, 'linkedin.com/feed/'))]",
            ]
            for sel in card_selectors:
                try:
                    anchors = element.find_elements(By.XPATH, sel)
                    for a in anchors:
                        href = a.get_attribute("href") or ""
                        if href:
                            raw_urls.append(href)
                except Exception:
                    continue
        except Exception:
            pass

    # 5. Unwrap, normalize, and strictly filter
    cleaned_links = []
    for u in raw_urls:
        unwrapped = unwrap_linkedin_url(u).rstrip(".,;:!?)'\"")
        if not unwrapped.startswith("http://") and not unwrapped.startswith("https://"):
            unwrapped = "https://" + unwrapped

        if is_genuine_apply_link(unwrapped):
            if unwrapped not in cleaned_links and len(unwrapped) > 10:
                cleaned_links.append(unwrapped)

    # Deduplicate overlapping matches
    unique_links = []
    for u in sorted(cleaned_links, key=len, reverse=True):
        if not any(u in existing for existing in unique_links):
            unique_links.append(u)

    return unique_links


def clean_post_text(raw_text: str) -> str:
    """Strips LinkedIn UI artifacts, actor headlines, and footer actions."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    # Strip leading "Feed post"
    text = re.sub(r"^Feed\s*post\s*", "", text, flags=re.IGNORECASE)
    # Strip UI author follow lines like: "Author Name • 3rd+ Headline 2h • Follow"
    text = re.sub(r"^[^\n]+•\s*(?:1st|2nd|3rd\+|Follow|Following)[^\n]*\n+", "", text, flags=re.IGNORECASE)
    # Strip footer social interaction lines
    text = re.split(r"\n+(?:Like\s*\n\s*Comment|Like\s*Comment|\bLike\b\s+Comment)", text, maxsplit=1)[0]
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_role_bullet(line: str) -> str:
    """Strips bullet emojis, numbers, and keycaps from role line."""
    cleaned = re.sub(r"^[\s\d\.\-•*🔹💻🎨📱⚙️☁️🤖👉✅#️⃣0-9\uFE0F\u20E3]+\s*", "", line)
    return cleaned.strip()


def extract_roles(text: str, default_role: str = "") -> str:
    """Extracts specific roles or tracks mentioned in the post."""
    roles = []
    lines = text.splitlines()
    in_roles_section = False

    role_triggers = [
        "available roles", "open roles", "open positions", "hiring for", "available tracks",
        "internship roles", "positions available", "profiles", "domains:", "tracks:"
    ]

    for line in lines:
        cleaned_line = line.strip()
        low = cleaned_line.lower()

        # Check section header
        if any(trig in low for trig in role_triggers):
            in_roles_section = True
            continue

        if in_roles_section:
            # End of section triggers
            if any(stop in low for stop in ["why join", "requirements", "eligibility", "perks", "location", "apply", "period", "duration", "how to"]):
                in_roles_section = False
            else:
                cand = clean_role_bullet(cleaned_line)
                if cand and len(cand) < 60 and not any(k in cand.lower() for k in ["http", "link", "click", "comment", "below"]):
                    roles.append(cand)
                    if len(roles) >= 6:
                        break

    if roles:
        return ", ".join(roles)

    # Fallback: regex search for standard engineering roles
    found_roles = []
    patterns = [
        r"(?:Full\s*Stack|Frontend|Backend|Software\s*Engineer(?:ing)?|Mobile|Flutter|Android|iOS|DevOps|Cloud|QA|Quality\s*Assurance|AI|GenAI|Machine\s*Learning|Data\s*Science|Web\s*Developer)\s*(?:Developer|Engineer|Intern(?:ship)?|Specialist)?",
    ]
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            r_str = m.group(0).strip()
            if len(r_str) > 3 and r_str.lower() not in [r.lower() for r in found_roles]:
                found_roles.append(r_str)
                if len(found_roles) >= 3:
                    break

    if found_roles:
        return ", ".join(found_roles[:3])

    return default_role or "Software Engineer Intern"


def extract_company(text: str, raw_author: str = "") -> str:
    """Extracts hiring company name from post text or author."""
    # Look for "📢 <Company> is Hiring", "<Company> is looking for", etc.
    m = re.search(r"\b([A-Z][A-Za-z0-9&.\s\(\)]{1,35})\s+is\s+(?:hiring|looking for|inviting|open for)", text, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        cand = re.sub(r"^[\s📢🚀💡✨🔹•*]+\s*", "", cand)
        if cand.lower() not in ["we", "team", "our team", "i", "who"]:
            return cand

    m = re.search(r"(?:at|join|innovate with|career at)\s+([A-Z][A-Za-z0-9&.]{2,25})", text, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if cand.lower() not in ["the", "this", "our", "us"]:
            return cand

    # Author clean up
    if raw_author:
        clean_author = raw_author.split("\n")[0].split("•")[0].strip()
        clean_author = re.sub(r"Feed\s*post\s*", "", clean_author, flags=re.IGNORECASE).strip()
        if clean_author and len(clean_author) < 40:
            return clean_author

    return "Tech Startup"


def extract_overview(text: str) -> str:
    """Extracts a clear summary of what the internship/company is about."""
    cleaned = clean_post_text(text)
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]

    overview_parts = []
    for p in paragraphs:
        p_low = p.lower()
        # Skip section headers & link lines
        if any(w in p_low for w in ["available roles:", "roles:", "requirements:", "how to apply:", "apply here:", "http://", "https://", "lnkd.in"]):
            continue
        # Check if introductory or program explanation
        if any(w in p_low for w in ["calling all", "internship", "level up", "kickstart", "looking for", "program", "opportunity", "hiring", "open for", "join our", "fresh graduates", "remote", "developer"]):
            overview_parts.append(" ".join(p.split()))
            if len(" ".join(overview_parts)) > 150:
                break

    if overview_parts:
        return " ".join(overview_parts)[:450]

    # Fallback to first non-empty paragraph
    for p in paragraphs:
        if len(p) > 40 and not any(w in p.lower() for w in ["http", "link", "comment"]):
            return " ".join(p.split())[:350]

    return "Internship program opportunity for software engineering and technical roles."


def extract_requirements_and_details(text: str) -> str:
    """Extracts skills, eligibility, location, perks, duration, and requirements."""
    details = []
    lines = text.splitlines()

    # 1. Location / Mode
    loc_match = re.search(r"(?:📍|Location|Work Mode|Mode)\s*[:\-–—]?\s*([^\n]+)", text, re.IGNORECASE)
    if loc_match:
        details.append(f"📍 {loc_match.group(1).strip()}")
    elif "remote" in text.lower():
        details.append("🌐 Remote")
    elif "hybrid" in text.lower():
        details.append("🏢 Hybrid")

    # 2. Tech stack / Skills
    tech_keywords = [
        "React", "Node.js", "Python", "Flutter", "FastAPI", "Django", "Java", "Docker",
        "Kubernetes", "AWS", "SQL", "PostgreSQL", "MongoDB", "TypeScript", "Next.js",
        "DevOps", "AI", "LLM", "GenAI", "REST APIs", "Git", "C++", "Spring Boot"
    ]
    found_tech = [t for t in tech_keywords if re.search(r"\b" + re.escape(t) + r"\b", text, re.IGNORECASE)]
    if found_tech:
        details.append(f"🛠️ Tech: {', '.join(found_tech[:6])}")

    # 3. Eligibility / Batch / Experience
    elig_match = re.search(r"(?:Eligibility|Batch|Graduation|Qualifications?|Who can apply|Criteria)\s*[:\-–—]?\s*([^\n]+)", text, re.IGNORECASE)
    if elig_match:
        details.append(f"🎓 Eligibility: {elig_match.group(1).strip()[:80]}")
    else:
        batches = re.findall(r"\b(202[4-8](?:\s*[-–/]\s*202[5-9])?)\s*(?:batch|passout|graduates)?\b", text, re.IGNORECASE)
        if batches:
            details.append(f"🎓 Batch: {batches[0]}")
        elif "fresh graduates" in text.lower() or "fresher" in text.lower():
            details.append("🎓 Freshers / College Students Welcome")

    # 4. Stipend / Duration
    stipend_match = re.search(r"(?:Stipend|Salary|Compensation)\s*[:\-–—]?\s*([^\n]+)", text, re.IGNORECASE)
    if stipend_match:
        details.append(f"💰 Stipend: {stipend_match.group(1).strip()[:60]}")

    duration_match = re.search(r"(?:Duration|Period|Timeline)\s*[:\-–—]?\s*([^\n]+)", text, re.IGNORECASE)
    if duration_match:
        details.append(f"⏳ Duration: {duration_match.group(1).strip()[:60]}")

    # 5. Requirements bullet section
    in_req = False
    req_bullets = []
    for line in lines:
        cleaned_line = line.strip()
        low = cleaned_line.lower()
        if any(r_head in low for r_head in ["requirements:", "what you need:", "skills required:", "criteria:"]):
            in_req = True
            continue
        if in_req:
            if any(stop in low for stop in ["apply", "link", "perks", "why join", "location", "period"]):
                in_req = False
            else:
                cand = clean_role_bullet(cleaned_line)
                if cand and len(cand) < 80:
                    req_bullets.append(cand)
                    if len(req_bullets) >= 3:
                        break
    if req_bullets:
        details.append(f"📋 Requirements: {'; '.join(req_bullets)}")

    # 6. Perks / Why join us
    perks_match = re.search(r"(?:Why join us\?|Perks)\s*[:\-–—]?\s*([^\n]+)", text, re.IGNORECASE)
    if perks_match:
        details.append(f"✨ Perks: {perks_match.group(1).strip()[:80]}")

    return " | ".join(details) if details else "Full-stack development, software engineering, and technical problem-solving."


def parse_internship_details(post_text: str, raw_author: str = "", default_role: str = "") -> dict:
    """
    Parses full post text into structured internship opportunity fields:
    - job_role: specific roles / tracks mentioned
    - company_name: hiring company or organization
    - recruiter_name: recruiter or post author
    - overview: what the internship is about
    - requirements: skills, eligibility, location, and requirements
    """
    cleaned = clean_post_text(post_text)
    company = extract_company(post_text, raw_author=raw_author)
    roles = extract_roles(post_text, default_role=default_role)
    overview = extract_overview(post_text)
    requirements = extract_requirements_and_details(post_text)

    # Recruiter cleanup
    recruiter = raw_author.split("\n")[0].split("•")[0].strip() if raw_author else "Hiring Team"
    recruiter = re.sub(r"Feed\s*post\s*", "", recruiter, flags=re.IGNORECASE).strip() or "Hiring Team"

    return {
        "job_role": roles,
        "company_name": company,
        "recruiter_name": recruiter,
        "overview": overview,
        "requirements": requirements,
    }


