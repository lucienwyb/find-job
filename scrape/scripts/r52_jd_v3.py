#!/usr/bin/env python3
"""Round 52 v3: Extract job IDs via JS, then navigate directly to each job's
hash URL to capture JD. More reliable than clicking cards.

Cambricon: app.mokahr.com/apply/cambricon/1113#/job/<jobId>
Zhipu: app.mokahr.com/social-recruitment/zphz/148983#/job/<jobId>
"""
import sys, json, re, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT = "/pulp/find-job/scrape/data"

def launch(p):
    return p.chromium.launch(headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled","--disable-gpu"],
        proxy={"server": PROXY})

def new_ctx(b):
    return b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1440,"height":1100}, locale="zh-CN", ignore_https_errors=True)

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>"," ",html,flags=re.S|re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>"," ",txt,flags=re.S|re.I)
    txt = re.sub(r"<[^>]+>"," ",txt)
    txt = re.sub(r"&nbsp;"," ",txt); txt = re.sub(r"&amp;","&",txt)
    return re.sub(r"\s+"," ",txt).strip()


def extract_job_links(page):
    """Try multiple JS strategies to extract job title -> jobId mapping."""
    strategies = [
        # Strategy 1: find anchor/clickable elements with href containing /job/
        """() => {
            const out = [];
            document.querySelectorAll('a[href*="job"], a[href*="#/job"]').forEach(a => {
                const t = (a.innerText||'').trim();
                const h = a.getAttribute('href')||'';
                if (t && t.length > 2) out.push({title: t, href: h});
            });
            // also any element with onclick or data-job
            document.querySelectorAll('[data-job-id], [data-id]').forEach(e => {
                const t = (e.innerText||'').trim();
                out.push({title: t, href: '', jobId: e.getAttribute('data-job-id')||e.getAttribute('data-id')});
            });
            return out;
        }""",
        # Strategy 2: look at React router history / window state
        """() => {
            const out = [];
            // mokahr stores jobs in window.__INITIAL_STATE__ or similar
            try {
                const keys = Object.keys(window).filter(k => k.includes('INITIAL') || k.includes('STORE') || k.includes('state'));
                return {windowKeys: keys.slice(0,20)};
            } catch(e) { return {err: String(e)} }
        }""",
        # Strategy 3: get all job card texts and their parent hrefs
        """() => {
            const out = [];
            const cards = document.querySelectorAll('[class*="item-"], [class*="job-"], [class*="position-"]');
            cards.forEach(c => {
                const t = (c.innerText||'').trim().split('\\n')[0];
                // look for nearby link
                const link = c.querySelector('a');
                const h = link ? (link.getAttribute('href')||'') : '';
                if (t && t.length > 2 && t.length < 60) out.push({title: t, href: h, cls: c.className.substring(0,40)});
            });
            return out;
        }""",
    ]
    for i, s in enumerate(strategies):
        try:
            res = page.evaluate(s)
            if res:
                return f"strategy_{i}", res
        except Exception as e:
            pass
    return "none", []


def get_job_ids_from_html(html):
    """Regex job IDs (UUIDs) from raw HTML - mokahr embeds job IDs in data attrs / JS."""
    # UUID pattern
    uuids = re.findall(r'(?:job["\']?\s*[:=]\s*["\']?|/job/)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', html, re.I)
    # also generic id patterns
    ids2 = re.findall(r'"id"\s*:\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"', html, re.I)
    all_ids = list(set(uuids + ids2))
    return all_ids


def capture_jd_at_url(page, url, title):
    """Navigate to a job detail URL and capture JD."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(8000)
        html = page.content()
        txt = clean(html)
        # Check it's a real JD page
        has_jd = any(k in txt for k in ['岗位职责','任职要求','职位描述','工作职责','任职资格','【工作职责】','【团队介绍】'])
        if not has_jd:
            return None
        return {"title": title, "url": url, "txt": txt, "txt_len": len(txt)}
    except Exception as e:
        return None


def extract_jd_fields(txt):
    duty=""; req=""; bonus=""; team=""
    for pat in [r'(岗位职责[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)',
                r'(工作职责[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)',
                r'(\【工作职责\】[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|\【)',
                r'(职位描述[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)']:
        m = re.search(pat, txt)
        if m: duty = m.group(1).strip(); break
    for pat in [r'(任职要求[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|岗位职责|工作职责|职位描述|$)',
                r'(任职资格[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|岗位职责|工作职责|职位描述|$)',
                r'(\【任职要求\】[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|\【|$)']:
        m = re.search(pat, txt)
        if m: req = m.group(1).strip(); break
    bm = re.search(r'(加分项[\s\S]{10,1500}?)(?:申请职位|公司信息|分享|收藏|最新职位|更多|京公网)', txt)
    if bm: bonus = bm.group(1).strip()
    tm = re.search(r'(\【团队介绍\】[\s\S]{10,1500}?)(?:\【工作职责\】|\【岗位职责\】|工作职责|岗位职责)', txt)
    if tm: team = tm.group(1).strip()
    return {"duty":duty,"requirement":req,"bonus":bonus,"team":team}


def scrape_cambricon():
    print("\n###### Cambricon v3 ######", flush=True)
    targets = {"高性能通信库研发工程师", "AI网络研发工程师", "芯片应用工程师-固件方向",
               "高性能计算库研发工程师", "高性能算法库工程师"}
    results = []
    with sync_playwright() as p:
        b = launch(p); ctx = new_ctx(b); page = ctx.new_page()
        page.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(18000)

        # Extract job IDs from HTML
        html = page.content()
        with open(f"{OUT}/cambricon_r52_v3_list.html","w") as f: f.write(html)
        job_ids = get_job_ids_from_html(html)
        print(f"  Found {len(job_ids)} job IDs in HTML", flush=True)

        # Also extract title->id mapping via JS
        strat, mapping = extract_job_links(page)
        print(f"  JS extraction ({strat}): {len(mapping) if isinstance(mapping,list) else mapping}", flush=True)
        if isinstance(mapping, list):
            for m in mapping[:20]:
                print(f"    {m}", flush=True)

        # Try paginating to collect ALL job ids across pages
        all_ids = set(job_ids)
        for pg in range(2, 6):
            try:
                btn = page.locator(f"text={pg}").first
                if btn.count() > 0:
                    btn.click(timeout=3000); page.wait_for_timeout(4000)
                    h2 = page.content()
                    ids2 = get_job_ids_from_html(h2)
                    new = [i for i in ids2 if i not in all_ids]
                    print(f"  page {pg}: +{len(new)} new ids", flush=True)
                    all_ids.update(new)
            except: pass
        # back to page 1
        try:
            pg1 = page.locator("text=1").first
            if pg1.count()>0: pg1.click(timeout=2000); page.wait_for_timeout(3000)
        except: pass

        print(f"\n  Total unique job IDs: {len(all_ids)}", flush=True)

        # Now visit each job ID URL, check if title matches our targets
        # URL format: https://app.mokahr.com/apply/cambricon/1113?hash=#/job/<jobId>
        found_targets = set()
        for jid in list(all_ids):
            url = f"https://app.mokahr.com/apply/cambricon/1113?hash=%23%2Fjob%2F{jid}"
            jd_data = capture_jd_at_url(page, url, "")
            if not jd_data: continue
            txt = jd_data["txt"]
            # Check if any target title is in this JD
            for t in targets:
                if t in txt or t.replace(" ","") in txt.replace(" ",""):
                    if t in found_targets: continue
                    fields = extract_jd_fields(txt)
                    fields["title"] = t; fields["url"] = url; fields["jobId"] = jid
                    print(f"\n  >> FOUND: {t} (jobId={jid})", flush=True)
                    print(f"     duty={len(fields['duty'])} req={len(fields['requirement'])} bonus={len(fields['bonus'])}", flush=True)
                    results.append(fields)
                    found_targets.add(t)
                    safe = re.sub(r'[^\w一-鿿]','_', t)[:30]
                    with open(f"{OUT}/cambricon_r52_jd_{safe}.txt","w") as f: f.write(txt)
                    break

        # Report missing
        for t in targets - found_targets:
            print(f"\n  >> NOT FOUND: {t}", flush=True)
            results.append({"title": t, "found": False})

        ctx.close(); b.close()
    with open(f"{OUT}/cambricon_r52_jd_v3.json","w") as f:
        json.dump({"company":"Cambricon","scrapeDate":"2026-07-16","targets":results}, f, ensure_ascii=False, indent=2)
    return results


def scrape_zhipu():
    print("\n###### Zhipu v3 ######", flush=True)
    targets = {"Agent Infra 开发工程师", "推理Infra工程师", "训练Infra工程师", "Agent Infra 运维开发工程师"}
    results = []
    with sync_playwright() as p:
        b = launch(p); ctx = new_ctx(b); page = ctx.new_page()
        page.goto("https://app.mokahr.com/social-recruitment/zphz/148983", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(20000)
        html = page.content()
        with open(f"{OUT}/zhipu_r52_v3_list.html","w") as f: f.write(html)
        job_ids = get_job_ids_from_html(html)
        print(f"  Found {len(job_ids)} job IDs in HTML", flush=True)

        # paginate to collect all ids
        all_ids = set(job_ids)
        for pg in range(2, 9):
            try:
                btn = page.locator(f"text={pg}").first
                if btn.count() > 0:
                    btn.click(timeout=3000); page.wait_for_timeout(4000)
                    h2 = page.content()
                    ids2 = get_job_ids_from_html(h2)
                    new = [i for i in ids2 if i not in all_ids]
                    if new: print(f"  page {pg}: +{len(new)} new ids", flush=True)
                    all_ids.update(new)
            except: pass

        print(f"\n  Total unique job IDs: {len(all_ids)}", flush=True)

        found_targets = set()
        for jid in list(all_ids):
            url = f"https://app.mokahr.com/social-recruitment/zphz/148983?hash=%23%2Fjob%2F{jid}"
            jd_data = capture_jd_at_url(page, url, "")
            if not jd_data: continue
            txt = jd_data["txt"]
            for t in targets:
                if t in txt or t.replace(" ","") in txt.replace(" ",""):
                    if t in found_targets: continue
                    fields = extract_jd_fields(txt)
                    fields["title"] = t; fields["url"] = url; fields["jobId"] = jid
                    print(f"\n  >> FOUND: {t} (jobId={jid[:12]}...)", flush=True)
                    print(f"     duty={len(fields['duty'])} req={len(fields['requirement'])} team={len(fields['team'])} bonus={len(fields['bonus'])}", flush=True)
                    results.append(fields)
                    found_targets.add(t)
                    safe = re.sub(r'[^\w一-鿿]','_', t)[:30]
                    with open(f"{OUT}/zhipu_r52_jd_{safe}.txt","w") as f: f.write(txt)
                    break

        for t in targets - found_targets:
            print(f"\n  >> NOT FOUND: {t}", flush=True)
            results.append({"title": t, "found": False})

        ctx.close(); b.close()
    with open(f"{OUT}/zhipu_r52_jd_v3.json","w") as f:
        json.dump({"company":"Zhipu","scrapeDate":"2026-07-16","targets":results}, f, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    scrape_cambricon()
    scrape_zhipu()
    print("\n=== DONE v3 ===", flush=True)
