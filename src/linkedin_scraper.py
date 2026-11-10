"""
linkedin_scraper.py - Dedicated LinkedIn Scraper for Tech Internship Postings
Scrapes live LinkedIn content posts for software engineering, full stack, and AI internships.
Extracts recruiter/founder email addresses, job details, and post links.
"""

import os
import time
import random
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
)

from config import (
    MIN_ACTION_DELAY,
    MAX_ACTION_DELAY,
    MAX_POSTS_PER_KEYWORD,
    MAX_SCROLL_ATTEMPTS,
    CHROME_PROFILE_DIR,
    HEADLESS_MODE,
)
from src.email_extractor import extract_emails, extract_apply_links
from src.post_filter import (
    evaluate_post,
    SELF_ANNOUNCEMENT_TERMS,
    SPAM_TERMS,
    JOB_SEEKER_TERMS,
    STORY_AND_RETROSPECTIVE_TERMS,
    STORY_REGEX_PATTERNS,
)

logger = logging.getLogger(__name__)


# Phrases that indicate the poster wants you to comment/DM to get the link/form
COMMENT_TRIGGER_PHRASES = [
    "comment below",
    "comment interested",
    "comment to get",
    "comment 'interested'",
    'comment "interested"',
    "drop a comment",
    "comment for the link",
    "comment for link",
    "comment to receive",
    "comment below to get",
    "comment your email",
    "comment email",
    "comment resume",
    "comment your resume",
    "comment here",
    "type interested",
    "type 'interested'",
    'type "interested"',
    "comment yes",
    "comment 'yes'",
    "comment to apply",
    "dm me",
    "dm for link",
    "dm for form",
    "dm to apply",
    "drop a dm",
    "drop your email",
    "drop your resume",
    "leave a comment",
]

# The comment we post when triggered
AUTO_COMMENT_TEXT = "Interested! 🙌 Please share the application link / form. Thank you!"



def _random_delay(min_sec: float = MIN_ACTION_DELAY, max_sec: float = MAX_ACTION_DELAY) -> None:
    time.sleep(random.uniform(min_sec, max_sec))


def _clean_chrome_profile_locks() -> None:
    """Removes stale SingletonLock files from Chrome profile directory."""
    if not CHROME_PROFILE_DIR:
        return
    p = Path(CHROME_PROFILE_DIR)
    if not p.exists():
        return
    for lf in [p / "SingletonLock", p / "SingletonCookie", p / "SingletonSocket"]:
        try:
            if lf.exists():
                lf.unlink()
                logger.info(f"Removed stale Chrome lock: {lf.name}")
        except Exception:
            pass


def create_driver() -> webdriver.Chrome:
    """Creates a configured Chrome WebDriver session with profile persistence."""
    _clean_chrome_profile_locks()

    chrome_options = Options()
    if HEADLESS_MODE:
        chrome_options.add_argument("--headless=new")

    if CHROME_PROFILE_DIR and os.path.exists(CHROME_PROFILE_DIR):
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
        chrome_options.add_argument("--profile-directory=Default")

    chrome_options.page_load_strategy = "eager"
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--window-size=1920,1080")

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        logger.warning(f"Initial Chrome start error: {e}. Attempting cleanup and retry...")
        try:
            os.system("taskkill /f /im chrome.exe /im chromedriver.exe >nul 2>&1")
            time.sleep(2)
            _clean_chrome_profile_locks()
        except Exception:
            pass
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.implicitly_wait(0.5)
    driver.set_page_load_timeout(45)
    return driver


def check_login_status(driver: webdriver.Chrome) -> bool:
    """Verifies if LinkedIn is logged in."""
    try:
        driver.get("https://www.linkedin.com/feed/")
        _random_delay(2.0, 3.5)
        current_url = driver.current_url.lower()
        if "login" in current_url or "checkpoint" in current_url or "authwall" in current_url:
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
        return False


def build_search_url(keyword: str, time_filter: str = "past-week") -> str:
    """
    Constructs LinkedIn Content Search URL for the given keyword.
    Encodes the clean keyword directly without over-constraining the query engine.
    time_filter: 'past-24h', 'past-week', or 'past-month'
    """
    clean_query = keyword.strip()
    encoded = quote_plus(clean_query)
    if time_filter == "past-24h":
        date_val = "%22past-24h%22"
    elif time_filter == "past-month":
        date_val = "%22past-month%22"
    else:
        date_val = "%22past-week%22"
    return (
        f"https://www.linkedin.com/search/results/content/"
        f"?keywords={encoded}"
        f"&datePosted={date_val}"
        f"&origin=FACETED_SEARCH"
        f"&sortBy=%22date_posted%22"
    )


def click_see_more_buttons(driver: webdriver.Chrome, limit: int = 60) -> None:
    """
    Clicks all '…more', '...more', 'see more', and 'read more' buttons across the page
    to expand truncated posts so that emails, requirements, and links at the end are fully visible.
    Uses multi-pass synthetic mouse events for modern React-based LinkedIn feed components.
    """
    try:
        js_clicked = driver.execute_script("""
            function triggerFullClick(el) {
                try { el.scrollIntoView({ behavior: 'instant', block: 'nearest' }); } catch(e) {}
                const evts = ['mouseover', 'mousedown', 'mouseup', 'click'];
                for (const evt of evts) {
                    try {
                        el.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                    } catch(e) {}
                }
                if (typeof el.click === 'function') {
                    try { el.click(); } catch(e) {}
                }
            }

            let total = 0;
            for (let pass = 0; pass < 2; pass++) {
                const candidates = Array.from(document.querySelectorAll(
                    'button.feed-shared-inline-show-more-text__see-more-less-toggle, ' +
                    'span.feed-shared-inline-show-more-text__see-more-less-toggle, ' +
                    'button[class*="see-more"], span[class*="see-more"], ' +
                    'button[class*="show-more"], span[class*="show-more"], ' +
                    'button, span[role="button"], a'
                ));
                let passClicked = 0;
                for (const el of candidates) {
                    const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                    const cls = (el.className || '').toLowerCase();

                    const isMore = (
                        text === '…more' || text === '...more' || text === 'more' ||
                        text.endsWith('…more') || text.endsWith('...more') ||
                        text.includes('see more') || text.includes('read more') ||
                        aria.includes('see more') || aria.includes('read more') ||
                        cls.includes('see-more-less-toggle')
                    );
                    const isExcluded = (
                        text.includes('show more results') || text.includes('see more results') ||
                        text.includes('load more') || text.includes('comment') ||
                        text.includes('notification') || text.includes('messaging')
                    );

                    if (isMore && !isExcluded) {
                        triggerFullClick(el);
                        passClicked++;
                        total++;
                    }
                }
                if (passClicked === 0) break;
            }
            return total;
        """)
        if js_clicked and js_clicked > 0:
            logger.debug(f"Expanded {js_clicked} 'see more' toggles via JavaScript.")
    except Exception as e:
        logger.debug(f"JS see more click error: {e}")

    # Python fallback selectors (runs in addition to JS to catch any missed toggles)
    xpaths = [
        "//button[contains(@class, 'feed-shared-inline-show-more-text__see-more-less-toggle')]",
        "//span[contains(@class, 'feed-shared-inline-show-more-text__see-more-less-toggle')]",
        "//button[contains(@aria-label, 'see more') or contains(., '\u2026more') or contains(., '...more') or contains(., '\u2026see more') or contains(., '...see more')]",
        "//button[normalize-space()='see more' or normalize-space()='See more' or normalize-space()='more']",
        "//button[contains(@class, 'show-more-less-html__button')]",
        "//span[contains(@class, 'see-more')]/button",
    ]
    clicked = 0
    for xpath in xpaths:
        try:
            buttons = driver.find_elements(By.XPATH, xpath)
            for btn in buttons[:limit]:
                try:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        clicked += 1
                        time.sleep(0.02)
                except Exception:
                    continue
        except Exception:
            continue
    if clicked > 0:
        logger.debug(f"Clicked {clicked} fallback 'see more' toggles.")


def scroll_page(driver: webdriver.Chrome, attempts: int = 20) -> None:
    """Incrementally scrolls down and triggers 'Show more results' to load 30-60 posts."""
    last_height = driver.execute_script("return document.body.scrollHeight;")
    no_change_count = 0

    for i in range(attempts):
        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(0.5)

        # Click 'Show more results' if button is present
        try:
            more_btns = driver.find_elements(By.XPATH,
                "//button[contains(@class, 'infinite-scroller__show-more-button') "
                "or contains(., 'Show more results') or contains(., 'See more results') "
                "or contains(@aria-label, 'Show more results')]"
            )
            for mb in more_btns:
                if mb.is_displayed():
                    driver.execute_script("arguments[0].click();", mb)
                    time.sleep(1.5)
                    break
        except Exception:
            pass

        # JS click on any load-more button
        try:
            driver.execute_script("""
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    const t = (b.innerText || '').toLowerCase();
                    if ((t.includes('show more') || t.includes('see more results') || t.includes('load more'))
                        && !t.includes('comment') && !t.includes('notification')) {
                        b.click(); break;
                    }
                }
            """)
        except Exception:
            pass

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.0)

        new_height = driver.execute_script("return document.body.scrollHeight;")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 4:
                break
        else:
            no_change_count = 0
        last_height = new_height

    # Final: log how many post elements are visible after scrolling
    try:
        post_count = driver.execute_script("""
            const selectors = [
                'li.reusable-search__result-container',
                'div[data-finite-scroll-hotkey-item]',
                'div[class*="occludable-update"]',
                'div[class*="feed-shared-update-v2"]',
                'div[class*="entity-result"]'
            ];
            let max = 0;
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > max) max = els.length;
            }
            return max;
        """)
        if post_count:
            import logging as _log
            _log.getLogger(__name__).debug(f"Post elements visible after scroll: {post_count}")
    except Exception:
        pass


def _get_post_elements(driver: webdriver.Chrome) -> list:
    """
    Tries multiple XPath selectors and returns the set that captures
    the MAXIMUM number of valid LinkedIn post blocks on the page.
    Uses JavaScript DOM inspection as primary fallback for resilience.
    """
    selectors = [
        # 2026 LinkedIn Search Results page (most reliable)
        "//li[contains(@class, 'reusable-search__result-container')]",
        "//div[contains(@class, 'search-results__list')]//li",
        # SDUI update cards
        "//div[contains(@componentkey, 'update-card')]",
        # Role=listitem in various containers
        "//div[@data-testid='lazy-column']//div[@role='listitem']",
        "//main//div[@role='listitem']",
        "//div[@role='listitem']",
        # artdeco-card (desktop LinkedIn)
        "//div[contains(@class, 'artdeco-card') and @data-urn]",
        "//div[@data-urn and contains(@class, 'feed-shared-update')]",
        "//div[contains(@class, 'feed-shared-update-v2')]",
        # Search result items by class fragments
        "//div[contains(@class, 'entity-result')]",
        "//div[contains(@class, 'search-entity')]",
        # Comment button ancestor trick
        "//button[contains(@aria-label, 'Comment')]/ancestor::div[@role='listitem']",
        "//button[contains(@aria-label, 'React')]/ancestor::div[@role='listitem']",
        # Any card with substantial text content
        "//div[contains(@class, 'occludable-update')]",
        "//div[contains(@class, 'update-components')]//ancestor::div[contains(@class, 'artdeco-card')]",
    ]
    best_elements = []
    try:
        driver.implicitly_wait(0.2)
        for sel in selectors:
            try:
                found = driver.find_elements(By.XPATH, sel)
                valid = [f for f in found if len(f.text.strip()) > 30]
                if len(valid) > len(best_elements):
                    best_elements = valid
                    if len(best_elements) >= 15:  # Good enough, stop searching
                        break
            except Exception:
                continue
    finally:
        driver.implicitly_wait(1.5)

    # JavaScript fallback: collect all post text blocks via DOM traversal
    if len(best_elements) < 5:
        try:
            js_blocks = driver.execute_script("""
                const results = [];
                // Try search result containers
                const searchItems = document.querySelectorAll(
                    'li.reusable-search__result-container, div[data-finite-scroll-hotkey-item], ' +
                    'div.search-results__list li, div[data-chameleon-result-urn], ' +
                    'li[data-occludable-entity-urn], div.occludable-update, ' +
                    'div[class*="search-result"], div[class*="entity-result"]'
                );
                if (searchItems.length > 3) {
                    for (const el of searchItems) {
                        if ((el.innerText || '').trim().length > 50) results.push(el);
                    }
                    return results.length;
                }
                return 0;
            """)
            if js_blocks and js_blocks > len(best_elements):
                # Re-query with the selector that worked
                for sel in [
                    "//li[contains(@class, 'reusable-search__result-container')]",
                    "//*[@data-finite-scroll-hotkey-item]",
                    "//*[@data-occludable-entity-urn]",
                    "//*[@data-chameleon-result-urn]",
                ]:
                    try:
                        found = driver.find_elements(By.XPATH, sel)
                        valid = [f for f in found if len(f.text.strip()) > 30]
                        if len(valid) > len(best_elements):
                            best_elements = valid
                    except Exception:
                        continue
        except Exception:
            pass

    return best_elements


def _fallback_text_blocks(driver: webdriver.Chrome) -> list:
    """
    Fallback: splits full page text into chunks by double newline.
    Used when structured selectors find 0 elements.
    Returns list of fake 'elements' as plain strings wrapped in a dict.
    """
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        chunks = [c.strip() for c in re.split(r"\n{2,}", body_text) if len(c.strip()) > 80]
        return chunks
    except Exception:
        return []


def should_comment_on_post(text: str) -> bool:
    """
    Checks if a post is from a genuine recruiter explicitly asking users to comment
    to receive a link, form, or details. Strictly filters out job-seekers and announcements.
    """
    text_low = text.lower()

    # 1. Do NOT comment on job-seekers looking for an internship (e.g. Sahil Akhade)
    if any(phrase in text_low for phrase in JOB_SEEKER_TERMS):
        return False

    # 2. Do NOT comment on self-announcements (students celebrating getting an offer/joining)
    if any(phrase in text_low for phrase in SELF_ANNOUNCEMENT_TERMS):
        return False

    # 3. Do NOT comment on spam / fee-based bootcamps
    if any(spam in text_low for spam in SPAM_TERMS):
        return False

    # 4. Do NOT comment on personal stories, career retrospectives, or advice essays
    if any(phrase in text_low for phrase in STORY_AND_RETROSPECTIVE_TERMS):
        return False
    if any(pat.search(text) for pat in STORY_REGEX_PATTERNS):
        return False

    # 5. Must have an internship hiring context from a company/recruiter
    hiring_context = any(k in text_low for k in [
        "we are hiring", "were hiring", "we're hiring", "hiring", "opening",
        "urgent hiring", "urgently hiring", "looking for interns", "looking for an intern",
        "looking for passionate", "join our team", "apply now", "send resume", "share cv",
        "drop cv", "drop resume", "internship", "interns", "freshers are welcome"
    ])
    if not hiring_context:
        return False


    # 5. Regex-based pattern matching for comment calls-to-action
    # Matches variations with hashtags (e.g. #Interested), quotes, or words in between
    comment_patterns = [
        # e.g. "comment #Interested", "comment 'interested'", "comment interested", "comment link"
        r"\bcomment\s+[#@'\"\`]?\s*(?:interested|yes|link|apply|info|details|form|email|resume|cv)\b",
        # e.g. "comment #Interested below", "comment below", "comment your email below"
        r"\bcomment\s+(?:\S+\s+){0,4}below\b",
        # e.g. "comment to receive the application link", "comment to get"
        r"\bcomment\s+(?:\S+\s+){0,4}to\s+(?:receive|get|apply|access|obtain)\b",
        # e.g. "drop your email below", "drop your resume in comments"
        r"\bdrop\s+(?:your\s+)?(?:email|resume|cv)\b",
        # e.g. "type #interested", "type yes"
        r"\btype\s+[#@'\"\`]?\s*(?:interested|yes)\b",
        # e.g. "leave a comment below"
        r"\bleave\s+a\s+comment\b",
        # e.g. "comment and I will send / DM"
        r"\bcomment\s+(?:and\s+)?(?:i\s+will|ill|i'll)\s+(?:send|dm|share)\b",
    ]

    return any(re.search(pat, text_low) for pat in comment_patterns)


def post_comment_on_post(driver: webdriver.Chrome, post_element, post_text: str) -> bool:
    """
    Locates comment button in the post, clicks it to open ProseMirror/Tiptap box,
    types AUTO_COMMENT_TEXT, and submits.
    Returns True if successfully posted.
    """
    if not should_comment_on_post(post_text):
        return False

    try:
        # Find the comment button inside this post element
        comment_btn = None
        comment_xpaths = [
            ".//button[contains(@aria-label, 'Comment') or contains(@aria-label, 'comment')]",
            ".//button[.//span[normalize-space()='Comment' or normalize-space()='comment']]",
            ".//button[contains(., 'Comment')]",
            ".//span[text()='Comment']/ancestor::button",
        ]
        for xp in comment_xpaths:
            try:
                btns = post_element.find_elements(By.XPATH, xp)
                if btns and btns[0].is_displayed():
                    comment_btn = btns[0]
                    break
            except Exception:
                continue

        if not comment_btn:
            logger.debug("Comment button not found on post element.")
            return False

        # Scroll to comment button and click
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", comment_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", comment_btn)
        time.sleep(1.5)

        # In-DOM Check: After opening the comments thread, verify if Jainam already commented
        try:
            my_comments = post_element.find_elements(
                By.XPATH,
                ".//*[contains(@class, 'comment') or contains(@class, 'feed-shared-comments')]//*[contains(text(), 'Jainam') or contains(text(), 'Interested! 🙌') or contains(text(), '#Interested')]"
            )
            if my_comments:
                logger.info(f"⚠️ Existing comment by Jainam already found on post. Skipping duplicate comment.")
                return False
        except Exception:
            pass

        # Find modern LinkedIn ProseMirror / tiptap comment box
        comment_box = None
        box_selectors = [
            "//div[contains(@class, 'tiptap') or contains(@class, 'ProseMirror')]",
            ".//div[contains(@class, 'tiptap') or contains(@class, 'ProseMirror')]",
            "//div[@role='textbox']",
            "//div[@contenteditable='true']",
        ]
        for sel in box_selectors:
            try:
                boxes = driver.find_elements(By.XPATH, sel)
                for b in reversed(boxes):
                    if b.is_displayed():
                        comment_box = b
                        break
                if comment_box:
                    break
            except Exception:
                continue

        if not comment_box:
            logger.warning("Comment text box (ProseMirror/Tiptap) not found.")
            return False

        # Focus, click, and type comment
        driver.execute_script("arguments[0].focus();", comment_box)
        time.sleep(0.3)
        comment_box.click()
        time.sleep(0.3)

        comment_to_post = AUTO_COMMENT_TEXT
        if "#interested" in post_text.lower():
            comment_to_post = "Interested! 🙌 Please share the application link / form. Thank you! #Interested"

        comment_box.send_keys(comment_to_post)
        time.sleep(1.0)

        # Submit comment
        submitted = False
        submit_xpaths = [
            "//button[(normalize-space()='Comment' or normalize-space()='Post') and not(@disabled)]",
            ".//button[(normalize-space()='Comment' or normalize-space()='Post') and not(@disabled)]",
            "//button[contains(@class, 'comments-comment-box__submit') and not(@disabled)]",
        ]
        for sxp in submit_xpaths:
            try:
                sbtns = driver.find_elements(By.XPATH, sxp)
                for sb in sbtns:
                    if sb.is_displayed() and sb.is_enabled():
                        driver.execute_script("arguments[0].click();", sb)
                        submitted = True
                        break
                if submitted:
                    break
            except Exception:
                continue

        if not submitted:
            from selenium.webdriver.common.keys import Keys
            comment_box.send_keys(Keys.CONTROL, Keys.RETURN)
            submitted = True

        time.sleep(1.5)
        logger.info(f"💬 Auto-commented on post: '{post_text[:60]}...'")
        return True

    except Exception as e:
        logger.warning(f"Auto-comment failed: {e}")
        return False


def extract_posts_from_page(driver: webdriver.Chrome, keyword: str, commented_keys: Optional[Set[str]] = None) -> List[Dict]:
    """
    Finds and parses all individual post elements on the search results page.
    """
    click_see_more_buttons(driver, limit=30)
    time.sleep(1.0)

    post_elements = _get_post_elements(driver)
    use_fallback = len(post_elements) == 0

    if use_fallback:
        logger.warning(f"0 structured post blocks found for '{keyword}' — using full-page text fallback.")
        text_chunks = _fallback_text_blocks(driver)
        logger.info(f"Fallback extracted {len(text_chunks)} text blocks for '{keyword}'")
    else:
        logger.info(f"Found {len(post_elements)} raw post blocks on page for '{keyword}'")

    leads: List[Dict] = []
    seen_emails = set()

    # Load persistent commented set if not passed
    if commented_keys is None:
        from config import COMMENTED_LOG_JSON
        from src.csv_manager import load_commented_keys
        commented_keys = load_commented_keys(COMMENTED_LOG_JSON)

    items = text_chunks if use_fallback else post_elements

    for idx, item in enumerate(items):
        try:
            if use_fallback:
                post_text = item
                post_key = str(hash(post_text[:120]))
                post_url = ""
                recruiter_name = ""
            else:
                # 1. Expand THIS specific post card if it contains any '...more' / 'see more' button
                try:
                    driver.execute_script("""
                        const item = arguments[0];
                        if (!item) return;
                        const toggles = item.querySelectorAll(
                            'button.feed-shared-inline-show-more-text__see-more-less-toggle, ' +
                            'span.feed-shared-inline-show-more-text__see-more-less-toggle, ' +
                            'button[class*="see-more"], span[class*="see-more"], ' +
                            'button[class*="show-more"], span[class*="show-more"], ' +
                            'button, span[role="button"], a'
                        );
                        for (const el of toggles) {
                            const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                            const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                            const cls = (el.className || '').toLowerCase();
                            const isSeeMore = (
                                txt === '…more' || txt === '...more' || txt === 'more' ||
                                txt.endsWith('…more') || txt.endsWith('...more') ||
                                txt.includes('see more') || txt.includes('read more') ||
                                aria.includes('see more') || aria.includes('read more') ||
                                cls.includes('see-more') || cls.includes('show-more') ||
                                cls.includes('inline-show-more')
                            );
                            const isExcluded = (
                                txt.includes('show more results') || txt.includes('see more results') ||
                                txt.includes('comment') || txt.includes('notification') ||
                                txt.includes('messaging')
                            );
                            if (isSeeMore && !isExcluded) {
                                try {
                                    el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true, view: window }));
                                    el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                                    el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                                    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                                    if (typeof el.click === 'function') el.click();
                                } catch(e) {}
                            }
                        }
                    """, item)
                except Exception:
                    pass

                # 2. Extract full post body text, ensuring trailing lines (emails, links) are preserved
                body_text = ""
                try:
                    body_els = item.find_elements(By.XPATH, ".//div[contains(@class, 'update-components-text')] | .//span[contains(@class, 'break-words')]")
                    if body_els and len(body_els[0].text.strip()) > 30:
                        body_text = body_els[0].text.strip()
                except Exception:
                    pass

                item_raw = ""
                try:
                    item_raw = item.text.strip()
                except Exception:
                    pass
                clean_item_text = re.split(r"\n+(?:Like\s*\n\s*Comment|Like\s*Comment|\bLike\b)", item_raw, maxsplit=1)[0].strip()

                from src.email_extractor import extract_emails
                # If clean_item_text captures an email or has more text at the end, prioritize it
                if extract_emails(clean_item_text) and not extract_emails(body_text):
                    post_text = clean_item_text
                elif len(clean_item_text) > len(body_text) and ("@" in clean_item_text or len(body_text) < 140):
                    post_text = clean_item_text
                elif body_text:
                    post_text = body_text
                else:
                    post_text = clean_item_text

                if not post_text or len(post_text) < 40:
                    continue

                from src.csv_manager import get_post_fingerprint
                fingerprint = get_post_fingerprint(post_text)

                # Extract stable URN or post key
                raw_key = item.get_attribute("componentkey") or item.get_attribute("data-urn") or ""
                post_key = raw_key or (f"fp:{fingerprint}" if fingerprint else str(hash(post_text[:120])))

                # Extract Recruiter / Author Name
                recruiter_name = ""
                try:
                    name_links = item.find_elements(By.XPATH, ".//a[contains(@href, '/in/')]")
                    for nl in name_links:
                        txt = nl.text.split("\n")[0].strip()
                        if txt and len(txt.split()) <= 5:
                            recruiter_name = txt
                            break
                    if not recruiter_name:
                        actor_names = item.find_elements(By.XPATH, ".//span[contains(@class, 'update-components-actor__name')]//span[@aria-hidden='true']")
                        if actor_names and actor_names[0].text.strip():
                            recruiter_name = actor_names[0].text.strip()
                    if not recruiter_name:
                        lines = [ln.strip() for ln in post_text.splitlines() if ln.strip()]
                        for cand in lines[:3]:
                            if cand != "Feed post" and len(cand.split()) <= 4 and not any(c.isdigit() for c in cand):
                                recruiter_name = cand
                                break
                except Exception:
                    pass

                # Extract Post Link & Stable Activity URN
                post_url = ""
                activity_id = ""
                try:
                    for attr in ["data-urn", "data-id", "data-activity-urn"]:
                        val = item.get_attribute(attr)
                        if val and ("activity:" in val or "ugcPost:" in val):
                            activity_id = val
                            m = re.search(r"((?:activity|ugcPost):\d+)", val)
                            if m:
                                post_url = f"https://www.linkedin.com/feed/update/urn:li:{m.group(1)}/"
                            break

                    if not post_url:
                        links = item.find_elements(By.XPATH, ".//a[contains(@href, '/feed/update/') or contains(@href, '/posts/') or contains(@href, 'activity:')]")
                        if links:
                            for lk in links:
                                href = lk.get_attribute("href") or ""
                                if "/feed/update/" in href or "/posts/" in href:
                                    post_url = href.split("?")[0]
                                    m = re.search(r"activity:(\d+)", href)
                                    if m:
                                        activity_id = f"urn:li:activity:{m.group(1)}"
                                    break

                    if not post_url:
                        time_links = item.find_elements(By.XPATH, ".//a[contains(@class, 'update-components-actor__sub-description-link')]")
                        if time_links:
                            href = time_links[0].get_attribute("href") or ""
                            if href:
                                post_url = href.split("?")[0]

                    if not post_url and post_text:
                        m_link = re.search(r"(https?://(?:www\.)?linkedin\.com/feed/update/[^\s]+|https?://lnkd\.in/[^\s]+)", post_text)
                        if m_link:
                            post_url = m_link.group(1).rstrip(".,;!)")
                except Exception:
                    pass

            if not post_text or len(post_text) < 40:
                continue

            # Multi-layer deduplication check across ephemeral keys, stable fingerprints, URLs, and URNs
            from src.csv_manager import get_post_fingerprint
            if not fingerprint:
                fingerprint = get_post_fingerprint(post_text)

            already_commented = (
                (post_key in commented_keys) or
                (bool(fingerprint) and fingerprint in commented_keys) or
                (bool(fingerprint) and f"fp:{fingerprint}" in commented_keys) or
                (bool(post_url) and post_url in commented_keys) or
                (bool(activity_id) and activity_id in commented_keys)
            )

            # Save relevant post to dashboard for review WITHOUT auto-commenting on LinkedIn
            if not use_fallback and not already_commented:
                if should_comment_on_post(post_text):
                    try:
                        commented_keys.add(post_key)
                        if fingerprint:
                            commented_keys.add(fingerprint)
                            commented_keys.add(f"fp:{fingerprint}")
                        if post_url:
                            commented_keys.add(post_url)
                        if activity_id:
                            commented_keys.add(activity_id)

                        from config import COMMENTED_LOG_JSON
                        from src.csv_manager import record_comment
                        record_comment(
                            post_key=post_key,
                            post_url=post_url,
                            recruiter_name=recruiter_name,
                            post_snippet=post_text[:250],
                            comment_text="Saved post for manual review & engagement",
                            commented_log_path=COMMENTED_LOG_JSON,
                            fingerprint=fingerprint,
                            activity_id=activity_id,
                        )
                        logger.info(f"📌 Saved post on dashboard for review: {recruiter_name or 'Hiring Post'}")
                    except Exception as ce:
                        logger.debug(f"Save post to dashboard failed: {ce}")

            # Extract emails and application links from both body text and full card DOM
            card_full_text = item.text if hasattr(item, "text") and item.text else ""
            combined_text = f"{post_text}\n{card_full_text}".strip()

            emails = extract_emails(post_text)
            if not emails and card_full_text:
                emails = extract_emails(card_full_text)

            # Check if there are mailto links or img alt attributes with emails
            if not emails and hasattr(item, "find_elements"):
                try:
                    for ml in item.find_elements(By.XPATH, ".//a[starts-with(@href, 'mailto:')]"):
                        href = ml.get_attribute("href") or ""
                        em = href.replace("mailto:", "").split("?")[0].strip()
                        if em:
                            emails.extend(extract_emails(em))
                    for img in item.find_elements(By.XPATH, ".//img[@alt]"):
                        alt = img.get_attribute("alt") or ""
                        if "@" in alt:
                            emails.extend(extract_emails(alt))
                except Exception:
                    pass

            from src.email_extractor import extract_phone_numbers, generate_whatsapp_link
            phones = extract_phone_numbers(combined_text)
            primary_phone = phones[0] if phones else ""

            apply_links = extract_apply_links(combined_text, item)

            # Check post quality and relevance using full context
            is_valid, score, reason = evaluate_post(
                combined_text,
                has_email=bool(emails),
                has_link=bool(apply_links),
                has_phone=bool(phones),
            )
            if not is_valid:
                logger.debug(f"Post {idx} skipped: {reason}")
                continue

            # Infer specific role from keyword / text
            from src.email_template import clean_role
            job_role = "Software Engineer Intern"
            text_low = post_text.lower()
            kw_low = keyword.lower()
            if "genai" in text_low or "llm" in text_low or "ai intern" in text_low or "genai" in kw_low or "ai intern" in kw_low:
                job_role = "GenAI / AI Developer Intern"
            elif "full stack" in text_low or "fullstack" in text_low or "full stack" in kw_low:
                job_role = "Full Stack Developer Intern"
            elif "frontend" in text_low or "react" in text_low or "react" in kw_low or "frontend" in kw_low:
                job_role = "Frontend Developer Intern"
            elif "backend" in text_low or "backend" in kw_low:
                job_role = "Backend Developer Intern"
            elif "python" in text_low or "python" in kw_low:
                job_role = "Python Developer Intern"
            elif "software" in text_low or "software" in kw_low:
                job_role = "Software Engineer Intern"
            else:
                job_role = clean_role(keyword)

            wa_link = generate_whatsapp_link(primary_phone, role=job_role) if primary_phone else ""
            snippet = re.sub(r"\s+", " ", post_text).strip()[:300]

            # 1. Extract and store external application links (Google Forms, Notion, Lever, career portals)
            if apply_links:
                from config import APPLICATION_LINKS_CSV, APPLICATION_LINKS_MD
                from src.csv_manager import save_application_link
                from src.email_extractor import parse_internship_details

                parsed_info = parse_internship_details(
                    post_text=post_text,
                    raw_author=recruiter_name,
                    default_role=job_role,
                )

                for al in apply_links:
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


            # 2. Add email leads (with phone/WhatsApp attached if present)
            from src.post_filter import is_blacklisted, is_location_allowed
            if emails:
                for em in emails:
                    b_lead, b_lead_reason = is_blacklisted(email=em, text=post_text, recruiter=recruiter_name)
                    if b_lead:
                        logger.info(f"🚫 Skipping blacklisted lead email: {em} ({b_lead_reason})")
                        continue
                    loc_ok, loc_reason = is_location_allowed(post_text)
                    if not loc_ok:
                        logger.info(f"🚫 Skipping lead email due to location: {em} ({loc_reason})")
                        continue
                    if em not in seen_emails:
                        seen_emails.add(em)
                        lead = {
                            "email": em,
                            "phone_number": primary_phone,
                            "whatsapp_link": wa_link,
                            "recruiter_name": recruiter_name,
                            "job_role": job_role,
                            "post_url": post_url,
                            "score": score,
                            "search_keyword": keyword,
                            "post_snippet": snippet,
                            "status": "pending",
                        }
                        leads.append(lead)
                        phone_tag = f" | Phone: {primary_phone}" if primary_phone else ""
                        logger.info(f"✨ Found Email Lead: {em}{phone_tag} | Role: {job_role} | Name: {recruiter_name or 'N/A'} (Score: {score})")

            # 2b. Add phone/WhatsApp-only leads (when post has phone number but no email)
            elif primary_phone:
                b_phone, b_phone_reason = is_blacklisted(text=post_text, recruiter=recruiter_name)
                loc_ok, loc_reason = is_location_allowed(post_text)
                if not b_phone and loc_ok:
                    phone_key = f"phone:{primary_phone}"
                    if phone_key not in seen_emails:
                        seen_emails.add(phone_key)
                        lead = {
                            "email": "",
                            "phone_number": primary_phone,
                            "whatsapp_link": wa_link,
                            "recruiter_name": recruiter_name,
                            "job_role": job_role,
                            "post_url": post_url,
                            "score": score,
                            "search_keyword": keyword,
                            "post_snippet": snippet,
                            "status": "whatsapp_pending",
                        }
                        leads.append(lead)
                        logger.info(f"📱 Found Phone/WhatsApp Lead: {primary_phone} | Role: {job_role} | Name: {recruiter_name or 'N/A'} (Score: {score})")

        except (StaleElementReferenceException, Exception) as e:
            continue

    # 3. Page-level sweep for any recruiter emails rendered on the page that missed card boundaries
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text
        page_emails = extract_emails(page_text)
        for pem in page_emails:
            if pem not in seen_emails:
                seen_emails.add(pem)
                pos = page_text.lower().find(pem.lower())
                start = max(0, pos - 600)
                end = min(len(page_text), pos + 400)
                surrounding = re.sub(r"\s+", " ", page_text[start:end]).strip()
                is_v, sc, _ = evaluate_post(surrounding, has_email=True)
                if is_v:
                    from src.email_extractor import parse_internship_details, extract_phone_numbers, generate_whatsapp_link
                    sweep_details = parse_internship_details(
                        post_text=surrounding,
                        raw_author="",
                        default_role="Software Engineer Intern"
                    )
                    sweep_phones = extract_phone_numbers(surrounding)
                    sweep_phone = sweep_phones[0] if sweep_phones else ""
                    sweep_wa = generate_whatsapp_link(sweep_phone, role=sweep_details.get("job_role", "Software Engineer Intern")) if sweep_phone else ""

                    leads.append({
                        "email": pem,
                        "phone_number": sweep_phone,
                        "whatsapp_link": sweep_wa,
                        "recruiter_name": sweep_details.get("recruiter_name") or sweep_details.get("company_name") or "Hiring Team",
                        "job_role": sweep_details.get("job_role", "Software Engineer Intern"),
                        "post_url": "",
                        "score": sc,
                        "search_keyword": keyword,
                        "post_snippet": surrounding,
                        "status": "pending",
                    })
                    phone_tag = f" | Phone: {sweep_phone}" if sweep_phone else ""
                    logger.info(f"✨ Found Page Sweep Lead: {pem}{phone_tag} | Role: {sweep_details.get('job_role')} | Company: {sweep_details.get('company_name')} (Score: {sc})")
    except Exception:
        pass

    return leads


def scrape_keyword(driver: webdriver.Chrome, keyword: str, time_filter: str = "past-week", commented_keys: Optional[Set[str]] = None) -> List[Dict]:
    """
    Navigates to LinkedIn content search for a given keyword and extracts leads.
    Performs deep infinite scrolling and aggressive 'see more' expansion.
    """
    url = build_search_url(keyword, time_filter=time_filter)
    logger.info(f"Scraping LinkedIn ({time_filter}): {keyword}")
    try:
        driver.get(url)
    except TimeoutException:
        try:
            driver.execute_script("window.stop();")
        except Exception:
            pass

    _random_delay(2.0, 3.5)

    # Wait for initial results to render
    time.sleep(3.5)

    # Scroll aggressively to trigger infinite scrolling and load all posts
    scroll_page(driver, attempts=25)
    time.sleep(1.5)

    # Expand all '…more' / 'see more' toggles across the page
    click_see_more_buttons(driver, limit=60)
    time.sleep(1.0)

    # Extract leads from all structured post blocks
    leads = extract_posts_from_page(driver, keyword, commented_keys=commented_keys)

    # ALWAYS perform full-page email sweep to catch any emails that escaped card boundaries
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text
        from src.email_extractor import extract_emails
        from src.post_filter import evaluate_post, is_blacklisted, is_location_allowed
        all_page_emails = extract_emails(page_text)
        already_found = {l.get("email") for l in leads if l.get("email")}
        for em in all_page_emails:
            if em in already_found:
                continue
            pos = page_text.lower().find(em.lower())
            ctx_start = max(0, pos - 500)
            ctx_end = min(len(page_text), pos + 400)
            ctx = page_text[ctx_start:ctx_end]
            is_v, sc, _ = evaluate_post(ctx, has_email=True)
            if not is_v:
                continue
            b, _ = is_blacklisted(email=em, text=ctx)
            if b:
                continue
            loc_ok, _ = is_location_allowed(ctx)
            if not loc_ok:
                continue
            already_found.add(em)
            leads.append({
                "email": em,
                "phone_number": "",
                "whatsapp_link": "",
                "recruiter_name": "Hiring Team",
                "job_role": "Software Developer Intern",
                "post_url": "",
                "score": sc,
                "search_keyword": keyword,
                "post_snippet": ctx[:300].strip(),
                "status": "pending",
            })
            logger.info(f"📧 Full-page sweep found extra email: {em} (Score: {sc})")
    except Exception as sweep_err:
        logger.debug(f"Full-page email sweep error: {sweep_err}")

    return leads


def run_scraper(keywords: Optional[List[str]] = None, time_filter: str = "past-week") -> List[Dict]:
    """
    Main entry point for scraping multiple internship keywords with auto-recovery.
    """
    from config import DEFAULT_SEARCH_KEYWORDS, COMMENTED_LOG_JSON
    from src.csv_manager import load_commented_keys

    search_list = keywords if keywords else DEFAULT_SEARCH_KEYWORDS
    all_leads: List[Dict] = []
    seen_emails = set()

    # Load previously commented posts so we NEVER double-comment across keywords or runs
    commented_keys = load_commented_keys(COMMENTED_LOG_JSON)
    logger.info(f"Loaded {len(commented_keys)} previously commented posts from {COMMENTED_LOG_JSON.name}")

    logger.info(f"Starting LinkedIn Scraper with {len(search_list)} keywords...")
    driver = create_driver()

    try:
        if not check_login_status(driver):
            logger.warning("LinkedIn session not logged in! Please log into LinkedIn in the browser window...")
            print("\n" + "=" * 60)
            print("ACTION REQUIRED: Please log in to your LinkedIn account in the Chrome window.")
            print("Once logged in, press Enter in this console to continue...")
            print("=" * 60 + "\n")
            input()

        for idx, kw in enumerate(search_list, 1):
            logger.info(f"\n--- [{idx}/{len(search_list)}] Searching: {kw} ---")
            try:
                leads = scrape_keyword(driver, kw, time_filter=time_filter, commented_keys=commented_keys)
                for l in leads:
                    em = l.get("email")
                    if em:
                        if em not in seen_emails:
                            seen_emails.add(em)
                            all_leads.append(l)
                    else:
                        all_leads.append(l)

                from config import LEADS_CSV
                from src.csv_manager import save_leads
                save_leads(all_leads, LEADS_CSV)
            except Exception as e:
                logger.error(f"Error scraping keyword '{kw}': {e}")
                err_msg = str(e).lower()
                # Auto-recovery: if Chrome died, crashed, or session was invalidated, resurrect it!
                if any(k in err_msg for k in ["invalid session id", "no such session", "session not created", "disconnected"]):
                    logger.warning("Detected crashed or dead Chrome session. Recreating fresh Chrome driver...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    try:
                        time.sleep(2.0)
                        driver = create_driver()
                        logger.info("✅ Successfully resurrected fresh Chrome session! Resuming scraper...")
                    except Exception as re_err:
                        logger.error(f"Failed to restart Chrome driver: {re_err}")

            _random_delay(2.0, 4.0)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    logger.info(f"\nScraping complete! Discovered {len(all_leads)} total unique leads.")
    return all_leads
