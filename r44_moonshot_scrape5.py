#!/usr/bin/env python3
"""Round 44 v5: Try to get all 98 jobs by using page's internal JS and filters."""
import json, re, time, sys
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT_JSON = "/pulp/find-job/r44_moonshot.json"

KEYWORDS = [
    "kernel", "内核", "eBPF", "系统", "embedded", "嵌入式", "存储", "storage",
    "Agent", "Infra", "infra", "SRE", "runtime", "运行时", "分布式",
    "C++", "Rust", "驱动", "平台", "基础设施", "推理", "inference",
    "调度", "scheduler", "RDMA", "高性能", "底层", "低延迟",
]

def clean_text(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S|re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S|re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    txt = re.sub(r"&[a-z]+;", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()

def parse_jobs_from_text(txt):
    """Extract jobs with dates from text."""
    jobs = {}
    # Better pattern - capture title before 发布于
    # The title is between the last "急" or job separator and "发布于"
    pattern = r'((?:急\s+)?[一-鿿\w/\-（）·,.\s&;:#+|]+?)\s+发布于\s+(\d{4}-\d{2}-\d{2})'
    matches = list(re.finditer(pattern, txt))
    for m in matches:
        title = re.sub(r'^急\s*', '', m.group(1)).strip()
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) > 100:  # Skip page headers
            continue
        date = m.group(2)
        after = txt[m.end():m.end()+300]
        # Try to extract location and department
        info_match = re.search(
            r'(全职|兼职|实习)\s+\1?\s*\|?\s*([一-鿿A-Za-z]+)\s+\2?\s*\|?\s*([一-鿿]+)',
            after
        )
        loc = ""
        dept = ""
        if info_match:
            dept = info_match.group(2) if info_match.group(2) else ""
            loc = info_match.group(3) if info_match.group(3) else ""
        key = (title, date)
        if key not in jobs:
            jobs[key] = {
                "title": title,
                "publish_date": date,
                "location": loc,
                "department": dept,
            }
    return list(jobs.values())

def main():
    print("=== Moonshot Careers Scrape v5 (Round 44) ===", flush=True)
    p = sync_playwright().start()
    b = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled"],
        proxy={"server": PROXY}
    )
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 1200},
        locale="zh-CN",
        ignore_https_errors=True,
    )

    page = ctx.new_page()
    base_url = "https://app.mokahr.com/apply/moonshot/148506"

    # Navigate to #/jobs
    print("\n--- Navigate to #/jobs ---", flush=True)
    try:
        page.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
    except:
        page.goto(f"{base_url}#/jobs", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)

    all_jobs = {}

    # Approach 1: Try to use page's internal JS to fetch all jobs
    print("\n--- Approach 1: Internal JS fetch ---", flush=True)
    try:
        result = page.evaluate("""
            async () => {
                const results = [];

                // Try to fetch the jobs/recent API directly
                try {
                    const resp = await fetch('/api/outer/ats-apply/website/jobs/recent', {
                        headers: {'Accept': 'application/json'}
                    });
                    const data = await resp.json();
                    results.push({
                        source: 'jobs/recent',
                        type: typeof data.data,
                        isString: typeof data.data === 'string',
                        keys: Object.keys(data),
                        dataPreview: typeof data.data === 'string' ? data.data.substring(0, 200) : JSON.stringify(data).substring(0, 200),
                    });
                } catch(e) {
                    results.push({source: 'jobs/recent', error: e.message});
                }

                // Try to find the internal HTTP client
                // Look for axios on window
                const axiosKeys = Object.keys(window).filter(k => k.toLowerCase().includes('axios') || k.toLowerCase().includes('http'));
                results.push({windowKeys: axiosKeys});

                // Try to find React fiber tree
                const root = document.querySelector('#root') || document.querySelector('#app');
                if (root) {
                    const fiberKey = Object.keys(root).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
                    results.push({fiberKey: fiberKey, rootId: root.id, rootTag: root.tagName});
                }

                // Try to find any global store/state
                const stateKeys = Object.keys(window).filter(k =>
                    k.startsWith('__') && !k.startsWith('__react') &&
                    !k.startsWith('__webpack') && !k.startsWith('__sentry')
                );
                results.push({globalStateKeys: stateKeys.slice(0, 20)});

                return results;
            }
        """)
        print(f"  JS evaluation result: {json.dumps(result, ensure_ascii=False, indent=2)[:1000]}", flush=True)
    except Exception as e:
        print(f"  JS evaluation error: {e}", flush=True)

    # Approach 2: Try to use the page's fetch with response interceptor
    print("\n--- Approach 2: Fetch with interceptor ---", flush=True)
    try:
        result = page.evaluate("""
            async () => {
                // Try to make a fetch request and see if the response is decrypted
                const resp = await fetch('/api/outer/ats-apply/website/jobs/module');
                const text = await resp.text();
                try {
                    const json = JSON.parse(text);
                    if (json.data && typeof json.data === 'string') {
                        // Data is encrypted - try to find decryption function
                        // Look for CryptoJS or similar
                        const cryptoKeys = Object.keys(window).filter(k =>
                            k.toLowerCase().includes('crypt') || k.toLowerCase().includes('decrypt')
                        );
                        return {
                            encrypted: true,
                            dataLen: json.data.length,
                            necromancer: json.necromancer,
                            cryptoKeys: cryptoKeys,
                            hasCryptoJS: typeof CryptoJS !== 'undefined',
                        };
                    } else if (json.data && typeof json.data === 'object') {
                        return {
                            encrypted: false,
                            data: JSON.stringify(json.data).substring(0, 500),
                        };
                    }
                    return {unknown: true, keys: Object.keys(json)};
                } catch(e) {
                    return {parseError: e.message, textLen: text.length, textStart: text.substring(0, 200)};
                }
            }
        """)
        print(f"  Fetch result: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}", flush=True)
    except Exception as e:
        print(f"  Fetch error: {e}", flush=True)

    # Approach 3: Try clicking on different category filters to load different jobs
    print("\n--- Approach 3: Category filters ---", flush=True)

    # First, parse jobs from the initial page (no filter)
    txt = clean_text(page.content())
    initial_jobs = parse_jobs_from_text(txt)
    for j in initial_jobs:
        key = (j['title'], j['publish_date'])
        if key not in all_jobs:
            all_jobs[key] = j
    print(f"  Initial (no filter): {len(initial_jobs)} jobs", flush=True)

    # Try clicking on different function type filters
    # The text shows: 职能类型 技术类 算法类 +1
    categories = ["技术类", "算法类", "产品类", "设计类", "市场类", "运营类", "职能类"]
    for cat in categories:
        try:
            # Find and click the category filter
            loc = page.locator(f"text={cat}").first
            if loc.count() > 0:
                # Check if it's clickable (not intercepted)
                try:
                    loc.click(timeout=5000)
                    page.wait_for_timeout(5000)

                    # Parse jobs from the filtered page
                    txt = clean_text(page.content())
                    jobs = parse_jobs_from_text(txt)
                    new_count = 0
                    for j in jobs:
                        key = (j['title'], j['publish_date'])
                        if key not in all_jobs:
                            all_jobs[key] = j
                            new_count += 1
                    print(f"  Filter '{cat}': {len(jobs)} jobs ({new_count} new)", flush=True)
                except Exception as e:
                    # Try using JavaScript click
                    try:
                        page.evaluate(f"""
                            () => {{
                                const elements = document.querySelectorAll('*');
                                for (const el of elements) {{
                                    if (el.textContent.trim() === '{cat}' && el.offsetParent !== null) {{
                                        el.click();
                                        return true;
                                    }}
                                }}
                                return false;
                            }}
                        """)
                        page.wait_for_timeout(5000)
                        txt = clean_text(page.content())
                        jobs = parse_jobs_from_text(txt)
                        new_count = 0
                        for j in jobs:
                            key = (j['title'], j['publish_date'])
                            if key not in all_jobs:
                                all_jobs[key] = j
                                new_count += 1
                        print(f"  Filter '{cat}' (JS click): {len(jobs)} jobs ({new_count} new)", flush=True)
                    except Exception as e2:
                        print(f"  Filter '{cat}' failed: {e2}", flush=True)
            else:
                print(f"  Filter '{cat}' not found", flush=True)
        except Exception as e:
            print(f"  Filter '{cat}' error: {e}", flush=True)

        # Clear filter by navigating back to #/jobs
        try:
            page.goto(f"{base_url}#/jobs", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
        except:
            pass

    # Approach 4: Try location filters
    print("\n--- Approach 4: Location filters ---", flush=True)
    locations = ["北京市", "上海市", "深圳市", "成都市", "美国", "新加坡"]
    for loc_name in locations:
        try:
            loc = page.locator(f"text={loc_name}").first
            if loc.count() > 0:
                try:
                    loc.click(timeout=5000)
                    page.wait_for_timeout(5000)
                    txt = clean_text(page.content())
                    jobs = parse_jobs_from_text(txt)
                    new_count = 0
                    for j in jobs:
                        key = (j['title'], j['publish_date'])
                        if key not in all_jobs:
                            all_jobs[key] = j
                            new_count += 1
                    print(f"  Location '{loc_name}': {len(jobs)} jobs ({new_count} new)", flush=True)
                except:
                    pass
        except:
            pass
        # Clear filter
        try:
            page.goto(f"{base_url}#/jobs", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
        except:
            pass

    # Approach 5: Try to use page.evaluate to call internal API with the page's decryption
    print("\n--- Approach 5: Internal API call with decryption ---", flush=True)
    try:
        result = page.evaluate("""
            async () => {
                // Try to intercept the internal axios instance
                // The page likely uses a custom HTTP client with response interceptor
                // that decrypts the 'data' field using the 'necromancer' key

                // Try to find the decryption function in the webpack modules
                const modules = window.webpackChunkmage_cli_jsonp;
                if (modules) {
                    return {
                        hasWebpack: true,
                        chunkCount: modules.length,
                    };
                }
                return {hasWebpack: false};
            }
        """)
        print(f"  Webpack result: {json.dumps(result, ensure_ascii=False)}", flush=True)
    except Exception as e:
        print(f"  Webpack error: {e}", flush=True)

    # Also try the careers.kimi.com API
    print("\n--- Approach 6: careers.kimi.com API ---", flush=True)
    try:
        result = page.evaluate("""
            async () => {
                try {
                    // Try various API endpoints
                    const urls = [
                        'https://careers.kimi.com/api/jobs',
                        'https://careers.kimi.com/api/positions',
                        'https://careers.kimi.com/_next/data/jobs.json',
                    ];
                    const results = [];
                    for (const url of urls) {
                        try {
                            const resp = await fetch(url);
                            const text = await resp.text();
                            results.push({
                                url: url,
                                status: resp.status,
                                contentType: resp.headers.get('content-type'),
                                textLen: text.length,
                                textStart: text.substring(0, 200),
                            });
                        } catch(e) {
                            results.push({url: url, error: e.message});
                        }
                    }
                    return results;
                } catch(e) {
                    return {error: e.message};
                }
            }
        """)
        print(f"  careers.kimi.com API: {json.dumps(result, ensure_ascii=False, indent=2)[:800]}", flush=True)
    except Exception as e:
        print(f"  careers.kimi.com error: {e}", flush=True)

    # Convert to list and sort
    all_jobs_list = list(all_jobs.values())
    all_jobs_list.sort(key=lambda x: x.get('publish_date', ''), reverse=True)

    # Print all jobs
    print(f"\n=== ALL UNIQUE JOBS ({len(all_jobs_list)}) ===", flush=True)
    matching = []
    for j in all_jobs_list:
        title_lower = j['title'].lower()
        matched = [kw for kw in KEYWORDS if kw.lower() in title_lower]
        is_new = j.get('publish_date', '') >= "2026-07-16"
        marker = ""
        if is_new:
            marker += " [NEW]"
        if matched:
            marker += f" [MATCH: {','.join(matched)}]"
        loc = j.get('location', '')
        dept = j.get('department', '')
        date = j.get('publish_date', 'N/A')
        print(f"  {date} | {j['title']} | {loc} | {dept}{marker}", flush=True)
        if matched or is_new:
            j['matched_keywords'] = matched
            j['is_new'] = is_new
            matching.append(j)

    # Save JSON
    output = {
        "scrape_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_scraped": len(all_jobs_list),
        "jobs": all_jobs_list,
        "matching_or_new": matching,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_jobs_list)} jobs to {OUT_JSON}", flush=True)
    print(f"Matching/new: {len(matching)}", flush=True)

    ctx.close()
    b.close()
    p.stop()

if __name__ == "__main__":
    main()
