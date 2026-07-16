#!/usr/bin/env python3
"""Round 44 v2: Scrape Galbot mokahr by clicking into categories.
Also retry Zhipu with longer timeout and search for correct portal.
"""
import sys, json, re, time, os
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT_DIR = "/pulp/find-job"

def launch(p):
    return p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled", "--disable-gpu"],
        proxy={"server": PROXY})

def new_ctx(b):
    return b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 1100}, locale="zh-CN", ignore_https_errors=True)

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    txt = re.sub(r"&[a-z]+;", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()

def extract_jobs_from_txt(txt):
    """Extract job title + publish date from plaintext DOM."""
    jobs = []
    # Pattern: <title> 发布于 YYYY-MM-DD <dept> | 全职 | <category>
    pattern = re.compile(
        r'([^\s|]{3,50}?)\s+发布于\s+(\d{4}-\d{2}-\d{2})\s+'
        r'([^\|]*?)\s*\|\s*([^\|]*?)\s*\|\s*([^\s]{2,20})')
    for m in pattern.finditer(txt):
        title = m.group(1).strip()
        date = m.group(2)
        dept = m.group(3).strip()
        jobtype = m.group(4).strip()
        category = m.group(5).strip()
        jobs.append({"title": title, "publishDate": date, "department": dept,
                     "type": jobtype, "category": category})
    # Looser fallback
    if not jobs:
        loose = re.findall(r'([^\s|]{4,50}?)\s+发布于\s+(\d{4}-\d{2}-\d{2})', txt)
        for title, date in loose:
            jobs.append({"title": title.strip(), "publishDate": date,
                         "department": "", "type": "", "category": ""})
    return jobs


def scrape_galbot():
    print("\n" + "=" * 60, flush=True)
    print("###### GALBOT (银河通用) ######", flush=True)
    print("=" * 60, flush=True)

    all_jobs = []
    # Categories most relevant to a kernel/eBPF engineer
    categories_to_check = ["软件类", "算法类", "测试类", "硬件类", "技术支持类"]

    with sync_playwright() as p:
        b = launch(p)
        ctx = new_ctx(b)
        page = ctx.new_page()

        url = "https://app.mokahr.com/social-recruitment/yinhetongyong/165929"
        print(f"Navigating to: {url}", flush=True)
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        print(f"  HTTP status: {resp.status if resp else 'None'}", flush=True)

        # Wait for landing page render
        print("  Waiting for landing page render (12s)...", flush=True)
        page.wait_for_timeout(12000)

        html = page.content()
        txt = clean(html)
        print(f"  Landing: html={len(html)} txt={len(txt)}", flush=True)

        # Show category counts from landing page
        cats = re.findall(r'(\S+类)\s+共(\d+)个职位', txt)
        print(f"  Categories on landing page: {cats}", flush=True)

        # Click into each category and extract jobs
        for cat in categories_to_check:
            print(f"\n  --- Clicking category: {cat} ---", flush=True)
            try:
                # Navigate fresh to landing page each time (mokahr SPA state can get stuck)
                if cat != categories_to_check[0]:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(8000)

                # Click the category
                loc = page.locator(f"text={cat}").first
                if loc.count() == 0:
                    print(f"    Category '{cat}' not found, skipping", flush=True)
                    continue

                loc.click(timeout=8000)
                print(f"    Clicked '{cat}', waiting for job list...", flush=True)
                page.wait_for_timeout(8000)

                # Scroll to load all jobs in this category
                prev_count = 0
                for i in range(30):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(500)
                    cur_txt = clean(page.content())
                    cur_count = cur_txt.count("发布于")
                    if cur_count == prev_count and i > 5:
                        break
                    prev_count = cur_count

                page.wait_for_timeout(2000)
                cat_html = page.content()
                cat_txt = clean(cat_html)
                print(f"    html={len(cat_html)} txt={len(cat_txt)} 发布于={cat_txt.count('发布于')}", flush=True)

                # Save raw for first (software) category
                if cat == "软件类":
                    with open(f"{OUT_DIR}/r44_galbot_software_raw.html", "w") as f:
                        f.write(cat_html)
                    with open(f"{OUT_DIR}/r44_galbot_software_raw.txt", "w") as f:
                        f.write(cat_txt)

                # Extract jobs
                jobs = extract_jobs_from_txt(cat_txt)
                # Tag with category
                for j in jobs:
                    if not j.get("category"):
                        j["category"] = cat
                print(f"    Extracted {len(jobs)} jobs", flush=True)

                # Also try page.evaluate for structured data
                try:
                    structured = page.evaluate("""(catName) => {
                        const results = [];
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            const text = el.innerText || '';
                            const dateMatch = text.match(/发布于\\s*(\\d{4}-\\d{2}-\\d{2})/);
                            if (dateMatch && text.length < 500 && text.length > 10) {
                                // Get the title - usually the text before 发布于
                                const before = text.substring(0, text.indexOf('发布于')).trim();
                                if (before.length > 2 && before.length < 60) {
                                    results.push({title: before, date: dateMatch[1], fullText: text.substring(0, 200)});
                                }
                            }
                        }
                        return results;
                    }""", cat)
                    if structured and len(structured) > len(jobs):
                        print(f"    Structured extraction found {len(structured)} jobs (using this)", flush=True)
                        jobs = [{"title": s["title"], "publishDate": s["date"],
                                 "department": "", "type": "", "category": cat,
                                 "fullText": s.get("fullText", "")} for s in structured]
                except Exception as e:
                    print(f"    Structured extraction err: {e}", flush=True)

                for j in jobs:
                    print(f"      {j['publishDate']}  {j['title']}", flush=True)
                all_jobs.extend(jobs)

            except Exception as e:
                print(f"    Error with category '{cat}': {e}", flush=True)

        ctx.close()
        b.close()

    # Deduplicate
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j["title"], j["publishDate"])
        if key not in seen and j["title"] and len(j["title"]) > 1:
            seen.add(key)
            unique_jobs.append(j)

    unique_jobs.sort(key=lambda x: x.get("publishDate", "0000"), reverse=True)

    print(f"\n{'='*60}")
    print(f"GALBOT: {len(unique_jobs)} unique jobs found")
    print(f"{'='*60}")
    for j in unique_jobs:
        flag = " ***NEW***" if j["publishDate"] >= "2026-07-16" else ""
        print(f"  {j['publishDate']}  {j['title']:<45} | {j.get('department',''):<20} | {j.get('category','')}{flag}")

    output = {
        "company": "银河通用 (Galbot)",
        "portal": url,
        "scrapeDate": "2026-07-16",
        "totalJobs": len(unique_jobs),
        "jobs": unique_jobs,
    }
    with open(f"{OUT_DIR}/r44_yinhetongyong.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved to {OUT_DIR}/r44_yinhetongyong.json", flush=True)
    return unique_jobs


def scrape_zhipu():
    print("\n" + "=" * 60, flush=True)
    print("###### ZHIPU (智谱) ######", flush=True)
    print("=" * 60, flush=True)

    all_jobs = []

    with sync_playwright() as p:
        b = launch(p)

        # Step 1: Try zhipuai.cn/zh/joinus with longer timeout - look for mokahr link
        ctx = new_ctx(b)
        page = ctx.new_page()

        api_captures = []
        def on_resp(resp):
            try:
                ct = resp.headers.get('content-type', '')
                u = resp.url
                if any(t in ct for t in ['json', 'text', 'javascript']):
                    body = resp.text()
                    if body and len(body) > 100:
                        api_captures.append({"url": u, "status": resp.status,
                                             "ct": ct[:30], "len": len(body),
                                             "body": body[:5000]})
            except:
                pass
        page.on("response", on_resp)

        url = "https://zhipuai.cn/zh/joinus"
        print(f"\n--- Trying zhipuai.cn: {url} ---", flush=True)
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"  HTTP status: {resp.status if resp else 'None'}", flush=True)
            page.wait_for_timeout(15000)

            html = page.content()
            txt = clean(html)
            print(f"  html={len(html)} txt={len(txt)}", flush=True)

            # Save raw
            with open(f"{OUT_DIR}/r44_zhipu_main_raw.html", "w") as f:
                f.write(html)
            with open(f"{OUT_DIR}/r44_zhipu_main_raw.txt", "w") as f:
                f.write(txt)

            # Look for mokahr links or job content
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
            moka_links = [h for h in hrefs if 'mokahr' in h.lower() or 'apply' in h.lower() or 'job' in h.lower()]
            print(f"  Found {len(hrefs)} hrefs, {len(moka_links)} job/moka-related", flush=True)
            for h in moka_links[:10]:
                print(f"    link: {h}", flush=True)

            # Check for job content
            has_jobs = any(k in txt for k in ['职位', '岗位', '工程师', '发布于', '招聘'])
            print(f"  Has job content: {has_jobs}", flush=True)
            if has_jobs:
                print(f"  txt preview: {txt[:1000]}", flush=True)

            # Look for API calls to mokahr
            for c in api_captures:
                if any(k in c['url'].lower() for k in ['mokahr', 'job', 'position', 'list']):
                    print(f"  API: {c['url'][:130]} len={c['len']}", flush=True)

            # Save API captures
            with open(f"{OUT_DIR}/r44_zhipu_main_api.json", "w") as f:
                json.dump(api_captures, f, ensure_ascii=False, indent=2)

            # If we found mokahr links, try them
            for link in moka_links:
                if 'mokahr.com' in link:
                    print(f"\n  Trying mokahr link found on page: {link}", flush=True)
                    # Extract slug from URL
                    m = re.search(r'/(?:social-recruitment|apply)/([^/]+)', link)
                    if m:
                        slug = m.group(1)
                        print(f"    Slug: {slug}", flush=True)
                        # Try this URL directly
                        page.goto(link, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(12000)
                        m_html = page.content()
                        m_txt = clean(m_html)
                        print(f"    html={len(m_html)} txt={len(m_txt)}", flush=True)
                        if '发布于' in m_txt or '工程师' in m_txt:
                            print(f"    *** REAL JOB CONTENT ***", flush=True)
                            with open(f"{OUT_DIR}/r44_zhipu_moka_raw.html", "w") as f:
                                f.write(m_html)
                            with open(f"{OUT_DIR}/r44_zhipu_moka_raw.txt", "w") as f:
                                f.write(m_txt)

                            # Try clicking categories and scrolling
                            for cat in ["全部", "技术", "工程", "研发", "Infra", "系统"]:
                                try:
                                    loc = page.locator(f"text={cat}").first
                                    if loc.count() > 0:
                                        loc.click(timeout=3000)
                                        page.wait_for_timeout(5000)
                                        break
                                except:
                                    pass

                            # Scroll
                            for i in range(30):
                                page.mouse.wheel(0, 3000)
                                page.wait_for_timeout(500)

                            m_html = page.content()
                            m_txt = clean(m_html)
                            jobs = extract_jobs_from_txt(m_txt)
                            print(f"    Extracted {len(jobs)} jobs", flush=True)
                            for j in jobs[:20]:
                                print(f"      {j['publishDate']}  {j['title']}", flush=True)
                            all_jobs = jobs
                            break

        except Exception as e:
            print(f"  Error: {e}", flush=True)

        ctx.close()

        # Step 2: If nothing found, try more mokahr slugs based on common patterns
        if not all_jobs:
            print("\n--- No jobs from main site, trying mokahr slugs ---", flush=True)
            # Try to find slug by searching mokahr
            extra_slugs = [
                "zhipu-ai", "zhipuai-ai", "zhipu-ai-tech", "zhipuaitech",
                "zhipu-ai-tech-co-ltd", "zhipu-ai-inc", "bigmodel",
                "zhipu-bigmodel", "chatglm", "zhipu-chatglm",
            ]
            for slug in extra_slugs:
                ctx2 = new_ctx(b)
                page2 = ctx2.new_page()
                url = f"https://app.mokahr.com/social-recruitment/{slug}"
                try:
                    resp = page2.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page2.wait_for_timeout(8000)
                    html = page2.content()
                    txt = clean(html)
                    if not ('页面不存在' in txt or len(txt) < 60):
                        if any(k in txt for k in ['职位', '工程师', '发布于', '智谱']):
                            print(f"  *** FOUND: {slug} ***", flush=True)
                            print(f"    txt: {txt[:500]}", flush=True)
                            with open(f"{OUT_DIR}/r44_zhipu_{slug}_raw.txt", "w") as f:
                                f.write(txt)
                            # Try to extract jobs
                            jobs = extract_jobs_from_txt(txt)
                            if jobs:
                                all_jobs = jobs
                                break
                except:
                    pass
                ctx2.close()

        b.close()

    # Deduplicate
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j["title"], j["publishDate"])
        if key not in seen and j["title"]:
            seen.add(key)
            unique_jobs.append(j)
    unique_jobs.sort(key=lambda x: x.get("publishDate", "0000"), reverse=True)

    print(f"\n{'='*60}")
    print(f"ZHIPU: {len(unique_jobs)} unique jobs found")
    print(f"{'='*60}")
    for j in unique_jobs:
        date = j.get("publishDate", "N/A")
        flag = " ***NEW***" if date and date >= "2026-07-16" else ""
        print(f"  {date:<12}  {j['title']:<50}{flag}")

    output = {
        "company": "智谱 (Zhipu)",
        "scrapeDate": "2026-07-16",
        "totalJobs": len(unique_jobs),
        "jobs": unique_jobs,
    }
    with open(f"{OUT_DIR}/r44_zhipu.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved to {OUT_DIR}/r44_zhipu.json", flush=True)
    return unique_jobs


def highlight_matching(jobs, company):
    keywords = ['kernel', 'eBPF', 'system', '嵌入式', 'BSP', 'OS', '操作系统',
                'Agent', 'Infra', 'SRE', 'runtime', '运行时', '系统', '底层',
                '驱动', '内核', '平台', '架构', '后端', '基础设施', '中间件', 'C++']
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
            print(f"  [{kw}] {date}  {j['title']:<45}{flag}")
    else:
        print("  (none found)")
    return matches


if __name__ == "__main__":
    print("Round 44 v2: Mokahr portal check")
    print(f"Date: 2026-07-16")

    galbot_jobs = scrape_galbot()
    highlight_matching(galbot_jobs, "GALBOT")

    zhipu_jobs = scrape_zhipu()
    highlight_matching(zhipu_jobs, "ZHIPU")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Galbot: {len(galbot_jobs)} jobs total")
    new_g = [j for j in galbot_jobs if j.get("publishDate", "") >= "2026-07-16"]
    print(f"  New (>=2026-07-16): {len(new_g)}")
    for j in new_g:
        print(f"    {j['publishDate']}  {j['title']}")
    print(f"Zhipu: {len(zhipu_jobs)} jobs total")
    new_z = [j for j in zhipu_jobs if j.get("publishDate", "") >= "2026-07-16"]
    print(f"  New (>=2026-07-16): {len(new_z)}")
    for j in new_z:
        print(f"    {j['publishDate']}  {j['title']}")
    print("\nDone.")
