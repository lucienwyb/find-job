#!/usr/bin/env python3
"""Deep scrape of Cambricon mokahr portal and Deepglint zhiye portal, plus search for others."""
import json
import os
import time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"


def scrape_page(browser, url, wait=5, scroll=True):
    """Scrape a page with full rendering and API capture."""
    api_data = []
    page = browser.new_page()

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                body = response.text()
                if body and len(body) > 100:
                    api_data.append({
                        'url': response.url[:500],
                        'body': body[:30000]
                    })
        except:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(wait)

        if scroll:
            # Scroll to load more content
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1)

        title = page.title()
        try:
            body_text = page.inner_text("body")
        except:
            body_text = ""

        links = []
        try:
            links = page.eval_on_selector_all("a[href]", """
                elements => elements.map(e => ({
                    text: e.innerText.trim().substring(0, 200),
                    href: e.href
                }))
            """)
        except:
            pass

        page.close()
        return {
            "url": url,
            "status": "ok",
            "title": title,
            "body_text": body_text[:50000],
            "links": links[:500],
            "api_data": api_data,
        }
    except Exception as e:
        page.close()
        return {
            "url": url,
            "status": "error",
            "error": str(e)[:300],
            "api_data": api_data,
            "body_text": "",
            "links": [],
        }


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    targets = [
        # Cambricon - mokahr portal with full job listing
        ("cambricon", "https://app.mokahr.com/apply/cambricon/1113#/jobs", 8),
        # Deepglint - zhiye.com social recruitment
        ("deepglint", "https://deepglint.zhiye.com/social", 8),
        # Try Baichuan - look for career links more carefully
        ("baichuan", "https://www.baichuan-ai.com/", 5),
        # 4Paradigm - try direct career pages
        ("4paradigm", "https://www.4paradigm.com/careers.html", 5),
        # ModelBest - try different career URLs
        ("modelbest", "https://www.modelbest.cn/about", 5),
        # DP Technology - try dp.tech
        ("dptechnology", "https://www.dp.tech/", 8),
        # Geovis - try more career paths
        ("geovis", "https://www.geovis.com.cn/about/", 5),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        for key, url, wait_time in targets:
            print(f"\n{'='*60}")
            print(f"Scraping: {key} -> {url}")
            print(f"{'='*60}")

            result = scrape_page(browser, url, wait=wait_time)

            print(f"  Status: {result['status']}")
            print(f"  Title: {result.get('title','')}")
            print(f"  Body length: {len(result.get('body_text',''))}")
            print(f"  Links: {len(result.get('links',[]))}")
            print(f"  API data: {len(result.get('api_data',[]))}")

            # Show career-related links
            links = result.get("links", [])
            career_links = []
            for link in links:
                text = link.get('text', '')
                href = link.get('href', '')
                combined = (text + href).lower()
                if any(k in combined for k in ['join', 'career', 'job', 'recruit', '社招', '校招', '招聘', '加入', 'talent', 'hire', 'mokahr', 'zhiye', 'position', '职位']):
                    career_links.append(link)
            if career_links:
                print(f"  Career links ({len(career_links)}):")
                for cl in career_links[:30]:
                    print(f"    {cl['text'][:80]} -> {cl['href'][:120]}")

            # Show API data snippets
            for api in result.get("api_data", [])[:5]:
                print(f"  API: {api['url'][:150]}")
                # Try to parse as JSON
                try:
                    data = json.loads(api["body"])
                    # Look for job/position data
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print(f"    Keys: {keys}")
                        if "data" in data:
                            d = data["data"]
                            if isinstance(d, dict):
                                print(f"    Data keys: {list(d.keys())}")
                                if "totalCount" in d:
                                    print(f"    Total positions: {d['totalCount']}")
                                if "list" in d:
                                    print(f"    List items: {len(d['list'])}")
                except:
                    print(f"    Body (first 200): {api['body'][:200]}")

            # Save result
            filepath = f"/pulp/find-job/r44_{key}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  Saved to {filepath}")

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
