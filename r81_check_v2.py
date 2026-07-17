#!/usr/bin/env python3
"""Round 81 v2: Robust check - render DOM for mokahr, capture full API for feishu/horizon."""
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
    return str(ts)[:10] if ts else ''


# ==================== MOKAHR ====================
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

    raw_api_bodies = []

    async def on_resp(response):
        u = response.url
        if any(x in u for x in ['group-by-job','jobs/module','jobs/v2','jobs/recent','website/jobs','job-list']):
            try:
                body = await response.text()
                raw_api_bodies.append({'url': u, 'body': body[:5000]})
                print(f"  [captured API] {u[:80]} len={len(body)}", flush=True)
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

    # Scroll to load all
    for _ in range(5):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except:
            pass

    # Extract job data from rendered DOM
    jobs = await page.evaluate("""
        () => {
            const results = [];
            // Try various selectors for job cards
            const selectors = [
                '.job-item', '.position-item', '.job-card', '[class*="job"]',
                '.job-list-item', '.position-card', '[data-job-id]',
                '.recruit-list-item', '.social-job-item', '.job-info',
                '[class*="position"]', '[class*="JobItem"]'
            ];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    for (const el of els) {
                        const text = el.textContent || '';
                        const titleEl = el.querySelector('[class*="title"], [class*="name"], h3, h4, .job-title, .position-name');
                        const title = titleEl ? titleEl.textContent.trim() : text.substring(0, 60).trim();
                        const dateEl = el.querySelector('[class*="date"], [class*="time"], time');
                        const date = dateEl ? dateEl.textContent.trim() : '';
                        const jobId = el.getAttribute('data-job-id') || el.getAttribute('data-id') || '';
                        if (title && title.length > 2) {
                            results.push({title, date, jobId, sel});
                        }
                    }
                    if (results.length > 0) break;
                }
            }
            // If still nothing, try extracting all links that look like job detail pages
            if (results.length === 0) {
                const links = document.querySelectorAll('a[href*="job"], a[href*="position"], a[href*="/detail"]');
                for (const a of links) {
                    const title = a.textContent.trim();
                    const href = a.getAttribute('href') || '';
                    if (title && title.length > 2 && title.length < 100) {
                        results.push({title, date: '', jobId: href, sel: 'link'});
                    }
                }
            }
            return results;
        }
    """)

    # Also try extracting from page's JS state (React/Vue state)
    if len(jobs) < 3:
        js_jobs = await page.evaluate("""
            () => {
                // Try to find job data in React fiber or Vue data
                const root = document.getElementById('root') || document.getElementById('app');
                if (root && root._reactRootContainer) {
                    // React class component state
                }
                // Try to find __INITIAL_STATE__ or __NUXT__
                const state = window.__INITIAL_STATE__ || window.__NUXT__ || window.__PRELOADED_STATE__;
                if (state) {
                    return JSON.stringify(state).substring(0, 3000);
                }
                // Try data attributes
                const scripts = document.querySelectorAll('script[type="application/json"]');
                const data = [];
                for (const s of scripts) {
                    data.push(s.textContent.substring(0, 2000));
                }
                return data;
            }
        """)
        if js_jobs:
            print(f"  [JS state] found: {repr(js_jobs)[:200]}", flush=True)

    # If DOM extraction failed, try necromancer decryption via page's own JS
    if len(jobs) < 3 and raw_api_bodies:
        print(f"  Trying necromancer decryption via page JS...", flush=True)
        for api in raw_api_bodies:
            decrypted = await page.evaluate(f"""
                (body) => {{
                    try {{
                        // Try using page's fetch to re-request and get decrypted response
                        return '';
                    }} catch(e) {{ return e.toString(); }}
                }}
            """)
        # Instead, let's re-fetch the API using the page's own context (with cookies/headers)
        for api_url_pattern in ['group-by-job', 'jobs/module']:
            try:
                # Use page.request which inherits context
                api_url = None
                for api in raw_api_bodies:
                    if api_url_pattern in api['url']:
                        api_url = api['url']
                        break
                if not api_url:
                    # Construct URL
                    if route_type == 'apply':
                        api_url = f"https://app.mokahr.com/api/outer/ats-apply/website/{api_url_pattern}"
                    else:
                        api_url = f"https://app.mokahr.com/api/outer/ats-social-recruitment/website/{api_url_pattern}"

                # Re-fetch through page context (gets decrypted response)
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const resp = await fetch('{api_url}', {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}},
                                credentials: 'include',
                                body: JSON.stringify({{ page_no: 1, page_size: 100, job_type: 'social' }})
                            }});
                            const text = await resp.text();
                            return {{ status: resp.status, body: text.substring(0, 2000), isEncrypted: !text.startsWith('{{') }};
                        }} catch(e) {{ return {{ error: e.toString() }}; }}
                    }}
                """)
                if result and 'body' in result:
                    body = result['body']
                    print(f"  [re-fetch {api_url_pattern}] status={result.get('status')} encrypted={result.get('isEncrypted')} body[:100]={body[:100]}", flush=True)
                    if body.startswith('{'):
                        try:
                            data = json.loads(body)
                            d = data.get('data', {})
                            job_list = d.get('jobList', d.get('list', d.get('jobs', [])))
                            if job_list:
                                jobs = []
                                for j in job_list:
                                    jid = j.get('id', '') or j.get('jobId', '')
                                    title = j.get('title', '') or j.get('name', '')
                                    pub = j.get('publishDate', '') or j.get('activeDate', '') or j.get('firstPublishTime', '')
                                    jobs.append({'title': title, 'jobId': jid, 'date': str(pub)[:10] if pub else ''})
                                print(f"  [decrypted] {len(jobs)} jobs", flush=True)
                        except:
                            pass
            except Exception as e:
                print(f"  [re-fetch err] {e}", flush=True)

    # Paginate if we got jobs from DOM
    if jobs and len(jobs) < 10:
        for pg in range(2, 20):
            prev = len(jobs)
            try:
                btn = await page.query_selector(f"text={pg}")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    new_jobs = await page.evaluate("""
                        () => {
                            const results = [];
                            const sels = ['.job-item', '.position-item', '.job-card', '[class*="job"]', '.job-list-item'];
                            for (const sel of sels) {
                                const els = document.querySelectorAll(sel);
                                if (els.length > 0) {
                                    for (const el of els) {
                                        const titleEl = el.querySelector('[class*="title"], h3, h4');
                                        const title = titleEl ? titleEl.textContent.trim() : '';
                                        const dateEl = el.querySelector('[class*="date"], [class*="time"]');
                                        const date = dateEl ? dateEl.textContent.trim() : '';
                                        if (title) results.push({title, date, jobId: ''});
                                    }
                                    break;
                                }
                            }
                            return results;
                        }
                    """)
                    if new_jobs:
                        jobs.extend(new_jobs)
                else:
                    break
            except:
                break
            if len(jobs) == prev:
                break

    print(f"  Total: {len(jobs)} jobs")
    relevant = [j for j in jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:20]:
        print(f"    {j.get('date','')} | {j.get('title','')[:55]} | {j.get('jobId','')[:20]}")

    await ctx.close()
    return jobs


# ==================== FEISHU ====================
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
    raw_sample = None

    async def on_resp(response):
        nonlocal raw_sample
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = await response.text()
                data = json.loads(body)
                posts = data.get('data', {}).get('job_post_list', [])
                if posts and not raw_sample:
                    raw_sample = posts[0]
                for p_ in posts:
                    pid = p_.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = p_.get('title', '')
                        # Check all possible time fields
                        ct = p_.get('create_time', 0)
                        ut = p_.get('update_time', 0)
                        pt = p_.get('publish_time', 0)
                        ts = ct or ut or pt
                        date_str = fmt_ts(ts) if ts else ''
                        all_jobs.append({
                            'title': title,
                            'id': pid,
                            'date': date_str,
                            'all_keys': list(p_.keys())[:15]
                        })
                print(f"  [API] +{len(posts)}, total {len(all_jobs)}", flush=True)
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

    # Scroll
    for _ in range(3):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except:
            pass

    # Paginate
    for pg in range(2, 20):
        prev = len(all_jobs)
        try:
            btn = await page.query_selector(f"text={pg}")
            if btn:
                await btn.click()
                await page.wait_for_timeout(2000)
            else:
                # Try arrow/next button
                btn2 = await page.query_selector(".next, [aria-label='下一页'], button:has-text('>')")
                if btn2:
                    await btn2.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
        except:
            break
        if len(all_jobs) == prev:
            break

    if raw_sample:
        print(f"  [Sample job keys] {list(raw_sample.keys())}", flush=True)
        # Print time-related fields
        time_fields = {k: v for k, v in raw_sample.items() if 'time' in k.lower() or 'date' in k.lower() or 'create' in k.lower() or 'update' in k.lower() or 'publish' in k.lower()}
        print(f"  [Time fields] {time_fields}", flush=True)

    print(f"  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:20]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | {j['id'][:20]}")

    await ctx.close()
    return all_jobs


# ==================== HORIZON ====================
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
        if 'listPosition' in u:
            try:
                body = await response.text()
                data = json.loads(body)
                d = data.get('data', data)
                jobs_list = []
                if isinstance(d, dict):
                    jobs_list = d.get('list', d.get('positionInfos', d.get('rows', [])))
                elif isinstance(d, list):
                    jobs_list = d
                for j in jobs_list:
                    pid = j.get('postId', '') or j.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = j.get('postName', '') or j.get('title', '')
                        pub = j.get('publishDate', '') or j.get('publishFirstDate', '')
                        all_jobs.append({'title': title, 'postId': pid, 'date': str(pub)[:10] if pub else '', 'postType': j.get('postTypeName','')})
                if jobs_list:
                    print(f"  [API] +{len(jobs_list)}, total {len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [parse err] {e}", flush=True)
    page.on("response", on_resp)

    # Try social.html
    try:
        await page.goto(f"https://wecruit.hotjob.cn/wecruit/webSite/index/{suite_key}/pb/social.html",
                        timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  goto err: {e}")

    # Scroll
    for _ in range(5):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except:
            pass

    # Try direct API with POST (hotjob uses POST)
    if len(all_jobs) < 10:
        print(f"  Trying direct POST API...", flush=True)
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
                                    body: 'currentPage={pg}&pageSize=20'
                                }}
                            );
                            const text = await resp.text();
                            return {{ status: resp.status, body: text.substring(0, 3000) }};
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
                    jobs_list = d.get('list', d.get('positionInfos', d.get('rows', [])))
                elif isinstance(d, list):
                    jobs_list = d
                if not jobs_list:
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

    with open('/pulp/find-job/r81_results_v2.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\n=== Saved to r81_results_v2.json ===")

asyncio.run(main())
