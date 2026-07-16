#!/usr/bin/env python3
"""Render recruitment pages via headless Chromium and extract job listings."""
import sys, json, re, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

def launch():
    p = sync_playwright().start()
    b = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
        proxy={"server": PROXY},
    )
    return p, b

def fetch(page, url, wait_sel=None, wait_ms=8000, scroll=True):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else None
    except Exception as e:
        return None, f"goto error: {e}", ""
    try:
        if wait_sel:
            page.wait_for_selector(wait_sel, timeout=wait_ms)
        else:
            page.wait_for_load_state("networkidle", timeout=wait_ms)
    except Exception:
        pass
    if scroll:
        for _ in range(6):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(700)
    html = page.content()
    return status, "ok", html

def extract_text_jobs(html):
    """Find job-like text: titles, common patterns."""
    # strip tags
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S|re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S|re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    txt = re.sub(r"&[a-z]+;", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt

def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["all"]
    sites = {
        "galaxy": {
            "url": "https://galaxy.zhiye.com.cn/social",
            "wait_sel": None,
        },
        "robotera": {
            "url": "https://www.robotera.com/join-us",
            "wait_sel": None,
        },
        "galbot": {
            "url": "https://app.mokahr.com/social-recruitment/yinhetongyong/165929",
            "wait_sel": None,
        },
        "zhipu": {
            "url": "https://www.zhipu.cn/joinus",
            "wait_sel": None,
        },
        "moonshot": {
            "url": "https://www.moonshot.cn/joinus",
            "wait_sel": None,
        },
        "01ai": {
            "url": "https://www.01.ai/join",
            "wait_sel": None,
        },
        "qiansheng": {
            "url": "https://www.qianshengai.com/join",
            "wait_sel": None,
        },
        "horizon": {
            "url": "https://www.horizon.cc/join",
            "wait_sel": None,
        },
    }
    p, b = launch()
    context = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 900},
        locale="zh-CN",
    )
    page = context.new_page()
    # enable console logging minimal
    results = {}
    keys = list(sites.keys()) if "all" in targets else targets
    for k in keys:
        cfg = sites.get(k)
        if not cfg:
            results[k] = {"error": "unknown site"}
            continue
        url = cfg["url"]
        print(f"\n===== {k}: {url} =====", flush=True)
        status, msg, html = fetch(page, url, wait_sel=cfg["wait_sel"])
        print(f"status={status} msg={msg} html_len={len(html)}", flush=True)
        txt = extract_text_jobs(html) if html else ""
        # save for inspection
        with open(f"/pulp/find-job/live_{k}.html", "w") as f:
            f.write(html or "")
        with open(f"/pulp/find-job/live_{k}.txt", "w") as f:
            f.write(txt[:20000])
        # print a preview
        preview = txt[:1500]
        print(preview, flush=True)
        results[k] = {"status": status, "msg": msg, "html_len": len(html or ""), "txt_preview": preview}
        time.sleep(1)
    context.close()
    b.close()
    p.stop()
    with open("/pulp/find-job/live_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nDONE", flush=True)

if __name__ == "__main__":
    main()
