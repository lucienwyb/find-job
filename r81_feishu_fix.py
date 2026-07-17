#!/usr/bin/env python3
"""Fix feishu: replay captured API URL with page_no as single arg."""
import asyncio
import json
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


async def check_feishu(browser, name, host):
    print(f"\n{'='*60}")
    print(f"{name} - Feishu ({host})")

    ctx = await browser.new_context(user_agent=UA, locale="zh-CN", viewport={"width":1440,"height":900})
    page = await ctx.new_page()

    all_jobs = []
    ids_seen = set()
    captured = {'url': None, 'post_data': None}

    async def on_request(request):
        u = request.url
        if 'search/job/posts' in u and request.method == 'POST':
            if not captured['url']:
                captured['url'] = u
                try:
                    captured['post_data'] = request.post_data
                except:
                    pass
    page.on("request", on_request)

    async def on_resp(response):
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = await response.text()
                data = json.loads(body)
                posts = data.get('data', {}).get('job_post_list', [])
                for p_ in posts:
                    pid = p_.get('id', '')
                    if pid and pid not in ids_seen:
                        ids_seen.add(pid)
                        title = p_.get('title', '')
                        pt = p_.get('publish_time', 0)
                        date_str = fmt_ts(pt) if pt else ''
                        all_jobs.append({'title': title, 'id': pid, 'date': date_str})
                print(f"  [XHR] +{len(posts)}, collected={len(all_jobs)}", flush=True)
            except:
                pass
    page.on("response", on_resp)

    try:
        await page.goto(f"https://{host}/", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
    except:
        pass

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

    # Replay API with pagination
    if captured['url'] and captured['post_data']:
        api_url = captured['url']
        try:
            orig = json.loads(captured['post_data'])
        except:
            orig = {}

        for page_no in range(1, 50):
            params = dict(orig)
            params['offset'] = (page_no - 1) * params.get('limit', 10)
            params['limit'] = params.get('limit', 10)
            post_body = json.dumps(params)

            # Use single arg with embedded values
            js_code = """
                async (args) => {
                    try {
                        const resp = await fetch(args.url, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            credentials: 'include',
                            body: args.body
                        });
                        return await resp.text();
                    } catch(e) { return 'ERR:' + e.toString(); }
                }
            """
            result = await page.evaluate(js_code, {'url': api_url, 'body': post_body})

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
        print(f"  No API URL captured!", flush=True)

    print(f"  Total: {len(all_jobs)} jobs")
    relevant = [j for j in all_jobs if match_job(j.get('title',''))]
    print(f"  Relevant: {len(relevant)}")
    for j in sorted(relevant, key=lambda x: x.get('date',''), reverse=True)[:25]:
        print(f"    {j.get('date','')} | {j['title'][:55]} | id={j['id'][:20]}")

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
                jobs = await check_feishu(browser, name, host)
                results[name] = jobs
            except Exception as e:
                print(f"  {name} ERROR: {e}")
                results[name] = []

        await browser.close()

    with open('/pulp/find-job/r81_feishu_all.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\n=== Saved to r81_feishu_all.json ===")

asyncio.run(main())
