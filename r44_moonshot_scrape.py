#!/usr/bin/env python3
"""Round 44: Scrape Moonshot (Kimi) careers portal for new positions.
Uses playwright headless with proxy to render the mokahr SPA.
"""
import json, re, time, sys
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT_JSON = "/pulp/find-job/r44_moonshot.json"
OUT_HTML = "/pulp/find-job/r44_moonshot.html"
OUT_TXT = "/pulp/find-job/r44_moonshot.txt"
OUT_API = "/pulp/find-job/r44_moonshot_api.json"

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

def extract_jobs_from_dom(page):
    """Try to extract structured job data from the rendered DOM."""
    jobs = []
    try:
        # mokahr typically renders job cards in specific containers
        # Try multiple selectors
        selectors_to_try = [
            "[class*='job-item']",
            "[class*='position-item']",
            "[class*='job-card']",
            "[class*='position-card']",
            "[class*='jobItem']",
            "[class*='positionItem']",
            "[class*='JobItem']",
            "[class*='PositionItem']",
            "[class*='job_list'] > *",
            "[class*='jobList'] > *",
            "[class*='positionList'] > *",
            "li[class*='job']",
            "div[class*='list'] > div[class*='item']",
        ]
        for sel in selectors_to_try:
            elements = page.query_selector_all(sel)
            if elements and len(elements) > 3:
                print(f"  Found {len(elements)} elements with selector: {sel}", flush=True)
                for el in elements:
                    try:
                        text = el.inner_text()
                        if text and len(text) > 5:
                            jobs.append(text.strip())
                    except:
                        pass
                if jobs:
                    break
    except Exception as e:
        print(f"  DOM extraction error: {e}", flush=True)
    return jobs

def extract_jobs_from_text(txt):
    """Parse job listings from cleaned page text.
    Format: [急] JobTitle 发布于 YYYY-MM-DD 全职 全职 | 技术类 技术类 | 北京市 北京市 ...
    """
    jobs = []
    # Find all job entries with publish dates
    # The pattern: job title followed by 发布于 date
    pattern = r'((?:急\s+)?[一-鿿\w/\-（）·,.\s&;:]+?)\s+发布于\s+(\d{4}-\d{2}-\d{2})'

    matches = list(re.finditer(pattern, txt))
    print(f"  Regex found {len(matches)} job entries with dates", flush=True)

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        date = m.group(2).strip()

        # Clean title - remove leading "急" and whitespace
        title = re.sub(r'^急\s*', '', title)
        # Remove trailing duplicate words (SPA rendering artifact)
        # e.g., "全职 全职" -> "全职"
        title = re.sub(r'\s+', ' ', title).strip()

        # Try to extract location and department from surrounding text
        after_text = txt[m.end():m.end()+200]

        # Look for location pattern: | City City |
        loc_match = re.search(r'\|\s*([一-鿿]+)\s+\1\s*\|', after_text)
        # Look for department: before the | City pattern, there's often Dept Dept |
        dept_match = re.search(r'\|\s*([一-鿿]+类)\s+\1', after_text)

        location = loc_match.group(1) if loc_match else ""
        department = dept_match.group(1) if dept_match else ""

        # Also try: after "全职 全职" look for "技术类 技术类 | 城市 城市"
        type_dept_match = re.search(
            r'(全职|兼职|实习)\s+\1\s*\|\s*([一-鿿]+)\s+\2\s*\|\s*([一-鿿]+)\s+\3',
            after_text
        )
        if type_dept_match:
            department = type_dept_match.group(2)
            location = type_dept_match.group(3)

        jobs.append({
            "title": title,
            "publish_date": date,
            "location": location,
            "department": department,
            "raw_after": after_text[:100],
        })

    return jobs

def main():
    print("=== Moonshot Careers Scrape (Round 44) ===", flush=True)
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

    # Capture API responses
    api_captures = []

    page = ctx.new_page()

    def on_response(resp):
        try:
            ct = resp.headers.get('content-type', '')
            url = resp.url
            if any(t in ct for t in ['json', 'text', 'javascript']) and len(url) > 10:
                body = resp.text()
                if body and len(body) > 100:
                    api_captures.append({
                        "url": url,
                        "status": resp.status,
                        "ct": ct[:50],
                        "len": len(body),
                        "body": body[:20000],
                    })
        except:
            pass

    page.on("response", on_response)

    # URLs to try
    urls = [
        "https://app.mokahr.com/apply/moonshot/148506",
        "https://careers.kimi.com/social",
    ]

    all_jobs = []
    best_txt = ""

    for url in urls:
        print(f"\n--- Navigating to {url} ---", flush=True)
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"  Status: {resp.status if resp else None}", flush=True)

            # Wait for SPA to render
            page.wait_for_timeout(8000)

            # Check if we need to wait longer or scroll
            html = page.content()
            txt = clean_text(html)
            print(f"  Initial: html={len(html)} txt={len(txt)}", flush=True)

            # If content is too small, wait more
            if len(txt) < 2000:
                print("  Content small, waiting more...", flush=True)
                page.wait_for_timeout(10000)
                html = page.content()
                txt = clean_text(html)
                print(f"  After wait: html={len(html)} txt={len(txt)}", flush=True)

            # Scroll down to load all jobs
            for scroll_round in range(20):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(500)

            # Also try scrolling within job list container
            try:
                page.evaluate("""
                    () => {
                        const containers = document.querySelectorAll('[class*="job"], [class*="position"], [class*="list"]');
                        containers.forEach(c => c.scrollTop = c.scrollHeight);
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                """)
                page.wait_for_timeout(3000)
            except:
                pass

            html = page.content()
            txt = clean_text(html)
            print(f"  After scroll: html={len(html)} txt={len(txt)}", flush=True)

            # Check if real content
            if any(k in txt for k in ['职位', '工程师', '招聘', '发布于']):
                print("  *** REAL JOB CONTENT DETECTED ***", flush=True)
                best_txt = txt

                # Try structured DOM extraction
                dom_jobs = extract_jobs_from_dom(page)
                if dom_jobs:
                    print(f"  DOM extraction: {len(dom_jobs)} jobs", flush=True)

                # Parse from text
                text_jobs = extract_jobs_from_text(txt)
                if text_jobs:
                    all_jobs = text_jobs
                    print(f"  Text parsing: {len(text_jobs)} jobs", flush=True)

                # Save HTML and text
                with open(OUT_HTML, "w") as f:
                    f.write(html)
                with open(OUT_TXT, "w") as f:
                    f.write(txt[:200000])
                print(f"  Saved HTML ({len(html)}) and TXT ({len(txt)})", flush=True)

                # If we found jobs, no need to try next URL
                if all_jobs:
                    break
            else:
                print(f"  No job content found. Preview: {txt[:300]}", flush=True)

        except Exception as e:
            print(f"  Error: {e}", flush=True)

    # Try clicking through job categories to get more
    if best_txt and not all_jobs:
        print("\n--- Trying category clicks ---", flush=True)
        for cat in ["技术类", "算法类", "全部"]:
            try:
                loc = page.locator(f"text={cat}").first
                if loc.count() > 0:
                    loc.click(timeout=5000)
                    page.wait_for_timeout(5000)
                    html = page.content()
                    txt = clean_text(html)
                    jobs = extract_jobs_from_text(txt)
                    if jobs:
                        all_jobs = jobs
                        print(f"  Found {len(jobs)} jobs after clicking {cat}", flush=True)
                        break
            except Exception as e:
                print(f"  Click {cat} error: {e}", flush=True)

    # Save API captures
    with open(OUT_API, "w") as f:
        json.dump(api_captures, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(api_captures)} API captures to {OUT_API}", flush=True)

    # Show API endpoints
    print("\n--- API Endpoints Captured ---", flush=True)
    for c in api_captures:
        if any(k in c['url'] for k in ['job', 'position', 'module', 'group', 'list']):
            print(f"  {c['url'][:150]} (len={c['len']})", flush=True)

    # Deduplicate and clean jobs
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j['title'], j['publish_date'])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    # Sort by date descending
    unique_jobs.sort(key=lambda x: x['publish_date'], reverse=True)

    # Save final JSON
    output = {
        "scrape_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_jobs": len(unique_jobs),
        "jobs": unique_jobs,
        "matching_keywords": [],
    }

    # Highlight matching jobs
    print("\n=== ALL JOBS (sorted by date desc) ===", flush=True)
    for j in unique_jobs:
        title_lower = j['title'].lower()
        matched = [kw for kw in KEYWORDS if kw.lower() in title_lower]
        is_match = bool(matched)
        date_str = j['publish_date']
        is_new = date_str >= "2026-07-16"
        marker = ""
        if is_new:
            marker += " [NEW]"
        if is_match:
            marker += f" [MATCH: {','.join(matched)}]"
        print(f"  {j['publish_date']} | {j['title']} | {j['location']} | {j['department']}{marker}", flush=True)
        if is_match or is_new:
            j['matched_keywords'] = matched
            j['is_new'] = is_new
            output["matching_keywords"].append(j)

    with open(OUT_JSON, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(unique_jobs)} jobs to {OUT_JSON}", flush=True)
    print(f"Matching/new jobs: {len(output['matching_keywords'])}", flush=True)

    ctx.close()
    b.close()
    p.stop()

if __name__ == "__main__":
    main()
