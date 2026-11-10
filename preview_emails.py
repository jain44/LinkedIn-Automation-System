#!/usr/bin/env python3
"""
preview_emails.py - Instant Email Body and Subject Line Previewer
Allows previewing generated cold emails for different simulated recruiters and roles.
"""

import sys
import io

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import CANDIDATE, DEFAULT_RESUME_PATH
from src.email_template import generate_subject, generate_email_body

sample_leads = [
    {
        "recruiter_name": "Arjun Sharma",
        "job_role": "Full Stack Developer Intern",
        "email": "arjun@techscale.io",
        "post_snippet": "We are looking for a proactive Full Stack Intern skilled in React and Node.js. Drop your resume!",
    },
    {
        "recruiter_name": "Sarah Chen",
        "job_role": "GenAI / LLM Engineer Intern",
        "email": "sarah@deepventures.ai",
        "post_snippet": "Hiring an AI intern passionate about autonomous agents, LangGraph, and Groq/Llama. Send resume to sarah@deepventures.ai",
    },
    {
        "recruiter_name": "Founder",
        "job_role": "Software Engineering Intern",
        "email": "hiring@earlystage.co",
        "post_snippet": "Seed funded AI startup hiring software developer interns. Remote. Stipend provided.",
    },
    {
        "recruiter_name": "Priya Nair",
        "job_role": "Python Backend Intern",
        "email": "priya.nair@hypergrowth.tech",
        "post_snippet": "Urgent opening for Python/FastAPI backend intern. Immediate joiners preferred.",
    },
]

print("=" * 70)
print(f"📄 RESUME ATTACHMENT: {DEFAULT_RESUME_PATH.name} (Found: {DEFAULT_RESUME_PATH.exists()})")
print(f"🎓 CANDIDATE PROFILE: {CANDIDATE.get('full_name')} | CGPA: {CANDIDATE.get('cgpa')}")
print("=" * 70)

for i, lead in enumerate(sample_leads, 1):
    subject = generate_subject(lead, CANDIDATE)
    body = generate_email_body(lead, CANDIDATE)
    print(f"\n[{i}] TO: {lead['email']} | ROLE: {lead['job_role']} | RECRUITER: {lead['recruiter_name']}")
    print("-" * 70)
    print(f"SUBJECT: {subject}")
    print("-" * 70)
    print(body)
    print("=" * 70)
