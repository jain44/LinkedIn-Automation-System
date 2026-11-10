# 🚀 Jainam Jain — Tech Internship LinkedIn Automation

Dedicated, automated cold email outreach system tailored specifically for **Jainam Jain**'s tech internship search (Full Stack, GenAI, Python, Web Development).

---

## 🌟 Key Features

- **No C2C / No Staffing Agency Jargon**: Clean, direct intern search queries specifically matching tech companies, AI startups, and engineering founders.
- **Dedicated Gmail Account**: Authenticated directly with `jainamjain1116@gmail.com` using Gmail App Password via secure TLS SMTP.
- **Smart LinkedIn Scraper**:
  - Searches past 24 hours and past week for fresh LinkedIn content posts.
  - Automatically clicks "see more" to uncover hidden text.
  - Extracts plain and obfuscated email addresses (`user [at] domain.com`, etc.).
  - Filters out course promotions, paid training schemes, and spam.
- **Automatic Resume Attachment**: Attaches `Jainam_Jain_1Page.pdf` to every email.
- **Personalized High-Converting Templates**:
  - Highlights B.Tech IT at TCET Mumbai (9.92 CGPA).
  - Highlights live projects (JusticeAI, Kavach, GrowthOS).
  - Includes links to GitHub (`github.com/jain44`) and LinkedIn.
- **Zero Duplicate Guarantee**: Automatically tracks all discovered leads in `data/leads.csv` and contacted recruiters in `data/sent_log.csv`.

---

## 📁 Directory Structure

```
Jainam_Internship_Automation/
├── .env                     # Your Gmail App Password & settings
├── candidate_data.json      # Jainam's education, skills, projects, links
├── config.py                # System settings and defaults
├── main.py                  # Primary runner script
├── preview_emails.py        # Instant email preview script
├── test_connection.py       # Gmail SMTP & resume verification script
├── requirements.txt         # Dependencies
├── resumes/
│   ├── Jainam_Jain_1Page.pdf
│   └── Jainam_Jain_2Page.pdf
├── data/
│   ├── leads.csv            # Extracted recruiter leads
│   └── sent_log.csv         # Sent history (deduplication)
└── src/
    ├── linkedin_scraper.py  # Selenium LinkedIn post scraper
    ├── email_extractor.py   # Regex & obfuscation email parser
    ├── email_template.py    # Cold email templates & subject generator
    ├── gmail_sender.py      # SMTP sender with attachment
    ├── csv_manager.py       # CSV storage & deduplication
    └── post_filter.py       # Tech internship relevance scorer
```

---

## ⚡ Quick Start

### 1. Launch Live Analytics Dashboard
Open the real-time command center:
```powershell
python start_dashboard.py
# or double click start_dashboard.bat
# or double click dashboard.html directly in browser
```
Visit: **`http://localhost:5050`**

### 2. Test Gmail Connection
Verify your Gmail credentials and resume file:
```powershell
python test_connection.py
```

### 2. Preview Emails
See sample email subjects and bodies generated with your credentials and resume:
```powershell
python preview_emails.py
```

### 3. Dry-Run Mode (Safe Simulation — No Emails Sent)
Scrapes LinkedIn, extracts leads, and previews the emails without sending:
```powershell
python main.py
```

### 4. Live Send Mode (Sends Real Emails)
When you're ready to send real emails to recruiters:
```powershell
python main.py --send
```

---

## 🎯 Advanced Commands

### Search Specific Keywords:
```powershell
python main.py --keywords "ai intern" "full stack intern" "software engineer intern"
```

### Search Past Week Posts:
```powershell
python main.py --time-filter past-week
```

### Process Existing Leads Without Scraping Again:
```powershell
python main.py --skip-scrape --send
```

### Limit Max Emails Per Session:
```powershell
python main.py --send --limit 20
```
