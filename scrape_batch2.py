#!/usr/bin/env python3
"""Batch 2: remaining sites + galaxy retries + galbot job titles drill-down."""
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

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S|re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S|re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    txt = re.sub(r"&[a-z]+;", " ", txt)
    return re.sub(r"\s+", " ", txt)

def fetch(page, url, wait_ms=10000, scroll_n=10):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=35000)
        status = resp.status if resp else None
    except Exception as e:
        return None, f"goto error: {e}", ""
    try:
        page.wait_for_load_state("networkidle", timeout=wait_ms)
    except Exception:
        pass
    for _ in range(scroll_n):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(600)
    return status, "ok", page.content()

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 1000}, locale="zh-CN",
    )
    page = ctx.new_page()

    targets = [
        # galaxy alternatives
        ("galaxy_zhiye_http", "http://galaxy.zhiye.com.cn/social"),
        ("galaxy_zhiye_root", "https://galaxy.zhiye.com.cn"),
        ("galaxy_liepin", "https://liepin.com/company/9614836"),
        ("zhipu", "https://www.zhipu.cn/joinus"),
        ("moonshot", "https://www.moonshot.cn/joinus"),
        ("01ai", "https://www.01.ai/join"),
        ("qiansheng", "https://www.qianshengai.com/join"),
        ("horizon", "https://www.horizon.cc/join"),
    ]
    results = {}
    for name, url in targets:
        print(f"\n===== {name}: {url} =====", flush=True)
        status, msg, html = fetch(page, url)
        print(f"status={status} msg={msg} len={len(html)}", flush=True)
        txt = clean(html) if html else ""
        with open(f"/pulp/find-job/live2_{name}.html", "w") as f:
            f.write(html or "")
        with open(f"/pulp/find-job/live2_{name}.txt", "w") as f:
            f.write(txt[:25000])
        print(txt[:1200], flush=True)
        results[name] = {"status": status, "msg": msg, "len": len(html or ""), "preview": txt[:1200]}
        time.sleep(1)

    # Galbot: click into 软件类 to get job titles
    print("\n===== galbot_software drill-down =====", flush=True)
    try:
        page.goto("https://app.mokahr.com/social-recruitment/yinhetongyong/165929", wait_until="domcontentloaded", timeout=35000)
        page.wait_for_timeout(4000)
        # try clicking 软件类
        clicked = False
        for sel in ["text=软件类", "text=软件", "div:has-text('软件类')"]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click(timeout=5000)
                    clicked = True
                    print(f"clicked {sel}", flush=True)
                    break
            except Exception as e:
                print(f"click {sel} err: {e}", flush=True)
        page.wait_for_timeout(4000)
        for _ in range(8):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(500)
        html = page.content()
        txt = clean(html)
        with open("/pulp/find-job/live2_galbot_software.html", "w") as f:
            f.write(html)
        with open("/pulp/find-job/live2_galbot_software.txt", "w") as f:
            f.write(txt[:30000])
        # find job titles - look for patterns
        # mokahr job items usually have job-name class
        print("galbot txt preview:", txt[:2000], flush=True)
        results["galbot_software"] = {"len": len(html), "preview": txt[:2000]}
    except Exception as e:
        print(f"galbot drill err: {e}", flush=True)
        results["galbot_software"] = {"error": str(e)}

    ctx.close(); b.close(); p.stop()
    with open("/pulp/find-job/live2_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nDONE2", flush=True)

if __name__ == "__main__":
    main()
