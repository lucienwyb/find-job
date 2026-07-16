#!/usr/bin/env python3
"""Click Baichuan social recruitment button and capture modal/popup."""
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

            # Click the "社会招聘" button
            btn = page.locator('button.join-button:has-text("社会招聘")')
            if btn.count() > 0:
                print("Found social recruitment button, clicking...")
                btn.first.click(timeout=10000)
                time.sleep(5)

                # Check if a new tab was opened
                pages = browser.pages
                print(f"Pages open: {len(pages)}")
                for i, pg in enumerate(pages):
                    print(f"  Page {i}: {pg.url} - {pg.title()}")

                # Check for modal/popup on current page
                body = page.inner_text("body")
                print(f"\nBody after click (length: {len(body)}):")
                print(body[:3000])

                # Check for iframes
                frames = page.frames
                print(f"\nFrames: {len(frames)}")
                for frame in frames:
                    if frame != page.main_frame:
                        print(f"  Frame: {frame.url}")
                        try:
                            frame_body = frame.inner_text("body")
                            print(f"  Frame body: {frame_body[:1000]}")
                        except:
                            pass

                # Check for modal/dialog elements
                modals = page.locator('[class*="modal"], [class*="dialog"], [class*="popup"], [class*="drawer"], [role="dialog"]')
                print(f"\nModal/dialog elements: {modals.count()}")
                for i in range(min(modals.count(), 3)):
                    try:
                        modal_text = modals.nth(i).inner_text()
                        print(f"  Modal {i}: {modal_text[:500]}")
                    except:
                        pass

                # Check all links on page after click
                links = page.eval_on_selector_all("a[href]", """
                    elements => elements.map(e => ({text: e.innerText.trim(), href: e.href}))
                """)
                new_links = [l for l in links if any(k in l.get('href','').lower() for k in ['job','career','recruit','position','join'])]
                if new_links:
                    print(f"\nNew career links:")
                    for nl in new_links:
                        print(f"  [{nl['text'][:60]}] -> {nl['href'][:100]}")

                # Look for any visible job listings
                job_elements = page.locator('[class*="job"], [class*="position"], [class*="vacancy"]')
                print(f"\nJob elements: {job_elements.count()}")
                for i in range(min(job_elements.count(), 10)):
                    try:
                        text = job_elements.nth(i).inner_text()
                        if text.strip():
                            print(f"  Job {i}: {text[:200]}")
                    except:
                        pass

            else:
                print("Button not found!")
                # Try clicking by text
                page.get_by_text("社会招聘").click()
                time.sleep(3)
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
            except:
                print(f"    Body: {api['body'][:200]}")

        # Save result
        result = {
            "company": "baichuan",
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
