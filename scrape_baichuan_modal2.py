#!/usr/bin/env python3
"""Click Baichuan social recruitment button and capture popup."""
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

        context = browser.new_context()
        page = context.new_page()
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

        # Listen for new pages (popups)
        popup_urls = []
        def handle_popup(popup_page):
            popup_urls.append(popup_page.url)
            print(f"  Popup opened: {popup_page.url}")
            popup_page.on("response", handle_response)
            time.sleep(3)
            try:
                print(f"  Popup title: {popup_page.title()}")
                popup_body = popup_page.inner_text("body")
                print(f"  Popup body: {popup_body[:2000]}")
            except:
                pass

        context.on("page", handle_popup)

        body = ""
        try:
            page.goto("https://www.baichuan-ai.com/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(5)

            # Click the "社会招聘" button
            btn = page.locator('button.join-button:has-text("社会招聘")')
            if btn.count() > 0:
                print("Found social recruitment button, clicking...")
                btn.first.click(timeout=10000)
                time.sleep(8)  # Wait for popup or modal

                # Check current page body
                body = page.inner_text("body")
                print(f"\nBody after click (length: {len(body)}):")
                print(body[:3000])

                # Check for modal/dialog elements
                modals = page.locator('[class*="modal"], [class*="dialog"], [class*="popup"], [class*="drawer"], [role="dialog"], [class*="overlay"]')
                print(f"\nModal/dialog elements: {modals.count()}")
                for i in range(min(modals.count(), 5)):
                    try:
                        modal_text = modals.nth(i).inner_text()
                        if modal_text.strip():
                            print(f"  Modal {i}: {modal_text[:500]}")
                    except:
                        pass

                # Check all visible text for job listings
                all_text = page.evaluate("document.body.innerText")
                # Look for job-related text
                lines = all_text.split('\n')
                job_lines = [l for l in lines if any(k in l for k in ['工程师', '开发', '算法', '架构', 'Infra', '系统', '平台', '运维', '测试', '前端', '后端', '产品', '经理', '实习'])]
                if job_lines:
                    print(f"\nJob-related text found ({len(job_lines)} lines):")
                    for line in job_lines[:30]:
                        print(f"  {line.strip()[:100]}")

                # Check for any new elements that appeared after click
                # Try to find job listing elements
                job_selectors = [
                    '[class*="job-item"]', '[class*="position-item"]', '[class*="job-list"]',
                    '[class*="position-list"]', '[class*="recruit"]', '[class*="career"]',
                    '[class*="vacancy"]', '.job-card', '.position-card',
                ]
                for sel in job_selectors:
                    try:
                        els = page.locator(sel)
                        if els.count() > 0:
                            print(f"\n  Found {els.count()} elements with selector: {sel}")
                            for i in range(min(els.count(), 5)):
                                print(f"    {els.nth(i).inner_text()[:200]}")
                    except:
                        pass

            else:
                print("Button not found, trying text click...")
                page.get_by_text("社会招聘").first.click()
                time.sleep(5)
                body = page.inner_text("body")
                print(f"Body after text click: {body[:2000]}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        # Print all API calls
        print(f"\n=== API calls captured ({len(api_data)}) ===")
        for api in api_data:
            print(f"  {api['url'][:200]}")
            try:
                d = json.loads(api['body'])
                if isinstance(d, dict):
                    print(f"    Keys: {list(d.keys())[:15]}")
                    # Look for job-related data
                    s = json.dumps(d)
                    if any(k in s.lower() for k in ['job', 'position', 'recruit', 'hire']):
                        print(f"    Contains job data!")
                        print(f"    Data: {s[:500]}")
            except:
                print(f"    Body: {api['body'][:200]}")

        # Save result
        result = {
            "company": "baichuan",
            "popup_urls": popup_urls,
            "api_data": api_data,
            "body_text": body[:20000] if body else "",
        }
        with open("/pulp/find-job/r44_baichuan.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        page.close()
        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
