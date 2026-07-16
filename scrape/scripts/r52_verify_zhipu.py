#!/usr/bin/env python3
"""Round 52 v5: Verify Agent Infra 开发工程师 still online + find Agent Infra 运维 job ID."""
import re, json
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

with sync_playwright() as p:
    b = launch(p); ctx = new_ctx(b); page = ctx.new_page()

    # 1. Verify Agent Infra 开发工程师 is still online
    jid = "392db0f2-6542-4a5a-ad7d-451a4486576e"
    url = f"https://app.mokahr.com/social-recruitment/zphz/148983?hash=%23%2Fjob%2F{jid}"
    print(f">> Verifying Agent Infra 开发工程师 (jobId={jid[:12]})...", flush=True)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)
    txt = clean(page.content())
    online = "Agent Infra" in txt and ("职位描述" in txt or "工作职责" in txt or "职位要求" in txt)
    print(f"   Online: {online} | txt_len={len(txt)}", flush=True)
    if online:
        with open(f"{OUT}/zhipu_r52_jd_Agent_Infra_开发工程师.txt","w") as f: f.write(txt)
        print(f"   Saved JD ({len(txt)} chars)", flush=True)
        # Print key excerpt
        for kw in ['职位要求','加分项','工作职责','Golang','Kubernetes','可观测性','Linux','学历','本科','硕士']:
            idx = txt.find(kw)
            if idx >= 0:
                print(f"   [{kw}] ...{txt[idx:idx+120]}...", flush=True)

    # 2. Find Agent Infra 运维开发工程师 - paginate through all pages
    print(f"\n>> Searching for Agent Infra 运维开发工程师 across all pages...", flush=True)
    page.goto("https://app.mokahr.com/social-recruitment/zphz/148983", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(18000)

    found_yunwei = None
    for pg in range(1, 10):
        # Get job mapping
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
        print(f"   page {pg}: {len(mapping)} jobs", flush=True)
        for m in mapping:
            if "Agent Infra" in m["title"] and "运维" in m["title"]:
                found_yunwei = m
                print(f"   FOUND: {m['title']} -> {m['jobId'][:12]}", flush=True)
            if "Agent Infra" in m["title"] and "开发" in m["title"]:
                print(f"   CONFIRM page {pg}: {m['title']} -> {m['jobId'][:12]}", flush=True)
        # next page
        clicked = False
        try:
            nxt = page.locator(f"text={pg+1}").first
            if nxt.count() > 0:
                nxt.click(timeout=3000); page.wait_for_timeout(4000); clicked = True
        except: pass
        if not clicked: break

    if found_yunwei:
        url2 = f"https://app.mokahr.com/social-recruitment/zphz/148983?hash=%23%2Fjob%2F{found_yunwei['jobId']}"
        page.goto(url2, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(10000)
        txt2 = clean(page.content())
        online2 = "Agent Infra" in txt2 and ("职位" in txt2 or "工作" in txt2)
        print(f"\n   Agent Infra 运维 Online: {online2} | txt={len(txt2)}", flush=True)
        if online2:
            with open(f"{OUT}/zhipu_r52_jd_Agent_Infra_运维开发工程师.txt","w") as f: f.write(txt2)
            for kw in ['职位要求','加分项','工作职责','SRE','可观测性','Linux','学历','本科','硕士','监控']:
                idx = txt2.find(kw)
                if idx >= 0:
                    print(f"   [{kw}] ...{txt2[idx:idx+120]}...", flush=True)
    else:
        print("\n   Agent Infra 运维开发工程师 NOT FOUND in pagination", flush=True)

    ctx.close(); b.close()
print("\n=== DONE v5 ===", flush=True)
