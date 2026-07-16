#!/usr/bin/env python3
"""Capture 01.AI Feishu Hire portal: render page, intercept API responses, dump JSON."""
import json, re, sys, time
from playwright.sync_api import sync_playwright

URL = "https://01ai.jobs.feishu.cn/"
OUT = "/pulp/find-job/r44_01ai.json"
CAPTURES = []  # list of (url, content-type, body)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = ctx.new_page()

        api_responses = []
        def on_response(response):
            try:
                url = response.url
                ct = response.headers.get("content-type","")
                if "json" in ct.lower() or "javascript" not in ct.lower() and ("text" in ct.lower() or "json" in ct.lower()):
                    if any(k in url.lower() for k in ["position","job","recruit","hire","search","list","portal","website"]):
                        try:
                            body = response.text()
                            api_responses.append((url, ct, body[:200], len(body)))
                            CAPTURES.append((url, ct, body))
                        except Exception as e:
                            api_responses.append((url, ct, f"<err {e}>", 0))
            except Exception:
                pass

        page.on("response", on_response)

        print("[*] Navigating to", URL, flush=True)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("[!] goto warning:", e, flush=True)

        # Give SPA time to fetch positions
        time.sleep(6)
        # Try scrolling / clicking to load more
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
        except Exception:
            pass

        # Print captured API responses
        print("\n=== Captured candidate API responses ===", flush=True)
        for u, ct, prev, n in api_responses:
            print(f"  [{n} bytes] {ct}  {u}", flush=True)
            print(f"     preview: {prev}", flush=True)

        # Dump all captures
        all_caps = []
        for u, ct, body in CAPTURES:
            all_caps.append({"url": u, "content_type": ct, "body": body})
        with open("/pulp/find-job/r44_01ai_captures.json","w") as f:
            json.dump(all_caps, f, ensure_ascii=False)
        print(f"\n[*] Saved {len(all_caps)} captures to r44_01ai_captures.json", flush=True)

        # Extract DOM job listings as fallback
        print("\n=== DOM extraction ===", flush=True)
        try:
            dom_jobs = page.evaluate("""() => {
                const items = document.querySelectorAll('[class*="position"], [class*="job"], [class*="card"], [data-id], a[href*="position"]');
                return Array.from(items).slice(0,200).map(el => ({
                    tag: el.tagName,
                    cls: el.className && el.className.toString ? el.className.toString().slice(0,120) : '',
                    text: (el.innerText||'').slice(0,300),
                    href: el.href || ''
                }));
            }""")
            print(f"[*] DOM candidate elements: {len(dom_jobs)}", flush=True)
            for j in dom_jobs[:10]:
                print(f"  {j['tag']}.{j['cls'][:40]} :: {j['text'][:80]}", flush=True)
        except Exception as e:
            print("[!] DOM extract error:", e, flush=True)
            dom_jobs = []

        # Also save full page text
        try:
            full_text = page.inner_text("body")
        except Exception:
            full_text = page.content()
        with open("/pulp/find-job/r44_01ai_page.txt","w") as f:
            f.write(full_text[:200000])
        print(f"[*] Saved page text ({len(full_text)} chars)", flush=True)

        browser.close()

    # Try to parse JSON bodies from captures
    parsed = []
    for cap in all_caps:
        body = cap["body"]
        if not body:
            continue
        try:
            data = json.loads(body)
        except Exception:
            # try to find JSON array/object embedded
            m = re.search(r'(\{.*\}|\[.*\])', body, re.S)
            if m:
                try:
                    data = json.loads(m.group(1))
                except Exception:
                    continue
            else:
                continue
        parsed.append({"url": cap["url"], "data": data})

    with open(OUT, "w") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    print(f"\n[*] Saved parsed API JSON ({len(parsed)} responses) to {OUT}", flush=True)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
