#!/usr/bin/env python3
"""Round 44 v4: Scrape ALL Moonshot jobs by scrolling the job list container."""
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
    print("=== Moonshot Careers Scrape v4 (Round 44) ===", flush=True)
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

    # Check initial state
    txt = clean_text(page.content())
    results_match = re.search(r'(\d+)\s*结果', txt)
    total_expected = int(results_match.group(1)) if results_match else 0
    print(f"  Expected total: {total_expected} jobs", flush=True)

    # Scroll the job list container to load all jobs
    print("\n--- Scrolling job list to load all jobs ---", flush=True)
    prev_job_count = 0
    stable_count = 0

    for scroll_round in range(100):
        # Use JavaScript to find and scroll the job list container
        # mokahr typically uses overflow-y: auto/scroll on a list container
        new_links = page.evaluate("""
            () => {
                // Find all scrollable elements and scroll them
                const scrollables = [];
                document.querySelectorAll('*').forEach(el => {
                    const style = window.getComputedStyle(el);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                        el.scrollHeight > el.clientHeight + 50) {
                        scrollables.push(el);
                    }
                });

                // Scroll each scrollable element
                scrollables.forEach(el => {
                    el.scrollTop = el.scrollHeight;
                });

                // Also scroll window
                window.scrollTo(0, document.body.scrollHeight);

                // Return current job links count
                const links = document.querySelectorAll("a[href*='#/job/']");
                return {
                    jobLinks: links.length,
                    scrollables: scrollables.length,
                    scrollableClasses: scrollables.map(el => el.className.substring(0, 80)),
                };
            }
        """)

        curr_count = new_links.get('jobLinks', 0)
        num_scrollables = new_links.get('scrollables', 0)
        scrollable_classes = new_links.get('scrollableClasses', [])

        if scroll_round == 0:
            print(f"  Found {num_scrollables} scrollable elements: {scrollable_classes[:5]}", flush=True)

        if curr_count != prev_job_count:
            print(f"  Round {scroll_round}: {curr_count} job links loaded", flush=True)
            prev_job_count = curr_count
            stable_count = 0
        else:
            stable_count += 1

        # If count hasn't changed for 10 rounds, we're done
        if stable_count >= 10:
            print(f"  Job count stable at {curr_count} for 10 rounds, stopping scroll", flush=True)
            break

        page.wait_for_timeout(1000)

    # Also try mouse wheel scrolling
    print("\n--- Additional mouse wheel scrolling ---", flush=True)
    for _ in range(20):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(300)

    # Get final HTML and text
    html = page.content()
    txt = clean_text(html)
    print(f"\n  Final: html={len(html)} txt={len(txt)}", flush=True)

    # Count all job links and dates
    all_job_links = page.query_selector_all("a[href*='#/job/']")
    print(f"  Total job links found: {len(all_job_links)}", flush=True)

    # Extract job URLs
    job_urls = []
    seen_ids = set()
    for link in all_job_links:
        try:
            href = link.get_attribute('href')
            if href and '#/job/' in href:
                job_id = href.split('/job/')[-1]
                if job_id not in seen_ids:
                    seen_ids.add(job_id)
                    text = link.inner_text().strip()[:200]
                    job_urls.append({
                        "url": f"{base_url}#/job/{job_id}",
                        "title_hint": text,
                    })
        except:
            pass

    # Also check HTML for job IDs
    job_ids_html = re.findall(r'#/job/([a-f0-9\-]+)', html)
    for jid in job_ids_html:
        if jid not in seen_ids:
            seen_ids.add(jid)
            job_urls.append({"url": f"{base_url}#/job/{jid}", "title_hint": ""})

    print(f"  Total unique job URLs: {len(job_urls)}", flush=True)

    # Save the jobs list page
    with open(OUT_HTML, "w") as f:
        f.write(html)
    with open(OUT_TXT, "w") as f:
        f.write(txt[:200000])

    # Now try to extract all jobs from the full text first
    print("\n--- Parsing jobs from text ---", flush=True)
    # Better pattern: capture title before 发布于
    pattern = r'((?:急\s+)?[一-鿿\w/\-（）·,.\s&;:#+|]+?)\s+发布于\s+(\d{4}-\d{2}-\d{2})'
    matches = list(re.finditer(pattern, txt))
    print(f"  Found {len(matches)} jobs with dates in text", flush=True)

    text_jobs = {}
    for m in matches:
        title = re.sub(r'^急\s*', '', m.group(1)).strip()
        title = re.sub(r'\s+', ' ', title).strip()
        # Skip if title is too long (likely page header text)
        if len(title) > 100:
            continue
        date = m.group(2)
        # Extract location and department
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
        if key not in text_jobs:
            text_jobs[key] = {
                "title": title,
                "publish_date": date,
                "location": loc,
                "department": dept,
            }

    print(f"  Unique text jobs: {len(text_jobs)}", flush=True)

    # Now visit each job page that we haven't already found in text
    text_job_titles = set(j['title'] for j in text_jobs.values())
    jobs_to_visit = []
    for ju in job_urls:
        # Check if the title_hint matches any text job
        hint = ju['title_hint'].replace('\n', ' ').strip()
        hint = re.sub(r'^急\s*', '', hint).strip()
        # Try to match
        matched = False
        for tj in text_job_titles:
            if hint and (hint in tj or tj in hint):
                matched = True
                break
        if not matched:
            jobs_to_visit.append(ju)

    print(f"\n  Jobs in text: {len(text_jobs)}, Need to visit: {len(jobs_to_visit)}", flush=True)

    # Visit remaining jobs
    visited_jobs = list(text_jobs.values())
    for i, ju in enumerate(jobs_to_visit):
        url = ju['url']
        hint = ju['title_hint'].replace('\n', ' ').strip()[:60]
        print(f"\n  [{i+1}/{len(jobs_to_visit)}] {hint} -> {url}", flush=True)
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"    Error: {e}", flush=True)
                continue
        page.wait_for_timeout(2000)

        job_txt = clean_text(page.content())

        date_match = re.search(r'发布于\s*(\d{4}-\d{2}-\d{2})', job_txt)
        date = date_match.group(1) if date_match else ""

        title_match = re.search(r'职位详情\s*/\s*(.+?)(?:\s+分享|\s+发布于|\s+全职|\s+兼职)', job_txt)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = hint
        title = re.sub(r'^急\s*', '', title).strip()

        info_match = re.search(
            r'(全职|兼职|实习)\s*\|?\s*([一-鿿A-Za-z]+)\s*\|?\s*([一-鿿]+)',
            job_txt
        )
        loc = ""
        dept = ""
        if info_match:
            dept = info_match.group(2) if info_match.group(2) else ""
            loc = info_match.group(3) if info_match.group(3) else ""

        desc_match = re.search(r'职位描述[:：]?\s*(.{0,500})', job_txt)
        desc = desc_match.group(1).strip() if desc_match else ""

        print(f"    Title: {title} | Date: {date} | Loc: {loc} | Dept: {dept}", flush=True)

        visited_jobs.append({
            "title": title,
            "publish_date": date,
            "location": loc,
            "department": dept,
            "url": url,
            "description_snippet": desc[:300],
        })

    # Now also visit jobs that were in text but don't have location/department
    # to get full details
    jobs_needing_details = [j for j in visited_jobs if not j.get('location') and not j.get('department') and j.get('publish_date')]
    if jobs_needing_details:
        print(f"\n--- Visiting {len(jobs_needing_details)} jobs to get location/dept ---", flush=True)
        # Build URL lookup from job_urls
        url_by_title = {}
        for ju in job_urls:
            hint = ju['title_hint'].replace('\n', ' ').strip()
            hint = re.sub(r'^急\s*', '', hint).strip()
            url_by_title[hint] = ju['url']

        for j in jobs_needing_details:
            title = j['title']
            url = url_by_title.get(title, "")
            if not url:
                # Try partial match
                for hint, u in url_by_title.items():
                    if title in hint or hint in title:
                        url = u
                        break
            if not url:
                continue
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except:
                    continue
            page.wait_for_timeout(2000)
            job_txt = clean_text(page.content())
            info_match = re.search(
                r'(全职|兼职|实习)\s+\1?\s*\|?\s*([一-鿿A-Za-z]+)\s+\2?\s*\|?\s*([一-鿿]+)',
                job_txt[:500]
            )
            if info_match:
                j['department'] = info_match.group(2) if info_match.group(2) else ""
                j['location'] = info_match.group(3) if info_match.group(3) else ""
            desc_match = re.search(r'职位描述[:：]?\s*(.{0,500})', job_txt)
            if desc_match:
                j['description_snippet'] = desc_match.group(1).strip()[:300]
            print(f"  {title}: {j.get('location','')} | {j.get('department','')}", flush=True)

    # Deduplicate
    seen = set()
    unique_jobs = []
    for j in visited_jobs:
        key = (j['title'], j['publish_date'])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    unique_jobs.sort(key=lambda x: x.get('publish_date', ''), reverse=True)

    # Print all jobs
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

    # Save JSON
    output = {
        "scrape_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_expected": total_expected,
        "total_scraped": len(unique_jobs),
        "jobs": unique_jobs,
        "matching_or_new": matching,
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
