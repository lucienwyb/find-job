#!/usr/bin/env python3
"""Final extraction: mokahr from rendered DOM, feishu with full pagination, hotjob alternatives."""
import json, time, re
from datetime import datetime
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fmt_date(d):
    if not d: return ''
    if isinstance(d, (int, float)):
        ts = int(d)
        if ts > 1e12: ts = ts // 1000
        if ts > 1e9:
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    s = str(d)
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return s

KEYWORDS = ['内核', 'kernel', 'eBPF', 'ebpf', 'BPF', '系统软件', '系统工程师', 'BSP',
            '嵌入式', 'embedded', '驱动', 'driver', '存储', 'storage', '分布式',
            'Agent', 'infra', 'Infra', '基础设施', '虚拟化', 'container', 'Runtime',
            '高性能', '底层', '操作系统', '固件', 'firmware', '硬件', '异构', '加速',
            '编译器', 'compiler', 'CUDA', '算子', '平台', 'infra', '平台开发',
            '云原生', 'kubernetes', 'K8s', 'sre', 'SRE', 'site reliability',
            '分布式存储', '高性能计算', 'HPC', '异构计算', '推理引擎', '推理框架',
            'AI Infra', 'AI Infrastructure', 'MLSys', '训练框架']

def match_job(title):
    t = title.lower()
    for kw in KEYWORDS:
        if kw.lower() in t:
            return True
    return False


def scrape_mokahr_dom(p, name, url):
    """Scrape mokahr by extracting job titles from rendered DOM + click into categories."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    # Capture API responses for dates
    api_data = {}
    def on_response(response):
        u = response.url
        if any(x in u for x in ['website/jobs', 'group-by-job', 'jobs/module', 'jobs/v2', 'jobs/recent']):
            try:
                body = response.json()
                api_data[u] = body
            except:
                pass
    page.on("response", on_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except:
        pass
    time.sleep(5)

    # Extract job titles from DOM - they have title attribute
    jobs = []

    # Method 1: Extract from div[title] elements
    title_els = page.query_selector_all('div[title]')
    for el in title_els:
        try:
            title = el.get_attribute('title')
            if title and len(title) > 2 and len(title) < 200:
                # Filter out non-job titles
                skip = ['隐私', 'protocol', 'description', '关键词']
                if not any(s in title.lower() for s in skip):
                    # Try to find date near this element
                    parent_text = el.evaluate("el => el.closest('div[class]')?.innerText || ''")
                    jobs.append({
                        'name': title,
                        'department': '',
                        'city': '',
                        'updateTime': '',
                        'context': parent_text[:200] if parent_text else '',
                    })
        except:
            pass

    # Also extract from inner text of job items
    if not jobs:
        # Method 2: get all visible text that looks like job titles
        all_text = page.evaluate("""() => {
            const els = document.querySelectorAll('div, span, a, p');
            const texts = [];
            for (const el of els) {
                const text = el.innerText?.trim();
                if (text && text.length > 4 && text.length < 100 && !text.includes('\\n')) {
                    const title = el.getAttribute('title');
                    if (title) texts.push({title: title, text: text});
                }
            }
            return texts;
        }""")
        for item in (all_text or []):
            jobs.append({'name': item.get('title', item.get('text', '')), 'department': '', 'city': '', 'updateTime': '', 'context': ''})

    # Deduplicate
    seen = set()
    unique = []
    for j in jobs:
        if j['name'] not in seen and j['name'] and len(j['name']) > 2:
            seen.add(j['name'])
            unique.append(j)

    # Try to click into categories to get more jobs
    # For mokahr, click on category headers to expand job lists
    try:
        # Look for category-like elements (e.g., "软件类 共30个职位")
        cat_els = page.query_selector_all('div, span')
        clicked_cats = set()
        for el in cat_els:
            try:
                text = el.inner_text().strip()
                # Match patterns like "软件类" or "北京市"
                if re.match(r'^(软件|算法|硬件|工程|技术|平台|基础|北京|上海|深圳)', text) and len(text) < 50:
                    if text not in clicked_cats:
                        clicked_cats.add(text)
                        el.click()
                        time.sleep(2)

                        # Capture new jobs that appeared
                        new_title_els = page.query_selector_all('div[title]')
                        for ntel in new_title_els:
                            try:
                                title = ntel.get_attribute('title')
                                if title and len(title) > 2 and len(title) < 200 and title not in seen:
                                    seen.add(title)
                                    unique.append({'name': title, 'department': '', 'city': '', 'updateTime': '', 'context': ''})
                            except:
                                pass
                        break  # Only click first matching category
            except:
                pass
    except:
        pass

    # Try clicking "查看更多" to expand
    for _ in range(5):
        try:
            more = page.query_selector('text=查看更多')
            if more:
                more.click()
                time.sleep(2)
                # Capture new jobs
                new_els = page.query_selector_all('div[title]')
                for el in new_els:
                    try:
                        title = el.get_attribute('title')
                        if title and len(title) > 2 and title not in seen:
                            seen.add(title)
                            unique.append({'name': title, 'department': '', 'city': '', 'updateTime': '', 'context': ''})
                    except:
                        pass
            else:
                break
        except:
            break

    # Now try to capture job details by clicking into individual jobs
    # This will trigger API calls that may contain update dates
    time.sleep(2)

    # Try the necromancer decryption - the data field in API response might be base64 or encrypted
    for u, body in api_data.items():
        if isinstance(body, dict) and 'data' in body:
            data = body['data']
            necromancer = body.get('necromancer', '')
            if isinstance(data, str):
                # Might be encrypted/encoded data
                print(f"  API {u.split('/')[-1]}: data is string (len={len(data)}), necromancer present: {bool(necromancer)}")
                # Try to find job data within the rendered page that matches this data
            elif isinstance(data, dict):
                print(f"  API {u.split('/')[-1]}: data is dict with keys: {list(data.keys())[:10]}")

    page.remove_listener("response", on_response)

    print(f"\n  TOTAL: {len(unique)} jobs")
    for j in unique:
        matched = "★ MATCH" if match_job(j['name']) else ""
        print(f"    - {j['name']} {matched}")

    context.close()
    browser.close()
    return unique


def scrape_feishu_all(p, name, base_url):
    """Scrape feishu with full pagination via page.evaluate fetch."""
    print(f"\n{'='*60}")
    print(f"[{name}] {base_url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_jobs = []
    seen_ids = set()

    # Capture API responses
    def on_response(response):
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = response.json()
                if isinstance(body, dict) and 'data' in body:
                    data = body['data']
                    if isinstance(data, dict):
                        posts = data.get('job_posts') or data.get('posts') or []
                        for post in posts:
                            if isinstance(post, dict):
                                pid = str(post.get('id') or post.get('post_id') or '')
                                title = post.get('title') or post.get('name') or ''
                                if title and '号' not in title and '座' not in title and '层' not in title and '大厦' not in title:
                                    if pid not in seen_ids:
                                        seen_ids.add(pid)
                                        all_jobs.append({
                                            'name': title,
                                            'department': post.get('department') or post.get('department_name') or '',
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

    # Now use page.evaluate to fetch all pages
    offset = 0
    limit = 20
    while True:
        try:
            result = page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{base_url}/api/v1/search/job/posts?keyword=&limit={limit}&offset={offset}&job_category_id_list=&tag_id_list=&location_code_list=&subject_id_list=', {{
                            method: 'GET',
                            headers: {{'Accept': 'application/json', 'Content-Type': 'application/json'}}
                        }});
                        return await r.json();
                    }} catch(e) {{
                        return {{error: e.message}};
                    }}
                }}
            """)

            if not result or 'error' in result:
                print(f"  API error at offset {offset}: {result.get('error','unknown') if result else 'empty'}")
                break

            data = result.get('data', {})
            posts = data.get('job_posts') or data.get('posts') or []
            total = data.get('total', 0)

            for post in posts:
                pid = str(post.get('id') or post.get('post_id') or '')
                title = post.get('title') or post.get('name') or ''
                if title and '号' not in title and '座' not in title and '层' not in title and '大厦' not in title:
                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        all_jobs.append({
                            'name': title,
                            'department': post.get('department') or post.get('department_name') or '',
                            'updateTime': fmt_date(post.get('update_time') or post.get('create_time') or post.get('publish_time') or post.get('update_time_ts') or ''),
                        })

            print(f"  Page offset={offset}: got {len(posts)} posts, total so far: {len(all_jobs)}/{total}")
            offset += limit
            if not posts or len(posts) < limit:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"  Exception at offset {offset}: {e}")
            break

    page.remove_listener("response", on_response)

    print(f"\n  TOTAL: {len(all_jobs)} jobs")
    for j in all_jobs:
        matched = "★ MATCH" if match_job(j['name']) else ""
        print(f"    - {j['name']} | {j.get('updateTime','')} {matched}")

    context.close()
    browser.close()
    return all_jobs


def scrape_hotjob_alt(p, name, url):
    """Try various hotjob URLs and API patterns."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_jobs = []

    def on_response(response):
        u = response.url
        if any(x in u for x in ['api', 'job', 'position']):
            try:
                body = response.json()
                if isinstance(body, dict) and 'data' in body:
                    data = body['data']
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                name = item.get('name') or item.get('title') or item.get('jobName') or ''
                                if name and isinstance(name, str) and len(name) > 2:
                                    all_jobs.append({
                                        'name': name,
                                        'department': str(item.get('department') or item.get('departmentName') or ''),
                                        'city': str(item.get('city') or item.get('cityName') or item.get('workPlace') or ''),
                                        'updateTime': fmt_date(item.get('updateTime') or item.get('createTime') or item.get('publishDate') or item.get('lastModifyTime') or ''),
                                    })
                    elif isinstance(data, dict):
                        for field in ['jobList', 'list', 'jobs', 'items']:
                            if field in data:
                                for item in (data[field] if isinstance(data[field], list) else []):
                                    if isinstance(item, dict):
                                        job_name = item.get('name') or item.get('title') or item.get('jobName') or ''
                                        if job_name and isinstance(job_name, str) and len(job_name) > 2:
                                            all_jobs.append({
                                                'name': job_name,
                                                'department': str(item.get('department') or item.get('departmentName') or ''),
                                                'city': str(item.get('city') or item.get('cityName') or item.get('workPlace') or ''),
                                                'updateTime': fmt_date(item.get('updateTime') or item.get('createTime') or item.get('publishDate') or item.get('lastModifyTime') or ''),
                                            })
            except:
                pass

    page.on("response", on_response)

    # Try different URL patterns
    urls_to_try = [
        url,
        url + '/',
        "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a/",
        "https://wecruit.hotjob.cn/su64819a4f2f9d2433ba8b043a",
    ]

    for try_url in urls_to_try:
        print(f"  Trying: {try_url}")
        try:
            resp = page.goto(try_url, wait_until="domcontentloaded", timeout=15000)
            print(f"    Status: {resp.status if resp else 'N/A'}")
            time.sleep(3)
            if resp and resp.status == 200:
                # Check content
                content_len = len(page.content())
                print(f"    Content length: {content_len}")
                if content_len > 1000:
                    # Look for job listings
                    title_els = page.query_selector_all('div[title], span[title], [class*="job"], [class*="position"]')
                    for el in title_els:
                        try:
                            title = el.get_attribute('title') or el.inner_text().strip()
                            if title and len(title) > 2 and len(title) < 200:
                                all_jobs.append({'name': title, 'department': '', 'city': '', 'updateTime': ''})
                        except:
                            pass
                    break
        except Exception as e:
            print(f"    Error: {e}")

    # Try direct API call
    api_urls = [
        "https://wecruit.hotjob.cn/api/v1/jobs?pageSize=200&pageNo=1",
        "https://wecruit.hotjob.cn/api/get-job-list",
        "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a/api/job/list",
    ]
    for api_url in api_urls:
        try:
            result = page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{api_url}', {{headers: {{'Accept': 'application/json'}}}});
                        return {{status: r.status, body: await r.text()}};
                    }} catch(e) {{
                        return {{error: e.message}};
                    }}
                }}
            """)
            if result and result.get('status') == 200:
                print(f"  API hit: {api_url}")
                body = result.get('body', '')
                print(f"    Response: {body[:300]}")
                try:
                    j = json.loads(body)
                    if 'data' in j:
                        print(f"    Data type: {type(j['data'])}")
                except:
                    pass
        except:
            pass

    page.remove_listener("response", on_response)

    # Deduplicate
    seen = set()
    unique = []
    for j in all_jobs:
        if j['name'] not in seen:
            seen.add(j['name'])
            unique.append(j)

    print(f"\n  TOTAL: {len(unique)} jobs")
    for j in unique[:30]:
        matched = "★ MATCH" if match_job(j['name']) else ""
        print(f"    - {j['name']} | {j.get('department','')} | {j.get('city','')} | {j.get('updateTime','')} {matched}")
    if len(unique) > 30:
        print(f"    ... and {len(unique)-30} more")

    context.close()
    browser.close()
    return unique


def main():
    with sync_playwright() as p:
        # 1-4. Mokahr sites
        moonshot = scrape_mokahr_dom(p, "月之暗面 Moonshot",
            "https://app.mokahr.com/apply/moonshot/148506")

        yinhe = scrape_mokahr_dom(p, "银河通用 Yinhe",
            "https://app.mokahr.com/social-recruitment/yinhetongyong/165929")

        zhipu = scrape_mokahr_dom(p, "智谱 Zhipu",
            "https://app.mokahr.com/social-recruitment/zphz/148983")

        cambricon = scrape_mokahr_dom(p, "寒武纪 Cambricon",
            "https://app.mokahr.com/apply/cambricon/1113")

        # 5. Horizon
        horizon = scrape_hotjob_alt(p, "地平线 Horizon",
            "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a")

        # 6-8. Feishu sites
        robotera = scrape_feishu_all(p, "星动纪元 Robotera",
            "https://k0fqxcszc9.jobs.feishu.cn")

        chitu = scrape_feishu_all(p, "清程极智 Chitu",
            "https://chitu-ai.jobs.feishu.cn")

        onai = scrape_feishu_all(p, "零一万物 01AI",
            "https://01ai.jobs.feishu.cn")

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
    with open('/pulp/find-job/scrape_r52_final.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\n\nSaved to /pulp/find-job/scrape_r52_final.json")

if __name__ == '__main__':
    main()
