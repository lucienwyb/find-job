#!/usr/bin/env python3
"""Scrape career portals for 7 companies - v3 with deeper navigation."""
import json
import os
import time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"


def scrape_with_navigation(browser, url, click_text=None, extra_urls=None):
    """Scrape a URL, optionally clicking on a link, capturing API responses."""
    api_data = []
    page = browser.new_page()

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                body = response.text()
                if body and len(body) > 100:
                    lower = body.lower()
                    if any(k in lower for k in ['job', 'position', 'recruit', 'department', 'vacanc', 'opening', 'hire', 'talent']):
                        api_data.append({
                            'url': response.url[:500],
                            'body': body[:20000]
                        })
        except:
            pass

    page.on("response", handle_response)

    result = {"url": url, "status": "error", "body_text": "", "title": "", "api_data": []}

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)

        # Try clicking on specified text
        if click_text:
            try:
                # Try to find and click the link
                el = page.get_by_text(click_text, exact=False).first
                if el:
                    el.click(timeout=10000)
                    time.sleep(5)  # Wait for page load after click
            except Exception as e:
                result["click_error"] = str(e)[:200]

        # Try additional URLs (like clicking through sub-pages)
        if extra_urls:
            for extra in extra_urls:
                try:
                    page.goto(extra, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)
                except:
                    pass

        result["title"] = page.title()
        try:
            result["body_text"] = page.inner_text("body")[:30000]
        except:
            pass
        result["status"] = "ok"
        result["api_data"] = api_data

        # Also capture all links on the page
        try:
            links = page.eval_on_selector_all("a[href]", """
                elements => elements.map(e => ({
                    text: e.innerText.trim().substring(0, 100),
                    href: e.href
                }))
            """)
            result["links"] = links[:200]
        except:
            result["links"] = []

    except Exception as e:
        result["error"] = str(e)[:300]
        result["api_data"] = api_data
    finally:
        page.close()

    return result


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    # Targeted URL strategies for each company
    strategies = {
        "4paradigm": [
            {"url": "https://www.4paradigm.com/about/", "click_text": "加入我们"},
            {"url": "https://www.4paradigm.com/careers"},
            {"url": "https://www.4paradigm.com/join"},
            # Try mokahr social recruitment
            {"url": "https://app.mokahr.com/social-recruitment/4paradigm"},
            {"url": "https://app.mokahr.com/apply/4paradigm"},
        ],
        "modelbest": [
            {"url": "https://www.modelbest.cn/about", "click_text": "加入我们"},
            {"url": "https://www.modelbest.cn/joinus"},
            {"url": "https://www.modelbest.cn/careers"},
            {"url": "https://www.modelbest.cn/join-us"},
            {"url": "https://www.modelbest.cn/recruit"},
        ],
        "deepglint": [
            {"url": "https://www.deepglint.com/joinus/", "click_text": "社会招聘"},
            {"url": "https://www.deepglint.com/joinus/", "click_text": "简历投递"},
            {"url": "https://www.deepglint.com/JoinUs/social.html"},
            {"url": "https://www.deepglint.com/JoinUs/campus.html"},
        ],
        "dptechnology": [
            {"url": "https://www.dptechnology.com.cn/careers"},
            {"url": "https://dp.tech/careers"},
            {"url": "https://www.dp.tech/"},
            {"url": "https://www.dptechnology.com.cn/"},
            {"url": "https://www.boyuai.com/"},
        ],
        "geovis": [
            {"url": "https://www.geovis.com.cn/", "click_text": "加入我们"},
            {"url": "https://www.geovis.com.cn/careers"},
            {"url": "https://www.geovis.com.cn/about/"},
            {"url": "https://www.geovis.com.cn/joinus"},
            {"url": "https://www.geovis.com.cn/JoinUs/"},
        ],
        "baichuan": [
            {"url": "https://www.baichuan-ai.com/", "click_text": "社会招聘"},
            {"url": "https://www.baichuan-ai.com/about"},
            {"url": "https://www.baichuan-ai.com/career"},
            {"url": "https://www.baichuan-ai.com/joinus"},
            {"url": "https://www.baichuan-ai.com/about/"},
            {"url": "https://app.mokahr.com/apply/baichuan-ai"},
        ],
        "cambricon": [
            {"url": "https://www.cambricon.com/", "click_text": "加入我们"},
            {"url": "https://www.cambricon.com/joinus"},
            {"url": "https://www.cambricon.com/careers"},
            {"url": "https://www.cambricon.com/about/"},
            {"url": "https://app.mokahr.com/apply/cambricon"},
        ],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        all_results = {}
        for key, url_list in strategies.items():
            print(f"\n{'='*60}")
            print(f"Scraping: {key}")
            print(f"{'='*60}")

            company_results = []
            best_result = None

            for strategy in url_list:
                url = strategy["url"]
                click_text = strategy.get("click_text")
                print(f"  Trying: {url} (click: {click_text})")

                result = scrape_with_navigation(browser, url, click_text)
                company_results.append({
                    "url": url,
                    "click_text": click_text,
                    "status": result["status"],
                    "title": result.get("title", ""),
                    "error": result.get("error", ""),
                    "body_length": len(result.get("body_text", "")),
                })

                # Check if this result has useful content
                body = result.get("body_text", "")
                if result["status"] == "ok" and len(body) > 200:
                    if "页面不存在" not in body and "已关停" not in body:
                        if best_result is None or len(body) > len(best_result.get("body_text", "")):
                            best_result = result
                            print(f"    -> Good! body={len(body)}, api={len(result.get('api_data', []))}, links={len(result.get('links', []))}")

                # Save API data from all attempts
                if not best_result:
                    best_result = result

            # Save the best result with full data
            final_result = {
                "company": key,
                "best_result": {
                    "url": best_result.get("url", ""),
                    "title": best_result.get("title", ""),
                    "body_text": best_result.get("body_text", "")[:20000],
                    "api_data": best_result.get("api_data", []),
                    "links": best_result.get("links", []),
                },
                "all_attempts": company_results,
            }

            filepath = f"/pulp/find-job/r44_{key}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, ensure_ascii=False, indent=2)
            print(f"  Saved to {filepath}")

            all_results[key] = final_result

        with open("/pulp/find-job/r44_all_results.json", 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
