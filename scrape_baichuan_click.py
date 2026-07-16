#!/usr/bin/env python3
"""Try clicking career links on Baichuan page and access BOSS直聘."""
import json
import os
import time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        # === BAICHUAN: Click on social recruitment ===
        print("="*60)
        print("BAICHUAN: Clicking career links")
        print("="*60)

        page = browser.new_page()
        api_data = []

        def handle_response(response):
            try:
                ct = response.headers.get('content-type', '')
                if 'json' in ct:
                    body = response.text()
                    if body and len(body) > 100:
                        api_data.append({'url': response.url[:500], 'body': body[:50000]})
            except:
                pass

        page.on("response", handle_response)

        try:
            page.goto("https://www.baichuan-ai.com/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(5)

            # Try to find and click "社会招聘"
            print("Looking for 社会招聘 link/button...")
            try:
                # Try different approaches
                selectors = [
                    'text=社会招聘',
                    'a:has-text("社会招聘")',
                    'button:has-text("社会招聘")',
                    '[class*="recruit"]',
                    '[class*="career"]',
                    '[class*="join"]',
                ]
                for sel in selectors:
                    try:
                        el = page.locator(sel)
                        if el.count() > 0:
                            print(f"  Found with selector: {sel}")
                            text = el.first.inner_text()
                            href = el.first.get_attribute('href') or ''
                            print(f"    Text: {text[:100]}, href: {href}")
                            el.first.click(timeout=5000)
                            time.sleep(5)
                            print(f"    After click - URL: {page.url}")
                            print(f"    Title: {page.title()}")
                            break
                    except:
                        pass

                # Also try looking at all elements containing "社会招聘"
                elements = page.eval_on_selector_all("*", """
                    elements => {
                        return elements.filter(e => e.innerText && e.innerText.trim() === '社会招聘')
                            .map(e => ({tag: e.tagName, class: e.className, href: e.href || '', onclick: e.onclick ? 'has_onclick' : ''}))
                    }
                """)
                if elements:
                    print(f"  Found elements with '社会招聘': {json.dumps(elements, ensure_ascii=False)[:500]}")

            except Exception as e:
                print(f"  Error clicking: {e}")

            # Also try navigating directly to possible career URLs
            for url in [
                "https://www.baichuan-ai.com/join-us",
                "https://www.baichuan-ai.com/joinus",
                "https://www.baichuan-ai.com/careers",
                "https://www.baichuan-ai.com/recruitment",
                "https://www.baichuan-ai.com/about-us",
                "https://www.baichuan-ai.com/about/join",
            ]:
                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    if resp and resp.status == 200:
                        body = page.inner_text("body")
                        if len(body) > 200 and "404" not in page.title():
                            print(f"  Found career page: {url}")
                            print(f"    Title: {page.title()}")
                            print(f"    Body: {body[:500]}")
                            break
                except:
                    pass

            # Get all links from the page
            try:
                links = page.eval_on_selector_all("a[href]", """
                    elements => elements.map(e => ({text: e.innerText.trim(), href: e.href}))
                """)
                for link in links:
                    if any(k in (link.get('text','') + link.get('href','')).lower() for k in ['recruit','career','job','join','社招','招聘']):
                        print(f"  Career link: [{link['text'][:60]}] -> {link['href'][:100]}")
            except:
                pass

            body_text = page.inner_text("body")
            baichuan_result = {
                "company": "baichuan",
                "url": page.url,
                "title": page.title(),
                "body_text": body_text[:20000],
                "api_data": api_data,
            }
        except Exception as e:
            print(f"  Error: {e}")
            baichuan_result = {"company": "baichuan", "error": str(e)[:300]}

        page.close()

        with open("/pulp/find-job/r44_baichuan.json", 'w', encoding='utf-8') as f:
            json.dump(baichuan_result, f, ensure_ascii=False, indent=2)
        print("Saved baichuan")

        # === 4PARADIGM: Try BOSS直聘 and other platforms ===
        print("\n" + "="*60)
        print("4PARADIGM: Trying BOSS直聘")
        print("="*60)

        page = browser.new_page()
        api_data_4p = []

        def handle_resp_4p(response):
            try:
                ct = response.headers.get('content-type', '')
                if 'json' in ct:
                    body = response.text()
                    if body and len(body) > 100:
                        api_data_4p.append({'url': response.url[:500], 'body': body[:50000]})
            except:
                pass

        page.on("response", handle_resp_4p)

        try:
            page.goto("https://www.zhipin.com/web/geek/job?query=第四范式&city=101010100", wait_until="domcontentloaded", timeout=45000)
            time.sleep(8)
            print(f"  Title: {page.title()}")
            body = page.inner_text("body")
            print(f"  Body length: {len(body)}")
            print(f"  Body: {body[:1000]}")

            # Get links
            links = page.eval_on_selector_all("a[href]", """
                elements => elements.map(e => ({text: e.innerText.trim(), href: e.href}))
            """)
            job_links = [l for l in links if any(k in l.get('href','') for k in ['job', 'position'])]
            print(f"  Job links: {len(job_links)}")
            for jl in job_links[:10]:
                print(f"    [{jl['text'][:60]}] -> {jl['href'][:100]}")

        except Exception as e:
            print(f"  Error: {e}")

        page.close()

        # Also try Liepin for 4Paradigm
        try:
            page = browser.new_page()
            page.goto("https://www.liepin.com/zhaopin/?key=第四范式&dqs=010", wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)
            body = page.inner_text("body")
            print(f"\n  Liepin body length: {len(body)}")
            print(f"  Liepin body: {body[:500]}")
            page.close()
        except Exception as e:
            print(f"  Liepin error: {e}")

        # Save 4paradigm
        parad_result = {
            "company": "4paradigm",
            "website_status": "under renovation (官网焕新升级中)",
            "boss_zhipin": "attempted",
            "body_text": body[:5000] if body else "",
        }
        with open("/pulp/find-job/r44_4paradigm.json", 'w', encoding='utf-8') as f:
            json.dump(parad_result, f, ensure_ascii=False, indent=2)
        print("Saved 4paradigm")

        # === MODELBEST: Try BOSS直聘 ===
        print("\n" + "="*60)
        print("MODELBEST: Trying BOSS直聘")
        print("="*60)

        page = browser.new_page()
        try:
            page.goto("https://www.zhipin.com/web/geek/job?query=面壁智能&city=101010100", wait_until="domcontentloaded", timeout=45000)
            time.sleep(8)
            print(f"  Title: {page.title()}")
            body = page.inner_text("body")
            print(f"  Body length: {len(body)}")
            print(f"  Body: {body[:1000]}")
        except Exception as e:
            print(f"  Error: {e}")
            body = ""

        page.close()

        modelbest_result = {
            "company": "modelbest",
            "official_site": "modelbest.cn (no career portal)",
            "contact_email": "career@modelbest.cn",
            "boss_zhipin_body": body[:5000] if body else "",
        }
        with open("/pulp/find-job/r44_modelbest.json", 'w', encoding='utf-8') as f:
            json.dump(modelbest_result, f, ensure_ascii=False, indent=2)
        print("Saved modelbest")

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
