#!/usr/bin/env python3
"""Round 44 v8: Access React fiber tree to get all 98 jobs from component state.
Also try calling API with offset:30 to get next batch.
"""
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
    print("=== Moonshot Careers Scrape v8 (Round 44) ===", flush=True)
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

    # Approach 1: Access React fiber tree to find job data
    print("\n--- Approach 1: React fiber tree ---", flush=True)
    try:
        result = page.evaluate("""
            () => {
                const app = document.querySelector('#app');
                if (!app) return {error: 'No #app'};

                // Find React fiber root
                const fiberKey = Object.keys(app).find(k =>
                    k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
                );
                const containerKey = Object.keys(app).find(k =>
                    k.startsWith('__reactContainere')
                );

                if (!fiberKey && !containerKey) {
                    return {error: 'No React fiber found', keys: Object.keys(app).slice(0, 10)};
                }

                // Get the fiber root
                const container = app[containerKey];
                let rootFiber = app[fiberKey];

                if (!rootFiber && container) {
                    rootFiber = container.current || container._reactRootContainer;
                }

                if (!rootFiber) {
                    return {error: 'No root fiber', hasContainer: !!container};
                }

                // Traverse the fiber tree to find job data
                const visited = new Set();
                const jobData = [];
                let maxDepth = 0;

                function traverseFiber(fiber, depth) {
                    if (!fiber || visited.has(fiber) || depth > 30) return;
                    visited.add(fiber);
                    maxDepth = Math.max(maxDepth, depth);

                    // Check memoizedState for job data
                    let state = fiber.memoizedState;
                    while (state) {
                        if (state.memoizedState) {
                            const val = state.memoizedState;
                            if (Array.isArray(val) && val.length > 0) {
                                // Check if this looks like job data
                                const first = val[0];
                                if (first && typeof first === 'object') {
                                    const keys = Object.keys(first);
                                    if (keys.some(k => k.toLowerCase().includes('job') || k.toLowerCase().includes('title') || k.toLowerCase().includes('position'))) {
                                        jobData.push({
                                            depth: depth,
                                            arrayLen: val.length,
                                            firstItemKeys: keys.slice(0, 10),
                                            firstItemPreview: JSON.stringify(first).substring(0, 500),
                                        });
                                    }
                                }
                            }
                        }
                        state = state.next;
                    }

                    // Check memoizedProps for job data
                    if (fiber.memoizedProps) {
                        const props = fiber.memoizedProps;
                        for (const key of Object.keys(props)) {
                            const val = props[key];
                            if (Array.isArray(val) && val.length > 5) {
                                const first = val[0];
                                if (first && typeof first === 'object') {
                                    const keys = Object.keys(first);
                                    if (keys.some(k => k.toLowerCase().includes('job') || k.toLowerCase().includes('title') || k.toLowerCase().includes('position') || k.toLowerCase().includes('name'))) {
                                        jobData.push({
                                            depth: depth,
                                            propKey: key,
                                            arrayLen: val.length,
                                            firstItemKeys: keys.slice(0, 15),
                                            firstItemPreview: JSON.stringify(first).substring(0, 500),
                                        });
                                    }
                                }
                            }
                        }
                    }

                    // Traverse children
                    traverseFiber(fiber.child, depth + 1);
                    traverseFiber(fiber.sibling, depth + 1);
                }

                try {
                    traverseFiber(rootFiber, 0);
                } catch(e) {
                    return {error: 'Traversal error: ' + e.message, partial: jobData};
                }

                return {
                    maxDepth: maxDepth,
                    visitedCount: visited.size,
                    jobDataFound: jobData.length,
                    jobData: jobData.slice(0, 10),
                };
            }
        """)
        print(f"  React fiber result:", flush=True)
        print(f"  {json.dumps(result, ensure_ascii=False, indent=2)[:3000]}", flush=True)

        # If we found job data, extract it
        if result.get('jobDataFound', 0) > 0:
            print(f"\n  *** FOUND {result['jobDataFound']} JOB DATA ARRAYS ***", flush=True)
            for jd in result.get('jobData', []):
                print(f"  Depth {jd.get('depth')}: {jd.get('arrayLen', '?')} items, keys={jd.get('firstItemKeys', jd.get('firstItemKeys', []))}", flush=True)
                print(f"  Preview: {jd.get('firstItemPreview', '')[:300]}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 2: Deeper React fiber search - look for arrays with > 30 items
    print("\n--- Approach 2: Deep fiber search for large arrays ---", flush=True)
    try:
        result = page.evaluate("""
            () => {
                const app = document.querySelector('#app');
                const fiberKey = Object.keys(app).find(k => k.startsWith('__reactFiber'));
                const containerKey = Object.keys(app).find(k => k.startsWith('__reactContainere'));

                let rootFiber = app[fiberKey];
                if (!rootFiber && containerKey) {
                    const container = app[containerKey];
                    rootFiber = container.current?.child || container;
                }

                const visited = new Set();
                const largeArrays = [];

                function traverseFiber(fiber, depth) {
                    if (!fiber || visited.has(fiber) || depth > 40) return;
                    visited.add(fiber);

                    // Check memoizedState
                    let state = fiber.memoizedState;
                    while (state) {
                        const val = state.memoizedState;
                        if (Array.isArray(val) && val.length > 10) {
                            try {
                                const first = val[0];
                                if (first && typeof first === 'object') {
                                    largeArrays.push({
                                        depth: depth,
                                        source: 'state',
                                        arrayLen: val.length,
                                        keys: Object.keys(first).slice(0, 20),
                                        preview: JSON.stringify(first).substring(0, 800),
                                    });
                                }
                            } catch(e) {}
                        }
                        state = state.next;
                    }

                    // Check memoizedProps
                    if (fiber.memoizedProps) {
                        for (const key of Object.keys(fiber.memoizedProps)) {
                            const val = fiber.memoizedProps[key];
                            if (Array.isArray(val) && val.length > 10) {
                                try {
                                    const first = val[0];
                                    if (first && typeof first === 'object') {
                                        largeArrays.push({
                                            depth: depth,
                                            source: 'props.' + key,
                                            arrayLen: val.length,
                                            keys: Object.keys(first).slice(0, 20),
                                            preview: JSON.stringify(first).substring(0, 800),
                                        });
                                    }
                                } catch(e) {}
                            }
                            // Also check nested objects
                            if (val && typeof val === 'object' && !Array.isArray(val)) {
                                for (const k2 of Object.keys(val)) {
                                    const v2 = val[k2];
                                    if (Array.isArray(v2) && v2.length > 10) {
                                        try {
                                            const first = v2[0];
                                            if (first && typeof first === 'object') {
                                                largeArrays.push({
                                                    depth: depth,
                                                    source: 'props.' + key + '.' + k2,
                                                    arrayLen: v2.length,
                                                    keys: Object.keys(first).slice(0, 20),
                                                    preview: JSON.stringify(first).substring(0, 800),
                                                });
                                            }
                                        } catch(e) {}
                                    }
                                }
                            }
                        }
                    }

                    traverseFiber(fiber.child, depth + 1);
                    traverseFiber(fiber.sibling, depth + 1);
                }

                try {
                    traverseFiber(rootFiber, 0);
                } catch(e) {
                    return {error: e.message, partial: largeArrays};
                }

                return {
                    visited: visited.size,
                    largeArraysFound: largeArrays.length,
                    largeArrays: largeArrays.slice(0, 20),
                };
            }
        """)
        print(f"  Visited {result.get('visited', 0)} fibers", flush=True)
        print(f"  Found {result.get('largeArraysFound', 0)} large arrays", flush=True)
        for la in result.get('largeArrays', []):
            print(f"    Depth {la.get('depth')}: {la.get('source', '?')} len={la.get('arrayLen', '?')} keys={la.get('keys', [])[:10]}", flush=True)
            print(f"    Preview: {la.get('preview', '')[:400]}", flush=True)
            print(flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Approach 3: Use page.route to modify API request offset
    print("\n--- Approach 3: Modify API offset via route ---", flush=True)
    all_jobs_from_pages = []

    for offset_val in [0, 30, 60, 90]:
        print(f"\n  Trying offset={offset_val}...", flush=True)

        # Create a new page with route interception
        page3 = ctx.new_page()

        # Capture the API response
        api_response_body = []
        def on_resp3(resp):
            if 'jobs/v2' in resp.url:
                try:
                    api_response_body.append(resp.text())
                except:
                    pass

        page3.on("response", on_resp3)

        # Set up route to modify POST data
        def handle_route(route):
            req = route.request
            if 'jobs/v2' in req.url and req.method == 'POST':
                try:
                    post_data = json.loads(req.post_data)
                    post_data['offset'] = offset_val
                    post_data['limit'] = 30
                    route.continue_(post_data=json.dumps(post_data))
                except:
                    route.continue_()
            else:
                route.continue_()

        page3.route('**/api/**', handle_route)

        try:
            page3.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
            page3.wait_for_timeout(8000)

            # Extract jobs from the page
            txt = clean_text(page3.content())
            jobs = parse_jobs_from_text(txt)
            new_count = 0
            for j in jobs:
                key = (j['title'], j['publish_date'])
                if not any(j2['title'] == j['title'] and j2['publish_date'] == j['publish_date'] for j2 in all_jobs_from_pages):
                    all_jobs_from_pages.append(j)
                    new_count += 1
            print(f"    Found {len(jobs)} jobs ({new_count} new)", flush=True)

            # Also count job links
            links = page3.query_selector_all("a[href*='#/job/']")
            print(f"    Job links: {len(links)}", flush=True)

            # Print API response size
            if api_response_body:
                print(f"    API response size: {len(api_response_body[0])} bytes", flush=True)

        except Exception as e:
            print(f"    Error: {e}", flush=True)

        page3.close()

    # Approach 4: Try to use the page's internal HTTP client (axios) to call API with offset
    print("\n--- Approach 4: Call API with different offsets via page context ---", flush=True)
    try:
        result = page.evaluate("""
            async () => {
                const baseUrl = '/api/outer/ats-apply/website/jobs/v2';
                const baseData = {
                    orgId: "moonshot",
                    siteId: "148506",
                    limit: 30,
                    offset: 0,
                    needStat: true,
                    jobIdTopList: [],
                    customFields: {},
                    site: "social",
                    locale: "zh-CN"
                };

                const results = [];
                for (const offset of [0, 30, 60, 90]) {
                    try {
                        const resp = await fetch(baseUrl, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                            },
                            body: JSON.stringify({...baseData, offset: offset}),
                        });
                        const text = await resp.text();
                        results.push({
                            offset: offset,
                            status: resp.status,
                            len: text.length,
                            // Check if the response contains different data
                            // by looking at a hash of the first 100 chars
                            hash: text.substring(0, 100),
                        });
                    } catch(e) {
                        results.push({offset: offset, error: e.message});
                    }
                }
                return results;
            }
        """)
        print(f"  API offset results:", flush=True)
        for r in result:
            print(f"    offset={r.get('offset')}: status={r.get('status', '?')} len={r.get('len', '?')} hash={r.get('hash', r.get('error', '?'))[:80]}", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)

    # Final: Combine all jobs
    print("\n--- Final results ---", flush=True)

    # Deduplicate all jobs from all approaches
    all_jobs = {}
    for j in all_jobs_from_pages:
        key = (j['title'], j['publish_date'])
        if key not in all_jobs:
            all_jobs[key] = j

    # Also add jobs from the current page
    txt = clean_text(page.content())
    page_jobs = parse_jobs_from_text(txt)
    for j in page_jobs:
        key = (j['title'], j['publish_date'])
        if key not in all_jobs:
            all_jobs[key] = j

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
