#!/usr/bin/env python3
"""Intercept JSON.parse to capture decrypted mokahr job data."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

PORTALS = [
    ("moonshot", "apply", "moonshot", "148506"),
    ("yinhe", "social-recruitment", "yinhetongyong", "165929"),
    ("zhipu", "social-recruitment", "zphz", "148983"),
]

async def check(browser, name, route_type, company, portal_id):
    print(f"\n{'='*60}")
    print(f"{name} - Mokahr (JSON.parse intercept)")
    url = f"https://app.mokahr.com/{route_type}/{company}/{portal_id}"

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1920,"height":1080})
    page = await ctx.new_page()

    # Inject script to capture all JSON.parse results that contain job data
    await page.add_init_script("""
        window.__CAPTURED_JOBS__ = [];
        const origParse = JSON.parse;
        JSON.parse = function(text) {
            const result = origParse.apply(this, arguments);
            try {
                // Check if result contains job data
                const str = JSON.stringify(result);
                // Look for job-like patterns: arrays of objects with 'title' and 'id' or 'jobId'
                if (str.includes('"title"') && (str.includes('"id"') || str.includes('"jobId"'))) {
                    // Also check for UUID patterns
                    if (str.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i)) {
                        window.__CAPTURED_JOBS__.push(str.substring(0, 200000));
                    }
                }
            } catch(e) {}
            return result;
        };
    """)

    try:
        await page.goto(url, timeout=45000, wait_until="networkidle")
    except:
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  goto err: {e}")
    await page.wait_for_timeout(5000)

    # Also try to extract from DOM
    dom_jobs = await page.evaluate("""
        () => {
            const results = [];
            const links = document.querySelectorAll('a[href]');
            for (const a of links) {
                const href = a.getAttribute('href') || '';
                const text = a.textContent.trim();
                const m = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                if (m && text && text.length > 2) {
                    results.push({title: text, jobId: m[1]});
                }
            }
            return results;
        }
    """)

    # Get captured data
    captured = await page.evaluate("() => window.__CAPTURED_JOBS__ || []")
    print(f"  DOM jobs: {len(dom_jobs)}, Captured JSON blobs: {len(captured)}", flush=True)

    # Parse captured data to find job lists
    all_ids = set()
    all_jobs = []

    # First add DOM jobs
    for j in dom_jobs:
        jid = j.get('jobId', '')
        if jid and jid not in all_ids:
            all_ids.add(jid)
            j['title'] = re.sub(r'^急', '', j.get('title', '').strip())
            all_jobs.append(j)

    # Then parse captured JSON
    for blob in captured:
        try:
            data = json.loads(blob)
            # Recursively search for job-like arrays
            def find_jobs(obj, depth=0):
                if depth > 5:
                    return
                if isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, dict):
                            title = item.get('title', '')
                            jid = item.get('id', '') or item.get('jobId', '')
                            if title and jid and isinstance(jid, str) and len(jid) > 5:
                                if jid not in all_ids:
                                    all_ids.add(jid)
                                    all_jobs.append({'title': title, 'jobId': jid})
                            # Also recurse into nested objects
                            find_jobs(item, depth+1)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        find_jobs(v, depth+1)
            find_jobs(data)
        except:
            pass

    print(f"  Total unique jobs: {len(all_jobs)}")

    # Now try clicking the job tab and waiting for more data
    for tab_text in ['社招职位', '职位列表', '社招', '职位']:
        try:
            clicked = await page.evaluate(f"""
                (text) => {{
                    const els = document.querySelectorAll('a, button, span, li');
                    for (const el of els) {{
                        if (el.textContent.trim() === text && el.children.length === 0) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, tab_text)
            if clicked:
                print(f"  Clicked: {tab_text}", flush=True)
                await page.wait_for_timeout(5000)

                # Check for new captured data
                new_captured = await page.evaluate("() => window.__CAPTURED_JOBS__ || []")
                new_dom = await page.evaluate("""
                    () => {
                        const results = [];
                        const links = document.querySelectorAll('a[href]');
                        for (const a of links) {
                            const href = a.getAttribute('href') || '';
                            const text = a.textContent.trim();
                            const m = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                            if (m && text && text.length > 2) {
                                results.push({title: text, jobId: m[1]});
                            }
                        }
                        return results;
                    }
                """)

                for j in new_dom:
                    jid = j.get('jobId', '')
                    if jid and jid not in all_ids:
                        all_ids.add(jid)
                        j['title'] = re.sub(r'^急', '', j.get('title', '').strip())
                        all_jobs.append(j)

                for blob in new_captured:
                    try:
                        data = json.loads(blob)
                        def find_jobs(obj, depth=0):
                            if depth > 5: return
                            if isinstance(obj, list):
                                for item in obj:
                                    if isinstance(item, dict):
                                        title = item.get('title', '')
                                        jid = item.get('id', '') or item.get('jobId', '')
                                        if title and jid and isinstance(jid, str) and len(jid) > 5:
                                            if jid not in all_ids:
                                                all_ids.add(jid)
                                                all_jobs.append({'title': title, 'jobId': jid})
                                        find_jobs(item, depth+1)
                            elif isinstance(obj, dict):
                                for v in obj.values():
                                    find_jobs(v, depth+1)
                        find_jobs(data)
                    except:
                        pass

                print(f"  After {tab_text}: {len(all_jobs)} jobs", flush=True)
                break
        except:
            continue

    # Try pagination
    for pg in range(2, 50):
        prev = len(all_jobs)
        clicked = await page.evaluate(f"""
            (pgNum) => {{
                const els = document.querySelectorAll('a, button, li, span');
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
            break
        await page.wait_for_timeout(2500)

        new_dom = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href]');
                for (const a of links) {
                    const href = a.getAttribute('href') || '';
                    const text = a.textContent.trim();
                    const m = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                    if (m && text && text.length > 2) {
                        results.push({title: text, jobId: m[1]});
                    }
                }
                return results;
            }
        """)
        for j in new_dom:
            jid = j.get('jobId', '')
            if jid and jid not in all_ids:
                all_ids.add(jid)
                j['title'] = re.sub(r'^急', '', j.get('title', '').strip())
                all_jobs.append(j)

        if len(all_jobs) == prev:
            break
        print(f"  Page {pg}: total={len(all_jobs)}", flush=True)

    print(f"  FINAL: {len(all_jobs)} unique jobs")
    await ctx.close()
    return all_jobs


async def main():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY})
        for name, route_type, company, portal_id in PORTALS:
            try:
                jobs = await check(browser, name, route_type, company, portal_id)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []
        await browser.close()

    with open('/pulp/find-job/r81_mokahr_intercept.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Quick comparison
    with open('snapshot_2026-07-16.json') as f:
        baseline = json.load(f)
    for company in ['moonshot','yinhe','zhipu']:
        b_ids = set(j.get('jobId','') for j in baseline.get(company,[]) if j.get('jobId'))
        n_ids = set(j.get('jobId','') for j in results.get(company,[]) if j.get('jobId'))
        added = n_ids - b_ids
        print(f"\n{company}: baseline={len(b_ids)}, new_scan={len(n_ids)}, ADDED={len(added)}")
        if added:
            for jid in added:
                job = next((j for j in results[company] if j.get('jobId')==jid), None)
                if job:
                    print(f"  NEW: {job.get('title','')[:50]} | {jid}")

    print("\n=== Saved ===")

asyncio.run(main())
