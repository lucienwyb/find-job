#!/usr/bin/env python3
"""Try BOSS直聘 and other platforms for Baichuan, 4Paradigm, ModelBest."""
import json
import os
import time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"


def scrape_page(browser, url, wait=8):
    """Scrape a page capturing API responses and body text."""
    api_data = []
    page = browser.new_page()

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            url_lower = response.url.lower()
            if 'json' in ct or 'json' in url_lower:
                body = response.text()
                if body and len(body) > 100:
                    api_data.append({
                        'url': response.url[:500],
                        'body': body[:50000]
                    })
        except:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(wait)

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
            "status": "ok",
            "title": title,
            "body_text": body_text[:30000],
            "links": links[:300],
            "api_data": api_data,
        }
    except Exception as e:
        page.close()
        return {
            "status": "error",
            "error": str(e)[:300],
            "body_text": "",
            "links": [],
            "api_data": api_data,
        }


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    targets = [
        # Baichuan - try BOSS直聘 and mokahr
        ("baichuan", [
            "https://www.zhipin.com/gongsi/baichuan-ai.html",
            "https://www.zhipin.com/web/geek/job?query=百川智能&city=101010100",
            "https://app.mokahr.com/apply/baichuan",
            "https://app.mokahr.com/apply/baichuansmart",
            "https://www.baichuan-ai.com/about",
        ]),
        # 4Paradigm - try careers page and BOSS直聘
        ("4paradigm", [
            "https://www.4paradigm.com/careers",
            "https://www.zhipin.com/gongsi/4paradigm.html",
            "https://www.zhipin.com/web/geek/job?query=第四范式&city=101010100",
        ]),
        # ModelBest - try BOSS直聘
        ("modelbest", [
            "https://www.zhipin.com/gongsi/modelbest.html",
            "https://www.zhipin.com/web/geek/job?query=面壁智能&city=101010100",
            "https://www.modelbest.cn/joinus",
            "https://www.modelbest.cn/about",
        ]),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        for key, urls in targets:
            print(f"\n{'='*60}")
            print(f"Scraping: {key}")
            print(f"{'='*60}")

            best_result = None
            all_results = []

            for url in urls:
                print(f"  Trying: {url[:80]}")
                result = scrape_page(browser, url, wait=8)
                all_results.append({
                    "url": url,
                    "status": result["status"],
                    "title": result.get("title", ""),
                    "body_length": len(result.get("body_text", "")),
                    "error": result.get("error", ""),
                })

                if result["status"] == "ok" and len(result.get("body_text", "")) > 500:
                    if best_result is None or len(result["body_text"]) > len(best_result.get("body_text", "")):
                        best_result = result
                        print(f"    -> Good! body={len(result['body_text'])}, api={len(result.get('api_data',[]))}")

                # Show career links
                links = result.get("links", [])
                career_links = [l for l in links if any(k in (l.get('text','') + l.get('href','')).lower()
                    for k in ['join','career','job','recruit','社招','校招','招聘','加入','talent','hire','position','职位','工程师','开发','kernel','系统','infra'])]
                if career_links:
                    print(f"    Career links ({len(career_links)}):")
                    for cl in career_links[:15]:
                        print(f"      [{cl['text'][:60]}] -> {cl['href'][:100]}")

                # Show API data
                for api in result.get("api_data", []):
                    if any(k in api["url"].lower() for k in ['job', 'position', 'recruit', 'search']):
                        print(f"    API: {api['url'][:150]}")
                        try:
                            d = json.loads(api["body"])
                            if isinstance(d, dict):
                                print(f"      Keys: {list(d.keys())[:15]}")
                        except:
                            print(f"      Body: {api['body'][:200]}")

            # Save best result
            if best_result is None:
                best_result = {"body_text": "", "links": [], "api_data": [], "title": ""}

            output = {
                "company": key,
                "best_result": {
                    "title": best_result.get("title", ""),
                    "body_text": best_result.get("body_text", "")[:20000],
                    "links": best_result.get("links", [])[:200],
                    "api_data": best_result.get("api_data", [])[:20],
                },
                "all_attempts": all_results,
            }

            filepath = f"/pulp/find-job/r44_{key}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved to {filepath}")

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
