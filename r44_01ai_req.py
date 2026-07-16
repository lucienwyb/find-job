#!/usr/bin/env python3
"""Log ALL requests to find the list endpoint; capture its response."""
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
        req_log = []
        resp_caps = []
        def on_request(req):
            u = req.url
            if "01ai.jobs.feishu.cn" in u and not any(x in u for x in ['.js','.css','.png','.jpg','.svg','.ico','.woff']):
                req_log.append({"method": req.method, "url": u, "post_data": req.post_data})
        def on_response(resp):
            u = resp.url
            if "01ai.jobs.feishu.cn" in u and "api" in u:
                try:
                    body = resp.text()
                except Exception:
                    body = "<err>"
                resp_caps.append({"url": u, "method": resp.request.method, "status": resp.status, "len": len(body) if isinstance(body,str) else 0, "body": body})
        page.on("request", on_request)
        page.on("response", on_response)

        print("[*] goto", flush=True)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("[!] goto:", e, flush=True)
        time.sleep(3)

        print("\n=== requests on initial load ===", flush=True)
        for r in req_log:
            print(f"  [{r['method']}] {r['url']}", flush=True)
            if r.get('post_data'):
                print(f"     post: {r['post_data'][:300]}", flush=True)

        req_log.clear()
        # Click Beijing
        try:
            page.locator("text=北京").first.click(timeout=8000)
            print("\n[*] clicked Beijing", flush=True)
        except Exception as e:
            print("[!] click:", e, flush=True)
        time.sleep(8)

        print("\n=== requests after click ===", flush=True)
        for r in req_log:
            print(f"  [{r['method']}] {r['url']}", flush=True)
            if r.get('post_data'):
                print(f"     post: {r['post_data'][:500]}", flush=True)

        print("\n=== API responses captured ===", flush=True)
        for c in resp_caps:
            print(f"  [{c['method']}] {c['status']} len={c['len']} {c['url']}", flush=True)
            if c['len'] > 100:
                print(f"     preview: {c['body'][:300]}", flush=True)

        with open("/pulp/find-job/r44_01ai_reqlog.json","w") as f:
            json.dump({"requests": req_log, "responses": resp_caps}, f, ensure_ascii=False)
        print("[*] saved reqlog", flush=True)

        browser.close()

if __name__ == "__main__":
    main()
