import json, time, re
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

SITES = [
    ("moonshot",  "https://app.mokahr.com/apply/moonshot/148506/"),
    ("yinhe",     "https://app.mokahr.com/social-recruitment/yinhetongyong/165929/"),
    ("zhipu",     "https://app.mokahr.com/social-recruitment/zphz/148983/"),
    ("cambricon", "https://app.mokahr.com/apply/cambricon/1113/"),
]

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": PROXY}, args=["--no-sandbox","--disable-dev-shm-usage"])
        for name, url in SITES:
            ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", viewport={"width":1366,"height":900})
            page = ctx.new_page()
            api_responses = []
            def on_response(resp):
                try:
                    ct = resp.headers.get("content-type","")
                    if "json" in ct and ("job" in resp.url.lower() or "position" in resp.url.lower() or "list" in resp.url.lower() or "search" in resp.url.lower()):
                        try:
                            body = resp.json()
                            api_responses.append({"url": resp.url, "body": body})
                        except Exception:
                            pass
                except Exception:
                    pass
            page.on("response", on_response)
            print(f"\n===== {name}: {url} =====", flush=True)
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"  goto warn: {e}", flush=True)
            # extra wait for SPA render
            time.sleep(4)
            # try scrolling to load more
            for _ in range(6):
                page.mouse.wheel(0, 2500)
                time.sleep(0.8)
            time.sleep(2)
            # dump DOM text
            try:
                html = page.content()
            except Exception as e:
                html = ""
                print(f"  content err: {e}", flush=True)
            with open(f"/pulp/find-job/{name}_dom.html","w") as f:
                f.write(html)
            print(f"  dom size: {len(html)}", flush=True)
            # captured APIs
            print(f"  captured api responses: {len(api_responses)}", flush=True)
            with open(f"/pulp/find-job/{name}_api.json","w") as f:
                json.dump(api_responses, f, ensure_ascii=False, indent=2)
            for r in api_responses[:3]:
                print(f"    API: {r['url'][:120]}", flush=True)
            ctx.close()
        browser.close()

if __name__ == "__main__":
    scrape()
