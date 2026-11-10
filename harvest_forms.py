#!/usr/bin/env python3
"""
harvest_forms.py - Dedicated Harvester for Google Forms, Application Links & ATS Portals
Searches LinkedIn specifically for posts with external registration links, Google Forms,
and application portals, parsing clean company overviews, roles, and requirements.

Usage:
  python harvest_forms.py                 # Scrapes curated form & apply link keywords
  python harvest_forms.py --limit-per-kw 10 # Scrape up to 10 opportunities per keyword
"""

import sys
import io
import time
import logging
import argparse
from pathlib import Path
from typing import List

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

from config import (
    APPLICATION_LINKS_CSV,
    APPLICATION_LINKS_MD,
    COMMENTED_LOG_JSON,
)
from src.linkedin_scraper import (
    create_driver,
    check_login_status,
    build_search_url,
    scroll_page,
    click_see_more_buttons,
    _get_post_elements,
    _fallback_text_blocks,
    _random_delay,
)
from src.email_extractor import extract_apply_links, parse_internship_details
from src.post_filter import evaluate_post
from src.csv_manager import save_application_link, load_saved_apply_links, sync_application_links_markdown

FORM_HARVEST_KEYWORDS = [
    "forms gle intern developer",
    "apply link software intern",
    "forms gle full stack intern",
    "apply link developer intern",
    "internship google form developer",
    "forms gle python intern",
    "apply link full stack intern",
    "forms gle ai intern",
    "registration link tech intern",
    "apply link frontend intern",
]


def harvest_keyword(driver, keyword: str, time_filter: str = "past-week") -> int:
    """Scrapes a single keyword specifically looking for forms and apply links."""
    url = build_search_url(keyword, time_filter=time_filter)
    logger.info(f"🔍 Searching: '{keyword}' ({time_filter})")
    try:
        driver.get(url)
    except Exception:
        pass

    _random_delay(2.0, 3.5)
    scroll_page(driver, attempts=12)
    click_see_more_buttons(driver, limit=25)
    time.sleep(1.0)

    post_elements = _get_post_elements(driver)
    use_fallback = len(post_elements) == 0

    if use_fallback:
        items = _fallback_text_blocks(driver)
        logger.info(f"Fallback extracted {len(items)} text blocks.")
    else:
        items = post_elements
        logger.info(f"Found {len(items)} raw post blocks on page.")

    saved_count = 0
    saved_links = load_saved_apply_links(APPLICATION_LINKS_CSV)

    for idx, item in enumerate(items):
        try:
            if use_fallback:
                post_text = item
                element = None
                recruiter_name = "Hiring Team"
                post_url = ""
            else:
                body_els = item.find_elements("xpath", ".//div[contains(@class, 'update-components-text')] | .//span[contains(@class, 'break-words')]")
                post_text = body_els[0].text if body_els and len(body_els[0].text.strip()) > 30 else item.text
                element = item

                # Extract recruiter name
                recruiter_name = ""
                name_links = item.find_elements("xpath", ".//a[contains(@href, '/in/')]")
                for nl in name_links:
                    txt = nl.text.split("\n")[0].strip()
                    if txt and len(txt.split()) <= 4:
                        recruiter_name = txt
                        break

                # Extract post URL
                post_url = ""
                links = item.find_elements("xpath", ".//a[contains(@href, '/feed/update/') or contains(@href, '/posts/')]")
                if links:
                    for lk in links:
                        href = lk.get_attribute("href") or ""
                        if "/feed/update/" in href or "/posts/" in href:
                            post_url = href.split("?")[0]
                            break

            apply_links = extract_apply_links(post_text, element)
            if not apply_links:
                continue

            # Evaluate post relevance
            is_valid, score, reason = evaluate_post(post_text, has_link=True)
            if not is_valid:
                continue

            parsed_info = parse_internship_details(
                post_text=post_text,
                raw_author=recruiter_name,
                default_role="Software Engineer Intern",
            )

            for al in apply_links:
                if al in saved_links:
                    continue
                saved = save_application_link(
                    job_role=parsed_info["job_role"],
                    company_name=parsed_info["company_name"],
                    recruiter_name=parsed_info["recruiter_name"],
                    apply_link=al,
                    post_url=post_url,
                    overview=parsed_info["overview"],
                    requirements=parsed_info["requirements"],
                    csv_path=APPLICATION_LINKS_CSV,
                    md_path=APPLICATION_LINKS_MD,
                )
                if saved:
                    saved_links.add(al)
                    saved_count += 1
                    logger.info(f"✨ NEW FORM SAVED: {al} | Company: {parsed_info['company_name']} | Role: {parsed_info['job_role']}")

        except Exception:
            continue

    return saved_count


def main():
    parser = argparse.ArgumentParser(description="Harvest Google Forms & Application Links from LinkedIn")
    parser.add_argument("--keywords", nargs="+", help="Specific keywords to harvest")
    parser.add_argument("--time-filter", choices=["past-24h", "past-week", "past-month"], default="past-week", help="Time filter")
    args = parser.parse_args()

    keywords = args.keywords if args.keywords else FORM_HARVEST_KEYWORDS

    print("\n" + "=" * 65)
    print("📋 JAINAM JAIN - GOOGLE FORMS & APPLICATION LINK HARVESTER")
    print("=" * 65)
    print(f" Target Keywords  : {len(keywords)} high-intent queries")
    print(f" Time Filter      : {args.time_filter}")
    print(f" Output CSV       : {APPLICATION_LINKS_CSV}")
    print(f" Live Dashboard   : http://localhost:5050")
    print("=" * 65 + "\n")

    driver = create_driver()
    total_new = 0

    try:
        if not check_login_status(driver):
            logger.warning("LinkedIn session not logged in! Please log in...")
            input("Press Enter once logged in...")

        for idx, kw in enumerate(keywords, 1):
            logger.info(f"--- [{idx}/{len(keywords)}] Harvesting: {kw} ---")
            new_found = harvest_keyword(driver, kw, time_filter=args.time_filter)
            total_new += new_found
            logger.info(f"Found {new_found} new forms for '{kw}'. Total so far: {total_new}")
            _random_delay(2.0, 3.5)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    sync_application_links_markdown(APPLICATION_LINKS_CSV, APPLICATION_LINKS_MD)
    all_saved = len(load_saved_apply_links(APPLICATION_LINKS_CSV))

    print("\n" + "=" * 65)
    print(f"🎉 HARVEST COMPLETE! Found {total_new} new application links.")
    print(f"📊 Total Saved Opportunities Now: {all_saved}")
    print(f"👉 Review them live at: http://localhost:5050")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
