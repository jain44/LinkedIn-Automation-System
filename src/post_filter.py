"""
post_filter.py - Internship Post Relevance and Spam Filtering
Filters out coaching institutes, course promotions, and unpaid fake job offers.
Ranks leads by relevance to Full Stack, GenAI, and Software Engineering.
"""

import re
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Terms indicating commercial courses, training institutes, or fake placement schemes
SPAM_TERMS = [
    "training and placement",
    "placement support",
    "pay after placement",
    "course fee",
    "registration fee",
    "paid training",
    "100% placement guarantee",
    "proxy interview",
    "fake profile",
    "join our batch",
    "masterclass",
    "bootcamp fee",
    "bench sales",
    "hotlist",
    "c2c",
    # Fake / unpaid internship signals
    "no stipend",
    "unpaid internship",
    "certificate only",
    "learn and earn",
    "training institute",
    "skill development institute",
    "join our program",
    "enroll now",
    "limited seats",
    "free internship",
    "work for experience",
    "exposure only",
    "for free",
    "no salary",
]

# Signals that confirm this is a genuine paid opportunity
PAID_SIGNALS = [
    "stipend",
    "paid internship",
    "paid opportunity",
    "compensation",
    "salary",
    "lpa",
    "per month",
    "₹",
    "inr",
    "usd",
    "$",
    "remuneration",
    "ctc",
    "pay",
]

# Pure software engineering, programming, and AI technical keywords
TECH_INTERN_KEYWORDS = [
    "developer", "engineer", "software", "full stack", "fullstack", "frontend",
    "backend", "web development", "web developer", "react", "next.js", "node",
    "python", "fastapi", "ai", "genai", "llm", "machine learning", "coding",
    "programmer", "programming", "git", "api", "database", "sql", "mongodb",
    "postgresql", "javascript", "typescript", "docker", "devops", "cloud",
    "langgraph", "llama", "flask", "django"
]

# Non-tech domains that should never be processed for Jainam's profile
NON_TECH_DOMAINS = [
    "human resources", "hr intern", "talent acquisition", "recruiter intern",
    "recruitment intern", "psychology", "business development intern", "bda intern",
    "bde intern", "sales intern", "marketing intern", "digital marketing", "seo intern",
    "content writer", "content writing", "copywriting", "graphic design", "graphic designer",
    "social media intern", "operations intern", "telecalling", "telecaller", "customer support",
    "customer service", "finance intern", "accounting intern", "legal intern", "video editor",
    "video editing", "public relations", "pr intern", "event management"
]

# Hiring indicator signals
HIRING_SIGNALS = [
    "hiring", "looking for", "we are hiring", "opening", "openings",
    "urgently hiring", "immediate joiner", "send resume", "drop resume",
    "share cv", "email cv", "apply at", "reach out at", "send your portfolio",
    "dm me", "dm for", "comment below", "apply now", "applications open",
    "we need", "join our team", "join us"
]



# Posts from students/job-seekers looking for an internship (NOT recruiters)
JOB_SEEKER_TERMS = [
    "looking for a",
    "looking for an",
    "looking for internship",
    "looking for internships",
    "looking for trainee",
    "seeking internship",
    "seeking an internship",
    "seeking opportunities",
    "seeking entry level",
    "i am looking for",
    "i'm looking for",
    "im looking for",
    "actively looking for",
    "actively looking",
    "actively seeking",
    "open to work",
    "open to opportunities",
    "open to internship",
    "open to unpaid",
    "aspiring mern",
    "aspiring developer",
    "aspiring software",
    "aspiring data",
    "student looking for",
    "fresher looking for",
    "beginner-friendly internship",
    "if you have any internship opening",
    "if you have any opening",
    "reach out if you have any opening",
    "opentowork",
    "#opentowork",
    "openforwork",
    "#openforwork",
    "what i'm looking for",
    "what im looking for",
    "what i am looking for",
    "a bit about me",
    "reposts help",
    "reposts help a lot",
    "appreciate a message or a referral",
    "referrals appreciated",
]

# Posts from people announcing they GOT an internship (not offering one)
SELF_ANNOUNCEMENT_TERMS = [
    "excited to share",
    "happy to share",
    "thrilled to share",
    "pleased to announce",
    "excited to announce",
    "happy to announce",
    "i have been selected",
    "i've been selected",
    "i got selected",
    "i am selected",
    "selected as a",
    "selected as an",
    "selected as intern",
    "selected as python",
    "selected for internship",
    "i have joined",
    "i've joined",
    "have joined",
    "i joined",
    "i am joining",
    "i'm joining",
    "starting my internship",
    "started my internship",
    "beginning my internship",
    "first day at",
    "new beginning",
    "my new journey",
    "starting my journey",
    "i am thrilled",
    "got my offer letter",
    "received my offer letter",
    "received offer letter",
    "signed offer letter",
    "my offer letter",
    "intern id",
    "grateful to share",
    "proud to share",
    "blessed to share",
    "grateful for this opportunity",
    "i will be joining",
    "i'll be joining",
    "got an internship",
    "secured an internship",
    "landed an internship",
    "completed my internship",
    "internship certificate",
    "completion certificate",
    "my internship offer",
    "excited to begin",
]

# Career retrospectives, personal storytelling, work anniversaries, and advice/opinion essays
STORY_AND_RETROSPECTIVE_TERMS = [
    # Nostalgia, Anniversaries & Career History
    "years ago today",
    "years ago,",
    "years ago i",
    "years ago we",
    "walked into an automobile",
    "walked into a company",
    "walked into the office",
    "walked into my first",
    "i was a campus hire",
    "when i was a campus hire",
    "when i was in college",
    "when i was an intern",
    "when i started my career",
    "when i first started",
    "when i graduated",
    "looking back at my career",
    "looking back on my career",
    "looking back over the past",
    "looking back at the journey",
    "looking back,",
    "my career journey",
    "my professional journey",
    "journey so far",
    "work anniversary",
    "celebrating my work anniversary",
    "celebrating 10 years",
    "celebrating 12 years",
    "celebrating 5 years",
    "years of experience have taught me",
    "years have taught me",
    "years in the industry",
    "the rest, as they say, is history",
    "the rest is history",
    "down memory lane",
    "trip down memory lane",
    "flashback to",
    "throwback to",
    "nostalgia",
    "nostalgic",

    # Advice, Opinion, Philosophy & Thought Leadership
    "campus recruitment is not a hiring",
    "recruitment is not a hiring",
    "recruitment is not just",
    "hiring is not a",
    "hiring is not about",
    "leadership is about",
    "leadership lesson",
    "lessons learned:",
    "lessons i learned",
    "things i've learned:",
    "things i have learned:",
    "things 12 years have taught",
    "things that taught me",
    "a few things i learned",
    "what 10 years taught me",
    "what my career taught me",
    "dear freshers",
    "dear students",
    "dear job seekers",
    "advice to students",
    "advice to freshers",
    "advice for students",
    "advice for freshers",
    "advice for job seekers",
    "career advice for",
    "my 2 cents",
    "unpopular opinion:",
    "food for thought",
    "here is what i learned",
    "here's what i learned",
    "a quick reflection",
    "just a reflection",
    "sunday musings",
    "monday motivation",
    "life lessons from",
    "career retrospective",
]

STORY_REGEX_PATTERNS = [
    re.compile(r"\b\d+\s+years\s+ago\b", re.IGNORECASE),
    re.compile(r"\b\d+\s+years\s+have\s+taught\s+me\b", re.IGNORECASE),
    re.compile(r"\b\d+\s+years\s+in\s+(?:hr|recruitment|tech|engineering|corporate)\b", re.IGNORECASE),
    re.compile(r"\bwalked\s+into\s+(?:an?|the)\b", re.IGNORECASE),
    re.compile(r"\bwhen\s+i\s+(?:first\s+)?joined\b", re.IGNORECASE),
    re.compile(r"\blooking\s+back\s+(?:at|on)\s+my\s+career\b", re.IGNORECASE),
    re.compile(r"\bhappy\s+work\s+anniversary\b", re.IGNORECASE),
    re.compile(r"\bcelebrating\s+(?:my\s+)?\d+\s*(?:st|nd|rd|th)?\s+year\b", re.IGNORECASE),
]


def is_blacklisted(
    email: str = "",
    text: str = "",
    company: str = "",
    recruiter: str = "",
    url: str = "",
) -> Tuple[bool, str]:
    """
    Checks if an email, post text, company name, recruiter, or link belongs to a blacklisted
    entity (such as The GAO Group, GAO Tek, GAO RFID, or related mass/unpaid entities).
    Returns (True, reason) if blacklisted, otherwise (False, "").
    """
    from config import BLACKLISTED_DOMAINS, BLACKLISTED_KEYWORDS

    # 1. Check email address & domain
    if email:
        em = email.strip().lower()
        if "hr-afg-teamb@thegaogroup.com" in em:
            return True, f"Explicitly blacklisted email: {email}"

        # Check domain
        if "@" in em:
            domain = em.split("@")[-1].strip()
            for bd in BLACKLISTED_DOMAINS:
                if domain == bd or domain.endswith("." + bd):
                    return True, f"Email domain '{domain}' matches blacklisted domain '{bd}'"
            # General GAO pattern in domain: e.g. gao*.com, *gao* in domain name
            if re.search(r"\bgao[a-z0-9\-]*\.", domain) or "thegao" in domain:
                return True, f"Email domain '{domain}' contains GAO signature"

        # Check if local part indicates GAO batch (e.g. hr-*-teama/b/c/d@...)
        if re.match(r"^hr-[a-z0-9\-]+@(thegaogroup|gao)", em):
            return True, f"Email '{em}' matches GAO recruiter pattern"

    # 2. Check URL / link
    if url:
        u_low = url.strip().lower()
        for bd in BLACKLISTED_DOMAINS:
            if bd in u_low:
                return True, f"URL contains blacklisted domain '{bd}'"
        if re.search(r"//[a-z0-9.\-]*gao[a-z0-9\-]*\.", u_low):
            return True, "URL matches GAO domain pattern"

    # 3. Check Company name
    if company:
        comp_low = company.strip().lower()
        for kw in BLACKLISTED_KEYWORDS:
            if kw in comp_low:
                return True, f"Company '{company}' matches blacklisted keyword '{kw}'"
        if re.search(r"\bgao\b", comp_low):
            return True, f"Company '{company}' matches 'GAO'"

    # 4. Check Recruiter name
    if recruiter:
        rec_low = recruiter.strip().lower()
        for kw in BLACKLISTED_KEYWORDS:
            if kw in rec_low:
                return True, f"Recruiter '{recruiter}' matches blacklisted keyword '{kw}'"
        if "gao" in rec_low and ("tek" in rec_low or "group" in rec_low or "tech" in rec_low):
            return True, f"Recruiter '{recruiter}' contains GAO reference"

    # 5. Check Post text / snippet
    if text:
        t_low = text.lower()
        for kw in BLACKLISTED_KEYWORDS:
            if kw in t_low:
                return True, f"Text matches blacklisted keyword '{kw}'"
        for bd in BLACKLISTED_DOMAINS:
            if bd in t_low:
                return True, f"Text references blacklisted domain '{bd}'"
        if re.search(r"\b(?:the\s+)?gao\s+(?:group|tek|tech|rfid|research|staff|inc|ltd)\b", t_low):
            return True, "Text matches GAO organization pattern"

    return False, ""


def is_location_allowed(text: str, location_hint: str = "") -> Tuple[bool, str]:
    """
    Checks whether a post's location meets Jainam's constraints:
    - Onsite/In-Office/Hybrid is ONLY allowed in Mumbai / MMR.
    - Outside Mumbai, the position MUST be strictly Remote/Virtual/WFH.
    - Explicit non-Mumbai locations without remote (e.g. Lahore, Pakistan, Bangalore, Noida, Canada) are rejected.
    Returns (True, reason) if allowed, or (False, rejection_reason) if blocked.
    """
    from config import ALLOWED_MUMBAI_LOCATIONS, REMOTE_KEYWORDS, NON_MUMBAI_LOCATIONS

    combined = f"{location_hint} {text}".lower()

    # 1. Check for negative remote indicators ("not remote", "no remote", "cannot work remote")
    neg_remote_patterns = [
        r"\bnot\s+remote\b",
        r"\bno\s+remote\b",
        r"\bnon-remote\b",
        r"\bnon\s+remote\b",
        r"\bremote\s+is\s+not\s+available\b",
        r"\bno\s+wfh\b",
        r"\bin-person\s+only\b",
        r"\bonly\s+onsite\b",
        r"\bonsite\s+only\b",
        r"\bwork\s+from\s+office\s+only\b",
    ]
    is_neg_remote = any(re.search(p, combined) for p in neg_remote_patterns)

    # 2. Check if remote is offered
    is_remote = False
    if not is_neg_remote:
        for rk in REMOTE_KEYWORDS:
            if re.search(r"\b" + re.escape(rk) + r"\b", combined):
                is_remote = True
                break

    # 3. Check if Mumbai is mentioned
    is_mumbai = False
    for ml in ALLOWED_MUMBAI_LOCATIONS:
        if re.search(r"\b" + re.escape(ml) + r"\b", combined):
            is_mumbai = True
            break

    # 4. Extract explicit location tags (e.g. "📍 Location: Johar Town, Lahore", "📍 Bengaluru (Hybrid)", "Location: Noida")
    loc_matches = re.findall(
        r"(?:📍|Location|Work Mode|Mode|City|Office Location|Job Location)\s*[:\-–—]?\s*([^\n|]+)",
        combined,
        re.IGNORECASE
    )
    for loc_str in loc_matches:
        loc_clean = loc_str.strip()
        loc_has_remote = any(re.search(r"\b" + re.escape(rk) + r"\b", loc_clean) for rk in REMOTE_KEYWORDS)
        loc_has_mumbai = any(re.search(r"\b" + re.escape(ml) + r"\b", loc_clean) for ml in ALLOWED_MUMBAI_LOCATIONS)

        if loc_has_remote or loc_has_mumbai:
            continue

        # Check if this explicit location line mentions a non-Mumbai location
        for nml in NON_MUMBAI_LOCATIONS:
            if re.search(r"\b" + re.escape(nml) + r"\b", loc_clean):
                return False, f"Explicit non-Mumbai location specified: '{loc_clean[:50]}' (Non-remote)"

    # 5. Check for Onsite/Hybrid/WFO requirement tied to a non-Mumbai location
    onsite_hybrid_terms = [
        "onsite", "on-site", "in-office", "in office", "work from office",
        "wfo", "work-from-office", "hybrid", "office-based", "office based",
        "work at office", "at our office", "office in", "relocate to"
    ]
    has_onsite_signal = any(re.search(r"\b" + re.escape(oh) + r"\b", combined) for oh in onsite_hybrid_terms)

    # If onsite/hybrid signal exists without Mumbai:
    if has_onsite_signal and not is_mumbai:
        for nml in NON_MUMBAI_LOCATIONS:
            if re.search(r"\b" + re.escape(nml) + r"\b", combined):
                return False, f"Onsite/Hybrid requirement in non-Mumbai location ('{nml}')"

    # 6. If non-Mumbai location is mentioned and NO remote signal at all exists
    if not is_remote and not is_mumbai:
        for nml in NON_MUMBAI_LOCATIONS:
            if re.search(r"\b" + re.escape(nml) + r"\b", combined):
                return False, f"Located in '{nml}' with no remote option"

    # 7. If negative remote was stated and not in Mumbai:
    if is_neg_remote and not is_mumbai:
        return False, "Non-remote job outside Mumbai"

    return True, "Valid location (Remote or Mumbai)"


def evaluate_post(post_text: str, has_email: bool = False, has_link: bool = False, has_phone: bool = False) -> Tuple[bool, int, str]:
    """
    Evaluates whether a LinkedIn post is a valid tech internship opportunity.
    Returns:
        (is_valid, score, reason)
    """
    text = str(post_text or "").lower()
    if not text or len(text) < 30:
        return False, 0, "Post text too short"

    # Check for blacklisted entities (e.g. The GAO Group, GAO Tech)
    blacklisted, b_reason = is_blacklisted(text=text)
    if blacklisted:
        return False, 0, f"Filtered out: Blacklisted entity ({b_reason})"

    # Check location constraints: Onsite ONLY in Mumbai, otherwise strictly Remote
    loc_ok, loc_reason = is_location_allowed(text)
    if not loc_ok:
        return False, 0, f"Filtered out location constraint: {loc_reason}"

    # Check for scam / coaching institute terms
    for spam in SPAM_TERMS:
        if spam in text:
            return False, 0, f"Filtered out due to scam/coaching term: '{spam}'"

    # Check for student / candidate job seeker posts
    for phrase in JOB_SEEKER_TERMS:
        if phrase in text:
            return False, 0, f"Filtered out: job-seeker post ('{phrase}')"

    # Check for self-announcement posts (student got an internship, not offering one)
    for phrase in SELF_ANNOUNCEMENT_TERMS:
        if phrase in text:
            return False, 0, f"Filtered out: self-announcement post ('{phrase}')"

    # Check for personal stories, career retrospectives, work anniversaries, and advice essays
    for phrase in STORY_AND_RETROSPECTIVE_TERMS:
        if phrase in text:
            return False, 0, f"Filtered out: career story/retrospective/advice post ('{phrase}')"

    for pat in STORY_REGEX_PATTERNS:
        if pat.search(text):
            return False, 0, f"Filtered out: retrospective story pattern ('{pat.pattern}')"


    # Check for non-tech fields (HR, Marketing, Sales, Content, etc.)
    for non_tech in NON_TECH_DOMAINS:
        if non_tech in text:
            tech_role_words = ["software", "developer", "engineer", "full stack", "programmer", "coding", "python", "react", "it intern", "tech"]
            if not any(trw in text for trw in tech_role_words):
                return False, 0, f"Filtered out non-tech domain: '{non_tech}'"

    # Check for tech / intern signals
    intern_hit = any(k in text for k in ["intern", "internship", "trainee", "fresher", "freshers", "junior", "hiring"])
    tech_hit = any(k in text for k in TECH_INTERN_KEYWORDS) or any(k in text for k in ["tech", "it", "web", "app", "code", "coding", "software", "development", "data", "ai", "engineer", "developer"])
    hiring_hit = any(k in text for k in HIRING_SIGNALS) or ("@" in text) or ("resume" in text) or ("cv" in text) or has_link or has_phone
    paid_hit = any(k in text for k in PAID_SIGNALS)

    # If this post already has a direct recruiter email, apply link, or WhatsApp/phone, accept it if it has general tech/intern relevance
    if has_email or has_link or has_phone:
        if any(k in text for k in ["intern", "trainee", "fresher", "developer", "engineer", "hiring", "software", "tech", "web", "code"]):
            score = 90
            if paid_hit:
                score = 100
            elif tech_hit:
                score = 95
            return True, score, "Recruiter post with direct opportunity"

    # Must mention internship/hiring context
    if not (intern_hit or "hiring" in text):
        return False, 10, "No internship or hiring keywords found"

    # MANDATORY: Must match tech/software development profile
    if not tech_hit:
        return False, 0, "No tech/software development keywords found"

    # Must have at least one genuine hiring signal (confirms it's a recruiter post)
    if not hiring_hit:
        return False, 0, "No hiring signals — likely not a genuine recruiter post"

    # Calculate match score (0 - 100)
    score = 50
    if intern_hit:
        score += 15
    if tech_hit:
        score += 15
    if hiring_hit:
        score += 10
    if paid_hit:
        score += 10

    # Bonus points for specific high-value domains Jainam excels in
    if any(k in text for k in ["genai", "llm", "ai", "langgraph"]):
        score += 10
    if any(k in text for k in ["full stack", "react", "next.js", "node"]):
        score += 10
    if "remote" in text:
        score += 5
    if any(k in text for k in ["usd", "$", "us"]):
        score += 5

    score = min(score, 100)
    return True, score, "Relevant tech internship from genuine recruiter"
