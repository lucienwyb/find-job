#!/usr/bin/env python3
"""Round 44 v2: Scrape Moonshot careers - focus on mokahr URL with better DOM extraction."""
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

def main():
    print("=== Moonshot Careers Scrape v2 (Round 44) ===", flush=True)
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

    api_captures = []
    page = ctx.new_page()

    def on_response(resp):
        try:
            ct = resp.headers.get('content-type', '')
            url = resp.url
            if any(t in ct for t in ['json', 'text', 'javascript']):
                body = resp.text()
                if body and len(body) > 100:
                    api_captures.append({
                        "url": url,
                        "status": resp.status,
                        "ct": ct[:50],
                        "len": len(body),
                        "body": body[:30000],
                    })
        except:
            pass

    page.on("response", on_response)

    url = "https://app.mokahr.com/apply/moonshot/148506"
    print(f"\n--- Navigating to {url} ---", flush=True)
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=60000)
        print(f"  Status: {resp.status if resp else None}", flush=True)
    except Exception as e:
        print(f"  goto error (trying domcontentloaded): {e}", flush=True)
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e2:
            print(f"  goto error2: {e2}", flush=True)

    # Wait for job content to render
    page.wait_for_timeout(15000)

    # Check initial content
    html = page.content()
    txt = clean_text(html)
    print(f"  After networkidle: html={len(html)} txt={len(txt)}", flush=True)
    print(f"  Text preview: {txt[:500]}", flush=True)

    # Try to find and click on job category tabs to load job lists
    # mokahr typically has category tabs like 技术类, 算法类
    print("\n--- Looking for job category tabs ---", flush=True)

    # Try clicking on various category labels
    categories = ["技术类", "算法类", "产品", "设计", "全部", "在招职位"]
    for cat in categories:
        try:
            locs = page.locator(f"text={cat}")
            count = locs.count()
            if count > 0:
                print(f"  Found '{cat}' ({count} occurrences)", flush=True)
                # Try clicking each one
                for i in range(min(count, 3)):
                    try:
                        locs.nth(i).click(timeout=3000)
                        page.wait_for_timeout(5000)
                        html2 = page.content()
                        txt2 = clean_text(html2)
                        if len(txt2) > len(txt):
                            print(f"    After click '{cat}[{i}]': txt={len(txt2)} (was {len(txt)})", flush=True)
                            txt = txt2
                            html = html2
                            if '发布于' in txt2 or '工程师' in txt2:
                                print(f"    *** JOB CONTENT FOUND ***", flush=True)
                                print(f"    Preview: {txt2[:500]}", flush=True)
                                break
                    except Exception as e:
                        pass
        except:
            pass

    # Scroll to load more
    print("\n--- Scrolling to load all jobs ---", flush=True)
    for _ in range(30):
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(300)

    # Also scroll any scrollable containers
    try:
        page.evaluate("""
            () => {
                document.querySelectorAll('*').forEach(el => {
                    if (el.scrollHeight > el.clientHeight && el.clientHeight > 100) {
                        el.scrollTop = el.scrollHeight;
                    }
                });
                window.scrollTo(0, document.body.scrollHeight);
            }
        """)
        page.wait_for_timeout(5000)
    except:
        pass

    html = page.content()
    txt = clean_text(html)
    print(f"\n  After scroll: html={len(html)} txt={len(txt)}", flush=True)

    # Try to extract job items from DOM
    print("\n--- DOM Job Item Extraction ---", flush=True)
    selectors_to_try = [
        "[class*='job-item']",
        "[class*='JobItem']",
        "[class*='position-item']",
        "[class*='PositionItem']",
        "[class*='job_card']",
        "[class*='jobCard']",
        "[class*='job-list'] > *",
        "[class*='positionList'] > *",
        "[class*='job_list'] > *",
        "a[href*='job']",
        "a[href*='position']",
        "[data-job-id]",
        "[data-position-id]",
    ]

    dom_jobs = []
    for sel in selectors_to_try:
        try:
            elements = page.query_selector_all(sel)
            if elements and len(elements) > 2:
                print(f"  Selector '{sel}': {len(elements)} elements", flush=True)
                for el in elements:
                    try:
                        inner = el.inner_text()
                        if inner and len(inner.strip()) > 3:
                            dom_jobs.append({
                                "selector": sel,
                                "text": inner.strip()[:500],
                            })
                    except:
                        pass
                if dom_jobs:
                    break
        except:
            pass

    if dom_jobs:
        print(f"\n  Extracted {len(dom_jobs)} DOM job items:", flush=True)
        for i, j in enumerate(dom_jobs[:30]):
            print(f"  [{i}] {j['text'][:200]}", flush=True)

    # Parse jobs from text
    print("\n--- Text-based job parsing ---", flush=True)
    # Pattern: job title + 发布于 + date
    pattern = r'((?:急\s+)?[一-鿿\w/\-（）·,.\s&;:#+]+?)\s+发布于\s+(\d{4}-\d{2}-\d{2})'
    matches = list(re.finditer(pattern, txt))
    print(f"  Found {len(matches)} job entries with dates", flush=True)

    jobs = []
    for m in matches:
        title = m.group(1).strip()
        title = re.sub(r'^急\s*', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        date = m.group(2).strip()

        # Extract location and department from text after the date
        after = txt[m.end():m.end()+300]
        # Pattern: 全职 全职 | 技术类 技术类 | 北京市 北京市
        info_match = re.search(
            r'(全职|兼职|实习)\s+\1\s*\|\s*([一-鿿A-Za-z]+)\s+\2\s*\|\s*([一-鿿]+)\s+\3',
            after
        )
        location = ""
        department = ""
        if info_match:
            department = info_match.group(2)
            location = info_match.group(3)
        else:
            # Try simpler patterns
            loc_match = re.search(r'\|\s*([一-鿿]+市)\s+\1', after)
            if loc_match:
                location = loc_match.group(1)
            dept_match = re.search(r'\|\s*([一-鿿]+类)\s+\1', after)
            if dept_match:
                department = dept_match.group(1)

        jobs.append({
            "title": title,
            "publish_date": date,
            "location": location,
            "department": department,
        })

    # If text parsing failed, try parsing from DOM job items
    if not jobs and dom_jobs:
        print("\n  Trying to parse from DOM job items...", flush=True)
        for j in dom_jobs:
            text = j['text']
            # Look for date in the text
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            date = date_match.group(1) if date_match else ""
            # Title is usually the first significant text
            lines = text.split('\n')
            title = lines[0].strip() if lines else text[:50]
            # Clean title
            title = re.sub(r'^急\s*', '', title)
            jobs.append({
                "title": title,
                "publish_date": date,
                "location": "",
                "department": "",
                "raw_text": text[:300],
            })

    # Deduplicate
    seen = set()
    unique_jobs = []
    for j in jobs:
        key = (j['title'], j['publish_date'])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    unique_jobs.sort(key=lambda x: x['publish_date'], reverse=True)

    # Save API captures
    with open(OUT_API, "w") as f:
        json.dump(api_captures, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(api_captures)} API captures", flush=True)
    for c in api_captures:
        if any(k in c['url'] for k in ['job', 'position', 'module', 'group', 'list']):
            print(f"  API: {c['url'][:150]} (len={c['len']})", flush=True)

    # Save HTML and text
    with open(OUT_HTML, "w") as f:
        f.write(html)
    with open(OUT_TXT, "w") as f:
        f.write(txt[:200000])

    # Print all jobs
    print(f"\n=== ALL JOBS ({len(unique_jobs)}) ===", flush=True)
    matching = []
    for j in unique_jobs:
        title_lower = j['title'].lower()
        matched = [kw for kw in KEYWORDS if kw.lower() in title_lower]
        is_new = j['publish_date'] >= "2026-07-16"
        marker = ""
        if is_new:
            marker += " [NEW]"
        if matched:
            marker += f" [MATCH: {','.join(matched)}]"
        loc = j.get('location', '')
        dept = j.get('department', '')
        print(f"  {j['publish_date']} | {j['title']} | {loc} | {dept}{marker}", flush=True)
        if matched or is_new:
            j['matched_keywords'] = matched
            j['is_new'] = is_new
            matching.append(j)

    # Save JSON
    output = {
        "scrape_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_jobs": len(unique_jobs),
        "jobs": unique_jobs,
        "matching_or_new": matching,
        "dom_job_items": dom_jobs[:50],
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
