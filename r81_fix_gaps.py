#!/usr/bin/env python3
"""Round 81: Fix gaps - feishu all pages, horizon full API, compare with baseline."""
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


async def check_feishu_all(browser, name, host):
    """Get ALL feishu jobs by making direct API calls with pagination."""
    print(f"\n{'='*60}")
    print(f"{name} - Feishu ({host}) - direct API pagination")

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1440,"height":900})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()

    # Capture the original API request URL to get the correct token/params
    api_url_captured = []

    async def on_resp(response):
        u = response.url
        if 'search/job/posts' in u:
            api_url_captured.append(u)
    page.on("response", on_resp)

    try:
        await page.goto(f"https://{host}/", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
    except:
        pass

    # Click 职位 if needed
    if not api_url_captured:
        for sel in ["text=职位", "text=岗位", "text=社招", "text=全部岗位", "a:has-text('职位')"]:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    if api_url_captured:
                        break
            except:
                continue

    # Now use page.evaluate to make API calls with different page_no
    # The feishu API accepts page_no and page_size
    for page_no in range(1, 30):
        result = await page.evaluate(f"""
            async () => {{
                try {{
                    const resp = await fetch('https://{host}/api/v1/search/job/posts',
                        {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            credentials: 'include',
                            body: JSON.stringify({{page_no: {page_no}, page_size: 30, keyword: ''}})
                        }});
                    const text = await resp.text();
                    return text;
                }} catch(e) {{ return e.toString(); }}
            }}
        """)

        if not result or result.startswith('Error') or not result.startswith('{'):
            # Maybe the API path is different, try the captured URL
            if api_url_captured:
                base_api = api_url_captured[0].split('?')[0]
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const resp = await fetch('{base_api}',
                                {{
                                    method: 'POST',
                                    headers: {{'Content-Type': 'application/json'}},
                                    credentials: 'include',
                                    body: JSON.stringify({{page_no: {page_no}, page_size: 30}})
                                }});
                            const text = await resp.text();
                            return text;
                        }} catch(e) {{ return e.toString(); }}
                    }}
                """)
            else:
                print(f"  [API pg{page_no}] no valid response", flush=True)
                break

        if not result or not result.startswith('{'):
            print(f"  [API pg{page_no}] not JSON: {str(result)[:100]}", flush=True)
            break

        try:
            data = json.loads(result)
            d = data.get('data', {})
            posts = d.get('job_post_list', [])
            total = d.get('total', d.get('total_count', 0))
            if not posts:
                print(f"  [API pg{page_no}] no more posts", flush=True)
                break
            for p_ in posts:
                pid = p_.get('id', '')
                if pid and pid not in ids_seen:
                    ids_seen.add(pid)
                    title = p_.get('title', '')
                    pt = p_.get('publish_time', 0)
                    date_str = fmt_ts(pt) if pt else ''
                    all_jobs.append({'title': title, 'id': pid, 'date': date_str})
            print(f"  [API pg{page_no}] +{len(posts)} (total={total}), collected={len(all_jobs)}", flush=True)
            if total and len(all_jobs) >= total:
                break
        except Exception as e:
            print(f"  [API pg{page_no}] parse err: {e}", flush=True)
            break

    print(f"  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:25]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | id={j['id'][:20]}")

    await ctx.close()
    return all_jobs


async def check_horizon_api(browser):
    """Get all horizon jobs via API."""
    print(f"\n{'='*60}")
    print(f"地平线 - Hotjob API")

    suite_key = "SU64819a4f2f9d2433ba8b043a"
    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1440,"height":900})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()

    # First navigate to the page to get cookies
    try:
        await page.goto(f"https://wecruit.hotjob.cn/wecruit/webSite/index/{suite_key}/pb/social.html",
                        timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
    except:
        pass

    # Try POST API with large page size - capture FULL response (no truncation)
    for pg in range(1, 30):
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
                    // Return full response but check if it's valid
                    return {{status: resp.status, len: text.length, body: text}};
                }} catch(e) {{ return {{error: e.toString()}}; }}
            }}
        """)

        if not result or 'error' in result:
            print(f"  [pg{pg}] err: {result}", flush=True)
            break

        body = result.get('body', '')
        if not body or not body.startswith('{'):
            print(f"  [pg{pg}] not JSON, len={result.get('len')}", flush=True)
            break

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            print(f"  [pg{pg}] JSON parse failed, len={len(body)}", flush=True)
            break

        d = data.get('data', data)
        jobs_list = []
        if isinstance(d, dict):
            for k in ['list', 'positionInfos', 'rows', 'positionList', 'positions']:
                if k in d and d[k]:
                    jobs_list = d[k]
                    break
            if not jobs_list:
                # Check nested data
                if 'data' in d and isinstance(d['data'], dict):
                    for k in ['list', 'positionInfos', 'rows']:
                        if k in d['data']:
                            jobs_list = d['data'][k]
                            break
        elif isinstance(d, list):
            jobs_list = d

        if not jobs_list:
            print(f"  [pg{pg}] no jobs, keys: {list(d.keys())[:10] if isinstance(d, dict) else 'list'}", flush=True)
            # Print first 500 chars to debug
            print(f"  [debug] body[:500]: {body[:500]}", flush=True)
            break

        for j in jobs_list:
            pid = j.get('postId', '') or j.get('id', '')
            if pid and pid not in ids_seen:
                ids_seen.add(pid)
                title = j.get('postName', '') or j.get('title', '') or j.get('positionName', '')
                pub = j.get('publishDate', '') or j.get('publishFirstDate', '')
                all_jobs.append({'title': title, 'postId': pid, 'date': str(pub)[:10] if pub else '', 'postType': j.get('postTypeName', '')})

        print(f"  [pg{pg}] +{len(jobs_list)}, total {len(all_jobs)}", flush=True)
        if len(jobs_list) < 20:
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

        # Feishu - get all pages via direct API
        for name, host in [("星动纪元", "k0fqxcszc9.jobs.feishu.cn"),
                           ("清程极智", "chitu-ai.jobs.feishu.cn"),
                           ("零一万物", "01ai.jobs.feishu.cn")]:
            try:
                jobs = await check_feishu_all(browser, name, host)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []

        # Horizon - full API
        try:
            jobs = await check_horizon_api(browser)
            results['horizon'] = jobs
        except Exception as e:
            print(f"  horizon ERROR: {e}")
            results['horizon'] = []

        await browser.close()

    with open('/pulp/find-job/r81_fix_results.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\n=== Saved to r81_fix_results.json ===")

asyncio.run(main())
