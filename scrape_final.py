#!/usr/bin/env python3
"""Final approach: route interception for feishu + mokahr necromancer decryption via JS."""
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
            '编译器', 'compiler', 'CUDA', '算子', '平台', '平台开发',
            '云原生', 'kubernetes', 'K8s', 'sre', 'SRE',
            '分布式存储', '高性能计算', 'HPC', '异构计算', '推理引擎', '推理框架',
            'AI Infra', 'AI Infrastructure', 'MLSys', '训练框架', 'Coding Agent',
            '系统开发', '性能优化', '后端', 'backend', '服务端']

def match_job(title):
    t = title.lower()
    for kw in KEYWORDS:
        if kw.lower() in t:
            return True
    return False


def scrape_feishu(p, name, base_url):
    """Scrape feishu using route interception to increase limit."""
    print(f"\n{'='*60}")
    print(f"[{name}] {base_url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_jobs = []
    seen_ids = set()
    total_reported = 0

    # Intercept the search API request and increase limit
    def handle_route(route, request):
        url = request.url
        if 'search/job/posts' in url and 'limit=10' in url:
            # Replace limit=10 with limit=200
            new_url = url.replace('limit=10', 'limit=200')
            route.continue_(url=new_url)
        else:
            route.continue_()

    page.route("**/api/v1/search/job/posts**", handle_route)

    def on_response(response):
        nonlocal total_reported
        u = response.url
        if 'search/job/posts' in u:
            try:
                body = response.json()
                if isinstance(body, dict) and 'data' in body:
                    data = body['data']
                    if isinstance(data, dict):
                        posts = data.get('job_posts') or data.get('posts') or []
                        total_reported = data.get('total', total_reported)
                        for post in posts:
                            if isinstance(post, dict):
                                pid = str(post.get('id') or post.get('post_id') or '')
                                title = post.get('title') or post.get('name') or ''
                                if title and not any(x in title for x in ['号', '座', '层', '大厦', '号楼', '号楼']):
                                    if pid not in seen_ids:
                                        seen_ids.add(pid)
                                        all_jobs.append({
                                            'name': title,
                                            'department': post.get('department') or '',
                                            'updateTime': fmt_date(post.get('update_time') or post.get('create_time') or post.get('publish_time') or post.get('update_time_ts') or ''),
                                            'city': '',
                                        })
            except:
                pass

    page.on("response", on_response)

    try:
        page.goto(base_url, wait_until="networkidle", timeout=45000)
    except:
        pass
    time.sleep(5)

    # Try clicking on "北京" location filter to trigger API call with all Beijing jobs
    try:
        beijing_els = page.query_selector_all('text=北京')
        for el in beijing_els[:2]:
            try:
                el.click()
                time.sleep(3)
            except:
                pass
    except:
        pass

    # Scroll to trigger lazy loading
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Try clicking load more
    for _ in range(10):
        try:
            load_more = page.query_selector('text=加载更多')
            if load_more:
                load_more.click()
                time.sleep(2)
            else:
                break
        except:
            break

    page.remove_listener("response", on_response)

    print(f"  Total reported: {total_reported}")
    print(f"  Jobs captured: {len(all_jobs)}")

    # Sort by date descending
    all_jobs.sort(key=lambda x: x.get('updateTime', ''), reverse=True)

    for j in all_jobs:
        matched = "★ MATCH" if match_job(j['name']) else ""
        print(f"    - {j['name']} | {j.get('updateTime','')} {matched}")

    context.close()
    browser.close()
    return all_jobs


def scrape_mokahr(p, name, url):
    """Scrape mokahr by clicking through categories and extracting DOM."""
    print(f"\n{'='*60}")
    print(f"[{name}]")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_jobs = []
    seen_names = set()

    # Capture API responses with necromancer data - try to decrypt
    necromancer_data = []

    def on_response(response):
        u = response.url
        if any(x in u for x in ['website/jobs', 'group-by-job', 'jobs/module', 'jobs/v2', 'jobs/recent']):
            try:
                body = response.json()
                if isinstance(body, dict) and 'necromancer' in body:
                    necromancer_data.append({
                        'url': u,
                        'data': body.get('data'),
                        'necromancer': body.get('necromancer'),
                    })
            except:
                pass

    page.on("response", on_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except:
        pass
    time.sleep(5)

    # Try to decrypt necromancer data using the page's own JS
    # The mokahr JS bundle must have a decrypt function. Let's try to find and call it.
    if necromancer_data:
        for nd in necromancer_data[:1]:  # Try first API response
            api_name = nd['url'].split('/')[-1].split('?')[0]
            print(f"\n  Trying to decrypt {api_name} (data len={len(nd['data']) if nd['data'] else 0})")

            # The mokahr frontend uses a specific decryption. Let me look for it.
            # Common pattern: the JS uses a function like decrypt(encryptedData, key)
            # that does XOR or AES decryption

            # Try to find the function by examining the JS modules
            decrypt_attempt = page.evaluate("""
                (params) => {
                    const data = params.data;
                    const necro = params.necromancer;

                    // Method 1: The data might be a JSON string that's been XOR'd with the necromancer key
                    // But first, let's check if the data is already JSON
                    if (typeof data === 'object') {
                        return {method: 'already_json', result: JSON.stringify(data).substring(0, 500)};
                    }

                    // Method 2: The mokahr JS likely uses a specific function.
                    // Let's look for it in the webpack chunk
                    // Common names: decryptData, necromancerDecrypt, _decrypt

                    // Try to find the function by checking the page's JS context
                    const result = {attempts: []};

                    // Attempt A: Simple XOR with necromancer key
                    try {
                        let decrypted = '';
                        for (let i = 0; i < data.length; i++) {
                            decrypted += String.fromCharCode(
                                data.charCodeAt(i) ^ necro.charCodeAt(i % necro.length)
                            );
                        }
                        // Check if it looks like JSON
                        if (decrypted.startsWith('{') || decrypted.startsWith('[')) {
                            result.attempts.push({method: 'xor', success: true, preview: decrypted.substring(0, 300)});
                            result.best = decrypted;
                        } else {
                            result.attempts.push({method: 'xor', success: false, preview: decrypted.substring(0, 100)});
                        }
                    } catch(e) {
                        result.attempts.push({method: 'xor', error: e.message});
                    }

                    // Attempt B: base64 decode then XOR
                    try {
                        const decoded = atob(data);
                        let decrypted = '';
                        for (let i = 0; i < decoded.length; i++) {
                            decrypted += String.fromCharCode(
                                decoded.charCodeAt(i) ^ necro.charCodeAt(i % necro.length)
                            );
                        }
                        if (decrypted.startsWith('{') || decrypted.startsWith('[')) {
                            result.attempts.push({method: 'b64+xor', success: true, preview: decrypted.substring(0, 300)});
                            result.best = decrypted;
                        } else {
                            result.attempts.push({method: 'b64+xor', success: false, preview: decrypted.substring(0, 100)});
                        }
                    } catch(e) {
                        result.attempts.push({method: 'b64+xor', error: e.message});
                    }

                    // Attempt C: The necromancer might be base64 encoded key
                    try {
                        const keyBytes = atob(necro);
                        const decoded = atob(data);
                        let decrypted = '';
                        for (let i = 0; i < decoded.length; i++) {
                            decrypted += String.fromCharCode(
                                decoded.charCodeAt(i) ^ keyBytes.charCodeAt(i % keyBytes.length)
                            );
                        }
                        if (decrypted.startsWith('{') || decrypted.startsWith('[')) {
                            result.attempts.push({method: 'b64key+b64data+xor', success: true, preview: decrypted.substring(0, 300)});
                            result.best = decrypted;
                        }
                    } catch(e) {
                        result.attempts.push({method: 'b64key+b64data+xor', error: e.message});
                    }

                    // Attempt D: Try using AES with the necromancer as key
                    // This would require crypto-js which might be in the page
                    // Skip for now

                    // Attempt E: Try RC4
                    try {
                        // RC4 implementation
                        let s = [];
                        for (let i = 0; i < 256; i++) s[i] = i;
                        let j = 0;
                        for (let i = 0; i < 256; i++) {
                            j = (j + s[i] + necro.charCodeAt(i % necro.length)) % 256;
                            [s[i], s[j]] = [s[j], s[i]];
                        }
                        let i = 0; j = 0;
                        let decrypted = '';
                        for (let k = 0; k < data.length; k++) {
                            i = (i + 1) % 256;
                            j = (j + s[i]) % 256;
                            [s[i], s[j]] = [s[j], s[i]];
                            decrypted += String.fromCharCode(data.charCodeAt(k) ^ s[(s[i] + s[j]) % 256]);
                        }
                        if (decrypted.startsWith('{') || decrypted.startsWith('[')) {
                            result.attempts.push({method: 'rc4', success: true, preview: decrypted.substring(0, 300)});
                            result.best = decrypted;
                        } else {
                            result.attempts.push({method: 'rc4', success: false, preview: decrypted.substring(0, 100)});
                        }
                    } catch(e) {
                        result.attempts.push({method: 'rc4', error: e.message});
                    }

                    return result;
                }
            """, {'data': nd['data'], 'necromancer': nd['necromancer']})

            if decrypt_attempt:
                for attempt in decrypt_attempt.get('attempts', []):
                    status = "SUCCESS" if attempt.get('success') else "FAIL"
                    preview = attempt.get('preview', attempt.get('error', ''))
                    print(f"    {attempt['method']}: {status} - {preview[:100]}")

                if decrypt_attempt.get('best'):
                    try:
                        decrypted_json = json.loads(decrypt_attempt['best'])
                        # Extract jobs from decrypted JSON
                        def extract_jobs_from_json(obj, depth=0):
                            jobs = []
                            if depth > 5: return jobs
                            if isinstance(obj, list):
                                for item in obj:
                                    if isinstance(item, dict):
                                        name = (item.get('name') or item.get('title') or item.get('jobName') or
                                               item.get('positionName') or item.get('jobTitle') or '')
                                        if name and isinstance(name, str) and len(name) > 2 and len(name) < 200:
                                            date = item.get('updateTime') or item.get('createTime') or item.get('publishDate') or item.get('modifyTime') or ''
                                            if isinstance(date, (int, float)):
                                                date = fmt_date(date)
                                            jobs.append({
                                                'name': name,
                                                'department': str(item.get('department') or item.get('departmentName') or ''),
                                                'updateTime': str(date) if date else '',
                                                'city': str(item.get('city') or item.get('cityName') or ''),
                                            })
                                    jobs.extend(extract_jobs_from_json(item, depth+1))
                            elif isinstance(obj, dict):
                                for v in obj.values():
                                    jobs.extend(extract_jobs_from_json(v, depth+1))
                            return jobs

                        extracted = extract_jobs_from_json(decrypted_json)
                        for j in extracted:
                            if j['name'] not in seen_names:
                                seen_names.add(j['name'])
                                all_jobs.append(j)
                        print(f"    Extracted {len(extracted)} jobs from decrypted data")
                    except json.JSONDecodeError:
                        print(f"    Decrypted data is not valid JSON")

    # Also extract from DOM by clicking through categories
    # For Yinhe: click on each category (算法类, 软件类, etc.)
    # For Zhipu: click on each city (北京, 上海, etc.)
    # For Moonshot: click "查看更多"
    # For Cambricon: already shows all jobs

    # Click "查看更多" for Moonshot
    try:
        more = page.query_selector('text=查看更多')
        if more:
            more.click()
            time.sleep(3)
            # Extract new jobs from DOM
            title_els = page.query_selector_all('div[title]')
            for el in title_els:
                try:
                    title = el.get_attribute('title')
                    if title and len(title) > 3 and len(title) < 200 and title not in seen_names:
                        seen_names.add(title)
                        all_jobs.append({'name': title, 'department': '', 'updateTime': '', 'city': ''})
                except:
                    pass
    except:
        pass

    # For Yinhe/Zhipu: click through categories
    try:
        cat_items = page.query_selector_all('div, span')
        for item in cat_items:
            try:
                text = item.inner_text().strip()
                # Match category patterns like "软件类\n共30个职位" or "北京市\n共39个职位"
                if re.match(r'^(软件|算法|硬件|工程|技术|平台|基础|北京|上海|深圳)', text) and '共' in text and len(text) < 50:
                    item.click()
                    time.sleep(3)
                    # Extract jobs from the now-visible list
                    title_els = page.query_selector_all('div[title]')
                    for el in title_els:
                        try:
                            title = el.get_attribute('title')
                            if title and len(title) > 3 and len(title) < 200 and title not in seen_names:
                                seen_names.add(title)
                                all_jobs.append({'name': title, 'department': '', 'updateTime': '', 'city': ''})
                        except:
                            pass
                    break  # Only click first category for now
            except:
                pass
    except:
        pass

    page.remove_listener("response", on_response)

    # Also try to get the full job list from DOM
    title_els = page.query_selector_all('div[title]')
    for el in title_els:
        try:
            title = el.get_attribute('title')
            if title and len(title) > 3 and len(title) < 200 and title not in seen_names:
                # Skip non-job titles
                if not any(x in title for x in ['关于我们', '社招职位', '校招', '搜索', '内部推荐', '员工内推', '产品与服务', '繁星', '共建', '开放', '银河北京', '银河深圳', '银河苏州', 'Think Big', '一群正直']):
                    seen_names.add(title)
                    all_jobs.append({'name': title, 'department': '', 'updateTime': '', 'city': ''})
        except:
            pass

    print(f"\n  TOTAL: {len(all_jobs)} jobs")
    for j in all_jobs:
        matched = "★ MATCH" if match_job(j['name']) else ""
        print(f"    - {j['name']} | dept={j.get('department','')} | date={j.get('updateTime','')} {matched}")

    context.close()
    browser.close()
    return all_jobs


def main():
    with sync_playwright() as p:
        # Mokahr sites
        moonshot = scrape_mokahr(p, "月之暗面 Moonshot",
            "https://app.mokahr.com/apply/moonshot/148506")

        yinhe = scrape_mokahr(p, "银河通用 Yinhe",
            "https://app.mokahr.com/social-recruitment/yinhetongyong/165929")

        zhipu = scrape_mokahr(p, "智谱 Zhipu",
            "https://app.mokahr.com/social-recruitment/zphz/148983")

        cambricon = scrape_mokahr(p, "寒武纪 Cambricon",
            "https://app.mokahr.com/apply/cambricon/1113")

        # Feishu sites with route interception
        robotera = scrape_feishu(p, "星动纪元 Robotera",
            "https://k0fqxcszc9.jobs.feishu.cn")

        chitu = scrape_feishu(p, "清程极智 Chitu",
            "https://chitu-ai.jobs.feishu.cn")

        onai = scrape_feishu(p, "零一万物 01AI",
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
    with open('/pulp/find-job/scrape_r52_final2.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\n\nSaved to /pulp/find-job/scrape_r52_final2.json")

if __name__ == '__main__':
    main()
