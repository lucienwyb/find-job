#!/usr/bin/env python3
"""Get ALL mokahr jobIds by scrolling through every page and extracting from DOM."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

MOKAHR_PORTALS = [
    ("moonshot", "apply", "moonshot", "148506"),
    ("yinhe", "social-recruitment", "yinhetongyong", "165929"),
    ("zhipu", "social-recruitment", "zphz", "148983"),
    ("cambricon", "apply", "cambricon", "1113"),
]

async def check_mokahr(browser, name, route_type, company, portal_id):
    print(f"\n{'='*60}")
    print(f"{name} - Mokahr (all pages)")
    url = f"https://app.mokahr.com/{route_type}/{company}/{portal_id}"

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1920,"height":1080})
    page = await ctx.new_page()

    all_job_ids = set()
    all_jobs = []

    try:
        await page.goto(url, timeout=45000, wait_until="networkidle")
    except:
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  goto err: {e}")

    await page.wait_for_timeout(3000)

    # Extract all links with UUID (jobId) from the entire page
    async def extract_all_links():
        return await page.evaluate("""
            () => {
                const results = [];
                // Get ALL anchor elements on the page
                const links = document.querySelectorAll('a[href]');
                for (const a of links) {
                    const href = a.getAttribute('href') || '';
                    const text = a.textContent.trim();
                    // Look for UUID pattern in href
                    const uuidMatch = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                    if (uuidMatch) {
                        results.push({title: text, jobId: uuidMatch[1], href: href});
                    }
                }
                // Also check for data attributes on any element
                const allEls = document.querySelectorAll('[data-id], [data-job-id]');
                for (const el of allEls) {
                    const jid = el.getAttribute('data-id') || el.getAttribute('data-job-id') || '';
                    if (jid && jid.length > 10) {
                        const title = el.textContent.trim().substring(0, 100);
                        results.push({title, jobId: jid, href: ''});
                    }
                }
                return results;
            }
        """)

    # Extract initial jobs
    jobs = await extract_all_links()
    for j in jobs:
        jid = j.get('jobId', '')
        if jid and jid not in all_job_ids:
            all_job_ids.add(jid)
            all_jobs.append(j)
    print(f"  Initial: {len(all_jobs)} jobs", flush=True)

    # Try to find and click all pagination elements
    # First, let's see what pagination elements exist
    pagination_info = await page.evaluate("""
        () => {
            const info = {buttons: [], pageText: ''};
            // Find pagination container
            const pagSelectors = ['.pagination', '.pager', '[class*="pagination"]', '[class*="pager"]',
                                  '.ant-pagination', '[class*="page-num"]', '[class*="PageNum"]'];
            for (const sel of pagSelectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    info.pageText = els[0].textContent.trim().substring(0, 200);
                    const btns = els[0].querySelectorAll('button, a, li, span');
                    for (const b of btns) {
                        info.buttons.push({text: b.textContent.trim(), tag: b.tagName, class: b.className.substring(0, 50)});
                    }
                    break;
                }
            }
            // Also look for any clickable elements with page numbers
            const numEls = document.querySelectorAll('[class*="page"]');
            for (const el of numEls) {
                const t = el.textContent.trim();
                if (/^\d+$/.test(t)) {
                    info.buttons.push({text: t, tag: el.tagName, class: el.className.substring(0, 50)});
                }
            }
            return info;
        }
    """)
    print(f"  Pagination: {pagination_info.get('pageText','')[:100]}", flush=True)
    if pagination_info.get('buttons'):
        btn_texts = [b['text'] for b in pagination_info['buttons'] if b['text']]
        print(f"  Pagination buttons: {btn_texts[:20]}", flush=True)

    # Try clicking each page number sequentially
    max_page = 30
    for pg in range(2, max_page):
        prev_count = len(all_jobs)
        clicked = False

        # Try multiple strategies to click the page number
        strategies = [
            f"li[class*='page']:has-text('{pg}')",
            f"button:has-text('{pg}')",
            f"a:has-text('{pg}')",
            f"text={pg}",
        ]

        for strategy in strategies:
            try:
                # Use a more specific selector
                btn = await page.query_selector(strategy)
                if btn:
                    await btn.click()
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            # Try using JavaScript to click
            clicked = await page.evaluate(f"""
                (pgNum) => {{
                    // Find elements with exact text matching the page number
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                    while (walker.nextNode()) {{
                        const el = walker.currentNode;
                        const text = el.textContent.trim();
                        if (text === String(pgNum) && el.children.length === 0) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, pg)

        if not clicked:
            # Try next button
            for sel in ["button:has-text('下一页')", "[aria-label='next']", "li.ant-pagination-next",
                        "[class*='next-btn']", "button[class*='next']"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        clicked = True
                        break
                except:
                    continue

        if not clicked:
            print(f"  No pagination found at pg {pg}", flush=True)
            break

        await page.wait_for_timeout(2500)

        # Extract jobs from new page
        jobs = await extract_all_links()
        new_count = 0
        for j in jobs:
            jid = j.get('jobId', '')
            if jid and jid not in all_job_ids:
                all_job_ids.add(jid)
                all_jobs.append(j)
                new_count += 1

        if new_count == 0:
            print(f"  No new jobs at pg {pg}, stopping", flush=True)
            break
        print(f"  Page {pg}: +{new_count}, total={len(all_jobs)}", flush=True)

    # Clean up titles
    for j in all_jobs:
        j['title'] = re.sub(r'^急', '', j.get('title', '').strip())

    print(f"  TOTAL: {len(all_jobs)} unique jobs with jobIds")
    return all_jobs


async def main():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY})
        for name, route_type, company, portal_id in MOKAHR_PORTALS:
            try:
                jobs = await check_mokahr(browser, name, route_type, company, portal_id)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []
        await browser.close()

    with open('/pulp/find-job/r81_mokahr_all.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n=== Saved to r81_mokahr_all.json ===")

asyncio.run(main())
