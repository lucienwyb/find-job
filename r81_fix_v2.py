#!/usr/bin/env python3
"""Round 81 final fixes: feishu replay captured URL, horizon pageForm.pageData."""
import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fmt_ts(ts):
    if not ts: return ''
    try:
        ts = int(ts)
        if ts > 1e12: ts = ts // 1000
        if ts > 1e9:
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except: pass
    return ''

KEYWORDS = ['内核','kernel','eBPF','ebpf','BPF','系统','BSP','嵌入式','embedded','驱动','driver',
            '存储','storage','分布式','Agent','infra','Infra','基础设施','虚拟化','Runtime',
            '高性能','底层','操作系统','固件','firmware','编译','compiler','CUDA','算子','平台',
            '云原生','推理','训练','机器人','控制','SLAM','规划','Coding','Agentic','架构',
            '后端','C++','Rust','Engineer','资深','专家','GPU','集群','runtime','sre','SRE',
            '感知','运动','异构','加速','HPC','MLSys']

def match_job(title):
    t = title.lower()
    return any(kw.lower() in t for kw in KEYWORDS)


async def check_feishu_replay(browser, name, host):
    """Capture the feishu API URL and replay with different page_no."""
    print(f"\n{'='*60}")
    print(f"{name} - Feishu ({host}) - replay API")

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1440,"height":900})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()
    captured_urls = []
    captured_bodies = []

    async def on_request(request):
        u = request.url
        if 'search/job/posts' in u and request.method == 'POST':
            try:
                post_data = request.post_data
                captured_urls.append({'url': u, 'method': request.method, 'headers': dict(request.headers), 'post_data': post_data})
            except:
                captured_urls.append({'url': u, 'method': request.method, 'post_data': None})
    page.on("request", on_request)

    async def on_resp(response):
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = await response.text()
                captured_bodies.append(body)
                data = json.loads(body)
                d = data.get('data', {})
                posts = d.get('job_post_list', [])
                for p_ in posts:
                    pid = p_.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = p_.get('title', '')
                        pt = p_.get('publish_time', 0)
                        date_str = fmt_ts(pt) if pt else ''
                        all_jobs.append({'title': title, 'id': pid, 'date': date_str})
                print(f"  [XHR] +{len(posts)}, collected={len(all_jobs)}", flush=True)
            except Exception as e:
                print(f"  [XHR err] {e}", flush=True)
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

    # Now try to replay the captured API request with different page_no
    if captured_urls:
        api_info = captured_urls[0]
        api_url = api_info['url']
        orig_post = api_info.get('post_data', '{}')

        print(f"  Captured API URL: {api_url[:80]}", flush=True)
        print(f"  Original post_data: {orig_post[:200] if orig_post else 'None'}", flush=True)

        # Parse original post data and modify page_no
        try:
            orig_params = json.loads(orig_post) if orig_data else {}
        except:
            orig_params = {}

        for page_no in range(2, 30):
            # Modify page_no in the post data
            params = dict(orig_params)
            params['page_no'] = page_no
            post_body = json.dumps(params)

            result = await page.evaluate(f"""
                async (url, body) => {{
                    try {{
                        const resp = await fetch(url, {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            credentials: 'include',
                            body: body
                        }});
                        return await resp.text();
                    }} catch(e) {{ return 'ERR:' + e.toString(); }}
                }}
            """, api_url, post_body)

            if not result or result.startswith('ERR:'):
                print(f"  [replay pg{page_no}] err: {result[:100]}", flush=True)
                break

            try:
                data = json.loads(result)
                posts = data.get('data', {}).get('job_post_list', [])
                if not posts:
                    print(f"  [replay pg{page_no}] no more posts", flush=True)
                    break
                new_count = 0
                for p_ in posts:
                    pid = p_.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = p_.get('title', '')
                        pt = p_.get('publish_time', 0)
                        date_str = fmt_ts(pt) if pt else ''
                        all_jobs.append({'title': title, 'id': pid, 'date': date_str})
                        new_count += 1
                print(f"  [replay pg{page_no}] +{new_count}, total={len(all_jobs)}", flush=True)
                if new_count == 0:
                    break
            except Exception as e:
                print(f"  [replay pg{page_no}] parse err: {e}", flush=True)
                break
    else:
        print(f"  No API URL captured, trying scroll+click pagination", flush=True)
        # Fallback: scroll and click page numbers
        for _ in range(3):
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)
            except:
                pass

        for pg in range(2, 20):
            prev = len(all_jobs)
            for sel in [f"text={pg}", f"button:has-text('{pg}')", f"li:has-text('{pg}')"]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(2500)
                        break
                except:
                    continue
            if len(all_jobs) == prev:
                break

    print(f"  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:25]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | id={j['id'][:20]}")

    await ctx.close()
    return all_jobs


async def check_horizon_fixed(browser):
    """Get all horizon jobs - extract from pageForm.pageData."""
    print(f"\n{'='*60}")
    print(f"地平线 - Hotjob (fixed)")

    suite_key = "SU64819a4f2f9d2433ba8b043a"
    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1440,"height":900})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()

    # Navigate first to get cookies
    try:
        await page.goto(f"https://wecruit.hotjob.cn/wecruit/webSite/index/{suite_key}/pb/social.html",
                        timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
    except:
        pass

    # Call API for all pages
    for pg in range(1, 20):
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
                    return await resp.text();
                }} catch(e) {{ return 'ERR:' + e.toString(); }}
            }}
        """)

        if not result or result.startswith('ERR:'):
            print(f"  [pg{pg}] err: {result[:100]}", flush=True)
            break

        try:
            data = json.loads(result)
        except:
            print(f"  [pg{pg}] JSON parse failed", flush=True)
            break

        d = data.get('data', {})
        pf = d.get('pageForm', {})
        total_pages = pf.get('totalPage', 1)
        jobs_list = pf.get('pageData', [])

        if not jobs_list:
            print(f"  [pg{pg}] no pageData", flush=True)
            break

        for j in jobs_list:
            pid = j.get('postId', '')
            if pid and pid not in ids_seen:
                ids_seen.add(pid)
                title = j.get('postName', '') or j.get('title', '')
                pub = j.get('publishDate', '') or j.get('publishFirstDate', '')
                all_jobs.append({'title': title, 'postId': pid, 'date': str(pub)[:10] if pub else '', 'postType': j.get('postTypeName', '')})

        print(f"  [pg{pg}] +{len(jobs_list)}, total {len(all_jobs)}, totalPages={total_pages}", flush=True)
        if pg >= total_pages:
            break

    print(f"  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:25]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | {j['postId'][:20]}")

    await ctx.close()
    return all_jobs


async def main():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY})

        for name, host in [("星动纪元", "k0fqxcszc9.jobs.feishu.cn"),
                           ("清程极智", "chitu-ai.jobs.feishu.cn"),
                           ("零一万物", "01ai.jobs.feishu.cn")]:
            try:
                jobs = await check_feishu_replay(browser, name, host)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []

        try:
            jobs = await check_horizon_fixed(browser)
            results['horizon'] = jobs
        except Exception as e:
            print(f"  horizon ERROR: {e}")
            results['horizon'] = []

        await browser.close()

    with open('/pulp/find-job/r81_fix_v2_results.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\n=== Saved to r81_fix_v2_results.json ===")

asyncio.run(main())
