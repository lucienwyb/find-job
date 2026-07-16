#!/usr/bin/env python3
"""Round 52 v4: Targeted capture of missing JDs.
- Zhipu: Agent Infra 开发工程师, Agent Infra 运维开发工程师 (need to find jobIds across all pages)
- Cambricon: 高性能计算库研发工程师, 高性能算法库工程师 (check #/jobs full list view)
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


def get_job_id_mapping(page):
    """Extract title -> jobId via JS from current page DOM."""
    mapping = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('a[href*="#/job/"]').forEach(a => {
            const t = (a.innerText||'').trim();
            const h = a.getAttribute('href')||'';
            const m = h.match(/#\\/job\\/([0-9a-f-]+)/);
            if (t && m) out.push({title: t, jobId: m[1]});
        });
        return out;
    }""")
    return mapping


def capture_jd(page, url, title):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(8000)
        html = page.content(); txt = clean(html)
        has_jd = any(k in txt for k in ['岗位职责','任职要求','职位描述','工作职责','任职资格','【工作职责】','【团队介绍】','职位要求'])
        if not has_jd: return None
        return {"title": title, "url": url, "txt": txt}
    except: return None


def extract_jd_fields(txt):
    duty=""; req=""; bonus=""; team=""
    for pat in [r'(岗位职责[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)',
                r'(工作职责[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)',
                r'(\【工作职责\】[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|\【)',
                r'(-工作内容[\s\S]{20,2500}?)(?:-职位要求|任职要求|任职资格|职位要求|加分项|申请职位)',
                r'(职位描述[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏|-职位要求)']:
        m = re.search(pat, txt)
        if m: duty = m.group(1).strip(); break
    for pat in [r'(任职要求[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|岗位职责|工作职责|职位描述|$)',
                r'(任职资格[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|岗位职责|工作职责|职位描述|$)',
                r'(-职位要求[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|方向|$)',
                r'(\【任职要求\】[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|\【|$)']:
        m = re.search(pat, txt)
        if m: req = m.group(1).strip(); break
    bm = re.search(r'(加分项[\s\S]{10,1500}?)(?:申请职位|公司信息|分享|收藏|最新职位|更多|京公网|职位信息)', txt)
    if bm: bonus = bm.group(1).strip()
    tm = re.search(r'(\【团队介绍\】[\s\S]{10,1500}?)(?:\【工作职责\】|\【岗位职责\】|工作职责|岗位职责|-工作内容)', txt)
    if tm: team = tm.group(1).strip()
    return {"duty":duty,"requirement":req,"bonus":bonus,"team":team}


def scrape_zhipu_agent_infra():
    print("\n###### Zhipu - find Agent Infra jobs ######", flush=True)
    targets = ["Agent Infra 开发工程师", "Agent Infra 运维开发工程师"]
    results = []
    with sync_playwright() as p:
        b = launch(p); ctx = new_ctx(b); page = ctx.new_page()
        page.goto("https://app.mokahr.com/social-recruitment/zphz/148983", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(20000)

        # Collect ALL job IDs across all pages by paginating
        all_jobs = []
        for pg in range(1, 10):
            mapping = get_job_id_mapping(page)
            for m in mapping:
                if m not in all_jobs:
                    all_jobs.append(m)
            print(f"  page {pg}: {len(mapping)} jobs (total unique: {len(all_jobs)})", flush=True)
            # find next page button - try multiple strategies
            # Strategy: look for pagination, click next number
            clicked = False
            # Try clicking the next page number
            try:
                # find pagination buttons
                pagenums = page.evaluate("""() => {
                    const out = [];
                    document.querySelectorAll('[class*="page"], [class*="pagination"], [class*="pager"] button, [class*="page"] a, li[class*="page"]').forEach(e => {
                        const t = (e.innerText||'').trim();
                        if (/^\\d+$/.test(t)) out.push({text: t, cls: e.className.substring(0,30)});
                    });
                    return out;
                }""")
                if pagenums:
                    next_pg = str(pg+1)
                    for pn in pagenums:
                        if pn["text"] == next_pg:
                            page.locator(f"text={next_pg}").first.click(timeout=3000)
                            page.wait_for_timeout(4000)
                            clicked = True
                            break
            except: pass
            if not clicked:
                # try "下一页" / ">" / "›"
                for sym in ["下一页", ">", "›", "»"]:
                    try:
                        loc = page.locator(f"text={sym}").first
                        if loc.count() > 0:
                            loc.click(timeout=2000); page.wait_for_timeout(4000); clicked=True; break
                    except: pass
            if not clicked:
                print(f"  No more pages after {pg}", flush=True)
                break

        print(f"\n  Total unique jobs collected: {len(all_jobs)}", flush=True)
        # save mapping
        with open(f"{OUT}/zhipu_r52_jobmap.json","w") as f:
            json.dump(all_jobs, f, ensure_ascii=False, indent=2)

        # Now find target jobs
        found = {}
        for j in all_jobs:
            t = j["title"]
            for tgt in targets:
                if tgt in t or tgt.replace(" ","") in t.replace(" ",""):
                    if tgt not in found:
                        found[tgt] = j
                        print(f"  MATCH: {tgt} -> {j['jobId'][:12]}... (full title: {t})", flush=True)

        # Capture JD for each found target
        for tgt, j in found.items():
            url = f"https://app.mokahr.com/social-recruitment/zphz/148983?hash=%23%2Fjob%2F{j['jobId']}"
            jd_data = capture_jd(page, url, tgt)
            if jd_data:
                fields = extract_jd_fields(jd_data["txt"])
                fields["title"] = tgt; fields["url"] = url; fields["jobId"] = j["jobId"]
                fields["full_title"] = j["title"]
                print(f"\n  >> {tgt}: duty={len(fields['duty'])} req={len(fields['requirement'])} team={len(fields['team'])}", flush=True)
                results.append(fields)
                safe = re.sub(r'[^\w一-鿿]','_', tgt)[:30]
                with open(f"{OUT}/zhipu_r52_jd_{safe}.txt","w") as f: f.write(jd_data["txt"])

        for t in targets:
            if t not in found:
                print(f"\n  >> NOT FOUND: {t}", flush=True)
                results.append({"title": t, "found": False})

        ctx.close(); b.close()
    with open(f"{OUT}/zhipu_r52_jd_v4.json","w") as f:
        json.dump({"company":"Zhipu","scrapeDate":"2026-07-16","targets":results}, f, ensure_ascii=False, indent=2)
    return results


def scrape_cambricon_full():
    print("\n###### Cambricon - check full list for 高性能计算库/算法库 ######", flush=True)
    targets = ["高性能计算库研发工程师", "高性能算法库工程师"]
    results = []
    with sync_playwright() as p:
        b = launch(p); ctx = new_ctx(b); page = ctx.new_page()
        # Navigate to full job list view
        page.goto("https://app.mokahr.com/apply/cambricon/1113#/jobs", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(18000)
        txt = clean(page.content())
        print(f"  #/jobs view: txt={len(txt)}", flush=True)
        # Check if targets are present
        for t in targets:
            present = t in txt or t.replace(" ","") in txt.replace(" ","")
            print(f"    [{ 'ONLINE' if present else 'NOT FOUND'}] {t}", flush=True)
            results.append({"title": t, "in_full_list": present})

        # Also try the original page and click 查看更多职位
        page.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(15000)
        # Get all job mappings from page 1 + paginate
        all_jobs = []
        for pg in range(1, 8):
            mapping = get_job_id_mapping(page)
            for m in mapping:
                if m not in all_jobs:
                    all_jobs.append(m)
            print(f"  cambricon page {pg}: {len(mapping)} jobs", flush=True)
            # next page
            try:
                nxt = page.locator(f"text={pg+1}").first
                if nxt.count() > 0:
                    nxt.click(timeout=3000); page.wait_for_timeout(4000)
                else: break
            except: break

        print(f"  Total cambricon jobs: {len(all_jobs)}", flush=True)
        with open(f"{OUT}/cambricon_r52_jobmap.json","w") as f:
            json.dump(all_jobs, f, ensure_ascii=False, indent=2)

        # Search for target titles
        for j in all_jobs:
            for t in targets:
                if t in j["title"] or t.replace(" ","") in j["title"].replace(" ",""):
                    print(f"  FOUND: {t} -> {j['jobId'][:12]}", flush=True)
                    url = f"https://app.mokahr.com/apply/cambricon/1113?hash=%23%2Fjob%2F{j['jobId']}"
                    jd_data = capture_jd(page, url, t)
                    if jd_data:
                        fields = extract_jd_fields(jd_data["txt"])
                        fields["title"]=t; fields["url"]=url; fields["jobId"]=j["jobId"]
                        print(f"     duty={len(fields['duty'])} req={len(fields['requirement'])}", flush=True)
                        results = [r for r in results if r.get("title")!=t]
                        results.append(fields)
                        safe = re.sub(r'[^\w一-鿿]','_', t)[:30]
                        with open(f"{OUT}/cambricon_r52_jd_{safe}.txt","w") as f: f.write(jd_data["txt"])

        ctx.close(); b.close()
    return results


if __name__ == "__main__":
    scrape_zhipu_agent_infra()
    scrape_cambricon_full()
    print("\n=== DONE v4 ===", flush=True)
