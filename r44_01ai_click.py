#!/usr/bin/env python3
"""Click into Beijing on 01.AI portal, capture all XHR responses, find the list endpoint."""
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
        xhr_caps = []
        def on_response(resp):
            try:
                ct = resp.headers.get("content-type","")
                if "json" in ct.lower():
                    body = resp.text()
                    xhr_caps.append({"url": resp.url, "method": resp.request.method, "status": resp.status, "len": len(body), "body": body})
            except Exception:
                pass
        page.on("response", on_response)
        print("[*] goto", flush=True)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("[!] goto:", e, flush=True)
        time.sleep(4)

        # Try to click the Beijing card to load position list
        print("[*] looking for Beijing clickable", flush=True)
        clicked = False
        for sel in ['text=北京', 'div.ud__card:has-text("北京")', '[class*="card"]:has-text("北京")', 'span:has-text("北京")']:
            try:
                els = page.query_selector_all(sel)
                print(f"  selector {sel!r} -> {len(els)} matches", flush=True)
                if els:
                    els[0].click(timeout=5000)
                    clicked = True
                    print(f"  clicked via {sel}", flush=True)
                    break
            except Exception as e:
                print(f"  selector {sel!r} err: {e}", flush=True)

        time.sleep(6)
        # try scrolling the job list
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
        except Exception:
            pass

        print(f"\n[*] total json captures: {len(xhr_caps)}", flush=True)
        # print all unique 01ai.jobs urls
        seen = set()
        for c in xhr_caps:
            if "01ai.jobs.feishu.cn" in c["url"] and c["url"] not in seen:
                seen.add(c["url"])
                print(f"  [{c['method']}] {c['status']} len={c['len']}  {c['url']}", flush=True)
                print(f"     preview: {c['body'][:200]}", flush=True)

        # Save the largest json responses (likely the list)
        big = sorted(xhr_caps, key=lambda c: -c["len"])[:5]
        print("\n[*] top 5 largest JSON responses:", flush=True)
        for c in big:
            print(f"  len={c['len']} [{c['method']}] {c['url']}", flush=True)
            print(f"     preview: {c['body'][:300]}", flush=True)

        with open("/pulp/find-job/r44_01ai_xhr.json","w") as f:
            json.dump(xhr_caps, f, ensure_ascii=False)
        print("[*] saved xhr captures", flush=True)

        # Save rendered DOM text after click
        try:
            txt = page.inner_text("body")
            open("/pulp/find-job/r44_01ai_page_after.txt","w").write(txt[:50000])
            print(f"[*] page text after click: {len(txt)} chars", flush=True)
        except Exception as e:
            print("[!] text:", e, flush=True)

        browser.close()

if __name__ == "__main__":
    main()
