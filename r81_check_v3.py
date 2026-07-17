#!/usr/bin/env python3
"""Round 81 v3: Get ALL jobIds from all pages, with proper pagination."""
import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

KEYWORDS = ['内核','kernel','eBPF','ebpf','BPF','系统','BSP','嵌入式','embedded','驱动','driver',
            '存储','storage','分布式','Agent','infra','Infra','基础设施','虚拟化','Runtime',
            '高性能','底层','操作系统','固件','firmware','编译','compiler','CUDA','算子','平台',
            '云原生','推理','训练','机器人','控制','SLAM','规划','Coding','Agentic','架构',
            '后端','C++','Rust','Engineer','资深','专家','GPU','集群','runtime','sre','SRE',
            '感知','运动','异构','加速','HPC','MLSys']

def match_job(title):
    t = title.lower()
    return any(kw.lower() in t for kw in KEYWORDS)

def fmt_ts(ts):
    if not ts: return ''
    try:
        ts = int(ts)
        if ts > 1e12: ts = ts // 1000
        if ts > 1e9:
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except: pass
    return ''


# ==================== MOKAHR (necromancer - use rendered DOM + pagination) ====================
MOKAHR_PORTALS = [
    ("moonshot", "apply", "moonshot", "148506"),
    ("yinhe", "social-recruitment", "yinhetongyong", "165929"),
    ("zhipu", "social-recruitment", "zphz", "148983"),
    ("cambricon", "apply", "cambricon", "1113"),
]

async def check_mokahr(browser, name, route_type, company, portal_id):
    print(f"\n{'='*60}")
    print(f"{name} - Mokahr")
    url = f"https://app.mokahr.com/{route_type}/{company}/{portal_id}"

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1920,"height":1080})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()

    # Capture API responses that contain jobId data (may be decrypted in JS)
    api_responses = []

    async def on_resp(response):
        u = response.url
        if any(x in u for x in ['group-by-job','jobs/module','jobs/v2','jobs/recent','website/jobs','job-list','jobs?']):
            try:
                body = await response.text()
                api_responses.append({'url': u, 'body': body})
            except:
                pass
    page.on("response", on_resp)

    try:
        await page.goto(url, timeout=45000, wait_until="networkidle")
    except:
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  goto err: {e}")

    await page.wait_for_timeout(3000)

    # Extract jobs from rendered DOM - look for links with jobId in href
    async def extract_dom_jobs():
        return await page.evaluate("""
            () => {
                const results = [];
                // Strategy 1: Find all links that contain job/position IDs
                const allLinks = document.querySelectorAll('a[href]');
                for (const a of allLinks) {
                    const href = a.getAttribute('href') || '';
                    const text = a.textContent.trim();
                    // mokahr job detail URLs contain jobId (UUID format or hex)
                    const uuidMatch = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                    const idMatch = href.match(/(?:job|position|detail)[\/=]([a-zA-Z0-9_-]+)/i);
                    const jobId = uuidMatch ? uuidMatch[1] : (idMatch ? idMatch[1] : '');
                    if (text && text.length > 2 && text.length < 100) {
                        results.push({title: text, jobId: jobId, href: href});
                    }
                }
                // Strategy 2: Find elements with data attributes
                const allEls = document.querySelectorAll('[data-job-id], [data-id], [data-position-id]');
                for (const el of allEls) {
                    const jobId = el.getAttribute('data-job-id') || el.getAttribute('data-id') || el.getAttribute('data-position-id') || '';
                    const titleEl = el.querySelector('[class*="title"], h3, h4, .name');
                    const title = titleEl ? titleEl.textContent.trim() : el.textContent.trim().substring(0, 80);
                    if (jobId && title) results.push({title, jobId, href: ''});
                }
                // Strategy 3: Find job cards by class and extract from onclick or data attrs
                const cardSels = ['.job-item', '.position-item', '.job-card', '.job-list-item',
                                  '.social-job-item', '.recruit-list-item', '[class*="job-item"]',
                                  '[class*="position-item"]', '[class*="JobCard"]', '[class*="job-card"]'];
                for (const sel of cardSels) {
                    const cards = document.querySelectorAll(sel);
                    for (const card of cards) {
                        const titleEl = card.querySelector('[class*="title"], [class*="name"], h3, h4');
                        const title = titleEl ? titleEl.textContent.trim() : '';
                        const dateEl = card.querySelector('[class*="date"], [class*="time"]');
                        const date = dateEl ? dateEl.textContent.trim() : '';
                        const linkEl = card.querySelector('a[href]');
                        const href = linkEl ? linkEl.getAttribute('href') : '';
                        const uuidMatch = href.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                        const jobId = uuidMatch ? uuidMatch[1] : '';
                        if (title && title.length > 2) {
                            results.push({title, jobId, date, href});
                        }
                    }
                }
                return results;
            }
        """)

    jobs = await extract_dom_jobs()
    # Deduplicate
    for j in jobs:
        jid = j.get('jobId', '')
        key = jid or j.get('title', '')
        if key and key not in ids_seen:
            ids_seen.add(key)
            all_jobs.append(j)

    print(f"  Page 1: {len(all_jobs)} unique jobs", flush=True)

    # Paginate - try clicking page numbers and "next" buttons
    for pg in range(2, 30):
        prev_count = len(all_jobs)
        try:
            # Try clicking page number
            clicked = False
            for sel in [f"button:has-text('{pg}')", f"a:has-text('{pg}')", f"text={pg}",
                        f"li:has-text('{pg}')", f"span:has-text('{pg}')"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                # Try "下一页" / next arrow
                for sel in ["button:has-text('下一页')", "[aria-label='next']",
                            ".next-btn", ".ant-pagination-next", "button.next",
                            "li.ant-pagination-next", "[class*='next']"]:
                    try:
                        btn = await page.query_selector(sel)
                        if btn:
                            await btn.click()
                            clicked = True
                            break
                    except:
                        continue

            if not clicked:
                print(f"  No more pages (pg {pg})", flush=True)
                break

            await page.wait_for_timeout(2500)
            new_jobs = await extract_dom_jobs()
            for j in new_jobs:
                jid = j.get('jobId', '')
                key = jid or j.get('title', '')
                if key and key not in ids_seen:
                    ids_seen.add(key)
                    all_jobs.append(j)

            if len(all_jobs) == prev_count:
                print(f"  No new jobs on pg {pg}, stopping", flush=True)
                break
            print(f"  Page {pg}: +{len(all_jobs) - prev_count}, total {len(all_jobs)}", flush=True)
        except Exception as e:
            print(f"  Pagination err pg {pg}: {e}", flush=True)
            break

    print(f"  Total: {len(all_jobs)} jobs")

    # Clean up titles (remove "急" prefix etc)
    for j in all_jobs:
        j['title'] = j['title'].strip()
        j['title'] = re.sub(r'^急', '', j['title'])

    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in relevant[:20]:
        print(f"    {j.get('title','')[:55]} | jobId={j.get('jobId','')[:20]} | date={j.get('date','')}")

    await ctx.close()
    return all_jobs


# ==================== FEISHU (paginate all pages) ====================
FEISHU_PORTALS = [
    ("星动纪元", "k0fqxcszc9.jobs.feishu.cn"),
    ("清程极智", "chitu-ai.jobs.feishu.cn"),
    ("零一万物", "01ai.jobs.feishu.cn"),
]

async def check_feishu(browser, name, host):
    print(f"\n{'='*60}")
    print(f"{name} - Feishu ({host})")

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1440,"height":900})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()
    total_count = 0

    async def on_resp(response):
        nonlocal total_count
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = await response.text()
                data = json.loads(body)
                d = data.get('data', {})
                total_count = d.get('total', d.get('total_count', 0))
                posts = d.get('job_post_list', [])
                for p_ in posts:
                    pid = p_.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = p_.get('title', '')
                        pt = p_.get('publish_time', 0)
                        date_str = fmt_ts(pt) if pt else ''
                        all_jobs.append({'title': title, 'id': pid, 'date': date_str})
                print(f"  [API] +{len(posts)} (total_in_api={total_count}), collected={len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [parse err] {e}", flush=True)

    page.on("response", on_resp)

    try:
        await page.goto(f"https://{host}/", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
    except:
        pass

    # Click 职位 if needed
    if not all_jobs:
        for sel in ["text=职位", "text=岗位", "text=社招", "text=全部岗位", "a:has-text('职位')"]:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    if all_jobs:
                        break
            except:
                continue

    # Scroll to load pagination
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
    except:
        pass

    # Paginate through all pages
    for pg in range(2, 30):
        prev_count = len(all_jobs)
        try:
            clicked = False
            # Try clicking page number
            for sel in [f"text={pg}", f"button:has-text('{pg}')", f"li:has-text('{pg}')",
                        f"span:has-text('{pg}')"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                # Try next/arrow button
                for sel in [".next-btn", "[aria-label='next']", "button:has-text('>')",
                            ".pagination-next", "li.ant-pagination-next",
                            "[class*='next']:not([class*='next-page-text'])",
                            "svg[class*='next']", "button[class*='next']"]:
                    try:
                        btn = await page.query_selector(sel)
                        if btn:
                            await btn.click()
                            clicked = True
                            break
                    except:
                        continue

            if not clicked:
                # Try keyboard right arrow
                try:
                    await page.keyboard.press("ArrowRight")
                    clicked = True
                except:
                    pass

            if not clicked:
                print(f"  No pagination found at pg {pg}", flush=True)
                break

            await page.wait_for_timeout(2500)

            if len(all_jobs) == prev_count:
                # Maybe the click didn't work - try scroll and wait more
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                if len(all_jobs) == prev_count:
                    print(f"  No new jobs at pg {pg}, total={len(all_jobs)}", flush=True)
                    break
            print(f"  Page {pg}: total {len(all_jobs)}", flush=True)
        except:
            break

    print(f"  Total: {len(all_jobs)} jobs (api_total={total_count})")
    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:20]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | id={j['id'][:20]}")

    await ctx.close()
    return all_jobs


# ==================== HORIZON (hotjob - render + API) ====================
async def check_horizon(browser):
    print(f"\n{'='*60}")
    print(f"地平线 - Hotjob")

    suite_key = "SU64819a4f2f9d2433ba8b043a"
    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1440,"height":900})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()

    async def on_resp(response):
        u = response.url
        if 'listPosition' in u or 'positionInfo' in u.lower():
            try:
                body = await response.text()
                data = json.loads(body)
                d = data.get('data', data)
                jobs_list = []
                if isinstance(d, dict):
                    jobs_list = d.get('list', d.get('positionInfos', d.get('rows', d.get('positionList', []))))
                    if not jobs_list:
                        # Maybe data itself is the list
                        for k in ['list','positionInfos','rows','positionList','positions']:
                            if k in d:
                                jobs_list = d[k]
                                break
                elif isinstance(d, list):
                    jobs_list = d
                for j in jobs_list:
                    pid = j.get('postId', '') or j.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = j.get('postName', '') or j.get('title', '') or j.get('positionName', '')
                        pub = j.get('publishDate', '') or j.get('publishFirstDate', '')
                        all_jobs.append({'title': title, 'postId': pid, 'date': str(pub)[:10] if pub else '', 'postType': j.get('postTypeName','')})
                if jobs_list:
                    print(f"  [API] +{len(jobs_list)}, total {len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [parse err] {e}", flush=True)
    page.on("response", on_resp)

    # Navigate to social.html
    try:
        await page.goto(f"https://wecruit.hotjob.cn/wecruit/webSite/index/{suite_key}/pb/social.html",
                        timeout=45000, wait_until="networkidle")
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  goto social.html err: {e}")
        try:
            await page.goto(f"https://wecruit.hotjob.cn/wecruit/webSite/index/{suite_key}/pb/social.html",
                            timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except:
            pass

    # If API didn't fire, try clicking "社招" or loading all
    if not all_jobs:
        for sel in ["text=社招", "text=全部", "text=全部职位", "a:has-text('社招')"]:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    if all_jobs:
                        break
            except:
                continue

    # Scroll to trigger lazy loading
    for _ in range(5):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except:
            pass

    # If still no jobs, extract from DOM
    if not all_jobs:
        dom_jobs = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="position"], a[href*="job"], [data-post-id]');
                for (const el of links) {
                    const text = el.textContent.trim();
                    const pid = el.getAttribute('data-post-id') || '';
                    if (text && text.length > 2) results.push({title: text, postId: pid});
                }
                // Also try job card selectors
                const cards = document.querySelectorAll('[class*="position"], [class*="job"], [class*="post"]');
                for (const card of cards) {
                    const t = card.textContent.trim();
                    if (t && t.length > 5 && t.length < 100) {
                        results.push({title: t, postId: ''});
                    }
                }
                return results.slice(0, 50);
            }
        """)
        if dom_jobs:
            print(f"  [DOM] found {len(dom_jobs)} elements", flush=True)
            for j in dom_jobs[:5]:
                print(f"    {j.get('title','')[:60]}", flush=True)

    # Try direct API call with GET (hotjob might use GET with query params)
    if len(all_jobs) < 10:
        print(f"  Trying GET API...", flush=True)
        for pg in range(1, 25):
            try:
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const resp = await fetch(
                                'https://wecruit.hotjob.cn/wecruit/positionInfo/listPosition/{suite_key}?iSaJAx=isAjax&request_locale=zh_CN',
                                {{
                                    method: 'POST',
                                    headers: {{
                                        'Content-Type': 'application/x-www-form-urlencoded',
                                        'X-Requested-With': 'XMLHttpRequest'
                                    }},
                                    credentials: 'include',
                                    body: 'currentPage={pg}&pageSize=20&recruitType=2'
                                }}
                            );
                            const text = await resp.text();
                            return {{ status: resp.status, body: text.substring(0, 5000) }};
                        }} catch(e) {{ return {{ error: e.toString() }}; }}
                    }}
                """)
                if not result or 'error' in result:
                    print(f"  [POST pg{pg}] err: {result}", flush=True)
                    break
                body = result.get('body', '')
                if not body or not body.startswith('{'):
                    print(f"  [POST pg{pg}] not JSON: {body[:100]}", flush=True)
                    break
                data = json.loads(body)
                d = data.get('data', data)
                jobs_list = []
                if isinstance(d, dict):
                    for k in ['list','positionInfos','rows','positionList','positions']:
                        if k in d:
                            jobs_list = d[k]
                            break
                    if not jobs_list and 'data' in d:
                        dd = d['data']
                        if isinstance(dd, dict):
                            for k in ['list','positionInfos','rows']:
                                if k in dd:
                                    jobs_list = dd[k]
                                    break
                elif isinstance(d, list):
                    jobs_list = d
                if not jobs_list:
                    print(f"  [POST pg{pg}] no jobs in response, keys: {list(d.keys()) if isinstance(d, dict) else 'list'}", flush=True)
                    break
                for j in jobs_list:
                    pid = j.get('postId', '') or j.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = j.get('postName', '') or j.get('title', '')
                        pub = j.get('publishDate', '') or j.get('publishFirstDate', '')
                        all_jobs.append({'title': title, 'postId': pid, 'date': str(pub)[:10] if pub else '', 'postType': j.get('postTypeName','')})
                print(f"  [POST pg{pg}] +{len(jobs_list)}, total {len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [POST pg{pg}] err: {e}", flush=True)
                break

    print(f"  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:20]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | {j['postId'][:20]}")

    await ctx.close()
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

        for name, host in FEISHU_PORTALS:
            try:
                jobs = await check_feishu(browser, name, host)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []

        try:
            jobs = await check_horizon(browser)
            results['horizon'] = jobs
        except Exception as e:
            print(f"  horizon ERROR: {e}")
            results['horizon'] = []

        await browser.close()

    with open('/pulp/find-job/r81_results_v3.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\n=== Saved to r81_results_v3.json ===")

asyncio.run(main())
