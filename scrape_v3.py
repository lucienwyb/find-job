#!/usr/bin/env python3
"""Focused scraping: mokahr API body capture + feishu pagination + hotjob fix."""
import json, time, re
from datetime import datetime
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fmt_date(d):
    if not d:
        return ''
    if isinstance(d, (int, float)):
        ts = int(d)
        if ts > 1e12: ts = ts // 1000
        if ts > 1e9:
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    s = str(d)
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return s


def scrape_mokahr(p, name, url, org_slug):
    """Scrape mokahr by capturing the jobs API response body."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    api_bodies = {}

    def on_response(response):
        u = response.url
        if any(x in u for x in ['website/jobs', 'group-by-job', 'jobs/module', 'jobs/v2']):
            try:
                body = response.json()
                api_bodies[u] = body
                print(f"  Captured: {u}")
            except:
                pass

    page.on("response", on_response)

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
    except:
        pass
    time.sleep(5)

    # Click to trigger job loading
    # Try clicking category/job items
    try:
        items = page.query_selector_all('div, span, a')
        for item in items[:200]:
            try:
                text = item.inner_text().strip()
                if text and len(text) < 50 and any(k in text for k in ['软件', '算法', '北京', '内核', '系统', '驱动', '嵌入式', '平台', '基础', '硬件']):
                    print(f"  Clicking: {text}")
                    item.click()
                    time.sleep(2)
                    break
            except:
                pass
    except:
        pass

    # Try clicking "查看更多"
    try:
        more = page.query_selector('text=查看更多')
        if more:
            more.click()
            time.sleep(2)
    except:
        pass

    time.sleep(2)
    page.remove_listener("response", on_response)

    # Analyze captured bodies
    all_jobs = []
    for u, body in api_bodies.items():
        print(f"\n  API: {u}")
        print(f"  Body keys: {list(body.keys()) if isinstance(body, dict) else type(body)}")

        if isinstance(body, dict) and 'data' in body:
            data = body['data']
            if isinstance(data, dict):
                print(f"  Data keys: {list(data.keys())}")
                # Try various job list field names
                for field in ['jobList', 'list', 'jobs', 'items', 'modules', 'result', 'data', 'positions']:
                    if field in data:
                        val = data[field]
                        print(f"  Found '{field}': type={type(val)}, len={len(val) if isinstance(val, (list,dict)) else 'N/A'}")
                        if isinstance(val, list):
                            for item in val:
                                if isinstance(item, dict):
                                    job_name = (item.get('name') or item.get('title') or item.get('jobName') or
                                               item.get('positionName') or item.get('jobTitle') or '')
                                    if job_name and isinstance(job_name, str) and len(job_name) > 2:
                                        all_jobs.append({
                                            'name': job_name,
                                            'department': str(item.get('department') or item.get('departmentName') or item.get('department_name') or ''),
                                            'city': str(item.get('city') or item.get('cityName') or item.get('workPlace') or item.get('location') or ''),
                                            'updateTime': fmt_date(item.get('updateTime') or item.get('createTime') or item.get('publishDate') or item.get('publishTime') or item.get('lastModifyTime') or item.get('modifyTime') or ''),
                                        })
                        elif isinstance(val, dict):
                            for sub_field in ['jobList', 'list', 'jobs', 'items']:
                                if sub_field in val:
                                    for item in val[sub_field]:
                                        if isinstance(item, dict):
                                            job_name = item.get('name') or item.get('title') or item.get('jobName') or ''
                                            if job_name and isinstance(job_name, str) and len(job_name) > 2:
                                                all_jobs.append({
                                                    'name': job_name,
                                                    'department': str(item.get('department') or item.get('departmentName') or ''),
                                                    'city': str(item.get('city') or item.get('cityName') or ''),
                                                    'updateTime': fmt_date(item.get('updateTime') or item.get('createTime') or item.get('publishDate') or ''),
                                                })
            elif isinstance(data, list):
                print(f"  Data is list, len={len(data)}")
                if data:
                    print(f"  Sample item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'not dict'}")

    # If still no jobs, try to extract from DOM
    if not all_jobs:
        print("  No jobs from API, trying DOM...")
        # Get all text from the page
        try:
            content = page.content()
            # Save for inspection
            with open(f'/tmp/mokahr_{org_slug}.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Saved HTML to /tmp/mokahr_{org_slug}.html ({len(content)} chars)")

            # Try extracting job names from DOM
            job_els = page.query_selector_all('[class*="job-name"], [class*="position-name"], [class*="JobName"], [class*="jobName"]')
            print(f"  Found {len(job_els)} job-name elements")
            for el in job_els:
                try:
                    text = el.inner_text().strip()
                    if text and len(text) > 2 and len(text) < 200:
                        all_jobs.append({'name': text, 'department': '', 'city': '', 'updateTime': ''})
                except:
                    pass
        except Exception as e:
            print(f"  DOM error: {e}")

    # Deduplicate
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        if j['name'] not in seen:
            seen.add(j['name'])
            unique_jobs.append(j)

    print(f"\n  TOTAL: {len(unique_jobs)} jobs")
    for j in unique_jobs:
        print(f"    - {j['name']} | {j.get('department','')} | {j.get('city','')} | {j.get('updateTime','')}")

    context.close()
    browser.close()
    return unique_jobs


def scrape_feishu_paginated(p, name, base_url, total_expected=100):
    """Scrape feishu with pagination to get all positions."""
    print(f"\n{'='*60}")
    print(f"[{name}] {base_url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_jobs = []
    seen_ids = set()

    def on_response(response):
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = response.json()
                if isinstance(body, dict) and 'data' in body:
                    data = body['data']
                    if isinstance(data, dict):
                        posts = data.get('job_posts') or data.get('posts') or data.get('list') or []
                        for post in posts:
                            if isinstance(post, dict):
                                pid = str(post.get('id') or post.get('post_id') or post.get('job_post_id') or '')
                                name = post.get('title') or post.get('name') or post.get('post_title') or ''
                                # Skip address-like entries
                                if name and '号' not in name and '座' not in name and '层' not in name:
                                    if pid not in seen_ids:
                                        seen_ids.add(pid)
                                        all_jobs.append({
                                            'name': name,
                                            'department': post.get('department') or post.get('department_name') or '',
                                            'city': '',
                                            'updateTime': fmt_date(post.get('update_time') or post.get('create_time') or post.get('publish_time') or post.get('update_time_ts') or ''),
                                        })
            except:
                pass

    page.on("response", on_response)

    try:
        page.goto(base_url, wait_until="networkidle", timeout=45000)
    except:
        pass
    time.sleep(5)

    # Get total count
    total = 0
    # Check captured count API
    count_api_data = {}
    def on_count(response):
        if 'job_post/count' in response.url:
            try:
                body = response.json()
                count_api_data['count'] = body
            except:
                pass
    page.on("response", on_count)

    # Now paginate by scrolling and clicking "加载更多" or using API
    # The feishu API uses offset/limit params
    # Let's try loading more pages by scrolling
    for i in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Try clicking "加载更多"
    for _ in range(20):
        try:
            load_more = page.query_selector('text=加载更多')
            if load_more:
                load_more.click()
                time.sleep(2)
            else:
                break
        except:
            break

    # Also try direct API call for all positions
    # Get CSRF token first
    csrf_token = None
    cookies = context.cookies()
    for cookie in cookies:
        if 'csrf' in cookie['name'].lower():
            csrf_token = cookie['value']

    # Try calling the search API with larger limit
    for offset in range(0, total_expected, 50):
        try:
            resp = page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{base_url}/api/v1/search/job/posts?keyword=&limit=50&offset={offset}&job_category_id_list=&tag_id_list=&location_code_list=&subject_id_list=', {{
                            method: 'GET',
                            headers: {{'Accept': 'application/json'}}
                        }});
                        return await r.json();
                    }} catch(e) {{
                        return {{error: e.message}};
                    }}
                }}
            """)
            if resp and 'data' in resp:
                data = resp['data']
                posts = data.get('job_posts') or data.get('posts') or data.get('list') or []
                if not posts:
                    break
                for post in posts:
                    pid = str(post.get('id') or post.get('post_id') or '')
                    name = post.get('title') or post.get('name') or ''
                    if name and '号' not in name and '座' not in name and '层' not in name:
                        if pid not in seen_ids:
                            seen_ids.add(pid)
                            all_jobs.append({
                                'name': name,
                                'department': post.get('department') or post.get('department_name') or '',
                                'city': '',
                                'updateTime': fmt_date(post.get('update_time') or post.get('create_time') or post.get('publish_time') or post.get('update_time_ts') or ''),
                            })
                if len(posts) < 50:
                    break
        except:
            break

    page.remove_listener("response", on_response)

    print(f"\n  TOTAL: {len(all_jobs)} jobs")
    for j in all_jobs:
        print(f"    - {j['name']} | {j.get('department','')} | {j.get('updateTime','')}")

    context.close()
    browser.close()
    return all_jobs


def scrape_hotjob(p, name, url):
    """Scrape hotjob.cn - try different approaches."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_jobs = []

    def on_response(response):
        u = response.url
        if 'api' in u.lower() or 'job' in u.lower():
            try:
                body = response.json()
                print(f"  API: {u[:150]}")
                # Try to find jobs
                if isinstance(body, dict):
                    data = body.get('data') or body
                    if isinstance(data, dict):
                        for field in ['jobList', 'list', 'jobs', 'items', 'result']:
                            if field in data:
                                vals = data[field]
                                if isinstance(vals, list):
                                    for item in vals:
                                        if isinstance(item, dict):
                                            name = item.get('name') or item.get('title') or item.get('jobName') or ''
                                            if name and isinstance(name, str) and len(name) > 2:
                                                all_jobs.append({
                                                    'name': name,
                                                    'department': str(item.get('department') or item.get('departmentName') or ''),
                                                    'city': str(item.get('city') or item.get('cityName') or item.get('workPlace') or ''),
                                                    'updateTime': fmt_date(item.get('updateTime') or item.get('createTime') or item.get('publishDate') or item.get('lastModifyTime') or ''),
                                                })
            except:
                pass

    page.on("response", on_response)

    # Try the URL with trailing slash
    for try_url in [url, url + '/', url + '/index']:
        try:
            page.goto(try_url, wait_until="networkidle", timeout=30000)
            time.sleep(5)
            break
        except:
            continue

    # Scroll
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Check if it redirected
    current_url = page.url
    print(f"  Current URL: {current_url}")

    # Try to get page content
    try:
        content = page.content()
        print(f"  Page content length: {len(content)}")
        if len(content) < 1000:
            print(f"  Content: {content[:500]}")
    except:
        pass

    # Try common hotjob API patterns
    api_urls = [
        f"{url}/api/get-job-list",
        f"{url}/api/job/list",
        "https://wecruit.hotjob.cn/api/get-job-list",
    ]
    for api_url in api_urls:
        try:
            resp = page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{api_url}', {{headers: {{'Accept': 'application/json'}}}});
                        return await r.json();
                    }} catch(e) {{
                        return {{error: e.message}};
                    }}
                }}
            """)
            if resp and 'error' not in resp:
                print(f"  Got API response from {api_url}")
                print(f"  Response: {json.dumps(resp, ensure_ascii=False)[:500]}")
        except:
            pass

    print(f"\n  TOTAL: {len(all_jobs)} jobs")
    for j in all_jobs[:50]:
        print(f"    - {j['name']} | {j.get('department','')} | {j.get('city','')} | {j.get('updateTime','')}")

    page.remove_listener("response", on_response)
    context.close()
    browser.close()
    return all_jobs


def main():
    with sync_playwright() as p:
        # 1. Moonshot
        moonshot = scrape_mokahr(p, "月之暗面 Moonshot",
            "https://app.mokahr.com/apply/moonshot/148506", "moonshot")

        # 2. Yinhe
        yinhe = scrape_mokahr(p, "银河通用 Yinhe",
            "https://app.mokahr.com/social-recruitment/yinhetongyong/165929", "yinhe")

        # 3. Zhipu
        zhipu = scrape_mokahr(p, "智谱 Zhipu",
            "https://app.mokahr.com/social-recruitment/zphz/148983", "zhipu")

        # 4. Cambricon
        cambricon = scrape_mokahr(p, "寒武纪 Cambricon",
            "https://app.mokahr.com/apply/cambricon/1113", "cambricon")

        # 5. Horizon - try with different approach
        horizon = scrape_hotjob(p, "地平线 Horizon",
            "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a")

        # 6-8. Feishu sites with pagination
        robotera = scrape_feishu_paginated(p, "星动纪元 Robotera",
            "https://k0fqxcszc9.jobs.feishu.cn", 50)

        chitu = scrape_feishu_paginated(p, "清程极智 Chitu",
            "https://chitu-ai.jobs.feishu.cn", 50)

        onai = scrape_feishu_paginated(p, "零一万物 01AI",
            "https://01ai.jobs.feishu.cn", 50)

    all_data = {
        'moonshot': moonshot,
        'yinhe': yinhe,
        'zhipu': zhipu,
        'cambricon': cambricon,
        'horizon': horizon,
        'robotera': robotera,
        'chitu': chitu,
        '01ai': onai,
    }
    with open('/pulp/find-job/scrape_r52_v3.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\n\nSaved to /pulp/find-job/scrape_r52_v3.json")

if __name__ == '__main__':
    main()
