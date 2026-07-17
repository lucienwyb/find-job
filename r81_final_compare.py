#!/usr/bin/env python3
"""Final mokahr check: use API fetch + JSON.parse intercept to get ALL jobs."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

PORTALS = [
    ("moonshot", "apply", "moonshot", "148506"),
    ("yinhe", "social-recruitment", "yinhetongyong", "165929"),
]

async def check(browser, name, route_type, company, portal_id):
    print(f"\n{'='*60}")
    print(f"{name} - Mokahr (API + intercept)")
    url = f"https://app.mokahr.com/{route_type}/{company}/{portal_id}"

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1920,"height":1080})
    page = await ctx.new_page()

    # Inject JSON.parse interceptor
    await page.add_init_script("""
        window.__JOBS_DATA__ = [];
        const origParse = JSON.parse;
        JSON.parse = function(text) {
            const result = origParse.apply(this, arguments);
            try {
                const str = JSON.stringify(result);
                if (str.includes('"title"') && str.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i)) {
                    window.__JOBS_DATA__.push(str.substring(0, 500000));
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
    await page.wait_for_timeout(3000)

    # Click the job tab
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
                break
        except:
            continue

    # Get initial captured data
    captured = await page.evaluate("() => window.__JOBS_DATA__ || []")
    print(f"  Initial captured blobs: {len(captured)}", flush=True)

    # Now try making direct API calls with different page_no
    # The API URL pattern: https://app.mokahr.com/api/outer/ats-{route_type}/website/jobs/module
    api_prefix = f"ats-{route_type}" if route_type == "apply" else f"ats-social-recruitment"

    all_ids = set()
    all_jobs = []

    def parse_captured(caps):
        for blob in caps:
            try:
                data = json.loads(blob)
                def find_jobs(obj, depth=0):
                    if depth > 6: return
                    if isinstance(obj, list):
                        for item in obj:
                            if isinstance(item, dict):
                                title = item.get('title', '')
                                jid = item.get('id', '') or item.get('jobId', '')
                                # Only accept UUID-format IDs (actual job IDs)
                                if title and jid and isinstance(jid, str):
                                    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', jid, re.I):
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

    parse_captured(captured)
    print(f"  After initial parse: {len(all_jobs)} jobs", flush=True)

    # Try direct API calls with pagination
    for pg in range(1, 30):
        # Make API call via page's fetch - the JSON.parse intercept will capture the decrypted result
        await page.evaluate(f"""
            async () => {{
                try {{
                    const urls = [
                        'https://app.mokahr.com/api/outer/{api_prefix}/website/jobs/module',
                        'https://app.mokahr.com/api/outer/{api_prefix}/website/group-by-job'
                    ];
                    for (const u of urls) {{
                        try {{
                            const resp = await fetch(u, {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}},
                                credentials: 'include',
                                body: JSON.stringify({{page_no: {pg}, page_size: 30}})
                            }});
                            const text = await resp.text();
                            // The response might be encrypted; the page's JS will decrypt it
                            // But if we call fetch directly, it won't go through the app's decryption
                            // So we need to trigger the app's own pagination
                        }} catch(e) {{}}
                    }}
                }} catch(e) {{}}
            }}
        """)

        await page.wait_for_timeout(1000)

        # Check if new data was captured
        new_captured = await page.evaluate("() => window.__JOBS_DATA__ || []")
        prev_len = len(all_jobs)
        parse_captured(new_captured)
        if len(all_jobs) == prev_len and pg > 1:
            print(f"  No new data at pg {pg}", flush=True)
            break
        print(f"  API pg {pg}: total={len(all_jobs)}", flush=True)

    # Also try clicking page numbers
    for pg in range(2, 30):
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

        new_captured = await page.evaluate("() => window.__JOBS_DATA__ || []")
        parse_captured(new_captured)

        # Also extract from DOM
        dom = await page.evaluate("""
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
        for j in dom:
            jid = j.get('jobId','')
            if jid and jid not in all_ids:
                all_ids.add(jid)
                j['title'] = re.sub(r'^急', '', j.get('title','').strip())
                all_jobs.append(j)

        if len(all_jobs) == prev:
            break
        print(f"  Click pg {pg}: total={len(all_jobs)}", flush=True)

    print(f"  FINAL: {len(all_jobs)} jobs")

    # Compare with baseline
    with open('/pulp/find-job/snapshot_2026-07-16.json') as f:
        baseline = json.load(f)
    b_ids = set(j.get('jobId','') for j in baseline.get(name,[]) if j.get('jobId'))
    n_ids = set(j.get('jobId','') for j in all_jobs if j.get('jobId'))
    added = n_ids - b_ids
    print(f"  Baseline: {len(b_ids)}, Scan: {len(n_ids)}, ADDED: {len(added)}")
    if added:
        for jid in added:
            job = next((j for j in all_jobs if j.get('jobId')==jid), None)
            if job:
                print(f"    NEW: {job.get('title','')[:50]} | {jid}")
    else:
        print(f"    (no new jobs)")

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
        await browser.close()

    with open('/pulp/find-job/r81_final_mokahr.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n=== Saved ===")

asyncio.run(main())
