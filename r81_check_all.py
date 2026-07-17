#!/usr/bin/env python3
"""Round 81: Check all 8 portals for new relevant positions."""
import asyncio
import json
import re
from playwright.async_api import async_playwright

PROXY = "http://100.66.66.64:8765"

TARGET_KEYWORDS = ["内核", "系统", "嵌入式", "eBPF", "Agent", "Infra", "基础设施",
                     "平台", "后端", "C++", "Rust", "底层", "驱动", "runtime",
                     "编译", "操作系统", "虚拟化", "分布式", "架构", "高性能",
                     "存储", "网络", "安全", "GPU", "CUDA", "推理", "训练",
                     "机器人", "控制", "SLAM", "运动", "感知", "规划",
                     "Coding", "Agentic", "RL", "Engineer", "engineer",
                     "Senior", "资深", "专家", "架构师"]

# ====== Mokahr portals ======
MOKAHR_PORTALS = [
    ("moonshot", "apply", "moonshot", "148506"),
    ("yinhe", "social-recruitment", "yinhetongyong", "165929"),
    ("zhipu", "social-recruitment", "zphz", "148983"),
    ("cambricon", "apply", "cambricon", "1113"),
]

async def check_mokahr(page, name, route_type, company, portal_id):
    """Check mokahr portal - capture job list API."""
    base_url = f"https://app.mokahr.com/{route_type}/{company}/{portal_id}"
    print(f"\n{'='*60}")
    print(f"{name} - Mokahr ({base_url})")

    all_jobs = []
    job_ids_seen = set()

    async def handle_response(response):
        url = response.url
        if 'api/v2' in url and ('position' in url.lower() or 'job' in url.lower()):
            try:
                body = await response.text()
                data = json.loads(body)
                # mokahr returns paginated job list
                jobs = []
                if isinstance(data, dict):
                    if 'data' in data:
                        d = data['data']
                        if isinstance(d, dict):
                            if 'jobList' in d:
                                jobs = d['jobList']
                            elif 'list' in d:
                                jobs = d['list']
                            elif 'jobs' in d:
                                jobs = d['jobs']
                        elif isinstance(d, list):
                            jobs = d
                if jobs:
                    for j in jobs:
                        jid = j.get('id', '') or j.get('jobId', '') or j.get('jobIdOuter', '')
                        if jid and jid not in job_ids_seen:
                            job_ids_seen.add(jid)
                            title = j.get('title', '') or j.get('name', '')
                            # Try to get publish date
                            pub_date = j.get('publishDate', '') or j.get('activeDate', '') or j.get('updateTime', '') or j.get('firstPublishTime', '')
                            dept = j.get('department', {}).get('name', '') if isinstance(j.get('department'), dict) else j.get('department', '')
                            urgent = j.get('urgent', False)
                            all_jobs.append({
                                'title': title,
                                'jobId': jid,
                                'date': str(pub_date)[:10] if pub_date else '',
                                'dept': dept,
                                'urgent': urgent,
                            })
                    print(f"  [API] +{len(jobs)} jobs, total {len(all_jobs)}", flush=True)
            except Exception as e:
                pass

    page.on("response", handle_response)

    try:
        await page.goto(base_url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
    except Exception as e:
        print(f"  goto err: {e}")

    # Scroll to trigger lazy load
    for _ in range(3):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except:
            pass

    # Try clicking next pages
    for pg in range(2, 15):
        prev = len(all_jobs)
        try:
            btn = await page.query_selector(f"text={pg}")
            if btn:
                await btn.click()
                await page.wait_for_timeout(2000)
            else:
                # Try "下一页" / next button
                btn2 = await page.query_selector("button:has-text('下一页')")
                if btn2:
                    await btn2.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
        except:
            break
        if len(all_jobs) == prev:
            break

    # Try direct API call for all pages
    if len(all_jobs) < 5:
        print(f"  Only {len(all_jobs)} jobs from UI, trying direct API...", flush=True)
        for pg_no in range(1, 20):
            try:
                api_url = f"https://app.mokahr.com/api/v2/{route_type}/{company}/{portal_id}/job-list?page={pg_no}&limit=20"
                resp = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch('{api_url}', {{credentials: 'include'}});
                            return await r.text();
                        }} catch(e) {{ return ''; }}
                    }}
                """)
                if not resp:
                    break
                data = json.loads(resp)
                d = data.get('data', {})
                jobs = d.get('jobList', d.get('list', []))
                if not jobs:
                    break
                for j in jobs:
                    jid = j.get('id', '') or j.get('jobId', '')
                    if jid and jid not in job_ids_seen:
                        job_ids_seen.add(jid)
                        title = j.get('title', '')
                        pub_date = j.get('publishDate', '') or j.get('activeDate', '')
                        all_jobs.append({'title': title, 'jobId': jid, 'date': str(pub_date)[:10] if pub_date else ''})
                print(f"  [API direct pg{pg_no}] +{len(jobs)}, total {len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [API direct pg{pg_no}] err: {e}", flush=True)
                break

    print(f"\n  Total: {len(all_jobs)} jobs")
    # Show recent/relevant
    relevant = [j for j in all_jobs if any(kw.lower() in j['title'].lower() for kw in TARGET_KEYWORDS)]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:20]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | {j['jobId'][:20]}")

    return all_jobs


# ====== Feishu portals ======
FEISHU_PORTALS = [
    ("星动纪元", "k0fqxcszc9.jobs.feishu.cn"),
    ("清程极智", "chitu-ai.jobs.feishu.cn"),
    ("零一万物", "01ai.jobs.feishu.cn"),
]

async def check_feishu(page, name, host):
    print(f"\n{'='*60}")
    print(f"{name} - Feishu ({host})")

    all_jobs = []
    job_ids_seen = set()

    async def handle_response(response):
        url = response.url
        if 'search/job/posts' in url:
            try:
                body = await response.text()
                data = json.loads(body)
                posts = data.get('data', {}).get('job_post_list', [])
                for p_ in posts:
                    pid = p_.get('id', '')
                    if pid and pid not in job_ids_seen:
                        job_ids_seen.add(pid)
                        title = p_.get('title', '')
                        # Feishu has create_time/update_time as timestamps
                        ct = p_.get('create_time', 0)
                        ut = p_.get('update_time', 0)
                        ts = ct or ut
                        from datetime import datetime
                        date_str = datetime.fromtimestamp(ts/1000 if ts > 1e12 else ts).strftime('%Y-%m-%d') if ts else ''
                        all_jobs.append({'title': title, 'id': pid, 'date': date_str, 'create_time': ct, 'update_time': ut})
                print(f"  [API] +{len(posts)}, total {len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [parse err] {e}", flush=True)

    page.on("response", handle_response)

    try:
        await page.goto(f"https://{host}/", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  goto err: {e}")

    # Click 职位/岗位 if needed
    if not all_jobs:
        for sel in ["text=职位", "text=岗位", "text=社招", "text=全部岗位"]:
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
    for _ in range(5):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except:
            pass

    # Paginate
    for pg in range(2, 15):
        prev = len(all_jobs)
        try:
            btn = await page.query_selector(f"text={pg}")
            if btn:
                await btn.click()
                await page.wait_for_timeout(2000)
            else:
                btn2 = await page.query_selector("button:has-text('下一页')")
                if btn2:
                    await btn2.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
        except:
            break
        if len(all_jobs) == prev:
            break

    print(f"\n  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if any(kw.lower() in j['title'].lower() for kw in TARGET_KEYWORDS)]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:20]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | {j['id'][:20]}")

    return all_jobs


# ====== Horizon (hotjob) ======
async def check_horizon(page):
    print(f"\n{'='*60}")
    print(f"地平线 - Hotjob")

    all_jobs = []
    ids_seen = set()

    async def handle_response(response):
        url = response.url
        if 'listPosition' in url or 'positionInfo' in url.lower():
            try:
                body = await response.text()
                data = json.loads(body)
                # hotjob returns data.data or data.list
                jobs = []
                if isinstance(data, dict):
                    d = data.get('data', data)
                    if isinstance(d, dict):
                        jobs = d.get('list', d.get('positionInfos', d.get('rows', [])))
                    elif isinstance(d, list):
                        jobs = d
                for j in jobs:
                    pid = j.get('postId', '') or j.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = j.get('postName', '') or j.get('title', '') or j.get('positionName', '')
                        pub = j.get('publishDate', '') or j.get('publishFirstDate', '')
                        post_type = j.get('postTypeName', '')
                        all_jobs.append({'title': title, 'postId': pid, 'date': str(pub)[:10] if pub else '', 'postType': post_type})
                if jobs:
                    print(f"  [API] +{len(jobs)}, total {len(all_jobs)}", flush=True)
            except Exception as e:
                pass

    page.on("response", handle_response)

    suite_key = "SU64819a4f2f9d2433ba8b043a"
    try:
        await page.goto(f"https://wecruit.hotjob.cn/wecruit/webSite/index/{suite_key}?websiteHash=f2f9d2433ba8b043a", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  goto err: {e}")

    # Try the social.html page
    try:
        await page.goto(f"https://wecruit.hotjob.cn/wecruit/webSite/index/{suite_key}/pb/social.html", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
    except:
        pass

    # Scroll
    for _ in range(5):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except:
            pass

    # Try direct API call
    if len(all_jobs) < 10:
        print(f"  Only {len(all_jobs)} from UI, trying direct API...", flush=True)
        for pg in range(1, 30):
            try:
                api_url = f"https://wecruit.hotjob.cn/wecruit/positionInfo/listPosition/{suite_key}?iSaJAx=isAjax&request_locale=zh_CN&page={pg}&limit=20"
                resp = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch('{api_url}', {{credentials: 'include', headers: {{'X-Requested-With': 'XMLHttpRequest'}}}});
                            return await r.text();
                        }} catch(e) {{ return e.toString(); }}
                    }}
                """)
                if not resp or 'error' in str(resp).lower()[:20]:
                    break
                data = json.loads(resp)
                d = data.get('data', data)
                jobs = []
                if isinstance(d, dict):
                    jobs = d.get('list', d.get('positionInfos', d.get('rows', [])))
                elif isinstance(d, list):
                    jobs = d
                if not jobs:
                    break
                for j in jobs:
                    pid = j.get('postId', '') or j.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = j.get('postName', '') or j.get('title', '')
                        pub = j.get('publishDate', '') or j.get('publishFirstDate', '')
                        all_jobs.append({'title': title, 'postId': pid, 'date': str(pub)[:10] if pub else '', 'postType': j.get('postTypeName','')})
                print(f"  [API direct pg{pg}] +{len(jobs)}, total {len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [API direct pg{pg}] err: {e}", flush=True)
                break

    print(f"\n  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if any(kw.lower() in j['title'].lower() for kw in TARGET_KEYWORDS)]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:20]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | {j['postId'][:20]}")

    return all_jobs


async def main():
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY})

        # --- Mokahr portals ---
        for name, route_type, company, portal_id in MOKAHR_PORTALS:
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
            )
            page = await ctx.new_page()
            try:
                jobs = await check_mokahr(page, name, route_type, company, portal_id)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []
            await ctx.close()

        # --- Feishu portals ---
        for name, host in FEISHU_PORTALS:
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
            )
            page = await ctx.new_page()
            try:
                jobs = await check_feishu(page, name, host)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []
            await ctx.close()

        # --- Horizon ---
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            locale="zh-CN",
            viewport={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()
        try:
            jobs = await check_horizon(page)
            results['horizon'] = jobs
        except Exception as e:
            print(f"  horizon ERROR: {e}")
            results['horizon'] = []
        await ctx.close()

        await browser.close()

    # Save results
    with open('/pulp/find-job/r81_results.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\n=== Saved to r81_results.json ===")


asyncio.run(main())
