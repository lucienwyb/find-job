import json, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

# (name, base_url, full_list_hash)
SITES = [
    ("moonshot",  "https://app.mokahr.com/apply/moonshot/148506/", "#/jobs/"),
    ("yinhe",     "https://app.mokahr.com/social-recruitment/yinhetongyong/165929/", "#/jobs"),
    ("zhipu",     "https://app.mokahr.com/social-recruitment/zphz/148983/", "#/jobs"),
    ("cambricon", "https://app.mokahr.com/apply/cambricon/1113/", "#/jobs/"),
]

def extract_jobs(page):
    # job-item cards; title, location, dept, jobId from href
    return page.evaluate("""() => {
        const out = [];
        const items = document.querySelectorAll('[class*=job-item]');
        items.forEach(it => {
            const a = it.querySelector('a[href]');
            const href = a ? a.getAttribute('href') : '';
            const titleEl = it.querySelector('[class*=title]');
            let urgent = false, title = '';
            if (titleEl) {
                titleEl.querySelectorAll('span').forEach(s => {
                    const t = s.textContent.trim();
                    if (t === '急') urgent = true;
                    else if (t) title = title ? title + ' ' + t : t;
                });
                if (!title) title = titleEl.textContent.trim();
            }
            const locEl = it.querySelector('[class*=status]');
            const loc = locEl ? locEl.textContent.trim().replace(/\\s+/g,' ') : '';
            out.push({title, location: loc, jobId: href, urgent});
        });
        return out;
    }""")

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": PROXY}, args=["--no-sandbox","--disable-dev-shm-usage"])
        for name, base, hashp in SITES:
            ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", viewport={"width":1366,"height":900})
            page = ctx.new_page()
            print(f"\n===== {name} =====", flush=True)
            try:
                page.goto(base, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"  base goto warn: {e}", flush=True)
            time.sleep(2)
            # navigate to full list
            full = base + hashp
            try:
                page.goto(full, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"  list goto warn: {e}", flush=True)
            time.sleep(4)
            # scroll to load all
            prev = 0
            for i in range(15):
                page.mouse.wheel(0, 3000)
                time.sleep(0.7)
                jobs = extract_jobs(page)
                cur = len(jobs)
                if cur == prev and i > 2:
                    break
                prev = cur
            jobs = extract_jobs(page)
            print(f"  total jobs extracted: {len(jobs)}", flush=True)
            with open(f"/pulp/find-job/{name}_jobs.json","w") as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            for j in jobs[:5]:
                t = ("[急] " if j["urgent"] else "") + j["title"]
                print(f"    {t} | {j['location']} | {j['jobId'][:50]}", flush=True)
            if len(jobs)>5:
                print(f"    ... and {len(jobs)-5} more", flush=True)
            # save dom for debugging cambricon
            with open(f"/pulp/find-job/{name}_full_dom.html","w") as f:
                f.write(page.content())
            ctx.close()
        browser.close()

if __name__ == "__main__":
    scrape()
