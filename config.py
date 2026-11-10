"""
config.py - Configuration settings for Jainam's Internship Outreach Automation
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RESUMES_DIR = PROJECT_ROOT / "resumes"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESUMES_DIR.mkdir(parents=True, exist_ok=True)

# Load .env file
load_dotenv(PROJECT_ROOT / ".env")

# Candidate Profile
CANDIDATE_DATA_PATH = PROJECT_ROOT / "candidate_data.json"
def load_candidate_data() -> dict:
    if CANDIDATE_DATA_PATH.exists():
        with open(CANDIDATE_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

CANDIDATE = load_candidate_data()

# Sender credentials
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "jainamjain1116@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Jainam Jain")

# Operational modes
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
HEADLESS_MODE = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")

# Resume configuration
DEFAULT_RESUME_FILENAME = os.getenv("DEFAULT_RESUME_FILENAME", "Jainam_Jain_1Page.pdf")
DEFAULT_RESUME_PATH = RESUMES_DIR / DEFAULT_RESUME_FILENAME
RESUME_DRIVE_LINK = os.getenv("RESUME_DRIVE_LINK", CANDIDATE.get("resume_drive_link", "https://drive.google.com/file/d/1K_q0i7hr_CFEbV4ec5Y3pS_ts-fLi5zs/view?usp=drivesdk"))

# Chrome Profile for Selenium
CHROME_PROFILE_DIR = os.getenv(
    "CHROME_PROFILE_DIR",
    r"C:\Users\jainam\Downloads\Siddhu_LinkedIn_Automation_20260708_1931\Siddhu_LinkedIn_Automation_20260708_1931\chrome-profile"
)

# AI API Key (Groq Llama 3 for intelligent matching)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Search Keywords for Tech Internships (Broad, realistic queries)
DEFAULT_SEARCH_KEYWORDS = CANDIDATE.get("search_keywords", [
    "software engineer intern",
    "software developer intern",
    "full stack intern",
    "web development intern",
    "genai intern",
    "ai intern",
    "python intern",
    "react intern",
    "frontend intern",
    "backend intern",
    "hiring intern developer",
    "looking for intern full stack",
    "internship send your resume"
])

# Delays and Limits
MIN_ACTION_DELAY = 1.2
MAX_ACTION_DELAY = 2.5
EMAIL_SEND_DELAY_MIN = 15.0
EMAIL_SEND_DELAY_MAX = 35.0
MAX_EMAILS_PER_SESSION = 80
MAX_SCROLL_ATTEMPTS = 20
MAX_POSTS_PER_KEYWORD = 60

# Storage Paths
LEADS_CSV = DATA_DIR / "leads.csv"
SENT_LOG_CSV = DATA_DIR / "sent_log.csv"
COMMENTED_LOG_JSON = DATA_DIR / "commented_posts.json"
APPLICATION_LINKS_CSV = DATA_DIR / "application_links.csv"
APPLICATION_LINKS_MD = DATA_DIR / "application_links.md"
REMINDER_LOG_CSV = DATA_DIR / "reminder_log.csv"

# Blacklisted Entities and Domains (Strict exclusion for unpaid mass recruiters like The GAO Group)
BLACKLISTED_DOMAINS = [
    "thegaogroup.com",
    "gaotek.com",
    "gaorfid.com",
    "gaostaff.com",
    "gaoresearch.com",
    "gao-tek.com",
    "thegaogroup.org",
    "thegaogroup.net",
    "gaogroup.com",
    "gao-group.com",
    "gaotek.in",
    "gaorfid.in",
]

BLACKLISTED_KEYWORDS = [
    "gao group",
    "the gao group",
    "gao tech",
    "gaotech",
    "gao tek",
    "gaotek",
    "gao rfid",
    "gao research",
    "gao staff",
    "gao company",
    "thegaogroup",
    "thegao group",
    "gao virtual internship",
    "gaotek inc",
    "gao tech inc",
    "gao group of companies",
]

# Location Filtering: Onsite ONLY in Mumbai, otherwise strictly Remote
ALLOWED_MUMBAI_LOCATIONS = [
    "mumbai", "bombay", "navi mumbai", "thane", "andheri", "bandra", "bkc",
    "powai", "goregaon", "borivali", "malad", "kandivali", "dadar", "worli",
    "kurla", "lower parel", "vashi", "airoli", "ghansoli", "mahape", "kalyan",
    "dombivli", "mira road", "bhayandar", "churchgate", "nariman point",
    "chembur", "ghatkopar", "mulund", "santacruz", "vile parle", "jogeshwari",
    "colaba", "mahim", "sion", "vidyavihar", "kanjurmarg", "bhandup", "dahisar",
    "khar", "juhu", "panvel", "belapur", "nerul", "sanpada", "turbhe", "kopar khairane"
]

REMOTE_KEYWORDS = [
    "remote", "work from home", "wfh", "virtual", "work-from-home",
    "work from anywhere", "telecommute", "online internship", "home-based",
    "pan-india remote", "fully remote", "100% remote", "remote (india)",
    "remote(india)", "remote - india", "remote-first", "remotely"
]

NON_MUMBAI_LOCATIONS = [
    # Top Tech Hubs & Cities in India (Onsite outside Mumbai is strictly excluded)
    "bengaluru", "bangalore", "hyderabad", "pune", "delhi", "new delhi", "ncr",
    "noida", "greater noida", "gurgaon", "gurugram", "faridabad", "ghaziabad",
    "chennai", "madras", "kolkata", "calcutta", "ahmedabad", "jaipur", "chandigarh",
    "mohali", "panchkula", "indore", "kochi", "cochin", "coimbatore", "trivandrum",
    "thiruvananthapuram", "kerala", "bhopal", "nagpur", "lucknow", "kanpur", "surat",
    "vadodara", "baroda", "bhubaneswar", "visakhapatnam", "vizag", "patna", "dehradun",
    "rishikesh", "uttarakhand", "mysore", "mysuru", "mangalore", "mangaluru", "goa",
    "punjab", "haryana", "rajasthan", "gujarat", "uttar pradesh", "karnataka",
    "tamil nadu", "andhra pradesh", "telangana", "odisha", "bihar", "assam", "guwahati",
    "madhya pradesh", "jamshedpur", "ranchi", "jharkhand", "chattisgarh", "raipur",

    # International Cities & Countries (Onsite outside India/Mumbai is strictly excluded)
    "lahore", "karachi", "islamabad", "rawalpindi", "faisalabad", "peshawar", "pakistan",
    "dhaka", "bangladesh", "colombo", "sri lanka", "nepal", "kathmandu",
    "jakarta", "indonesia", "dubai", "abu dhabi", "uae", "singapore", "malaysia",
    "kuala lumpur", "london", "uk", "united kingdom", "manchester", "birmingham",
    "toronto", "canada", "markham", "vancouver", "montreal", "ottawa", "calgary",
    "berlin", "germany", "munich", "frankfurt", "amsterdam", "netherlands",
    "sydney", "melbourne", "australia", "brisbane", "perth",
    "paris", "france", "dublin", "ireland", "tokyo", "japan", "hong kong",
    "nigeria", "lagos", "abuja", "kenya", "nairobi", "egypt", "cairo", "south africa",
]



