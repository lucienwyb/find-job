#!/usr/bin/env python3
"""Click 社招职位 tab first, then extract all jobs with pagination."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

PORTALS = [
    ("moonshot", "apply", "moonshot", "148506", ["社招职位", "社招", "职位"]),
    ("yinhe", "social-recruitment", "yinhetongyong", "165929", ["社招职位", "社招", "职位"]),
    ("zhipu", "social-recruitment", "zphz", "148983", ["职位列表", "职位", "社招"]),
]

async def check(browser, name, route_type, company, portal_id, tab_texts):
    print(f"\n{'='*60}")
    print(f"{name} - Mokahr")
    url = f"https://app.mokahr.com/{route_type}/{company}/{portal_id}"

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1920,"height":1080})
    page = await ctx.new_page()

    all_ids = set()
    all_jobs = []

    async def extract():
        return await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href]');
                for (const a of links) {
                    const href = a.getAttribute('href') || '';
                    const text = a.textContent.trim();
                    const m = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                    if (m && text && text.length > 2 && text.length < 100) {
                        results.push({title: text, jobId: m[1], href: href});
                    }
                }
                return results;
            }
        """)

    async def collect():
        jobs = await extract()
        n = 0
        for j in jobs:
            jid = j.get('jobId', '')
            if jid and jid not in all_ids:
                all_ids.add(jid)
                j['title'] = re.sub(r'^急', '', j.get('title', '').strip())
                all_jobs.append(j)
                n += 1
        return n

    try:
        await page.goto(url, timeout=45000, wait_until="networkidle")
    except:
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  goto err: {e}")
    await page.wait_for_timeout(3000)

    # Click the job listing tab
    for tab_text in tab_texts:
        try:
            # Try clicking by text
            clicked = await page.evaluate(f"""
                (text) => {{
                    const els = document.querySelectorAll('a, button, span, div, li');
                    for (const el of els) {{
                        if (el.textContent.trim() === text && el.children.length === 0) {{
                            el.click();
                            return true;
                        }}
                    }}
                    // Also try partial match
                    for (const el of els) {{
                        if (el.textContent.trim().includes(text) && el.children.length <= 1 && el.textContent.trim().length < 20) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, tab_text)
            if clicked:
                print(f"  Clicked tab: {tab_text}", flush=True)
                await page.wait_for_timeout(4000)
                break
        except:
            continue

    n = await collect()
    print(f"  After tab click: {len(all_jobs)} jobs", flush=True)

    # Try pagination by clicking page numbers
    for pg in range(2, 50):
        prev = len(all_jobs)
        # Try clicking page number
        clicked = await page.evaluate(f"""
            (pgNum) => {{
                const els = document.querySelectorAll('a, button, li, span, div');
                for (const el of els) {{
                    if (el.textContent.trim() === String(pgNum) && el.children.length === 0) {{
                        el.click();
                        return true;
                    }}
                }}
                return false;
            }}
        """, pg)

        if not clicked:
            # Try next button
            for text in ['下一页', '>', '下一页>', 'Next']:
                clicked = await page.evaluate(f"""
                    (text) => {{
                        const els = document.querySelectorAll('a, button, li');
                        for (const el of els) {{
                            if (el.textContent.trim().includes(text) && el.textContent.trim().length < 10) {{
                                el.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """, text)
                if clicked:
                    break

        if not clicked:
            print(f"  No pagination at pg {pg}", flush=True)
            break

        await page.wait_for_timeout(2500)
        n = await collect()
        if n == 0:
            print(f"  No new jobs at pg {pg}, stopping", flush=True)
            break
        print(f"  Page {pg}: +{n}, total={len(all_jobs)}", flush=True)

    # Also try scrolling
    for _ in range(5):
        try:
            await page.evaluate("""
                () => {
                    const containers = [
                        document.querySelector('[class*="job-list"]'),
                        document.querySelector('[class*="position"]'),
                        document.querySelector('[class*="list"]'),
                        document.querySelector('main'),
                        document.body
                    ];
                    for (const c of containers) {
                        if (c) c.scrollTop = c.scrollHeight;
                    }
                    window.scrollTo(0, document.body.scrollHeight);
                }
            """)
            await page.wait_for_timeout(1500)
            n = await collect()
            if n == 0:
                break
            print(f"  Scroll: +{n}, total={len(all_jobs)}", flush=True)
        except:
            break

    print(f"  TOTAL: {len(all_jobs)} unique jobs")
    await ctx.close()
    return all_jobs


async def main():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY})
        for name, route_type, company, portal_id, tabs in PORTALS:
            try:
                jobs = await check(browser, name, route_type, company, portal_id, tabs)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []
        await browser.close()

    with open('/pulp/find-job/r81_mokahr_tabs.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n=== Saved ===")

asyncio.run(main())
