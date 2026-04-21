"""
Google Maps Reviews Scraper – Gratis versjon med Playwright
============================================================
Automatiserer en ekte nettleser for å hente anmeldelser fra Google Maps.
Ingen API-nøkkel nødvendig.

Installasjon:
    pip install playwright pandas
    playwright install chromium

Kjør:
    python lugano_scraper_free.py
"""

import json
import time
import random
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── Konfigurasjon ──────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("lugano_output")

# Liste over parker/grønne områder i Lugano.
# Legg til eller fjern URL-er etter behov.
# Slik finner du URL-en: Søk opp stedet på maps.google.com, kopier URL-en fra adressefeltet.
PLACES = [
    {
        "name": "Parco Ciani",
        "url": "https://www.google.com/maps/place/Parco+Ciani/@46.0059,8.9563,17z",
    },
    {
        "name": "Parco Tassino",
        "url": "https://www.google.com/maps/place/Parco+Tassino,+Lugano/@46.0021,8.9441,17z",
    },
    {
        "name": "Parco Civico",
        "url": "https://www.google.com/maps/place/Parco+Civico+di+Lugano/@46.006,8.9563,17z",
    },
    {
        "name": "Monte San Salvatore",
        "url": "https://www.google.com/maps/place/Monte+San+Salvatore/@45.9717,8.9392,15z",
    },
    {
        "name": "Parco degli Ulivi",
        "url": "https://www.google.com/maps/place/Parco+degli+Ulivi,+Gandria/@46.0086,9.0003,16z",
    },
    {
        "name": "Lungolago Lugano",
        "url": "https://www.google.com/maps/place/Lungolago+di+Lugano/@46.005,8.9517,16z",
    },
    {
        "name": "Monte Brè",
        "url": "https://www.google.com/maps/place/Monte+Br%C3%A8/@46.0222,9.0217,15z",
    },
    {
        "name": "Parco San Michele",
        "url": "https://www.google.com/maps/place/Parco+San+Michele,+Lugano/@46.0004,8.9481,17z",
    },
]

# Hvor mange anmeldelser du vil hente per sted (bla nedover)
TARGET_REVIEWS = 50


# ── Hjelpefunksjoner ───────────────────────────────────────────────────────────

def human_delay(min_s=1.0, max_s=2.5):
    """Tilfeldig pause for å ligne menneskelig oppførsel."""
    time.sleep(random.uniform(min_s, max_s))


def close_cookie_banner(page):
    """Lukk Google sin cookie-popup hvis den dukker opp."""
    try:
        # Prøv ulike knapp-tekster
        for text in ["Godta alle", "Accept all", "Accetta tutto", "Reject all", "Rifiuta tutto"]:
            btn = page.get_by_role("button", name=text)
            if btn.is_visible(timeout=2000):
                btn.click()
                human_delay(0.5, 1.0)
                return
    except PlaywrightTimeout:
        pass


def click_reviews_tab(page):
    """Klikk på 'Anmeldelser'-fanen."""
    try:
        # Prøv ulike språk-varianter
        for text in ["Reviews", "Recensioni", "Anmeldelser", "Avis"]:
            try:
                tab = page.get_by_role("tab", name=text)
                if tab.is_visible(timeout=3000):
                    tab.click()
                    human_delay(1.0, 2.0)
                    return True
            except PlaywrightTimeout:
                continue
    except Exception:
        pass
    return False


def sort_by_newest(page):
    """Sorter anmeldelser etter nyeste for mer kronologisk data."""
    try:
        sort_btn = page.locator('button[aria-label*="Sort"], button[data-value="sort"]').first
        if sort_btn.is_visible(timeout=3000):
            sort_btn.click()
            human_delay(0.5, 1.0)
            # Velg "Newest" / "Più recenti"
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


def expand_all_reviews(page):
    """Klikk 'Mer' for å ekspandere avkortede anmeldelser."""
    try:
        more_buttons = page.locator('button[aria-label="See more"], button.w8nwRe')
        count = more_buttons.count()
        for i in range(count):
            try:
                more_buttons.nth(i).click()
                human_delay(0.1, 0.3)
            except Exception:
                pass
    except Exception:
        pass


def scroll_reviews_panel(page, target_count: int) -> int:
    """Scroll i anmeldelses-panelet til vi har nok anmeldelser."""
    # Finn scroll-containeren (panelet til venstre)
    scrollable = page.locator('div[role="main"] div.m6QErb[tabindex]').last

    last_count = 0
    no_change_rounds = 0

    for _ in range(60):  # maks 60 scroll-forsøk
        # Tell nåværende antall
        current_count = page.locator('div.jftiEf').count()

        if current_count >= target_count:
            print(f"     → Nådd {current_count} anmeldelser")
            break

        if current_count == last_count:
            no_change_rounds += 1
            if no_change_rounds >= 4:
                print(f"     → Ingen nye anmeldelser etter scrolling. Stopper på {current_count}.")
                break
        else:
            no_change_rounds = 0
            print(f"     → {current_count} anmeldelser lastet …")

        last_count = current_count
        expand_all_reviews(page)

        # Scroll ned i panelet
        try:
            scrollable.evaluate("el => el.scrollBy(0, 800)")
        except Exception:
            page.keyboard.press("End")

        human_delay(0.8, 1.5)

    return page.locator('div.jftiEf').count()


def parse_reviews(page, place_name: str) -> list[dict]:
    """Les ut anmeldelsesdata fra DOM-en."""
    reviews = []
    review_elements = page.locator('div.jftiEf').all()

    for el in review_elements:
        try:
            # Navn
            try:
                name = el.locator('div.d4r55').inner_text(timeout=1000)
            except Exception:
                name = ""

            # Stjerner (aria-label inneholder f.eks. "4 stars")
            try:
                stars_el = el.locator('span[role="img"]').first
                aria = stars_el.get_attribute("aria-label") or ""
                rating = int("".join(c for c in aria if c.isdigit())[:1]) if aria else None
            except Exception:
                rating = None

            # Dato
            try:
                date = el.locator('span.rsqaWe').inner_text(timeout=1000)
            except Exception:
                date = ""

            # Anmeldelsestekst
            try:
                text = el.locator('span.wiI7pd').inner_text(timeout=1000)
            except Exception:
                text = ""

            # Lokal guide?
            try:
                guide_badge = el.locator('span.RfnDt').is_visible(timeout=500)
            except Exception:
                guide_badge = False

            if name or text:
                reviews.append({
                    "place_name": place_name,
                    "reviewer_name": name.strip(),
                    "review_rating": rating,
                    "review_date": date.strip(),
                    "review_text": text.strip(),
                    "local_guide": guide_badge,
                    "scraped_at": datetime.now().isoformat(),
                })
        except Exception:
            continue

    return reviews


# ── Hoved-funksjon ─────────────────────────────────────────────────────────────

def scrape_place(page, place: dict) -> list[dict]:
    name = place["name"]
    url = place["url"]
    print(f"\n📍 {name}")
    print(f"   URL: {url}")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        human_delay(2.0, 3.5)

        close_cookie_banner(page)
        human_delay(0.5, 1.0)

        # Klikk på anmeldelses-fanen
        found_tab = click_reviews_tab(page)
        if not found_tab:
            print("   ⚠️  Fant ikke anmeldelses-fanen, prøver likevel …")

        # Sorter etter nyeste (valgfritt)
        sort_by_newest(page)

        # Scroll for å laste anmeldelser
        print(f"   ⏳ Scroller for å laste opp til {TARGET_REVIEWS} anmeldelser …")
        count = scroll_reviews_panel(page, TARGET_REVIEWS)

        # Parse
        reviews = parse_reviews(page, name)
        print(f"   ✅ Hentet {len(reviews)} anmeldelse(r)")
        return reviews

    except PlaywrightTimeout:
        print(f"   ❌ Timeout – siden lastet ikke inn. Hopper over.")
        return []
    except Exception as e:
        print(f"   ❌ Feil: {e}")
        return []


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_reviews = []

    print("🌿 Lugano Urban Green Spaces – Gratis Scraper")
    print("=" * 50)
    print(f"Steder å scrape: {len(PLACES)}")
    print(f"Mål per sted: {TARGET_REVIEWS} anmeldelser\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Sett til True for å kjøre uten vindu
            args=["--lang=en-US"],  # Engelsk grensesnitt for stabile selektorer
        )
        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        for place in PLACES:
            reviews = scrape_place(page, place)
            all_reviews.extend(reviews)
            human_delay(2.0, 4.0)  # Pause mellom steder

        browser.close()

    # Lagre resultater
    print(f"\n💾 Lagrer {len(all_reviews)} anmeldelser …")

    if all_reviews:
        df = pd.DataFrame(all_reviews)

        csv_path = OUTPUT_DIR / f"reviews_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"   ✅ CSV  → {csv_path}")

        json_path = OUTPUT_DIR / f"reviews_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_reviews, f, ensure_ascii=False, indent=2)
        print(f"   ✅ JSON → {json_path}")

        # Rask statistikk
        print("\n📊 Statistikk:")
        print(f"   Totalt anmeldelser : {len(df)}")
        print(f"   Unike steder       : {df['place_name'].nunique()}")
        ratings = df["review_rating"].dropna()
        if not ratings.empty:
            print(f"   Snittrating        : {ratings.mean():.2f} / 5")
        print(f"\n   Per sted:")
        for place, grp in df.groupby("place_name"):
            r = grp["review_rating"].mean()
            print(f"   {'  ' + place:<35} {len(grp):>3} anmeldelser  ⭐ {r:.1f}")
    else:
        print("   ⚠️  Ingen anmeldelser ble hentet. Sjekk at Playwright er riktig installert.")

    print(f"\n✨ Ferdig! Sjekk mappen: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()