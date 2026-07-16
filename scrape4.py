import json, time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

PROXY = "http://100.66.66.64:8765"

EXTRACT_JS = """() => {
    const out = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.getAttribute('href') || '';
        if (!href.includes('/job/')) return;
        const card = a;
        const titleEl = card.querySelector('span[class*=title]');
        if (!titleEl) return;
        let urgent = !!card.querySelector('span.prior-');
        const title = titleEl.textContent.trim();
        const dateEl = card.querySelector('span[class*=published-at]');
        const date = dateEl ? dateEl.textContent.replace(/发布于\\s*/,'').trim() : '';
        const jobId = href.split('/job/').pop();
        out.push({title, date, jobId, urgent});
    });
    const seen = new Set(); const res = [];
    for (const j of out) { if (!seen.has(j.jobId)) { seen.add(j.jobId); res.push(j); } }
    return res;
}"""

def click_next(page):
    # click the pagination next-page arrow
    return page.evaluate("""() => {
        // find pagination next button
        const pagers = document.querySelectorAll('[class*=Pagination], [class*=pagination], li[class*=page], button[class*=next]');
        for (const p of pagers) {
            if (p.getAttribute('aria-disabled') === 'true' || p.classList.contains('disabled')) continue;
        }
        // try the next-arrow: last li in pagination
        const items = document.querySelectorAll('li[class*=Pagination-item], li[class*=page-item], [class*=Pagination] li');
        if (items.length > 0) {
            const next = items[items.length-1];
            const cls = next.getAttribute('class')||'';
            if (cls.includes('disabled') || cls.includes('next')===false && next.querySelector('svg[class*=down]')===null) {}
            next.click();
            return 'clicked-last-li';
        }
        return 'no-pager';
    }""")

def scrape_pages(name, url, max_pages=4):
    all_jobs = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": PROXY}, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", viewport={"width":1366,"height":900})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=50000)
        except Exception as e:
            print(f"  goto warn: {e}", flush=True)
        time.sleep(4)
        for pg in range(max_pages):
            jobs = page.evaluate(EXTRACT_JS)
            for j in jobs:
                if j["jobId"] not in all_jobs:
                    all_jobs[j["jobId"]] = j
            print(f"  {name} page {pg+1}: +{len(jobs)} (total {len(all_jobs)})", flush=True)
            # try clicking next
            before = len(all_jobs)
            res = click_next(page)
            time.sleep(2.5)
            # check if new jobs appeared
            jobs2 = page.evaluate(EXTRACT_JS)
            newcount = sum(1 for j in jobs2 if j["jobId"] not in all_jobs)
            if newcount == 0:
                print(f"    no new jobs after click ({res}), stopping", flush=True)
                break
            for j in jobs2:
                if j["jobId"] not in all_jobs:
                    all_jobs[j["jobId"]] = j
        browser.close()
    return list(all_jobs.values())

if __name__ == "__main__":
    import sys
    # Paginate moonshot and zhipu to confirm no newer jobs
    for name, url in [
        ("moonshot", "https://app.mokahr.com/apply/moonshot/148506/#/jobs/"),
        ("zhipu", "https://app.mokahr.com/social-recruitment/zphz/148983/#/jobs"),
    ]:
        print(f"\n===== {name} (paginated) =====", flush=True)
        jobs = scrape_pages(name, url, max_pages=6)
        with open(f"/pulp/find-job/{name}_paginated.json","w") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"  FINAL: {len(jobs)} total jobs", flush=True)
