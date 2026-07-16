#!/usr/bin/env python3
"""Capture ALL responses (any content-type) to find list endpoint; extract structured jobs + dates."""
import json, time, re
from playwright.sync_api import sync_playwright

URL = "https://01ai.jobs.feishu.cn/"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = ctx.new_page()
        all_caps = []
        def on_response(resp):
            try:
                u = resp.url
                if "01ai.jobs.feishu.cn" in u or "feishucdn" not in u and ("api" in u or "search" in u or "position" in u or "job" in u):
                    ct = resp.headers.get("content-type","")
                    try:
                        body = resp.text()
                    except Exception:
                        body = "<binary>"
                    all_caps.append({"url": u, "method": resp.request.method, "status": resp.status, "ct": ct, "len": len(body), "body": body})
            except Exception:
                pass
        page.on("response", on_response)
        print("[*] goto", flush=True)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("[!] goto:", e, flush=True)
        time.sleep(4)

        # Click Beijing
        try:
            page.locator("text=北京").first.click(timeout=8000)
            print("[*] clicked Beijing", flush=True)
        except Exception as e:
            print("[!] click:", e, flush=True)
        time.sleep(6)

        # Print all 01ai.jobs API calls
        print("\n=== ALL 01ai.jobs.feishu.cn API responses ===", flush=True)
        for c in all_caps:
            if "01ai.jobs.feishu.cn" in c["url"]:
                print(f"  [{c['method']}] {c['status']} ct={c['ct'][:30]} len={c['len']}  {c['url']}", flush=True)
                if c['len'] > 200 and c['len'] < 500000:
                    print(f"     preview: {c['body'][:250]}", flush=True)

        # Find the largest response that contains job/position data
        big = [c for c in all_caps if "01ai.jobs.feishu.cn" in c["url"]]
        big.sort(key=lambda c: -c["len"])
        if big:
            print(f"\n[*] Largest 01ai response: {big[0]['len']} bytes -> {big[0]['url']}", flush=True)
            print(f"    preview: {big[0]['body'][:500]}", flush=True)

        with open("/pulp/find-job/r44_01ai_all_xhr.json","w") as f:
            json.dump(all_caps, f, ensure_ascii=False)
        print("[*] saved all_xhr", flush=True)

        # Extract structured job data from DOM
        print("\n=== DOM job extraction ===", flush=True)
        jobs = page.evaluate("""() => {
            // Try to find job list items
            const results = [];
            // Common patterns: look for repeated card structures
            const cards = document.querySelectorAll('[class*="job"], [class*="position"], [class*="card-item"], [class*="list-item"]');
            const allDivs = document.querySelectorAll('div');
            // Heuristic: find the job title elements
            const titleEls = document.querySelectorAll('span, a, h3, h2, div');
            const seen = new Set();
            for (const el of titleEls) {
                const t = (el.innerText||'').trim();
                if (t.length > 4 && t.length < 80 && !seen.has(t) && el.children.length === 0) {
                    // skip nav
                }
            }
            // Better: dump outerHTML of jobModule-content region
            const content = document.querySelector('[class*="jobModule-content"], [class*="position-list"], [class*="list"]');
            return {
                html: document.body.innerHTML.length,
                contentHTML: content ? content.innerHTML.slice(0,3000) : null,
            };
        }""")
        print(f"  body html len: {jobs.get('html')}", flush=True)
        if jobs.get('contentHTML'):
            print(f"  contentHTML preview: {jobs['contentHTML'][:500]}", flush=True)

        # Save full rendered HTML for parsing
        html = page.content()
        with open("/pulp/find-job/r44_01ai_dom.html","w") as f:
            f.write(html)
        print(f"[*] saved DOM html ({len(html)} chars)", flush=True)

        browser.close()

if __name__ == "__main__":
    main()
