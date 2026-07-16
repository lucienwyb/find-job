#!/usr/bin/env python3
"""Round 44 v7: Access Vue component state and intercept API to get all 98 jobs."""
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
    jobs = {}
    pattern = r'((?:急\s+)?[一-鿿\w/\-（）·,.\s&;:#+|]+?)\s+发布于\s+(\d{4}-\d{2}-\d{2})'
    matches = list(re.finditer(pattern, txt))
    for m in matches:
        title = re.sub(r'^急\s*', '', m.group(1)).strip()
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) > 100:
            continue
        date = m.group(2)
        after = txt[m.end():m.end()+300]
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
    print("=== Moonshot Careers Scrape v7 (Round 44) ===", flush=True)
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

    # Capture the POST data for jobs/v2 API
    api_post_data = {}
    def on_request(req):
        if 'jobs/v2' in req.url and req.method == 'POST':
            api_post_data['url'] = req.url
            api_post_data['headers'] = dict(req.headers)
            api_post_data['post_data'] = req.post_data

    page.on("request", on_request)

    # Navigate to #/jobs
    print("\n--- Navigate to #/jobs ---", flush=True)
    try:
        page.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
    except:
        page.goto(f"{base_url}#/jobs", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)

    # Print captured POST data
    print(f"\n--- Captured API POST data ---", flush=True)
    print(f"  URL: {api_post_data.get('url', 'N/A')}", flush=True)
    print(f"  Post data: {api_post_data.get('post_data', 'N/A')}", flush=True)
    print(f"  Headers: {json.dumps(api_post_data.get('headers', {}), indent=2)[:500]}", flush=True)

    # Approach 1: Try to access Vue component state
    print("\n--- Approach 1: Vue component state ---", flush=True)
    try:
        result = page.evaluate("""
            () => {
                const app = document.querySelector('#app');
                if (!app) return {error: 'No #app element'};

                // Try Vue 3
                const vue3 = app.__vue_app__;
                if (vue3) {
                    return {vueVersion: 3, hasApp: true};
                }

                // Try Vue 2
                const vue2 = app.__vue__;
                if (vue2) {
                    return {vueVersion: 2, hasApp: true};
                }

                // Try to find Vue component instances
                const allElements = document.querySelectorAll('*');
                let vueInstances = [];
                for (const el of allElements) {
                    const keys = Object.keys(el);
                    const vueKey = keys.find(k => k.startsWith('__vue') || k.startsWith('__o'));
                    if (vueKey) {
                        vueInstances.push({
                            tag: el.tagName,
                            class: el.className.toString().substring(0, 50),
                            key: vueKey,
                        });
                        if (vueInstances.length >= 5) break;
                    }
                }

                // Try to find internal data stores
                const internalKeys = Object.keys(app).filter(k =>
                    k.startsWith('__') && !k.startsWith('__react') && !k.startsWith('__sentry')
                );

                return {
                    vueInstances: vueInstances,
                    internalKeys: internalKeys,
                    appKeys: Object.keys(app).slice(0, 20),
                };
            }
        """)
        print(f"  Vue state: {json.dumps(result, ensure_ascii=False, indent=2)[:800]}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 2: Try to use the page's own HTTP client (axios) with interceptor
    print("\n--- Approach 2: Use page's HTTP client ---", flush=True)
    try:
        # Try to call the jobs/v2 API with different page sizes using POST
        post_data = api_post_data.get('post_data', '{}')
        result = page.evaluate(f"""
            async () => {{
                const postUrl = '{api_post_data.get("url", "/api/outer/ats-apply/website/jobs/v2")}';
                const originalData = {post_data or '{}'};

                // Try to modify the POST data to get all jobs
                const modifications = [
                    {{...originalData, pageNo: 1, pageSize: 100}},
                    {{...originalData, page: 1, size: 100}},
                    {{...originalData, pageNum: 1, pageSize: 100}},
                    {{...originalData, offset: 0, limit: 100}},
                ];

                const results = [];
                for (const data of modifications) {{
                    try {{
                        const resp = await fetch(postUrl, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                            }},
                            body: JSON.stringify(data),
                        }});
                        const text = await resp.text();
                        results.push({{
                            data: JSON.stringify(data).substring(0, 100),
                            status: resp.status,
                            len: text.length,
                            start: text.substring(0, 200),
                        }});
                    }} catch(e) {{
                        results.push({{data: JSON.stringify(data).substring(0, 100), error: e.message}});
                    }}
                }}
                return results;
            }}
        """)
        print(f"  API call results:", flush=True)
        for r in result:
            print(f"    {r.get('data', '?')[:80]}: status={r.get('status', '?')} len={r.get('len', '?')} start={r.get('start', r.get('error', '?'))[:200]}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 3: Try to find the decryption function in webpack modules
    print("\n--- Approach 3: Find decryption in webpack ---", flush=True)
    try:
        result = page.evaluate("""
            async () => {
                // The page uses webpack chunks (webpackChunkmage_cli_jsonp)
                const chunks = window.webpackChunkmage_cli_jsonp;
                if (!chunks) return {error: 'No webpack chunks'};

                // Try to find the module that handles API responses
                // Look for modules that contain 'decrypt' or 'necromancer' in their code
                let found = [];
                for (const chunk of chunks) {
                    if (!Array.isArray(chunk) || chunk.length < 2) continue;
                    const modules = chunk[1];
                    if (typeof modules !== 'object') continue;
                    for (const [key, mod] of Object.entries(modules)) {
                        const code = mod.toString();
                        if (code.includes('necromancer') || code.includes('decrypt')) {
                            found.push({
                                key: key,
                                codePreview: code.substring(0, 500),
                            });
                        }
                    }
                }
                return {found: found, chunkCount: chunks.length};
            }
        """)
        print(f"  Webpack search: {json.dumps(result, ensure_ascii=False, indent=2)[:1500]}", flush=True)

        # If we found the decryption function, try to use it
        if result.get('found'):
            for found_item in result['found']:
                code = found_item.get('codePreview', '')
                if 'necromancer' in code:
                    print(f"\n  Found necromancer code in module {found_item['key']}:", flush=True)
                    print(f"  {code[:500]}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 4: Try to intercept the API response and capture decrypted data
    print("\n--- Approach 4: Override fetch to capture decrypted response ---", flush=True)
    try:
        # Override the page's fetch/XHR to capture the decrypted data
        page.evaluate("""
            () => {
                window._decryptedJobs = null;

                // Store original fetch
                const originalFetch = window.fetch;
                window.fetch = async function(...args) {
                    const resp = await originalFetch.apply(this, args);
                    const url = args[0]?.url || args[0] || '';
                    if (typeof url === 'string' && url.includes('jobs/v2')) {
                        const clone = resp.clone();
                        try {
                            const json = await clone.json();
                            if (json.data && typeof json.data !== 'string') {
                                window._decryptedJobs = json.data;
                            }
                        } catch(e) {}
                    }
                    return resp;
                };

                // Also override XMLHttpRequest
                const OriginalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    const xhr = new OriginalXHR();
                    const originalOnReady = xhr.onreadystatechange;
                    Object.defineProperty(xhr, 'onreadystatechange', {
                        set: function(fn) {
                            const wrappedFn = function() {
                                if (xhr.readyState === 4 && xhr.responseText) {
                                    try {
                                        const json = JSON.parse(xhr.responseText);
                                        if (json.data && typeof json.data !== 'string') {
                                            window._decryptedJobs = json.data;
                                        }
                                    } catch(e) {}
                                }
                                return fn.apply(this, arguments);
                            };
                            originalOnReady = wrappedFn;
                        },
                        get: function() { return originalOnReady; }
                    });
                    return xhr;
                };
            }
        """)

        # Reload the page
        page.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(10000)

        # Check if we captured decrypted data
        result = page.evaluate("() => ({jobs: window._decryptedJobs, type: typeof window._decryptedJobs})")
        print(f"  Decrypted data type: {result.get('type', 'undefined')}", flush=True)
        if result.get('jobs'):
            print(f"  Decrypted data: {json.dumps(result['jobs'], ensure_ascii=False)[:500]}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 5: Use page.route to intercept API and modify POST data
    print("\n--- Approach 5: Route intercept with modified POST data ---", flush=True)
    try:
        # Create a new page with route interception
        page2 = ctx.new_page()

        captured_response = []
        def handle_route(route):
            request = route.request
            if 'jobs/v2' in request.url and request.method == 'POST':
                # Let the request go through and capture the response
                route.continue_()
            else:
                route.continue_()

        # Set up request interception to capture POST data
        post_data_captured = []
        def on_req2(req):
            if 'jobs/v2' in req.url and req.method == 'POST':
                post_data_captured.append(req.post_data)

        page2.on("request", on_req2)

        page2.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
        page2.wait_for_timeout(10000)

        print(f"  Captured POST data: {post_data_captured}", flush=True)

        # Now try to call the API with modified POST data
        if post_data_captured:
            original_post = post_data_captured[0]
            try:
                original_json = json.loads(original_post)
                print(f"  Original POST JSON: {json.dumps(original_json, ensure_ascii=False)}", flush=True)
            except:
                print(f"  Original POST (not JSON): {original_post[:200]}", flush=True)

        page2.close()
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Final: Collect all jobs
    print("\n--- Final job collection ---", flush=True)
    txt = clean_text(page.content())
    all_jobs = parse_jobs_from_text(txt)
    print(f"  Jobs from text: {len(all_jobs)}", flush=True)

    # Deduplicate and sort
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j['title'], j['publish_date'])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    unique_jobs.sort(key=lambda x: x.get('publish_date', ''), reverse=True)

    # Print all jobs
    print(f"\n=== ALL UNIQUE JOBS ({len(unique_jobs)}) ===", flush=True)
    matching = []
    for j in unique_jobs:
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
        "total_scraped": len(unique_jobs),
        "jobs": unique_jobs,
        "matching_or_new": matching,
        "api_post_data": api_post_data.get('post_data', ''),
        "api_url": api_post_data.get('url', ''),
    }
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(unique_jobs)} jobs to {OUT_JSON}", flush=True)
    print(f"Matching/new: {len(matching)}", flush=True)

    ctx.close()
    b.close()
    p.stop()

if __name__ == "__main__":
    main()
