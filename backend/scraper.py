import os
import random
import re
from typing import Callable, List, Dict, Any

from playwright.sync_api import sync_playwright


BUSINESS_CATEGORIES = ["gyms", "hotels", "cafes"]
INDIAN_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]


def normalize_indian_phone(phone: str) -> str | None:
    """Normalize a local Indian number; preserve explicit international codes."""
    value = re.sub(r"\s*(?:ext\.?|x)\s*\d+\s*$", "", phone.strip(), flags=re.IGNORECASE)
    digits = re.sub(r"\D", "", value)

    if value.startswith("00"):
        digits = digits[2:]
        return f"+{digits}" if 8 <= len(digits) <= 15 else None
    if value.startswith("+"):
        return f"+{digits}" if 8 <= len(digits) <= 15 else None
    if digits.startswith("91") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"+91{digits}"
    return None


def detect_phone(page) -> str | None:
    """Read a business phone from Google Maps' detail panel controls."""
    selectors = (
        'a[href^="tel:"]',
        '[data-item-id^="phone:"]',
        '[aria-label^="Phone:"]',
        '[aria-label*="Phone"]',
    )
    for selector in selectors:
        for element in page.locator(selector).all():
            try:
                raw_value = (
                    element.get_attribute("href")
                    or element.get_attribute("data-item-id")
                    or element.get_attribute("aria-label")
                    or element.inner_text()
                )
                if raw_value:
                    match = re.search(r"(?:tel:|phone:)?\s*(\+?[\d][\d\s().-]{7,}\d)", raw_value, re.IGNORECASE)
                    candidate = match.group(1) if match else raw_value
                    normalized = normalize_indian_phone(candidate)
                    if normalized:
                        return normalized
            except Exception:
                continue

    try:
        body_text = page.locator("body").inner_text()
        match = re.search(
            r"(?:phone|telephone|call)\D{0,20}(\+?[\d][\d\s().-]{7,}\d)",
            body_text,
            re.IGNORECASE,
        )
        if match:
            return normalize_indian_phone(match.group(1))
    except Exception:
        pass
    return None


def detect_website(page) -> str | None:
    """Search the results panel for any visible website URL."""
    candidate_links = page.locator('a[href]').all()
    for link in candidate_links:
        try:
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "").strip().lower()
            if not href or href.startswith("tel:") or href.startswith("mailto:"):
                continue
            if "google.com" in href or "maps.google" in href:
                continue
            if text in {"website", "visit website", "more info"} or "." in href:
                return href
        except Exception:
            continue

    page_text = page.locator("body").inner_text().lower()
    if "website" in page_text and "http" in page_text:
        for text in page_text.split():
            if text.startswith("http"):
                return text
    return None


def collect_businesses(
    category: str,
    city: str = "India",
    max_results: int = 8,
    on_business: Callable[[Dict[str, Any]], None] | None = None,
) -> List[Dict[str, Any]]:
    """Best-effort Google Maps scraping for local businesses."""
    results: List[Dict[str, Any]] = []
    query = f"{category} {city}".strip()

    with sync_playwright() as p:
        headless_setting = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
        browser = p.chromium.launch(headless=headless_setting)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        print(f"Opening Google Maps for: {query} | headless={headless_setting}")
        page.goto("https://www.google.com/maps", wait_until="domcontentloaded")

        try:
            search_box = page.locator('#ucc-1').first
            search_box.wait_for(state="visible", timeout=15000)
            if search_box.count():
                print("Search box found using id='ucc-1'. Entering query...")
                search_box.fill(query)
                page.keyboard.press("Enter")
            else:
                print("Search box with id='ucc-1' not found. Google Maps may be blocking automation or the DOM changed.")
        except Exception as exc:
            print(f"Search selector error: {exc}")

        cards_locator = page.locator('div[role="article"]')
        try:
            cards_locator.first.wait_for(state="visible", timeout=15000)
        except Exception as exc:
            print(f"Google Maps result cards did not appear for '{query}': {exc}")
        cards = cards_locator.all()
        print(f"Found {len(cards)} potential result cards")

        for index, card in enumerate(cards[:max_results]):
            try:
                text = card.inner_text()
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                if not lines:
                    continue

                business_name = lines[0]
                print(f"Opening business #{index + 1}: {business_name}")
                card.click()
                page.wait_for_timeout(500)

                business_website = detect_website(page)
                business_phone = detect_phone(page)
                business_type = category.replace(" in India", "").strip()
                result = {
                    "name": business_name,
                    "category": business_type,
                    "city": city,
                    "website": business_website,
                    "phone": business_phone,
                    "address": " | ".join(lines[1:3]) if len(lines) > 1 else "Not available",
                }
                results.append(result)
                if on_business:
                    on_business(result)
                print(f"Website for {business_name}: {business_website or 'No website found'}")
                print(f"Phone for {business_name}: {business_phone or 'No phone found'}")
            except Exception as exc:
                print(f"Could not inspect result card: {exc}")
                continue

        browser.close()

    if not results:
        print(f"No real Google Maps results were detected for '{category}'. No sample data saved.")
        print("Reason: Google Maps likely blocked automation, changed its DOM, or the search results never loaded.")

    return results


def select_random_businesses(per_category: int = 5) -> List[Dict[str, Any]]:
    businesses: List[Dict[str, Any]] = []
    selected_states = random.sample(INDIAN_STATES, k=len(BUSINESS_CATEGORIES))
    for business_type, state in zip(BUSINESS_CATEGORIES, selected_states):
        print(f"Searching for {business_type} in {state}")
        businesses.extend(collect_businesses(business_type, city=state, max_results=per_category))

    businesses = [lead for lead in businesses if lead.get("name") and not str(lead.get("name", "")).startswith("Sample ")]
    return businesses
