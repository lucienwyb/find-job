#!/usr/bin/env python3
"""Round 44: Check mokahr portals for Galbot (银河通用) and Zhipu (智谱) for new positions.
Today: 2026-07-16. Goal: find jobs published on or after 2026-07-16.

Approach: mokahr uses "necromancer" encryption on API responses.
Playwright renders the page, decrypting into plaintext DOM.
Job cards contain: title, "发布于 YYYY-MM-DD", department, location, category.
"""
import sys, json, re, time, os
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT_DIR = "/pulp/find-job"

def launch(p):
    b = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled",
              "--disable-gpu"],
        proxy={"server": PROXY})
    return b

def new_ctx(b):
    return b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 1100},
        locale="zh-CN",
        ignore_https_errors=True)

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    txt = re.sub(r"&[a-z]+;", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def extract_jobs_from_dom(html, txt):
    """Extract job title, publish date, department, location, category from rendered mokahr DOM.

    Mokahr job card structure (plaintext after tag strip):
      [急] <title> 发布于 YYYY-MM-DD <department> | 全职 | <category> 岗位职责：...

    We also try a structured approach via page.evaluate on React/Vue state.
    """
    jobs = []

    # Approach 1: regex on plaintext - find title + 发布于 date pairs
    # The text pattern: <title> 发布于 DATE <dept> | <type> | <category>
    pattern = re.compile(
        r'([^\s|]{3,50}?)\s+发布于\s+(\d{4}-\d{2}-\d{2})\s+'
        r'([^\|]*?)\s*\|\s*([^\|]*?)\s*\|\s*([^\s]{2,20})',
    )
    for m in pattern.finditer(txt):
        title = m.group(1).strip().strip('+0').strip()
        date = m.group(2)
        dept = m.group(3).strip()
        jobtype = m.group(4).strip()
        category = m.group(5).strip()
        # Clean repeated dept (mokahr shows dept twice)
        jobs.append({
            "title": title,
            "publishDate": date,
            "department": dept,
            "type": jobtype,
            "category": category,
        })

    # Approach 2: if approach 1 misses, try looser pattern - just title + date
    if not jobs:
        loose = re.findall(r'([^\s|]{4,50}?)\s+发布于\s+(\d{4}-\d{2}-\d{2})', txt)
        for title, date in loose:
            jobs.append({"title": title.strip(), "publishDate": date,
                         "department": "", "type": "", "category": ""})

    return jobs


def scrape_galbot():
    """Scrape 银河通用 (Galbot) mokahr portal."""
    print("\n" + "=" * 60, flush=True)
    print("###### GALBOT (银河通用) ######", flush=True)
    print("=" * 60, flush=True)

    with sync_playwright() as p:
        b = launch(p)
        ctx = new_ctx(b)
        page = ctx.new_page()

        url = "https://app.mokahr.com/social-recruitment/yinhetongyong/165929"
        print(f"Navigating to: {url}", flush=True)

        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"  HTTP status: {resp.status if resp else 'None'}", flush=True)
        except Exception as e:
            print(f"  goto error: {e}", flush=True)
            # Try alternate URL pattern
            url2 = "https://app.mokahr.com/apply/yinhetongyong/165929"
            print(f"  Trying alternate: {url2}", flush=True)
            resp = page.goto(url2, wait_until="domcontentloaded", timeout=45000)

        # Wait for page to render - mokahr needs time for JS decryption
        print("  Waiting for render (15s)...", flush=True)
        page.wait_for_timeout(15000)

        # Check if content loaded
        html = page.content()
        txt = clean(html)
        print(f"  Initial: html={len(html)} txt={len(txt)}", flush=True)

        if not any(k in txt for k in ['职位', '岗位', '工程师', '银河通用', '招聘']):
            print("  WARNING: No job content detected yet, waiting more...", flush=True)
            page.wait_for_timeout(15000)
            html = page.content()
            txt = clean(html)
            print(f"  After extra wait: html={len(html)} txt={len(txt)}", flush=True)

        # Try to clear category filter to see ALL jobs, not just 软件类
        # Look for "清除" (clear) or "全部" (all) buttons
        for clear_text in ["清除", "全部职位", "全部"]:
            try:
                loc = page.locator(f"text={clear_text}").first
                if loc.count() > 0:
                    print(f"  Clicking '{clear_text}' to clear filters...", flush=True)
                    loc.click(timeout=5000)
                    page.wait_for_timeout(5000)
                    break
            except:
                pass

        # Scroll down to load all job cards (lazy loading)
        print("  Scrolling to load all jobs...", flush=True)
        prev_count = 0
        for i in range(30):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(600)
            # Check if "发布于" count stabilized
            cur_html = page.content()
            cur_txt = clean(cur_html)
            cur_count = cur_txt.count("发布于")
            if cur_count == prev_count and i > 5:
                print(f"    Scroll {i}: {cur_count} jobs (stabilized)", flush=True)
                break
            if cur_count != prev_count:
                print(f"    Scroll {i}: {cur_count} jobs", flush=True)
            prev_count = cur_count

        # Final wait
        page.wait_for_timeout(3000)

        # Get final rendered content
        html = page.content()
        txt = clean(html)
        print(f"  Final: html={len(html)} txt={len(txt)}", flush=True)
        print(f"  '发布于' count: {txt.count('发布于')}", flush=True)

        # Save raw HTML and text
        with open(f"{OUT_DIR}/r44_galbot_raw.html", "w") as f:
            f.write(html)
        with open(f"{OUT_DIR}/r44_galbot_raw.txt", "w") as f:
            f.write(txt)

        # Extract jobs
        jobs = extract_jobs_from_dom(html, txt)
        print(f"\n  Extracted {len(jobs)} jobs via regex", flush=True)

        # Also try structured extraction via page.evaluate
        try:
            structured = page.evaluate("""() => {
                // Try to find job cards in DOM
                const results = [];
                // mokahr job list items
                const cards = document.querySelectorAll('[class*="job"], [class*="position"], [class*="card"], li[class*="item"]');
                cards.forEach(card => {
                    const text = card.innerText || '';
                    const dateMatch = text.match(/发布于\\s*(\\d{4}-\\d{2}-\\d{2})/);
                    if (dateMatch) {
                        results.push({text: text.substring(0, 300), date: dateMatch[1]});
                    }
                });
                return results;
            }""")
            print(f"  Structured DOM extraction: {len(structured)} cards with dates", flush=True)
            for s in structured[:5]:
                print(f"    {s['date']}: {s['text'][:100]}", flush=True)
        except Exception as e:
            print(f"  Structured extraction error: {e}", flush=True)
            structured = []

        # Deduplicate jobs by title+date
        seen = set()
        unique_jobs = []
        for j in jobs:
            key = (j["title"], j["publishDate"])
            if key not in seen and j["title"]:
                seen.add(key)
                unique_jobs.append(j)

        # Sort by publish date descending
        unique_jobs.sort(key=lambda x: x["publishDate"], reverse=True)

        print(f"\n{'='*60}")
        print(f"GALBOT: {len(unique_jobs)} unique jobs found")
        print(f"{'='*60}")
        for j in unique_jobs:
            flag = " ***NEW***" if j["publishDate"] >= "2026-07-16" else ""
            print(f"  {j['publishDate']}  {j['title']:<40} | {j['department']:<20} | {j['category']}{flag}")

        # Save to JSON
        output = {
            "company": "银河通用 (Galbot)",
            "portal": url,
            "scrapeDate": "2026-07-16",
            "totalJobs": len(unique_jobs),
            "jobs": unique_jobs,
            "structuredCards": structured,
        }
        with open(f"{OUT_DIR}/r44_yinhetongyong.json", "w") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n  Saved to {OUT_DIR}/r44_yinhetongyong.json", flush=True)

        ctx.close()
        b.close()

    return unique_jobs


def scrape_zhipu():
    """Scrape 智谱 (Zhipu) - try main portal and mokahr slugs."""
    print("\n" + "=" * 60, flush=True)
    print("###### ZHIPU (智谱) ######", flush=True)
    print("=" * 60, flush=True)

    # URLs to try
    urls_to_try = [
        ("zhipu_main", "https://zhipuai.cn/zh/joinus"),
        ("mokahr_zhipu", "https://app.mokahr.com/social-recruitment/zhipu"),
        ("mokahr_zhipuai", "https://app.mokahr.com/social-recruitment/zhipuai"),
        ("mokahr_zhipu-ai", "https://app.mokahr.com/social-recruitment/zhipu-ai"),
        ("mokahr_apply_zhipu", "https://app.mokahr.com/apply/zhipu"),
        ("mokahr_apply_zhipuai", "https://app.mokahr.com/apply/zhipuai"),
        ("mokahr_zhipuai-ai", "https://app.mokahr.com/social-recruitment/zhipuai-ai"),
    ]

    all_jobs = []
    best_source = None

    with sync_playwright() as p:
        b = launch(p)

        for name, url in urls_to_try:
            ctx = new_ctx(b)
            page = ctx.new_page()

            # Capture API responses
            api_captures = []
            def on_resp(resp, ac=api_captures):
                try:
                    ct = resp.headers.get('content-type', '')
                    u = resp.url
                    if any(t in ct for t in ['json', 'text', 'javascript']) and len(u) > 10:
                        body = resp.text()
                        if body and len(body) > 100:
                            ac.append({"url": u, "status": resp.status,
                                       "ct": ct[:30], "len": len(body),
                                       "body": body[:8000]})
                except:
                    pass
            page.on("response", on_resp)

            print(f"\n--- Trying {name}: {url} ---", flush=True)
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                status = resp.status if resp else None
                print(f"  HTTP status: {status}", flush=True)
                page.wait_for_timeout(12000)

                html = page.content()
                txt = clean(html)
                print(f"  html={len(html)} txt={len(txt)}", flush=True)

                # Check for error page
                if '页面不存在' in txt or 'not found' in txt.lower() or '404' in txt[:200]:
                    print(f"  -> Error/404 page, skipping", flush=True)
                    ctx.close()
                    continue

                # Check if real job content
                has_jobs = any(k in txt for k in ['职位', '岗位', '工程师', '智谱', '招聘', '发布于'])
                print(f"  Has job content: {has_jobs}", flush=True)

                if not has_jobs:
                    # Print preview for debugging
                    print(f"  txt preview: {txt[:300]}", flush=True)
                    ctx.close()
                    continue

                # Found real content - scroll to load all
                print(f"  *** REAL CONTENT FOUND ***", flush=True)

                # Try to clear filters
                for clear_text in ["清除", "全部"]:
                    try:
                        loc = page.locator(f"text={clear_text}").first
                        if loc.count() > 0:
                            loc.click(timeout=3000)
                            page.wait_for_timeout(3000)
                            break
                    except:
                        pass

                # Scroll to load all jobs
                prev_count = 0
                for i in range(40):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(500)
                    cur_txt = clean(page.content())
                    cur_count = cur_txt.count("发布于")
                    if cur_count == prev_count and i > 5:
                        break
                    prev_count = cur_count

                page.wait_for_timeout(3000)
                html = page.content()
                txt = clean(html)
                print(f"  Final: html={len(html)} txt={len(txt)}", flush=True)
                print(f"  '发布于' count: {txt.count('发布于')}", flush=True)

                # Save raw
                with open(f"{OUT_DIR}/r44_zhipu_{name}_raw.html", "w") as f:
                    f.write(html)
                with open(f"{OUT_DIR}/r44_zhipu_{name}_raw.txt", "w") as f:
                    f.write(txt)

                # Save API captures
                with open(f"{OUT_DIR}/r44_zhipu_{name}_api.json", "w") as f:
                    json.dump(api_captures, f, ensure_ascii=False, indent=2)

                # Print API endpoints for debugging
                for c in api_captures:
                    if any(k in c['url'].lower() for k in ['job', 'position', 'list', 'search', 'module']):
                        print(f"  API: {c['url'][:130]} len={c['len']}", flush=True)

                # Extract jobs
                jobs = extract_jobs_from_dom(html, txt)
                print(f"  Extracted {len(jobs)} jobs", flush=True)

                if jobs:
                    all_jobs = jobs
                    best_source = name
                    print(f"  Using results from {name}", flush=True)
                    ctx.close()
                    break

                # If no "发布于" dates found, try extracting job titles differently
                # Some mokahr pages show dates differently or not at all
                if '发布于' not in txt:
                    print(f"  No '发布于' dates found, trying alternate extraction...", flush=True)
                    # Look for job titles near department/location markers
                    titles = re.findall(r'>([^<]{4,60})<', html)
                    job_titles = [t.strip() for t in titles
                                  if any(k in t for k in ['工程师', '开发', '架构', '系统', '平台',
                                                          'Agent', 'Infra', 'SRE', '运维', '后端',
                                                          '前端', '算法', '数据', '安全', '测试',
                                                          '经理', '专家', '主管', '总监', '实习'])
                                  and '智谱' not in t and '招聘' not in t
                                  and len(t.strip()) > 4]
                    if job_titles:
                        print(f"  Found {len(job_titles)} job titles (no dates):", flush=True)
                        for t in job_titles[:30]:
                            print(f"    - {t}", flush=True)
                        all_jobs = [{"title": t, "publishDate": "", "department": "",
                                     "type": "", "category": ""} for t in job_titles]
                        best_source = name
                        ctx.close()
                        break

                ctx.close()

            except Exception as e:
                print(f"  Error: {e}", flush=True)
                ctx.close()
                continue

        b.close()

    # Deduplicate
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j["title"], j.get("publishDate", ""))
        if key not in seen and j["title"]:
            seen.add(key)
            unique_jobs.append(j)

    unique_jobs.sort(key=lambda x: x.get("publishDate", "0000"), reverse=True)

    print(f"\n{'='*60}")
    print(f"ZHIPU: {len(unique_jobs)} unique jobs found (source: {best_source})")
    print(f"{'='*60}")
    for j in unique_jobs:
        date = j.get("publishDate", "N/A")
        flag = " ***NEW***" if date and date >= "2026-07-16" else ""
        print(f"  {date:<12}  {j['title']:<50}{flag}")

    output = {
        "company": "智谱 (Zhipu)",
        "portal": best_source,
        "scrapeDate": "2026-07-16",
        "totalJobs": len(unique_jobs),
        "jobs": unique_jobs,
    }
    with open(f"{OUT_DIR}/r44_zhipu.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved to {OUT_DIR}/r44_zhipu.json", flush=True)

    return unique_jobs


def highlight_matching(jobs, company):
    """Highlight positions matching candidate profile."""
    keywords = ['kernel', 'eBPF', 'system', '嵌入式', 'BSP', 'OS', '操作系统',
                'Agent', 'Infra', 'SRE', 'runtime', '运行时', '系统', '底层',
                '驱动', '内核', '平台', '架构', '后端', '基础设施']
    print(f"\n--- {company}: Matching positions ---")
    matches = []
    for j in jobs:
        title = j.get("title", "")
        for kw in keywords:
            if kw.lower() in title.lower():
                matches.append((j, kw))
                break

    if matches:
        for j, kw in matches:
            date = j.get("publishDate", "N/A")
            flag = " ***NEW***" if date and date >= "2026-07-16" else ""
            print(f"  [{kw}] {date}  {j['title']:<40} | {j.get('department','')}{flag}")
    else:
        print("  (none found)")
    return matches


if __name__ == "__main__":
    print("Round 44: Mokahr portal check")
    print(f"Date: 2026-07-16")
    print(f"Proxy: {PROXY}")
    print(f"Output dir: {OUT_DIR}")

    os.makedirs(OUT_DIR, exist_ok=True)

    galbot_jobs = scrape_galbot()
    highlight_matching(galbot_jobs, "GALBOT")

    zhipu_jobs = scrape_zhipu()
    highlight_matching(zhipu_jobs, "ZHIPU")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Galbot: {len(galbot_jobs)} jobs total")
    new_galbot = [j for j in galbot_jobs if j.get("publishDate", "") >= "2026-07-16"]
    print(f"  New (>=2026-07-16): {len(new_galbot)}")
    for j in new_galbot:
        print(f"    {j['publishDate']}  {j['title']}")

    print(f"Zhipu: {len(zhipu_jobs)} jobs total")
    new_zhipu = [j for j in zhipu_jobs if j.get("publishDate", "") >= "2026-07-16"]
    print(f"  New (>=2026-07-16): {len(new_zhipu)}")
    for j in new_zhipu:
        print(f"    {j['publishDate']}  {j['title']}")

    print("\nDone.")
