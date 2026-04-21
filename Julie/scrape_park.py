"""
Google Maps Park Scraper – feed it a URL, it scrapes automatically
===================================================================
Set PLACE_URL to a Google Maps place URL and run. The script navigates
directly to the page and scrapes up to TARGET_REVIEWS reviews.

Usage:
    python scrape_park.py
"""

import re
import time
import random
import pandas as pd
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── SET THE URL HERE ───────────────────────────────────────────────────────────

PLACE_URL = "https://www.google.com/maps/place/Dog+Park+Pregassona+-+Rug%C3%AC/@46.0078413,8.9306054,14.05z/data=!4m10!1m3!11m2!2s7H_mnpNDSxntS3tEFxBggg!3e3!3m5!1s0x4784339c38d13279:0xc77c23ea9290bcb0!8m2!3d46.0260386!4d8.966781!16s%2Fg%2F11fk572r6z?entry=ttu&g_ep=EgoyMDI2MDQxNS4wIKXMDSoASAFQAw%3D%3D"

TARGET_REVIEWS = 10_000
OUTPUT_DIR = Path("lugano_output")

# ──────────────────────────────────────────────────────────────────────────────

def extract_place_name(url: str) -> str:
    """Pull the human-readable name out of a Google Maps place URL."""
    match = re.search(r"/maps/place/([^/@]+)", url)
    if match:
        return unquote(match.group(1)).replace("+", " ")
    return "unknown_place"

def human_delay(min_s=1.0, max_s=2.5):
    time.sleep(random.uniform(min_s, max_s))

def close_cookie_banner(page):
    for text in ["Accept all", "Godta alle", "Accetta tutto", "Reject all"]:
        try:
            btn = page.get_by_role("button", name=text)
            if btn.is_visible(timeout=2000):
                btn.click()
                human_delay(0.5, 1.0)
                return
        except PlaywrightTimeout:
            continue

def force_english_url(url: str) -> str:
    """Append hl=en so Google Maps serves the page in English."""
    if "hl=" in url:
        return re.sub(r"hl=[^&]+", "hl=en", url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}hl=en"

def open_url(page, url: str):
    url = force_english_url(url)
    print(f"   Opening: {url[:80]}...")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    human_delay(2.0, 3.0)
    close_cookie_banner(page)
    human_delay(1.0, 2.0)

def click_reviews_tab(page):
    for text in ["Reviews", "Recensioni", "Anmeldelser"]:
        try:
            tab = page.get_by_role("tab", name=text)
            if tab.is_visible(timeout=4000):
                tab.click()
                human_delay(1.5, 2.5)
                return True
        except PlaywrightTimeout:
            continue
    return False

def sort_by_newest(page):
    try:
        sort_btn = page.locator('button[aria-label*="Sort"], button[data-value="sort"]').first
        if sort_btn.is_visible(timeout=3000):
            sort_btn.click()
            human_delay(0.5, 1.0)
            for text in ["Newest", "Più recenti", "Plus récentes"]:
                try:
                    option = page.get_by_role("menuitemradio", name=text)
                    if option.is_visible(timeout=2000):
                        option.click()
                        human_delay(1.0, 1.5)
                        return
                except PlaywrightTimeout:
                    continue
    except Exception:
        pass

def expand_reviews(page):
    try:
        btns = page.locator('button[aria-label="See more"], button.w8nwRe')
        for i in range(btns.count()):
            try:
                btns.nth(i).click()
                human_delay(0.1, 0.2)
            except Exception:
                pass
    except Exception:
        pass

def scroll_to_target(page, target: int):
    last_count = 0
    stale_rounds = 0

    for _ in range(3000):
        current = page.locator('div.jftiEf').count()

        if current >= target:
            print(f"   → Target reached: {current} reviews")
            break
        if current == last_count:
            stale_rounds += 1
            if stale_rounds >= 8:
                print(f"   → No more loading. Stopped at {current}.")
                break
        else:
            stale_rounds = 0
            print(f"   → {current} / {target} …")

        last_count = current
        expand_reviews(page)

        # Walk up from the last review to find its scrollable container, then scroll it
        try:
            page.evaluate("""
                const review = document.querySelector('div.jftiEf');
                if (review) {
                    let el = review.parentElement;
                    while (el && el !== document.body) {
                        if (el.scrollHeight > el.clientHeight + 10) {
                            el.scrollTop = el.scrollHeight;
                            break;
                        }
                        el = el.parentElement;
                    }
                }
            """)
        except Exception:
            page.keyboard.press("End")

        human_delay(0.7, 1.3)

def parse_reviews(page, place_name: str) -> list[dict]:
    reviews = []
    for el in page.locator('div.jftiEf').all():
        try:
            name = el.locator('div.d4r55').inner_text(timeout=1000)
        except Exception:
            name = ""
        try:
            aria = el.locator('span[role="img"]').first.get_attribute("aria-label") or ""
            rating = int("".join(c for c in aria if c.isdigit())[:1]) if aria else None
        except Exception:
            rating = None
        try:
            date = el.locator('span.rsqaWe').inner_text(timeout=1000)
        except Exception:
            date = ""
        try:
            text = el.locator('span.wiI7pd').inner_text(timeout=1000)
        except Exception:
            text = ""
        try:
            local_guide = el.locator('span.RfnDt').is_visible(timeout=500)
        except Exception:
            local_guide = False

        if text.strip():
            reviews.append({
                "place_name": place_name,
                "reviewer_name": name.strip(),
                "review_rating": rating,
                "review_date": date.strip(),
                "review_text": text.strip(),
                "local_guide": local_guide,
                "scraped_at": datetime.now().isoformat(),
            })
    return reviews

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    place_name = extract_place_name(PLACE_URL)
    print(f"\n🌿 {place_name}")
    print(f"   Target: {TARGET_REVIEWS} reviews\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--lang=en-US"])
        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = context.new_page()

        open_url(page, PLACE_URL)
        click_reviews_tab(page)
        sort_by_newest(page)
        scroll_to_target(page, TARGET_REVIEWS)
        reviews = parse_reviews(page, place_name)
        browser.close()

    df = pd.DataFrame(reviews)
    filename = place_name.lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{filename}_{timestamp}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")

    print(f"\n✅ {len(reviews)} reviews → {path}")
    if not df.empty:
        print(f"   Avg rating: {df['review_rating'].mean():.2f}")

if __name__ == "__main__":
    main()