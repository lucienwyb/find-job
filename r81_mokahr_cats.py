#!/usr/bin/env python3
"""Get all mokahr jobs by clicking through category tabs and scrolling."""
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
]

async def check_mokahr(browser, name, route_type, company, portal_id):
    print(f"\n{'='*60}")
    print(f"{name} - Mokahr (categories + scroll)")
    url = f"https://app.mokahr.com/{route_type}/{company}/{portal_id}"

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1920,"height":1080})
    page = await ctx.new_page()

    all_job_ids = set()
    all_jobs = []

    async def extract_links():
        return await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href]');
                for (const a of links) {
                    const href = a.getAttribute('href') || '';
                    const text = a.textContent.trim();
                    const uuidMatch = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                    if (uuidMatch && text && text.length > 2) {
                        results.push({title: text, jobId: uuidMatch[1], href: href});
                    }
                }
                return results;
            }
        """)

    async def collect():
        jobs = await extract_links()
        new_count = 0
        for j in jobs:
            jid = j.get('jobId', '')
            if jid and jid not in all_job_ids:
                all_job_ids.add(jid)
                j['title'] = re.sub(r'^急', '', j.get('title', '').strip())
                all_jobs.append(j)
                new_count += 1
        return new_count

    try:
        await page.goto(url, timeout=45000, wait_until="networkidle")
    except:
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  goto err: {e}")

    await page.wait_for_timeout(3000)
    n = await collect()
    print(f"  Initial: {len(all_jobs)} jobs", flush=True)

    # 1. Try clicking each category/department tab
    tabs = await page.evaluate("""
        () => {
            const tabs = [];
            // Look for tab-like elements
            const tabSels = [
                '[class*="tab"]', '[class*="category"]', '[class*="filter"]',
                '[class*="dept"]', '[class*="group"]', '[role="tab"]',
                '.ant-tabs-tab', '[class*="Tag"]', '[class*="menu-item"]'
            ];
            for (const sel of tabSels) {
                const els = document.querySelectorAll(sel);
                for (const el of els) {
                    const text = el.textContent.trim();
                    if (text && text.length > 0 && text.length < 40 && el.children.length <= 2) {
                        tabs.push({text: text, tag: el.tagName, class: el.className.substring(0, 60)});
                    }
                }
            }
            // Deduplicate
            const seen = new Set();
            return tabs.filter(t => {
                if (seen.has(t.text)) return false;
                seen.add(t.text);
                return true;
            }).slice(0, 30);
        }
    """)
    if tabs:
        print(f"  Found {len(tabs)} tab-like elements: {[t['text'][:15] for t in tabs[:10]]}", flush=True)

    # Click through tabs
    for tab in tabs[:20]:
        try:
            # Try to find and click the tab
            clicked = await page.evaluate(f"""
                (tabText) => {{
                    const els = document.querySelectorAll('[class*="tab"], [class*="category"], [class*="filter"], [class*="dept"], [class*="group"], [role="tab"], .ant-tabs-tab');
                    for (const el of els) {{
                        if (el.textContent.trim() === tabText) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, tab['text'])
            if clicked:
                await page.wait_for_timeout(2000)
                n = await collect()
                if n > 0:
                    print(f"  Tab '{tab['text'][:20]}': +{n}, total={len(all_jobs)}", flush=True)
        except:
            continue

    # 2. Try scrolling in the job list container
    for _ in range(10):
        try:
            # Scroll the main content area
            await page.evaluate("""
                () => {
                    // Try scrolling various containers
                    const containers = [
                        document.querySelector('[class*="job-list"]'),
                        document.querySelector('[class*="position-list"]'),
                        document.querySelector('[class*="recruit"]'),
                        document.querySelector('.ant-layout-content'),
                        document.querySelector('main'),
                        document.body
                    ];
                    for (const c of containers) {
                        if (c) {
                            c.scrollTop = c.scrollHeight;
                        }
                    }
                    window.scrollTo(0, document.body.scrollHeight);
                }
            """)
            await page.wait_for_timeout(1500)
            n = await collect()
            if n > 0:
                print(f"  Scroll: +{n}, total={len(all_jobs)}", flush=True)
            else:
                break
        except:
            break

    # 3. Try URL with page parameter
    for pg in range(2, 20):
        try:
            new_url = f"{url}?page={pg}"
            await page.goto(new_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            n = await collect()
            if n == 0:
                break
            print(f"  URL page {pg}: +{n}, total={len(all_jobs)}", flush=True)
        except:
            break

    # 4. Try the "全部" (all) view if it exists
    for sel in ["text=全部", "text=全部职位", "text=全部岗位", "a:has-text('全部')", "text=所有职位"]:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await page.wait_for_timeout(3000)
                n = await collect()
                if n > 0:
                    print(f"  '全部' view: +{n}, total={len(all_jobs)}", flush=True)
                break
        except:
            continue

    print(f"  TOTAL: {len(all_jobs)} unique jobs")
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

    with open('/pulp/find-job/r81_mokahr_cats.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n=== Saved ===")

asyncio.run(main())
