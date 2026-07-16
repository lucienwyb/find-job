import json, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

SITES = [
    ("moonshot",  "https://app.mokahr.com/apply/moonshot/148506/", "#/jobs/"),
    ("yinhe",     "https://app.mokahr.com/social-recruitment/yinhetongyong/165929/", "#/jobs"),
    ("zhipu",     "https://app.mokahr.com/social-recruitment/zphz/148983/", "#/jobs"),
    ("cambricon", "https://app.mokahr.com/apply/cambricon/1113/", "#/jobs/"),
]

EXTRACT_JS = """() => {
    const out = [];
    // job card links: a[href*='/job/']
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.getAttribute('href') || '';
        if (!href.includes('/job/')) return;
        const card = a.closest('a') || a;
        const titleEl = card.querySelector('span[class*=title]');
        if (!titleEl) return;
        let urgent = !!card.querySelector('span.prior-');
        const title = titleEl.textContent.trim();
        const dateEl = card.querySelector('span[class*=published-at]');
        const date = dateEl ? dateEl.textContent.replace(/发布于\\s*/,'').trim() : '';
        // meta: collect text spans after date
        const jobId = href.split('/job/').pop();
        out.push({title, date, jobId, urgent});
    });
    // dedupe by jobId
    const seen = new Set(); const res = [];
    for (const j of out) { if (!seen.has(j.jobId)) { seen.add(j.jobId); res.push(j); } }
    return res;
}"""

def count_jobs(page):
    try:
        return len(page.evaluate("() => (document.querySelectorAll('a[href*=\"/job/\"]')).length"))
    except Exception:
        return 0

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": PROXY}, args=["--no-sandbox","--disable-dev-shm-usage"])
        for name, base, hashp in SITES:
            ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", viewport={"width":1366,"height":900})
            page = ctx.new_page()
            print(f"\n===== {name} =====", flush=True)
            url = base + hashp
            try:
                page.goto(url, wait_until="networkidle", timeout=50000)
            except Exception as e:
                print(f"  goto warn: {e}", flush=True)
            time.sleep(4)
            # scroll the window AND the main scrollable container to load all jobs
            prev = -1
            stable = 0
            for i in range(40):
                page.mouse.wheel(0, 2000)
                time.sleep(0.5)
                # also scroll any inner scrollable
                page.evaluate("""() => {
                    document.querySelectorAll('*').forEach(el => {
                        if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                            el.scrollTop = el.scrollHeight;
                        }
                    });
                }""")
                time.sleep(0.4)
                cur = count_jobs(page)
                if cur == prev:
                    stable += 1
                    if stable >= 4:
                        break
                else:
                    stable = 0
                    prev = cur
                if i % 5 == 0:
                    print(f"  ...{cur} jobs loaded (iter {i})", flush=True)
            jobs = page.evaluate(EXTRACT_JS)
            print(f"  TOTAL: {len(jobs)} jobs", flush=True)
            with open(f"/pulp/find-job/{name}_all.json","w") as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            ctx.close()
        browser.close()

if __name__ == "__main__":
    scrape()
