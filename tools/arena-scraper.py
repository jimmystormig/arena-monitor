#!/usr/bin/env python3
"""
Arena för lärande browser scraper.
Logs into Arena as Personal, switches to Vårdnadshavare, scrapes news for
all children, fetches full content for each item.

Outputs a JSON array to stdout:
[
  {
    "child": "CHILD NAME",
    "title": "...",
    "date": "12 februari 2026",
    "url": "https://arena.alingsas.se/nyhet/...",
    "content_html": "...",
    "content_text": "..."
  },
  ...
]

Reads credentials from environment variables:
  ARENA_URL, ARENA_USERNAME, ARENA_PASSWORD

Optional flags:
  --limit N   Max news items per child (default 5)
  --headless  Run browser headlessly (default true)
"""

import json
import os
import sys
import time
import argparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(json.dumps({"error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}))
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print(json.dumps({"error": "BeautifulSoup not installed. Run: pip install beautifulsoup4"}))
    sys.exit(1)

ARENA_URL = os.environ.get("ARENA_URL", "https://arena.alingsas.se")
ARENA_USERNAME = os.environ["ARENA_USERNAME"]
ARENA_PASSWORD = os.environ["ARENA_PASSWORD"]


def login_to_arena(page, max_retries=2):
    for attempt in range(max_retries + 1):
        page.goto(ARENA_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        if "arena.alingsas.se" in page.url and (
            "Nyheter" in page.title() or page.locator("text=ROLL").count() > 0
        ):
            return True

        personal_btn = page.locator("button:has-text('Personal')")
        if personal_btn.count() > 0:
            personal_btn.click()
            time.sleep(2)

        user_pass_btn = page.locator("button:has-text('Användarnamn och lösenord')")
        if user_pass_btn.count() > 0:
            user_pass_btn.click()
            time.sleep(2)

        username_field = page.locator("input[type='text']")
        password_field = page.locator("input[type='password']")

        if username_field.count() > 0 and password_field.count() > 0:
            username_field.fill(ARENA_USERNAME)
            password_field.fill(ARENA_PASSWORD)
            login_btn = page.locator("button[type='submit']")
            if login_btn.count() > 0:
                login_btn.click()
            else:
                password_field.press("Enter")
            time.sleep(5)

        if "Inloggningsfel" in page.title() or "novasoftware" in page.url:
            page.goto(ARENA_URL, wait_until="networkidle", timeout=30000)
            time.sleep(3)

        if "arena.alingsas.se" in page.url and ("Nyheter" in page.title() or "Arena" in page.title()):
            return True

    return False


def switch_to_guardian_view(page):
    # Check for child name elements (class="text-subtitle-2 text-uppercase font-weight-bold")
    if page.locator(".text-subtitle-2.text-uppercase.font-weight-bold").count() > 0:
        return True

    if "arena.alingsas.se" not in page.url:
        return False

    # The role button displays the current role name (e.g. "Lärare").
    # Click it to open the dropdown, then pick Vårdnadshavare from the list.
    role_btn = page.locator("button:has-text('Lärare')").first
    if role_btn.count() == 0:
        return False

    role_btn.click()
    time.sleep(1)

    vh_btn = page.locator(".v-list-item--link:has-text('Vårdnadshavare')").first
    if vh_btn.count() == 0:
        return False

    vh_btn.click()

    try:
        page.wait_for_function(
            "document.querySelectorAll('.text-subtitle-2.text-uppercase.font-weight-bold').length > 0",
            timeout=10000
        )
        return True
    except Exception:
        return False


def scrape_news_list(page, limit=5):
    time.sleep(2)

    for _ in range(5):
        load_more = page.locator("text=Ladda fler")
        if load_more.count() > 0:
            try:
                load_more.first.click()
                time.sleep(1)
            except Exception:
                break
        else:
            break

    time.sleep(1)

    try:
        news_data = page.evaluate("""() => {
            const items = [];

            // Each child's news is wrapped in a card: div.mb-6.v-card
            // The child name sits in the card header: .text-subtitle-2.text-uppercase.font-weight-bold
            // The DOM text is title-case (CSS text-uppercase only affects rendering).
            const cards = document.querySelectorAll('.mb-6.v-card');
            for (const card of cards) {
                const nameEl = card.querySelector('.text-subtitle-2.font-weight-bold');
                if (!nameEl) continue;
                const childName = nameEl.textContent.trim().toUpperCase();

                const links = card.querySelectorAll('a[href*="/nyhet/"]');
                for (const link of links) {
                    const linkText = link.textContent;
                    const dateMatch = linkText.match(/PUBLICERAT:\\s*([\\d]+\\s+\\w+\\s+\\d{4})/i);
                    const titleEl = link.querySelector('.text-subtitle-2');
                    const title = titleEl ? titleEl.textContent.trim() : link.textContent.trim();
                    items.push({
                        child: childName,
                        title: title,
                        href: link.getAttribute('href'),
                        date: dateMatch ? dateMatch[1] : null
                    });
                }
            }
            return items;
        }""")
    except Exception as e:
        return [], str(e)

    items = []
    per_child = {}
    for item in news_data:
        href = item.get("href", "")
        if not href:
            continue
        child = item.get("child") or "Okänt barn"
        per_child.setdefault(child, 0)
        if per_child[child] >= limit:
            continue
        per_child[child] += 1
        full_url = ARENA_URL + href if href.startswith("/") else href
        items.append({
            "child": child,
            "title": item.get("title", "Untitled"),
            "date": item.get("date"),
            "url": full_url,
            "content_html": None,
            "content_text": None,
        })

    return items, None


def fetch_content(page, item):
    try:
        page.goto(item["url"], wait_until="networkidle", timeout=30000)
        time.sleep(3)

        content_html = page.evaluate("""() => {
            const layout = document.querySelector('#__layout') ||
                           document.querySelector('#__nuxt') ||
                           document.body;
            const main = layout.querySelector('.v-main__wrap') ||
                         layout.querySelector('.v-main') ||
                         layout.querySelector('main') ||
                         layout;
            const clone = main.cloneNode(true);
            clone.querySelectorAll('nav, header, footer, .v-app-bar, .v-navigation-drawer').forEach(el => el.remove());
            return clone.innerHTML;
        }""")

        # Make attachment links absolute
        links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .filter(a => {
                    const h = a.getAttribute('href');
                    return h && (h.includes('/sites/default/files/') ||
                                 h.endsWith('.pdf') || h.endsWith('.docx') || h.endsWith('.xlsx'));
                })
                .map(a => a.getAttribute('href'));
        }""")

        for href in links:
            if href.startswith("/"):
                content_html = (content_html or "").replace(
                    f'href="{href}"', f'href="{ARENA_URL + href}"'
                )

        item["content_html"] = content_html

        soup = BeautifulSoup(content_html or "", "html.parser")
        item["content_text"] = soup.get_text(separator="\n", strip=True)

    except Exception as e:
        item["error"] = str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="Max items per child")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    args = parser.parse_args()

    headless = not args.no_headless

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="sv-SE")
        page = ctx.new_page()

        try:
            if not login_to_arena(page):
                print(json.dumps({"error": "Login failed"}))
                sys.exit(1)

            switch_to_guardian_view(page)

            items, err = scrape_news_list(page, limit=args.limit)
            if err:
                print(json.dumps({"error": err}))
                sys.exit(1)

            for item in items:
                fetch_content(page, item)

        finally:
            browser.close()

    print(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
