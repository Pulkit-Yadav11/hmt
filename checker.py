

import json
import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime


#  CONFIGURATION

# Specific product pages you always want to track
SPECIFIC_WATCHES = [
    {
        "name": "HMT Watch (6297d606)",
        "url": "https://www.hmtwatches.store/product/6297d606-55df-44a0-9d2c-7ed811bf8e27",
    },
    {
        "name": "HMT Watch (2ab8780d)",
        "url": "https://www.hmtwatches.store/product/2ab8780d-a5f3-4c87-8051-dfc691d1cb11",
    },
    {
        "name": "HMT Watch (b8dd05e3)",
        "url": "https://www.hmtwatches.store/product/b8dd05e3-7936-4291-bcb4-1cea41b14cdf",
    },
]

# Catalog pages to scan for ANY new/restocked item
CATALOG_PAGES = [
    "https://www.hmtwatches.in/",
    "https://www.hmtwatches.store/all-products",
]

STATE_FILE = "stock_state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

#  NOTIFICATION

def notify(title: str, message: str):
    """Send a desktop notification. Falls back to print in CI."""
    print(f"\n🔔 ALERT: {title}\n   {message}\n")

    # Try desktop notification (only works locally, not in GitHub Actions)
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="HMT Stock Bot",
            timeout=15,
        )
    except Exception:
        pass  # silently skip in headless/CI environments


#  STATE MANAGEMENT

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)



#  SCRAPING HELPERS


def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ⚠ Could not fetch {url}: {e}")
        return None


def is_out_of_stock_text(text: str) -> bool:
    """Return True if the text signals out-of-stock."""
    oos_keywords = ["out of stock", "sold out", "unavailable", "notify me", "coming soon"]
    t = text.lower()
    return any(kw in t for kw in oos_keywords)


#  CHECK SPECIFIC PRODUCT PAGE

def check_specific_product(watch: dict, state: dict) -> dict:
    url = watch["url"]
    name = watch["name"]
    print(f"  Checking: {name}")

    soup = fetch(url)
    if not soup:
        return state

    page_text = soup.get_text(" ", strip=True)

    # Heuristic: look for add-to-cart button or out-of-stock markers
    add_to_cart = bool(
        soup.find(
            lambda tag: tag.name in ["button", "input", "a"]
            and "add to cart" in tag.get_text(strip=True).lower()
        )
    )
    out_of_stock = is_out_of_stock_text(page_text)

    if add_to_cart and not out_of_stock:
        current_status = "in_stock"
    elif out_of_stock:
        current_status = "out_of_stock"
    else:
        # Ambiguous — treat as unknown, don't alert
        current_status = state.get(url, {}).get("status", "unknown")

    prev_status = state.get(url, {}).get("status", "unknown")

    if current_status == "in_stock" and prev_status != "in_stock":
        notify(
            f"🟢 IN STOCK: {name}",
            f"{name} is now available!\n{url}",
        )

    state[url] = {
        "name": name,
        "status": current_status,
        "last_checked": datetime.utcnow().isoformat(),
        "url": url,
    }
    print(f"    → Status: {current_status} (was: {prev_status})")
    return state


#  CHECK CATALOG PAGE (hmtwatches.in)

def check_catalog_hmtwatches_in(state: dict) -> dict:
    url = "https://www.hmtwatches.in/"
    print(f"  Scanning catalog: {url}")
    soup = fetch(url)
    if not soup:
        return state

    # Products on hmtwatches.in appear as cards with product names + status text
    # They label out-of-stock items with "Out Of Stock" badge
    product_cards = soup.find_all(
        lambda tag: tag.name in ["div", "li", "article"]
        and tag.find(["h2", "h3", "h4", "p", "span"],
                     string=lambda s: s and len(s.strip()) > 5)
    )

    seen = set()
    for card in product_cards:
        text = card.get_text(" ", strip=True)
        # Try to grab a product name from heading tags
        heading = card.find(["h2", "h3", "h4"])
        if not heading:
            continue
        prod_name = heading.get_text(strip=True)
        if not prod_name or prod_name in seen or len(prod_name) < 4:
            continue
        seen.add(prod_name)

        # Find a link for this product
        link_tag = card.find("a", href=True)
        prod_url = link_tag["href"] if link_tag else url
        if prod_url.startswith("/"):
            prod_url = "https://www.hmtwatches.in" + prod_url

        card_text = text.lower()
        if "out of stock" in card_text:
            current_status = "out_of_stock"
        else:
            current_status = "in_stock"

        key = f"hmtwatches.in::{prod_name}"
        prev = state.get(key, {}).get("status", "unknown")

        if current_status == "in_stock" and prev == "out_of_stock":
            notify(
                f"🟢 RESTOCKED on hmtwatches.in: {prod_name}",
                f"{prod_name} is back in stock!\n{prod_url}",
            )
        elif current_status == "in_stock" and prev == "unknown":
            notify(
                f"🆕 NEW / IN STOCK on hmtwatches.in: {prod_name}",
                f"Newly listed or first seen: {prod_name}\n{prod_url}",
            )

        state[key] = {
            "name": prod_name,
            "status": current_status,
            "url": prod_url,
            "source": "hmtwatches.in",
            "last_checked": datetime.utcnow().isoformat(),
        }

    return state


def check_catalog_hmtwatches_store(state: dict) -> dict:
    url = "https://www.hmtwatches.store/all-products"
    print(f"  Scanning catalog: {url}")
    soup = fetch(url)
    if not soup:
        return state

    # The store likely renders product cards with names and availability cues
    cards = soup.find_all(
        lambda tag: tag.name in ["div", "li", "article"]
        and tag.find(["h2", "h3", "h4"])
    )

    seen = set()
    for card in cards:
        heading = card.find(["h2", "h3", "h4"])
        if not heading:
            continue
        prod_name = heading.get_text(strip=True)
        if not prod_name or prod_name in seen or len(prod_name) < 4:
            continue
        seen.add(prod_name)

        link_tag = card.find("a", href=True)
        prod_url = link_tag["href"] if link_tag else url
        if prod_url.startswith("/"):
            prod_url = "https://www.hmtwatches.store" + prod_url

        card_text = card.get_text(" ", strip=True).lower()
        if is_out_of_stock_text(card_text):
            current_status = "out_of_stock"
        else:
            current_status = "in_stock"

        key = f"hmtwatches.store::{prod_name}"
        prev = state.get(key, {}).get("status", "unknown")

        if current_status == "in_stock" and prev == "out_of_stock":
            notify(
                f"🟢 RESTOCKED on hmtwatches.store: {prod_name}",
                f"{prod_name} is back in stock!\n{prod_url}",
            )
        elif current_status == "in_stock" and prev == "unknown":
            notify(
                f"🆕 NEW / IN STOCK on hmtwatches.store: {prod_name}",
                f"Newly listed: {prod_name}\n{prod_url}",
            )

        state[key] = {
            "name": prod_name,
            "status": current_status,
            "url": prod_url,
            "source": "hmtwatches.store",
            "last_checked": datetime.utcnow().isoformat(),
        }

    return state



def main():
    print(f"\n{'='*50}")
    print(f"HMT Stock Checker — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    state = load_state()

    # 1. Check the 3 specific product pages first
    print("── Specific Watches ──")
    for watch in SPECIFIC_WATCHES:
        state = check_specific_product(watch, state)
        time.sleep(2)  # be polite to the server

    # 2. Scan full catalogs
    print("\n── Catalog Scan ──")
    state = check_catalog_hmtwatches_in(state)
    time.sleep(2)
    state = check_catalog_hmtwatches_store(state)

    save_state(state)
    print(f"\n✅ Done. State saved to {STATE_FILE}")

    # Print a quick summary table
    print("\n── Current Status of Specific Watches ──")
    for watch in SPECIFIC_WATCHES:
        s = state.get(watch["url"], {})
        status = s.get("status", "unknown")
        icon = "🟢" if status == "in_stock" else ("🔴" if status == "out_of_stock" else "⚪")
        print(f"  {icon} {watch['name']}: {status}")


if __name__ == "__main__":
    main()
