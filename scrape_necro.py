#!/usr/bin/env python3
"""Scrape using page's own JS context for decryption (mokahr) and CSRF-protected API (feishu)."""
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
            'AI Infra', 'AI Infrastructure', 'MLSys', '训练框架', 'Coding Agent']

def match_job(title):
    t = title.lower()
    for kw in KEYWORDS:
        if kw.lower() in t:
            return True
    return False

def scrape_mokahr_necromancer(p, name, url, org_slug):
    """Scrape mokahr by decrypting necromancer data using page's JS."""
    print(f"\n{'='*60}")
    print(f"[{name}]")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    # Capture API responses
    api_data = []
    def on_response(response):
        u = response.url
        if any(x in u for x in ['website/jobs', 'group-by-job', 'jobs/module', 'jobs/v2', 'jobs/recent']):
            try:
                body = response.json()
                api_data.append({'url': u, 'body': body})
            except:
                pass
    page.on("response", on_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except:
        pass
    time.sleep(5)

    # Try to use page's JS to decrypt necromancer data
    # The mokahr frontend likely has a global decryption function
    # Let's find it
    decrypt_result = page.evaluate("""
        () => {
            // Try to find the decryption function
            const results = [];

            // Check if there's a global decrypt function
            if (typeof window.__NECROMANCER_DECRYPT__ === 'function') {
                results.push('found __NECROMANCER_DECRYPT__');
            }

            // Check for common mokahr global objects
            const globals = Object.keys(window).filter(k =>
                k.toLowerCase().includes('necro') ||
                k.toLowerCase().includes('decrypt') ||
                k.toLowerCase().includes('moka')
            );
            results.push('Globals: ' + globals.join(', '));

            // Try to find the decryption in the webpack modules
            if (window.webpackJsonp || window.__webpack_modules__) {
                results.push('webpack found');
            }

            return results;
        }
    """)
    print(f"  JS globals check: {decrypt_result}")

    # Try to intercept the XHR response and decrypt it using the page's own code
    # The page must have already decrypted and rendered the data
    # Let's get all text content from the page
    full_text = page.evaluate("""
        () => {
            // Get all text nodes that look like job titles
            const allElements = document.querySelectorAll('*');
            const jobTexts = [];
            for (const el of allElements) {
                const title = el.getAttribute('title');
                if (title && title.length > 3 && title.length < 200) {
                    jobTexts.push(title);
                }
                // Also check class names for job-related content
                const className = el.className;
                if (typeof className === 'string' && className.includes('job')) {
                    const text = el.innerText?.trim();
                    if (text && text.length > 3 && text.length < 200) {
                        jobTexts.push(text);
                    }
                }
            }
            return [...new Set(jobTexts)];
        }
    """)

    print(f"  DOM text extraction: {len(full_text)} items")
    for t in full_text[:20]:
        print(f"    {t}")

    # Try calling the mokahr API directly from page context with proper headers
    # and then decrypt using the same JS that the page uses
    api_urls = [
        f"https://app.mokahr.com/api/outer/ats-apply/website/jobs/v2?limit=200&offset=0",
        f"https://app.mokahr.com/api/outer/ats-apply/website/jobs/module",
        f"https://app.mokahr.com/api/outer/ats-apply/website/jobs/recent?limit=200",
    ]

    for api_url in api_urls:
        try:
            js_code = """
                async (apiUrl) => {
                    try {
                        const r = await fetch(apiUrl, {
                            headers: {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json',
                            },
                            credentials: 'include'
                        });
                        const data = await r.json();
                        if (data.necromancer && data.data && typeof data.data === 'string') {
                            let decrypted = null;

                            // Try using page's own decrypt function
                            if (typeof window.__decrypt === 'function') {
                                try { decrypted = window.__decrypt(data.data, data.necromancer); } catch(e) {}
                            }

                            // Try XOR
                            try {
                                const key = data.necromancer;
                                const encrypted = data.data;
                                let result = '';
                                for (let i = 0; i < encrypted.length; i++) {
                                    result += String.fromCharCode(encrypted.charCodeAt(i) ^ key.charCodeAt(i % key.length));
                                }
                                decrypted = result;
                            } catch(e) {}

                            // Try base64 decode then XOR
                            try {
                                const key = data.necromancer;
                                const encrypted = atob(data.data);
                                let result = '';
                                for (let i = 0; i < encrypted.length; i++) {
                                    result += String.fromCharCode(encrypted.charCodeAt(i) ^ key.charCodeAt(i % key.length));
                                }
                                decrypted = result;
                            } catch(e) {}

                            return {
                                api: apiUrl.split('/').pop().split('?')[0],
                                necromancer: data.necromancer.substring(0, 50),
                                data_preview: data.data.substring(0, 100),
                                decrypted_preview: decrypted ? decrypted.substring(0, 500) : null,
                                decrypted_len: decrypted ? decrypted.length : 0,
                            };
                        }
                        return {
                            api: apiUrl.split('/').pop().split('?')[0],
                            body_keys: Object.keys(data),
                            data_type: typeof data.data,
                            data_preview: typeof data.data === 'string' ? data.data.substring(0, 100) : null,
                        };
                    } catch(e) {
                        return {error: e.message};
                    }
                }
            """
            result = page.evaluate(js_code, api_url)

            if result and 'error' not in result:
                print(f"\n  API {result.get('api','')}:")
                if result.get('decrypted_preview'):
                    print(f"    Decrypted ({result.get('decrypted_len',0)} chars): {result['decrypted_preview'][:300]}")
                else:
                    print(f"    Keys: {result.get('body_keys','')}")
                    if result.get('necromancer'):
                        print(f"    Necromancer: {result.get('necromancer','')}")
                    if result.get('data_preview'):
                        print(f"    Data preview: {result.get('data_preview','')}")
        except Exception as e:
            print(f"  API call error: {e}")

    # Also try to extract data from the already-decrypted DOM
    # Wait for page to fully render and scroll
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Get all visible job titles
    dom_jobs = page.evaluate("""
        () => {
            const jobs = [];
            // Look for elements with title attributes
            const els = document.querySelectorAll('[title]');
            for (const el of els) {
                const title = el.getAttribute('title');
                if (title && title.length > 3 && title.length < 200) {
                    // Get parent text for context (might contain date)
                    const parent = el.parentElement;
                    const context = parent ? parent.innerText.substring(0, 300) : '';
                    jobs.push({title: title, context: context});
                }
            }
            return jobs;
        }
    """)

    print(f"\n  DOM [title] elements: {len(dom_jobs)}")
    for j in dom_jobs:
        title = j.get('title', '')
        context = j.get('context', '')
        # Try to extract date from context
        date_match = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2})', context)
        date = date_match.group(1) if date_match else ''
        matched = "★" if match_job(title) else ""
        print(f"    - {title} | date={date} {matched}")

    page.remove_listener("response", on_response)

    # Return combined results
    return [{'name': j.get('title',''), 'updateTime': '', 'context': j.get('context','')} for j in dom_jobs]


def scrape_feishu_csrf(p, name, base_url):
    """Scrape feishu using CSRF token from page context."""
    print(f"\n{'='*60}")
    print(f"[{name}] {base_url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_jobs = []
    seen_ids = set()

    # Capture initial API responses
    def on_response(response):
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = response.json()
                if isinstance(body, dict) and 'data' in body:
                    data = body['data']
                    if isinstance(data, dict):
                        posts = data.get('job_posts') or data.get('posts') or []
                        total = data.get('total', 0)
                        for post in posts:
                            if isinstance(post, dict):
                                pid = str(post.get('id') or post.get('post_id') or '')
                                title = post.get('title') or post.get('name') or ''
                                if title and not any(x in title for x in ['号', '座', '层', '大厦', '号楼']):
                                    if pid not in seen_ids:
                                        seen_ids.add(pid)
                                        all_jobs.append({
                                            'name': title,
                                            'department': post.get('department') or '',
                                            'updateTime': fmt_date(post.get('update_time') or post.get('create_time') or post.get('publish_time') or post.get('update_time_ts') or ''),
                                        })
                        if total:
                            print(f"  Total positions reported: {total}")
            except:
                pass

    page.on("response", on_response)

    try:
        page.goto(base_url, wait_until="networkidle", timeout=45000)
    except:
        pass
    time.sleep(5)

    # Now get CSRF token and make paginated requests
    # The CSRF token is in cookies set by the /api/v1/csrf/token endpoint
    cookies = context.cookies()
    csrf_token = None
    csrf_header = None
    for cookie in cookies:
        if 'csrf' in cookie['name'].lower():
            csrf_token = cookie['value']
            csrf_header = cookie['name']

    print(f"  CSRF: {csrf_header}={csrf_token[:20] if csrf_token else 'None'}...")

    # Also check if there's a CSRF meta tag
    meta_csrf = page.evaluate("""
        () => {
            const meta = document.querySelector('meta[name="csrf-token"]');
            return meta ? meta.content : null;
        }
    """)
    if meta_csrf:
        csrf_token = meta_csrf
        print(f"  Meta CSRF: {csrf_token[:20]}...")

    # Make paginated API calls using the page's fetch with CSRF token
    offset = 0
    limit = 20
    while True:
        # Build the API URL
        api_path = f"/api/v1/search/job/posts?keyword=&limit={limit}&offset={offset}&job_category_id_list=&tag_id_list=&location_code_list=&subject_id_list="
        full_api_url = base_url + api_path

        # Build headers dict as JS object string
        headers_parts = ["'Accept': 'application/json'", "'Content-Type': 'application/json'"]
        if csrf_token and csrf_header:
            headers_parts.append(f"'{csrf_header}': '{csrf_token}'")
        headers_js = "{" + ", ".join(headers_parts) + "}"

        js_code = """
            async (params) => {
                try {
                    const r = await fetch(params.url, {
                        method: 'GET',
                        headers: params.headers,
                        credentials: 'include'
                    });
                    const text = await r.text();
                    try {
                        return {status: r.status, json: JSON.parse(text)};
                    } catch(e) {
                        return {status: r.status, text: text.substring(0, 200)};
                    }
                } catch(e) {
                    return {error: e.message};
                }
            }
        """
        # Build headers as dict
        headers_dict = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if csrf_token and csrf_header:
            headers_dict[csrf_header] = csrf_token
        result = page.evaluate(js_code, {'url': full_api_url, 'headers': headers_dict})

        if not result:
            break

        if 'error' in result:
            print(f"  Error at offset {offset}: {result['error']}")
            break

        if result.get('text'):
            # HTML response, not JSON
            print(f"  HTML response at offset {offset}: {result['text'][:100]}")
            break

        data = result.get('json', {}).get('data', {})
        posts = data.get('job_posts') or data.get('posts') or []
        total = data.get('total', 0)

        for post in posts:
            pid = str(post.get('id') or post.get('post_id') or '')
            title = post.get('title') or post.get('name') or ''
            if title and not any(x in title for x in ['号', '座', '层', '大厦', '号楼']):
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    all_jobs.append({
                        'name': title,
                        'department': post.get('department') or '',
                        'updateTime': fmt_date(post.get('update_time') or post.get('create_time') or post.get('publish_time') or post.get('update_time_ts') or ''),
                    })

        print(f"  offset={offset}: {len(posts)} posts, total={len(all_jobs)}/{total}")
        offset += limit
        if not posts or len(posts) < limit:
            break
        time.sleep(0.5)

    page.remove_listener("response", on_response)

    print(f"\n  TOTAL: {len(all_jobs)} jobs")
    for j in all_jobs:
        matched = "★ MATCH" if match_job(j['name']) else ""
        print(f"    - {j['name']} | {j.get('updateTime','')} {matched}")

    context.close()
    browser.close()
    return all_jobs


def main():
    with sync_playwright() as p:
        # Mokahr sites - try necromancer decryption
        moonshot = scrape_mokahr_necromancer(p, "月之暗面 Moonshot",
            "https://app.mokahr.com/apply/moonshot/148506", "moonshot")

        yinhe = scrape_mokahr_necromancer(p, "银河通用 Yinhe",
            "https://app.mokahr.com/social-recruitment/yinhetongyong/165929", "yinhe")

        zhipu = scrape_mokahr_necromancer(p, "智谱 Zhipu",
            "https://app.mokahr.com/social-recruitment/zphz/148983", "zhipu")

        cambricon = scrape_mokahr_necromancer(p, "寒武纪 Cambricon",
            "https://app.mokahr.com/apply/cambricon/1113", "cambricon")

        # Feishu sites - try CSRF-protected pagination
        robotera = scrape_feishu_csrf(p, "星动纪元 Robotera",
            "https://k0fqxcszc9.jobs.feishu.cn")

        chitu = scrape_feishu_csrf(p, "清程极智 Chitu",
            "https://chitu-ai.jobs.feishu.cn")

        onai = scrape_feishu_csrf(p, "零一万物 01AI",
            "https://01ai.jobs.feishu.cn")

    all_data = {
        'moonshot': moonshot,
        'yinhe': yinhe,
        'zhipu': zhipu,
        'cambricon': cambricon,
        'robotera': robotera,
        'chitu': chitu,
        '01ai': onai,
    }
    with open('/pulp/find-job/scrape_r52_necro.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\n\nSaved to /pulp/find-job/scrape_r52_necro.json")

if __name__ == '__main__':
    main()
