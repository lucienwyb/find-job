import json, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

# Cambricon uses a different card structure. Extract title/dept/location from each job link.
EXTRACT_JS = """() => {
    const out = [];
    document.querySelectorAll('a[href*="/job/"]').forEach(a => {
        const href = a.getAttribute('href') || '';
        const jobId = href.split('/job/').pop();
        // cambricon: each card has spans for 急, title, dept, category, location
        const allText = [];
        a.querySelectorAll('span,div,p').forEach(el => {
            const t = el.textContent.trim();
            if (t && !allText.includes(t)) allText.push(t);
        });
        // Also direct text nodes
        const urgent = allText.includes('急');
        // filter out marker texts
        const noise = ['急','技术类-社招','职能类-社招','社招','急招'];
        const locs = ['北京市','上海市','广东','深圳市','海淀区','浦东新区','南京市','四川','成都市','西安市','杭州市','武汉市','美国'];
        let title='', dept='';
        const clean = allText.filter(t => !noise.includes(t) && !locs.some(l=>t.includes(l)));
        title = clean[0] || '';
        dept = clean[1] || '';
        out.push({title, dept, jobId, urgent});
    });
    const seen = new Set(); const res = [];
    for (const j of out) { if (!seen.has(j.jobId)) { seen.add(j.jobId); res.push(j); } }
    return res;
}"""

def scrape():
    allj = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, proxy={"server": PROXY}, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", viewport={"width":1366,"height":900})
        page = ctx.new_page()
        url = "https://app.mokahr.com/apply/cambricon/1113/#/jobs/"
        try:
            page.goto(url, wait_until="networkidle", timeout=50000)
        except Exception as e:
            print(f"  goto warn: {e}", flush=True)
        time.sleep(4)
        for pg in range(1, 8):
            jobs = page.evaluate(EXTRACT_JS)
            for j in jobs:
                allj[j["jobId"]] = j
            print(f"  cambricon pg{pg}: {len(jobs)} jobs (cum {len(allj)})", flush=True)
            next_pg = pg + 1
            clicked = page.evaluate("""(np) => {
                const btn = document.querySelector('button[data-page="'+np+'"]');
                if (btn) { btn.click(); return 'ok'; }
                const fwd = document.querySelector('button[class*=Pagination-forward]');
                if (fwd && !fwd.disabled) { fwd.click(); return 'fwd'; }
                return 'none';
            }""", str(next_pg))
            if clicked in ('ok','fwd'):
                time.sleep(3)
            else:
                print(f"    no page {next_pg}, done", flush=True)
                break
        b.close()
    return list(allj.values())

if __name__ == "__main__":
    jobs = scrape()
    with open("/pulp/find-job/cambricon_full.json","w") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"\nFINAL cambricon: {len(jobs)} jobs")
    for j in jobs:
        flag = "[急]" if j["urgent"] else "     "
        print(f"  {flag} {j['title']} | {j['dept']} | {j['jobId'][:40]}")
