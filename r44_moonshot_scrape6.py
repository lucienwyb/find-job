#!/usr/bin/env python3
"""Round 44 v6: Intercept API requests, try keyboard scroll, and use mokahr API directly."""
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
    print("=== Moonshot Careers Scrape v6 (Round 44) ===", flush=True)
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

    # Capture all API requests
    api_requests = []
    def on_request(req):
        if '/api/' in req.url and any(k in req.url for k in ['job', 'position', 'module', 'group']):
            api_requests.append({
                "url": req.url,
                "method": req.method,
                "headers": dict(req.headers),
                "post_data": req.post_data,
            })

    def on_response(resp):
        if '/api/' in resp.url and any(k in resp.url for k in ['job', 'position', 'module', 'group']):
            try:
                body = resp.text()
                api_requests.append({
                    "url": resp.url,
                    "status": resp.status,
                    "body_len": len(body),
                    "body": body[:30000],
                })
            except:
                pass

    page.on("request", on_request)
    page.on("response", on_response)

    # Navigate to #/jobs
    print("\n--- Navigate to #/jobs ---", flush=True)
    try:
        page.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
    except:
        page.goto(f"{base_url}#/jobs", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)

    # Check initial job count
    all_job_links = page.query_selector_all("a[href*='#/job/']")
    initial_count = len(all_job_links)
    print(f"  Initial job links: {initial_count}", flush=True)

    # Approach 1: Keyboard scrolling - focus on the job list and press keys
    print("\n--- Approach 1: Keyboard scrolling ---", flush=True)

    # Try to focus on the job list container
    try:
        # Click on the first job link to focus the list
        if all_job_links:
            all_job_links[0].click()
            page.wait_for_timeout(1000)

        # Press Page Down, End, and Arrow Down repeatedly
        for i in range(50):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(200)
            if i % 10 == 9:
                links = page.query_selector_all("a[href*='#/job/']")
                print(f"  After {i+1} PageDowns: {len(links)} links", flush=True)
                if len(links) > initial_count:
                    print(f"  *** NEW JOBS LOADED ***", flush=True)

        # Also try End key
        for i in range(10):
            page.keyboard.press("End")
            page.wait_for_timeout(500)

        # Try Arrow Down
        for i in range(100):
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(50)

        links = page.query_selector_all("a[href*='#/job/']")
        print(f"  After keyboard scroll: {len(links)} links", flush=True)
    except Exception as e:
        print(f"  Keyboard scroll error: {e}", flush=True)

    # Approach 2: Try to find and scroll the job list container using JS
    print("\n--- Approach 2: Find scrollable container ---", flush=True)
    try:
        result = page.evaluate("""
            () => {
                // Find all elements that could be scrollable
                const candidates = [];
                document.querySelectorAll('*').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.height > 100 && rect.height < 2000) {
                        const style = window.getComputedStyle(el);
                        const overflow = style.overflow + ' ' + style.overflowY;
                        if (overflow.includes('auto') || overflow.includes('scroll') || overflow.includes('hidden')) {
                            candidates.push({
                                tag: el.tagName,
                                class: el.className.toString().substring(0, 100),
                                height: rect.height,
                                scrollHeight: el.scrollHeight,
                                clientHeight: el.clientHeight,
                                overflow: overflow.trim(),
                                canScroll: el.scrollHeight > el.clientHeight,
                            });
                        }
                    }
                });
                return candidates.slice(0, 20);
            }
        """)
        print(f"  Scrollable candidates: {len(result)}", flush=True)
        for c in result:
            if c.get('canScroll'):
                print(f"    {c['tag']}.{c['class'][:50]} height={c['height']} scroll={c['scrollHeight']} canScroll=True", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 3: Try to scroll the found container
    print("\n--- Approach 3: Scroll containers ---", flush=True)
    try:
        page.evaluate("""
            () => {
                // Scroll all elements that can be scrolled
                document.querySelectorAll('*').forEach(el => {
                    if (el.scrollHeight > el.clientHeight + 10) {
                        // Scroll incrementally
                        let step = 100;
                        let current = 0;
                        const interval = setInterval(() => {
                            current += step;
                            el.scrollTop = current;
                            if (current >= el.scrollHeight) {
                                clearInterval(interval);
                            }
                        }, 50);
                    }
                });
            }
        """)
        page.wait_for_timeout(10000)

        links = page.query_selector_all("a[href*='#/job/']")
        print(f"  After container scroll: {len(links)} links", flush=True)

        # Parse jobs from current page
        txt = clean_text(page.content())
        jobs = parse_jobs_from_text(txt)
        print(f"  Jobs parsed: {len(jobs)}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 4: Try calling the mokahr API with the correct parameters
    print("\n--- Approach 4: Direct API calls ---", flush=True)

    # Print captured API request details
    print(f"  Captured {len(api_requests)} API requests", flush=True)
    for req in api_requests:
        if isinstance(req.get('url'), str) and 'jobs/module' in req.get('url', ''):
            print(f"  jobs/module request: {json.dumps(req, ensure_ascii=False)[:500]}", flush=True)

    # Try calling the API with the page's cookies and headers
    try:
        result = page.evaluate("""
            async () => {
                // Try calling the jobs/module API with different parameters
                const urls = [
                    '/api/outer/ats-apply/website/jobs/module?pageNo=1&pageSize=100',
                    '/api/outer/ats-apply/website/jobs/module?page=1&size=100',
                    '/api/outer/ats-apply/website/jobs/v2?pageNo=1&pageSize=100',
                    '/api/outer/ats-apply/website/jobs/v2',
                    '/api/outer/ats-apply/website/jobs/recent?pageNo=1&pageSize=100',
                ];
                const results = [];
                for (const url of urls) {
                    try {
                        const resp = await fetch(url, {
                            headers: {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json',
                            }
                        });
                        const text = await resp.text();
                        results.push({
                            url: url,
                            status: resp.status,
                            len: text.length,
                            start: text.substring(0, 300),
                        });
                    } catch(e) {
                        results.push({url: url, error: e.message});
                    }
                }
                return results;
            }
        """)
        print(f"  API call results:", flush=True)
        for r in result:
            print(f"    {r.get('url', '?')}: status={r.get('status', '?')} len={r.get('len', '?')} start={r.get('start', r.get('error', '?'))[:200]}", flush=True)
    except Exception as e:
        print(f"  API call error: {e}", flush=True)

    # Approach 5: Try to use the mokahr API with the correct company ID
    print("\n--- Approach 5: Mokahr API with company ID ---", flush=True)
    try:
        result = page.evaluate("""
            async () => {
                // The company ID from the URL is 148506
                // Try different API endpoints
                const urls = [
                    '/api/outer/ats-apply/website/jobs/module?applyId=148506',
                    '/api/outer/ats-apply/website/jobs/v2?applyId=148506',
                    '/api/outer/ats-apply/website/jobs/recent?applyId=148506',
                    '/api/outer/ats-apply/website/group-by-job?applyId=148506',
                ];
                const results = [];
                for (const url of urls) {
                    try {
                        const resp = await fetch(url);
                        const text = await resp.text();
                        results.push({url, status: resp.status, len: text.length, start: text.substring(0, 200)});
                    } catch(e) {
                        results.push({url, error: e.message});
                    }
                }
                return results;
            }
        """)
        for r in result:
            print(f"    {r.get('url', '?')}: status={r.get('status', '?')} len={r.get('len', '?')} start={r.get('start', r.get('error', '?'))[:150]}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 6: Try to use the page's own HTTP client by intercepting XHR
    print("\n--- Approach 6: Override XHR to intercept decrypted data ---", flush=True)
    try:
        # Reload the page and intercept the API response after decryption
        page.evaluate("""
            () => {
                // Store original XMLHttpRequest
                window._originalXHR = window.XMLHttpRequest;
                window._apiResponses = [];

                // Create a proxy XMLHttpRequest
                window.XMLHttpRequest = function() {
                    const xhr = new window._originalXHR();
                    const originalOpen = xhr.open;
                    const originalSend = xhr.send;

                    xhr.open = function(method, url, ...args) {
                        this._url = url;
                        return originalOpen.call(this, method, url, ...args);
                    };

                    xhr.send = function(body) {
                        this.addEventListener('load', function() {
                            if (this._url && (this._url.includes('jobs') || this._url.includes('position'))) {
                                try {
                                    window._apiResponses.push({
                                        url: this._url,
                                        status: this.status,
                                        responseLen: this.responseText.length,
                                        responseStart: this.responseText.substring(0, 500),
                                    });
                                } catch(e) {}
                            }
                        });
                        return originalSend.call(this, body);
                    };

                    return xhr;
                };
            }
        """)

        # Reload the page to trigger API calls
        page.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(10000)

        # Check captured responses
        result = page.evaluate("() => window._apiResponses || []")
        print(f"  Captured {len(result)} XHR responses", flush=True)
        for r in result:
            print(f"    {r.get('url', '?')[:100]}: len={r.get('responseLen', '?')} start={r.get('responseStart', '?')[:200]}", flush=True)
    except Exception as e:
        print(f"  XHR intercept error: {e}", flush=True)

    # Final: Collect all jobs from the page
    print("\n--- Final job collection ---", flush=True)
    txt = clean_text(page.content())
    all_jobs = parse_jobs_from_text(txt)

    # Also collect from HTML for job links
    html = page.content()
    job_ids = set(re.findall(r'#/job/([a-f0-9\-]+)', html))

    print(f"  Jobs from text: {len(all_jobs)}", flush=True)
    print(f"  Job IDs in HTML: {len(job_ids)}", flush=True)

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
        "job_ids_found": list(job_ids),
        "jobs": unique_jobs,
        "matching_or_new": matching,
        "api_requests": [{"url": r.get("url", ""), "method": r.get("method", ""), "post_data": r.get("post_data", "")} for r in api_requests if "method" in r],
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
