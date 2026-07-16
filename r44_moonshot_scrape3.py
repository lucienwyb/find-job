#!/usr/bin/env python3
"""Round 44 v3: Scrape Moonshot careers - navigate to full job list, click each job."""
import json, re, time, sys
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT_JSON = "/pulp/find-job/r44_moonshot.json"
OUT_HTML = "/pulp/find-job/r44_moonshot.html"
OUT_TXT = "/pulp/find-job/r44_moonshot.txt"

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
    print("=== Moonshot Careers Scrape v3 (Round 44) ===", flush=True)
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

    # Step 1: Navigate to the main page
    print("\n--- Step 1: Load main page ---", flush=True)
    try:
        page.goto(base_url, wait_until="networkidle", timeout=60000)
    except:
        page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)

    # Step 2: Navigate to #/jobs to see full job list
    print("\n--- Step 2: Navigate to #/jobs ---", flush=True)
    try:
        page.goto(f"{base_url}#/jobs", wait_until="networkidle", timeout=60000)
    except:
        page.goto(f"{base_url}#/jobs", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)

    html = page.content()
    txt = clean_text(html)
    print(f"  html={len(html)} txt={len(txt)}", flush=True)
    print(f"  Text preview: {txt[:500]}", flush=True)

    # Check if we have job list
    has_jobs = '发布于' in txt or '职位' in txt or '工程师' in txt
    print(f"  Has job content: {has_jobs}", flush=True)

    # Step 3: Scroll to load all jobs in the list
    print("\n--- Step 3: Scroll to load all jobs ---", flush=True)
    for i in range(40):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(200)

    # Also scroll any scrollable containers
    try:
        page.evaluate("""
            () => {
                document.querySelectorAll('*').forEach(el => {
                    if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 100) {
                        el.scrollTop = el.scrollHeight;
                    }
                });
            }
        """)
        page.wait_for_timeout(5000)
    except:
        pass

    html = page.content()
    txt = clean_text(html)
    print(f"  After scroll: html={len(html)} txt={len(txt)}", flush=True)

    # Step 4: Extract all job links
    print("\n--- Step 4: Extract job links ---", flush=True)
    job_links = page.query_selector_all("a[href*='#/job/']")
    print(f"  Found {len(job_links)} job links", flush=True)

    job_urls = []
    for link in job_links:
        try:
            href = link.get_attribute('href')
            if href and '#/job/' in href:
                full_url = f"{base_url}{href}" if href.startswith('#') else href
                # Get the link text as a hint for the job title
                text = link.inner_text().strip()[:200]
                job_urls.append({"url": full_url, "title_hint": text})
        except:
            pass

    # Also try to get job links from the full job list by looking for all job IDs
    # The page might have more jobs that aren't all rendered yet
    # Try to find all job IDs in the HTML
    job_ids = re.findall(r'#/job/([a-f0-9\-]+)', html)
    print(f"  Found {len(job_ids)} unique job IDs in HTML", flush=True)

    # Deduplicate
    seen_ids = set()
    unique_job_urls = []
    for j in job_urls:
        job_id = j['url'].split('/job/')[-1] if '/job/' in j['url'] else ''
        if job_id and job_id not in seen_ids:
            seen_ids.add(job_id)
            unique_job_urls.append(j)

    # Add any IDs found in HTML that weren't in the link elements
    for jid in job_ids:
        if jid not in seen_ids:
            seen_ids.add(jid)
            unique_job_urls.append({"url": f"{base_url}#/job/{jid}", "title_hint": ""})

    print(f"  Total unique job URLs: {len(unique_job_urls)}", flush=True)

    # Save the jobs list page HTML
    with open(OUT_HTML, "w") as f:
        f.write(html)
    with open(OUT_TXT, "w") as f:
        f.write(txt[:200000])

    # Step 5: Visit each job page to extract details
    print("\n--- Step 5: Visit each job page ---", flush=True)
    all_jobs = []

    # If we didn't find individual job links, try parsing the full text
    if not unique_job_urls and has_jobs:
        print("  No individual job links found, parsing from text...", flush=True)
        pattern = r'((?:急\s+)?[一-鿿\w/\-（）·,.\s&;:#+|]+?)\s+发布于\s+(\d{4}-\d{2}-\d{2})'
        matches = list(re.finditer(pattern, txt))
        print(f"  Found {len(matches)} jobs with dates in text", flush=True)
        for m in matches:
            title = re.sub(r'^急\s*', '', m.group(1)).strip()
            title = re.sub(r'\s+', ' ', title).strip()
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
            all_jobs.append({
                "title": title,
                "publish_date": m.group(2),
                "location": loc,
                "department": dept,
            })

    # Visit each job page individually
    for i, job_url_info in enumerate(unique_job_urls):
        url = job_url_info['url']
        title_hint = job_url_info['title_hint']
        print(f"\n  [{i+1}/{len(unique_job_urls)}] {title_hint[:50]} -> {url}", flush=True)
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"    Error: {e}", flush=True)
                continue
        page.wait_for_timeout(3000)

        job_html = page.content()
        job_txt = clean_text(job_html)

        # Extract publish date
        date_match = re.search(r'发布于\s*(\d{4}-\d{2}-\d{2})', job_txt)
        date = date_match.group(1) if date_match else ""

        # Extract title - look for pattern after "职位详情"
        # The title usually appears after "首页 / 职位列表 / 职位详情 /"
        title_match = re.search(r'职位详情\s*/\s*(.+?)(?:\s+分享|\s+发布于)', job_txt)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Try another pattern
            title_match2 = re.search(r'申请职位\s+(.+?)(?:\s+发布于|\s+全职|\s+兼职)', job_txt)
            if title_match2:
                title = title_match2.group(1).strip()
            else:
                title = title_hint

        # Clean title
        title = re.sub(r'^急\s*', '', title).strip()

        # Extract job type, department, location
        # Pattern: 全职 | 技术类 | 北京市
        info_match = re.search(
            r'(全职|兼职|实习)\s*\|\s*([一-鿿A-Za-z]+类?)\s*\|\s*([一-鿿]+)',
            job_txt
        )
        location = ""
        department = ""
        if info_match:
            department = info_match.group(2)
            location = info_match.group(3)
        else:
            # Try to find location separately
            loc_match = re.search(r'(北京市|上海市|深圳市|成都市|新加坡|美国|硅谷)', job_txt)
            if loc_match:
                location = loc_match.group(1)

        # Extract description snippet (first 500 chars after "职位描述")
        desc_match = re.search(r'职位描述[:：]?\s*(.{0,500})', job_txt)
        desc = desc_match.group(1).strip() if desc_match else ""

        print(f"    Title: {title}", flush=True)
        print(f"    Date: {date} | Loc: {location} | Dept: {department}", flush=True)

        all_jobs.append({
            "title": title,
            "publish_date": date,
            "location": location,
            "department": department,
            "url": url,
            "description_snippet": desc[:300],
        })

    # Also try the full text parse from the jobs list page
    if has_jobs:
        pattern = r'((?:急\s+)?[一-鿿\w/\-（）·,.\s&;:#+|]+?)\s+发布于\s+(\d{4}-\d{2}-\d{2})'
        matches = list(re.finditer(pattern, txt))
        if matches:
            print(f"\n  Also found {len(matches)} jobs in the full list text", flush=True)
            for m in matches:
                title = re.sub(r'^急\s*', '', m.group(1)).strip()
                title = re.sub(r'\s+', ' ', title).strip()
                date = m.group(2)
                # Check if already in all_jobs
                if not any(j['title'] == title and j['publish_date'] == date for j in all_jobs):
                    all_jobs.append({
                        "title": title,
                        "publish_date": date,
                        "location": "",
                        "department": "",
                        "url": "",
                    })

    # Deduplicate
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j['title'], j['publish_date'])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    unique_jobs.sort(key=lambda x: x.get('publish_date', ''), reverse=True)

    # Save final JSON
    output = {
        "scrape_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_jobs": len(unique_jobs),
        "jobs": unique_jobs,
        "matching_or_new": [],
    }

    print(f"\n=== ALL JOBS ({len(unique_jobs)}) ===", flush=True)
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

    output["matching_or_new"] = matching

    with open(OUT_JSON, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(unique_jobs)} jobs to {OUT_JSON}", flush=True)
    print(f"Matching/new: {len(matching)}", flush=True)

    ctx.close()
    b.close()
    p.stop()

if __name__ == "__main__":
    main()
