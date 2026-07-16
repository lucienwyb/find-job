#!/usr/bin/env python3
"""Capture ALL response bodies across all hosts; find which contains job titles."""
import json, time
from playwright.sync_api import sync_playwright

URL = "https://01ai.jobs.feishu.cn/"
KEYWORDS = ["塞尔维亚", "多模态内容审核", "招聘实习生"]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = ctx.new_page()
        caps = []
        def on_response(resp):
            try:
                ct = resp.headers.get("content-type","")
                u = resp.url
                # capture text-ish responses
                if any(x in ct.lower() for x in ["json","text","html","javascript"]):
                    try:
                        body = resp.text()
                    except Exception:
                        return
                    caps.append({"url": u, "method": resp.request.method, "status": resp.status, "ct": ct, "len": len(body), "body": body})
            except Exception:
                pass
        page.on("response", on_response)

        print("[*] goto + click Beijing + wait for jobs", flush=True)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("[!] goto:", e, flush=True)
        time.sleep(3)
        try:
            page.locator("text=北京").first.click(timeout=8000)
            print("[*] clicked", flush=True)
        except Exception as e:
            print("[!] click:", e, flush=True)
        time.sleep(10)

        # Search captures for keywords
        print(f"\n[*] total captures: {len(caps)}", flush=True)
        found = []
        for c in caps:
            for kw in KEYWORDS:
                if kw in c["body"]:
                    found.append((c, kw))
                    break
        print(f"\n=== captures containing job keywords: {len(found)} ===", flush=True)
        for c, kw in found:
            print(f"  [{c['method']}] {c['status']} {c['ct'][:30]} len={c['len']} kw={kw!r}", flush=True)
            print(f"  URL: {c['url']}", flush=True)
            # show context around keyword
            i = c["body"].find(kw)
            print(f"  ctx: ...{c['body'][max(0,i-150):i+200]}...", flush=True)
            print()

        # Save all captures
        with open("/pulp/find-job/r44_01ai_allhosts.json","w") as f:
            json.dump(caps, f, ensure_ascii=False)
        print(f"[*] saved {len(caps)} captures to r44_01ai_allhosts.json", flush=True)

        # Also confirm inner_text has jobs
        txt = page.inner_text("body")
        has_jobs = "塞尔维亚" in txt or "多模态" in txt
        print(f"[*] inner_text has job keywords: {has_jobs} (len={len(txt)})", flush=True)
        if has_jobs:
            with open("/pulp/find-job/r44_01ai_jobs_text.txt","w") as f:
                f.write(txt)
        browser.close()

if __name__ == "__main__":
    main()
