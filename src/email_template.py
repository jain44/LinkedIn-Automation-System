"""
email_template.py - High-Converting Cold Email Templates for Jainam's Internship Outreach
Modeled directly after high-response agency & professional candidate submission formats:
- Clean, structured "SUBMISSION DETAILS" card
- Role-targeted opening hook
- One-page resume attachment callout & 10-15 min call request
- Verifiable job reference footer quoting the recruiter's post
"""

import re
import html
import random
from typing import Dict, Any, Optional


def clean_text(text: Any) -> str:
    if not text:
        return ""
    cleaned = str(text).replace("\r", " ").replace("\n", " ").strip()
    return re.sub(r"\s+", " ", cleaned)


def infer_recruiter_first_name(raw_name: str) -> str:
    name = clean_text(raw_name)
    if not name or "@" in name or any(char.isdigit() for char in name):
        return ""
    bad_tokens = {
        "hiring", "recruiter", "talent", "hr", "manager", "team", "post", "feed",
        "linkedin", "careers", "founder", "director", "lead", "head"
    }
    words = [w for w in re.split(r"\s+", name) if w.lower() not in bad_tokens and len(w) > 1]
    if words:
        first = words[0].capitalize()
        if re.match(r"^[A-Za-z'-]{2,20}$", first):
            return first
    return ""


def clean_role(role_hint: str) -> str:
    role = clean_text(role_hint)
    if not role:
        return "Full Stack & GenAI Developer Intern"

    # Strip search-action / scraper noise prefixes
    noise_patterns = [
        r"^send\s+(?:your\s+)?(?:resume|cv)\s+",
        r"^email\s+(?:your\s+)?(?:resume|cv)\s+",
        r"^share\s+(?:your\s+)?(?:resume|cv)\s+",
        r"^drop\s+(?:your\s+)?(?:resume|cv)\s+",
        r"^hiring\s+interns?\s*(?:remote\s*)?(?:send\s+resume\s*)?",
        r"^apply\s+link\s+",
        r"^forms\s+gle\s+",
        r"^careers\s+intern\s+",
        r"^feed\s+post\s+",
    ]
    for pat in noise_patterns:
        role = re.sub(pat, "", role, flags=re.IGNORECASE).strip()

    role_lower = role.lower().strip()

    # Map common truncated / search-query remnants to professional roles
    if not role_lower or role_lower in ("intern", "internship", "hiring"):
        return "Full Stack & GenAI Developer Intern"
    if role_lower in ("software intern", "software engineering intern", "software intern position"):
        return "Software Engineer Intern"
    if role_lower in ("developer intern", "dev intern", "software dev intern", "intern developer"):
        return "Software Developer Intern"
    if role_lower in ("python intern", "python developer"):
        return "Python Developer Intern"
    if role_lower in ("react intern", "frontend intern", "react developer"):
        return "Frontend Developer Intern"
    if role_lower in ("full stack intern", "fullstack intern"):
        return "Full Stack Developer Intern"
    if role_lower in ("backend intern", "backend developer"):
        return "Backend Developer Intern"
    if role_lower in ("genai intern", "ai intern", "genai developer intern"):
        return "GenAI / AI Developer Intern"

    # Title-case and preserve common tech acronyms
    words = role.split()
    capitalized = []
    acronym_map = {
        "ai": "AI",
        "genai": "GenAI",
        "llm": "LLM",
        "ml": "ML",
        "api": "API",
        "ui": "UI",
        "ux": "UX",
        "it": "IT",
        "c2c": "C2C",
        "qa": "QA",
        "saas": "SaaS"
    }
    for w in words:
        stripped = w.strip("()[]/,.-")
        if stripped.lower() in acronym_map:
            fixed = acronym_map[stripped.lower()]
            w_fixed = w.lower().replace(stripped.lower(), fixed)
            capitalized.append(w_fixed)
        else:
            capitalized.append(w.capitalize())
    return " ".join(capitalized)



# ---------------------------------------------------------------------------
# JD-AWARE SKILL PICKER
# Maps keywords found in role/JD → the subset of Jainam's skills to highlight.
# Each entry: (search_terms, display_skills_string, project_hint)
# ---------------------------------------------------------------------------
_SKILL_PROFILES = [
    # AI / LLM / GenAI
    (
        ["genai", "gen ai", "llm", "langchain", "langgraph", "openai", "gpt", "ai agent",
         "machine learning", "ml engineer", "deep learning", "nlp", "rag", "vector", "huggingface"],
        "LangGraph, LLM Agents, Groq Llama 3.3, OpenAI API, Python, FastAPI, and RAG pipelines",
        "autonomous AI agent systems (GrowthOS — 7 parallel agents) and a multilingual AI legal co-pilot (JusticeAI)"
    ),
    # Full Stack
    (
        ["full stack", "fullstack", "full-stack", "mern", "mean", "next.js", "nextjs", "react", "node.js", "nodejs"],
        "React, Next.js, Node.js, TypeScript, FastAPI, PostgreSQL, MongoDB, and Docker",
        "full-stack production platforms (GrowthOS, JusticeAI, Samyak) shipped end-to-end"
    ),
    # Frontend / UI
    (
        ["frontend", "front end", "front-end", "ui developer", "react developer", "vue", "angular",
         "tailwind", "css", "html", "javascript", "typescript"],
        "React, Next.js, TypeScript, TailwindCSS, and responsive UI/UX engineering",
        "production-grade frontends including an award-winning ACM chapter portal and a Jain spiritual learning platform"
    ),
    # Backend / API
    (
        ["backend", "back end", "back-end", "api developer", "rest api", "django", "flask",
         "fastapi", "express", "microservice", "spring", "server"],
        "Node.js, Express, FastAPI (Python), PostgreSQL, MongoDB, Prisma, and REST API design",
        "scalable API backends powering 3 live production systems"
    ),
    # Python / Data
    (
        ["python", "django", "flask", "data engineer", "data science", "analytics", "pandas",
         "numpy", "sklearn", "scikit", "xgboost"],
        "Python, FastAPI, XGBoost, Pandas, PostgreSQL, and ML model deployment via Docker",
        "an MSME credit risk engine (Kavach — AUC-ROC 0.74, FastAPI + XGBoost) and financial crime investigation agents"
    ),
    # Java
    (
        ["java", "spring boot", "spring", "j2ee", "maven", "hibernate", "kotlin"],
        "Java, OOP principles, SQL, REST APIs, and backend system design",
        "production backend architectures and API-driven systems across multiple internships"
    ),
    # Mobile / Android / Flutter
    (
        ["android", "flutter", "mobile", "ios", "react native", "kotlin", "dart"],
        "React Native, TypeScript, REST API integration, and cross-platform mobile development",
        "mobile-responsive production apps and cross-platform UI systems"
    ),
    # DevOps / Cloud
    (
        ["devops", "cloud", "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "terraform",
         "linux", "deployment", "infrastructure"],
        "Docker, CI/CD pipelines, Git, REST APIs, and cloud-ready deployment architectures",
        "containerised production deployments and scalable API-driven infrastructure"
    ),
    # Software Engineer (generic SWE)
    (
        ["software engineer", "software developer", "sde", "swe", "software intern"],
        "React, Next.js, Node.js, Python, FastAPI, Docker, and LangGraph",
        "production full-stack systems and autonomous AI agents"
    ),
]

_DEFAULT_SKILLS = "React, Next.js, Node.js, FastAPI, Python, and LangGraph"
_DEFAULT_PROJECT_HINT = "production full-stack systems and autonomous AI agents"


def pick_skills_for_jd(role: str, post_snippet: str) -> tuple:
    """
    Analyses the job role and post snippet, returns (skills_string, project_hint)
    matching Jainam's most relevant stack for that JD.
    """
    text = (role + " " + post_snippet).lower()
    best_hits = 0
    best_skills = _DEFAULT_SKILLS
    best_hint = _DEFAULT_PROJECT_HINT

    for keywords, skills, hint in _SKILL_PROFILES:
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_hits:
            best_hits = hits
            best_skills = skills
            best_hint = hint

    return best_skills, best_hint


def generate_subject(lead: Dict[str, Any], candidate: Dict[str, Any]) -> str:
    """
    Generates high-response subject line modeled after professional submission format:
    e.g. "Jainam Jain – Full Stack Developer Intern | 9.92 CGPA | Immediate"
    """
    role = clean_role(lead.get("job_role", "Full Stack Developer Intern"))
    name = candidate.get("full_name", "Jainam Jain")
    cgpa = candidate.get("cgpa", "9.92 / 10").replace(" / 10", "").strip()

    templates = [
        f"{name} – {role} | {cgpa} CGPA | Immediate Joiner",
        f"{role} Application – {name} | {cgpa} CGPA | Full Stack & GenAI",
        f"{name} – {role} | TCET Mumbai | Production Projects | Available Now",
        f"Internship Application: {role} – {name} | {cgpa} CGPA | Mumbai",
    ]
    return random.choice(templates)


def generate_email_body(lead: Dict[str, Any], candidate: Dict[str, Any]) -> str:
    """
    Generates plain-text submission email with structured details and job reference footer.
    """
    recruiter_raw = lead.get("recruiter_name", "")
    first_name = infer_recruiter_first_name(recruiter_raw)

    if first_name:
        salutation = f"Dear {first_name},"
    elif recruiter_raw and len(recruiter_raw.split()) <= 3 and not any(c.isdigit() for c in recruiter_raw):
        salutation = f"Dear {clean_text(recruiter_raw)},"
    else:
        salutation = "Dear Hiring Manager,"

    role = clean_role(lead.get("job_role", "Full Stack & GenAI Developer Intern"))
    name = candidate.get("full_name", "Jainam Jain")
    phone = candidate.get("phone", "+91 79779 63474")
    email = candidate.get("email", "jainamjain1116@gmail.com")
    github = candidate.get("github", "https://github.com/jain44")
    linkedin = candidate.get("linkedin", "https://www.linkedin.com/in/jainam-jain-746188263")
    resume_drive_link = candidate.get("resume_drive_link") or candidate.get("resumes", {}).get("drive_link", "https://drive.google.com/file/d/1K_q0i7hr_CFEbV4ec5Y3pS_ts-fLi5zs/view?usp=drivesdk")
    cgpa = candidate.get("cgpa", "9.92 / 10")
    college = candidate.get("college", "TCET Mumbai")
    degree = candidate.get("degree", "B.Tech IT + Minor in AI, 2024-2028")
    experience = candidate.get("total_experience", "1+ Year (3 internships + 2 live production systems)")

    post_snippet = clean_text(lead.get("post_snippet", ""))
    post_url = clean_text(lead.get("post_url", "")) or "https://www.linkedin.com/search/results/content/"

    # JD-aware skill picker — tailors skills/projects to the actual role + post snippet
    jd_skills, jd_project_hint = pick_skills_for_jd(role, post_snippet)

    # Universal opener — confident, direct, JD-tailored for EVERY email
    opening = (
        f"I came across your posting for the {role} position. "
        f"With 1+ year of hands-on experience building {jd_project_hint}, "
        f"my background in {jd_skills} aligns directly with what you are looking for."
    )

    # Submission details block
    details_block = f"""--- SUBMISSION DETAILS ---
• Candidate Name    : {name}
• Applied Role      : {role}
• Education         : {degree}, {college} (CGPA: {cgpa})
• Experience        : {experience}
• Tech Stack        : React, Next.js, Node.js, Python, FastAPI, Docker, LangGraph, LLM Agents
• Notable Projects  :
    – FinCrime Investigation    : LangGraph multi-agent orchestration → {github}/Financial-Crime-Investigation-Agent
    – GrowthOS                  : 7 autonomous AI agents for growth (Next.js 14) → {github}/GrowthhOs
    – Kavach (Sentinel)         : ML MSME default prediction (AUC 0.74, FastAPI) → {github}/kavach
    – JusticeAI                 : AI-powered legal co-pilot (Groq + Node.js) → {github}/JusticeAI
    – Samyak                    : Educational platform (Next.js, React 19, Supabase) → {github}/samyak
• GitHub Portfolio  : {github}
• Location          : Mumbai, India
• Work Mode         : 100% Remote or Mumbai Onsite / Hybrid
• Availability      : Immediate — Full-time Internship
• Phone / WhatsApp  : {phone}
• Email             : {email}
• LinkedIn          : {linkedin}
• Resume (PDF Drive): {resume_drive_link}"""

    # Call to action & sign-off
    closing = (
        "Please find my 1-page resume attached for your review (also accessible online: "
        f"{resume_drive_link}). "
        "I would love the opportunity to contribute to your engineering team and am available for an "
        "interview at your convenience. If helpful, I can also share a quick 2-minute walkthrough of "
        "any of my live projects. Thank you for your time — I look forward to hearing from you."
    )

    signature = f"""Best regards,
{name}
B.Tech IT | {college} | CGPA: {cgpa}
📞 {phone}  |  ✉ {email}
LinkedIn : {linkedin}
GitHub   : {github}
Resume   : {resume_drive_link}"""

    # Optional Job reference section at bottom
    job_ref = ""
    if post_snippet or post_url:
        snippet_display = post_snippet[:280] + ("..." if len(post_snippet) > 280 else "")
        job_ref = f"""\n\n--- JOB REFERENCE & DESCRIPTION ---
LinkedIn Job Source: {post_url}
"{snippet_display}" """

    body = f"""{salutation}

{opening}

Please find my submission details below for your review:

{details_block}

{closing}

{signature}{job_ref}"""

    return body.strip()


def generate_email_html_body(
    plain_body: str,
    lead: Optional[Dict[str, Any]] = None,
    candidate: Optional[Dict[str, Any]] = None
) -> str:
    """
    Renders email into a visually polished, high-deliverability HTML layout matching
    the Gmail reference card screenshot with structured submission box and job reference footer.
    """
    # Parse candidate / lead if provided or fallback
    c = candidate or {}
    l = lead or {}

    name = c.get("full_name", "Jainam Jain")
    phone = c.get("phone", "+91 79779 63474")
    email = c.get("email", "jainamjain1116@gmail.com")
    github = c.get("github", "https://github.com/jain44")
    linkedin = c.get("linkedin", "https://www.linkedin.com/in/jainam-jain-746188263")
    resume_drive_link = c.get("resume_drive_link") or c.get("resumes", {}).get("drive_link", "https://drive.google.com/file/d/1K_q0i7hr_CFEbV4ec5Y3pS_ts-fLi5zs/view?usp=drivesdk")
    role = clean_role(l.get("job_role", "Full Stack & GenAI Developer Intern"))
    cgpa = c.get("cgpa", "9.92 / 10")
    college = c.get("college", "TCET Mumbai")
    degree = c.get("degree", "B.Tech IT + Minor in AI, 2024-2028")
    experience = c.get("total_experience", "1+ Year (3 internships + 2 live production systems)")
    post_snippet = clean_text(l.get("post_snippet", ""))
    post_url = clean_text(l.get("post_url", "")) or "https://www.linkedin.com/search/results/content/"

    # If lead/candidate wasn't explicitly passed, extract key values from plain_body
    first_line = plain_body.split("\n")[0] if plain_body else "Dear Hiring Manager,"
    salutation = first_line if "Dear" in first_line or "Hi" in first_line else "Dear Hiring Manager,"

    # Extract opening paragraph
    paras = [p.strip() for p in plain_body.split("\n\n") if p.strip()]
    opening_p = ""
    for p in paras:
        if "writing to express" in p or "came across" in p or "B.Tech IT" in p:
            opening_p = p
            break
    # Extract opening paragraph from plain_body (already JD-tailored by generate_email_body)
    paras = [p.strip() for p in plain_body.split("\n\n") if p.strip()]
    opening_p = ""
    for p in paras:
        if "came across" in p or "writing to express" in p or "B.Tech IT" in p:
            opening_p = p
            break
    if not opening_p:
        # Fallback: build JD-aware opener fresh from lead data
        jd_skills, jd_project_hint = pick_skills_for_jd(role, post_snippet)
        opening_p = (
            f"I came across your posting for the {role} position. "
            f"With 1+ year of hands-on experience building {jd_project_hint}, "
            f"my background in {jd_skills} aligns directly with what you are looking for."
        )

    # Job snippet from plain body if not in lead
    if not post_snippet and "--- JOB REFERENCE & DESCRIPTION ---" in plain_body:
        after_ref = plain_body.split("--- JOB REFERENCE & DESCRIPTION ---")[-1]
        post_snippet = clean_text(after_ref.replace("LinkedIn Job Source:", ""))

    job_ref_html = ""
    if post_snippet or post_url:
        disp_snippet = post_snippet[:280] + ("..." if len(post_snippet) > 280 else "")
        job_ref_html = f"""
        <div style="margin-top: 24px; padding-top: 14px; border-top: 1px dashed #cbd5e1;">
            <p style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; margin: 0 0 6px 0; text-transform: uppercase;">
                --- Job Reference &amp; Description ---
            </p>
            <p style="font-size: 12px; color: #475569; margin: 0 0 6px 0;">
                <strong>LinkedIn Source:</strong> <a href="{html.escape(post_url)}" style="color: #0a66c2; text-decoration: none;">{html.escape(post_url)}</a>
            </p>
            <div style="background-color: #f1f5f9; border-left: 3px solid #94a3b8; border-radius: 4px; padding: 10px 14px; font-size: 12.5px; color: #334155; font-style: italic; line-height: 1.5;">
                {html.escape(disp_snippet)}
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    line-height: 1.6;
    font-size: 14.5px;
    margin: 0;
    padding: 12px;
    background-color: #ffffff;
}}
p {{
    margin: 0 0 14px 0;
}}
a {{
    color: #0a66c2;
    text-decoration: none;
}}
a:hover {{
    text-decoration: underline;
}}
.submission-card {{
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #0a66c2;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 18px 0;
    line-height: 1.7;
    font-size: 14px;
}}
.card-header {{
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.8px;
    color: #0a66c2;
    margin-bottom: 10px;
    text-transform: uppercase;
}}
.detail-item {{
    margin-bottom: 4px;
    color: #334155;
}}
.detail-label {{
    font-weight: 600;
    color: #0f172a;
}}
</style>
</head>
<body>
    <p>{html.escape(salutation)}</p>

    <p>{html.escape(opening_p)}</p>

    <p>Please find my submission details below for your review:</p>

    <div class="submission-card">
        <div class="card-header">--- SUBMISSION DETAILS ---</div>
        <div class="detail-item">&bull; <span class="detail-label">Candidate Name:</span> {html.escape(name)}</div>
        <div class="detail-item">&bull; <span class="detail-label">Applied Role:</span> {html.escape(role)}</div>
        <div class="detail-item">&bull; <span class="detail-label">Education:</span> {html.escape(degree)}, {html.escape(college)} (CGPA: {html.escape(cgpa)})</div>
        <div class="detail-item">&bull; <span class="detail-label">Total Experience:</span> {html.escape(experience)}</div>
        <div class="detail-item">&bull; <span class="detail-label">Primary Tech Stack:</span> React, Next.js, Node.js, Python, FastAPI, Docker, LangGraph, LLM Agents</div>
        <div class="detail-item">&bull; <span class="detail-label">Key Projects (GitHub):</span> 
            <a href="{html.escape(github)}/Financial-Crime-Investigation-Agent" style="color: #2563eb; font-weight: 600; text-decoration: underline;">FinCrime Agent</a> (LangGraph Multi-Agent), 
            <a href="{html.escape(github)}/GrowthhOs" style="color: #2563eb; font-weight: 600; text-decoration: underline;">GrowthOS</a> (Next.js/React Agents), 
            <a href="{html.escape(github)}/kavach" style="color: #2563eb; font-weight: 600; text-decoration: underline;">Kavach</a> (FastAPI ML AUC 0.74), 
            <a href="{html.escape(github)}/JusticeAI" style="color: #2563eb; font-weight: 600; text-decoration: underline;">JusticeAI</a> (Groq/Node AI), 
            <a href="{html.escape(github)}/samyak" style="color: #2563eb; font-weight: 600; text-decoration: underline;">Samyak</a> (React 19/Next.js)
        </div>
        <div class="detail-item">&bull; <span class="detail-label">Current Location:</span> Mumbai, India</div>
        <div class="detail-item">&bull; <span class="detail-label">Work Mode:</span> 100% Remote (Global / US / India) or Mumbai Hybrid</div>
        <div class="detail-item">&bull; <span class="detail-label">Availability:</span> Immediate (Full-time or Part-time)</div>
        <div class="detail-item">&bull; <span class="detail-label">Phone / WhatsApp:</span> <a href="https://wa.me/{html.escape(phone.replace(' ', '').replace('+', ''))}" style="color: #16a34a; font-weight: 600; text-decoration: underline;">{html.escape(phone)}</a></div>
        <div class="detail-item">&bull; <span class="detail-label">Email Address:</span> <a href="mailto:{html.escape(email)}">{html.escape(email)}</a></div>
        <div class="detail-item">&bull; <span class="detail-label">LinkedIn Profile:</span> <a href="{html.escape(linkedin)}">{html.escape(linkedin)}</a></div>
        <div class="detail-item">&bull; <span class="detail-label">GitHub / Portfolio:</span> <a href="{html.escape(github)}">{html.escape(github)}</a></div>
        <div class="detail-item">&bull; <span class="detail-label">Resume (Google Drive):</span> <a href="{html.escape(resume_drive_link)}" style="color: #2563eb; font-weight: 600; text-decoration: underline;">View 1-Page Resume PDF</a></div>
    </div>

    <div style="margin: 16px 0 16px 0;">
        <a href="{html.escape(resume_drive_link)}" style="display: inline-block; background-color: #2563eb; color: #ffffff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 13px; margin-right: 8px;">&#128196; View Resume (Drive)</a>
        <a href="{html.escape(github)}" style="display: inline-block; background-color: #0f172a; color: #ffffff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 13px; margin-right: 8px;">&#128025; View GitHub Repositories</a>
        <a href="{html.escape(linkedin)}" style="display: inline-block; background-color: #0a66c2; color: #ffffff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 13px;">&#128188; View LinkedIn Profile</a>
    </div>

    <p>
        Please find my updated 1-page resume attached. I would love the opportunity to contribute to your engineering team and am available for an interview at your earliest convenience. If helpful, I can also share a 2-minute live demo or codebase walkthrough of any of my projects. Thank you for your time — I look forward to hearing from you.
    </p>

    <p style="margin-top: 18px; margin-bottom: 4px;">Best regards,</p>
    <p style="margin: 0; font-weight: 700; color: #0f172a; font-size: 15px;">{html.escape(name)}</p>
    <p style="margin: 2px 0 6px 0; color: #475569; font-size: 13.5px;">
        Full Stack &amp; GenAI Developer Intern | {html.escape(college)} ({html.escape(cgpa)} CGPA)
    </p>
    <p style="margin: 0; font-size: 13px; color: #64748b;">
        Phone: <a href="tel:{html.escape(phone.replace(' ', ''))}">{html.escape(phone)}</a> | 
        Email: <a href="mailto:{html.escape(email)}">{html.escape(email)}</a><br>
        LinkedIn: <a href="{html.escape(linkedin)}">{html.escape(linkedin)}</a><br>
        GitHub: <a href="{html.escape(github)}">{html.escape(github)}</a>
    </p>

    {job_ref_html}
</body>
</html>"""
