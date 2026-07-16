#!/usr/bin/env python3
"""Batch 4: click-based SPA nav for zhipu/moonshot/robotera + horizon mokahr + qiansheng."""
import sys, json, re, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

def launch():
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage","--disable-blink-features=AutomationControlled"], proxy={"server": PROXY})
    return p, b

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S|re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S|re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;"," ",txt); txt=re.sub(r"&amp;","&",txt); txt=re.sub(r"&[a-z]+;"," ",txt)
    return re.sub(r"\s+"," ",txt)

def save(name, html):
    txt = clean(html) if html else ""
    with open(f"/pulp/find-job/live4_{name}.html","w") as f: f.write(html or "")
    with open(f"/pulp/find-job/live4_{name}.txt","w") as f: f.write(txt[:30000])
    return txt

def click_nav(page, labels):
    """Try clicking nav items by text."""
    for label in labels:
        for sel in [f"text={label}", f"a:has-text('{label}')", f"li:has-text('{label}')", f"span:has-text('{label}')", f"div:has-text('{label}')"]:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    loc.click(timeout=4000)
                    return label
            except Exception:
                pass
    return None

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN")
    page = ctx.new_page()
    results = {}

    # --- Zhipu: zhipuai.cn, click 加入我们 ---
    print("\n===== ZHIPU (zhipuai.cn) =====",flush=True)
    try:
        page.goto("https://www.zhipuai.cn", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        clicked = click_nav(page, ["加入我们","招聘","JOIN US","Careers","人才招聘"])
        print(f"clicked: {clicked}",flush=True)
        page.wait_for_timeout(5000)
        for _ in range(6):
            page.mouse.wheel(0,1500); page.wait_for_timeout(500)
        cur = page.url
        html = page.content()
        txt = save("zhipu", html)
        print(f"url={cur} len={len(html)}",flush=True)
        print(txt[:1000],flush=True)
        results["zhipu"]={"url":cur,"len":len(html),"preview":txt[:1000]}
    except Exception as e:
        print(f"zhipu err: {e}",flush=True); results["zhipu"]={"error":str(e)}

    # --- Moonshot: moonshot.cn, click 加入我们 ---
    print("\n===== MOONSHOT =====",flush=True)
    try:
        page.goto("https://www.moonshot.cn/about", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        # capture all link hrefs before/after
        clicked = click_nav(page, ["加入我们","Join Us","Careers","招聘"])
        print(f"clicked: {clicked}",flush=True)
        page.wait_for_timeout(5000)
        for _ in range(6):
            page.mouse.wheel(0,1500); page.wait_for_timeout(500)
        cur = page.url
        html = page.content()
        txt = save("moonshot", html)
        print(f"url={cur} len={len(html)}",flush=True)
        print(txt[:1200],flush=True)
        # also extract any hrefs that look like careers
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
        career_hrefs = [h for h in hrefs if any(k in h.lower() for k in ['join','career','job','recruit','hire','moka'])]
        print(f"career hrefs: {career_hrefs[:10]}",flush=True)
        results["moonshot"]={"url":cur,"len":len(html),"preview":txt[:1200],"hrefs":career_hrefs[:10]}
    except Exception as e:
        print(f"moonshot err: {e}",flush=True); results["moonshot"]={"error":str(e)}

    # --- Robotera: click 加入我们 ---
    print("\n===== ROBOTERA =====",flush=True)
    try:
        page.goto("https://www.robotera.com", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        clicked = click_nav(page, ["加入我们","招聘","Join Us","Careers","人才招聘"])
        print(f"clicked: {clicked}",flush=True)
        page.wait_for_timeout(5000)
        for _ in range(6):
            page.mouse.wheel(0,1500); page.wait_for_timeout(500)
        cur = page.url
        html = page.content()
        txt = save("robotera", html)
        print(f"url={cur} len={len(html)}",flush=True)
        print(txt[:1200],flush=True)
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
        career_hrefs = [h for h in hrefs if any(k in h.lower() for k in ['join','career','job','recruit','hire','moka','zaopin','zhaopin'])]
        print(f"career hrefs: {career_hrefs[:10]}",flush=True)
        results["robotera"]={"url":cur,"len":len(html),"preview":txt[:1200],"hrefs":career_hrefs[:10]}
    except Exception as e:
        print(f"robotera err: {e}",flush=True); results["robotera"]={"error":str(e)}

    # --- Horizon: try mokahr with hyphen ---
    print("\n===== HORIZON =====",flush=True)
    h_urls = [
        "https://app.mokahr.com/social-recruitment/horizon-robotics/3143",
        "https://app.mokahr.com/social-recruitment/horizon-robotics",
        "https://horizon.cc/zh-CN/join-us",
        "https://www.horizon.cc/join",
        "https://app.mokahr.com/social-recruitment/horizonrobotics/3143",
    ]
    for i,u in enumerate(h_urls):
        name=f"horizon_{i}"
        try:
            resp=page.goto(u, wait_until="domcontentloaded", timeout=25000)
            s=resp.status if resp else None
            page.wait_for_timeout(4000)
            for _ in range(5):
                page.mouse.wheel(0,1500); page.wait_for_timeout(400)
            html=page.content()
            txt=save(name,html)
            print(f"{name}: {u} status={s} len={len(html)}",flush=True)
            print(txt[:500],flush=True)
            results[name]={"url":u,"status":s,"len":len(html),"preview":txt[:500]}
            if s==200 and len(html)>5000 and "404" not in txt[:100] and "不存在" not in txt[:200]:
                print("HORIZON FOUND",flush=True)
                break
        except Exception as e:
            print(f"{name} err: {e}",flush=True); results[name]={"error":str(e)}
        time.sleep(1)

    # --- Qiansheng: alt domains ---
    print("\n===== QIANSHENG =====",flush=True)
    q_urls = [
        "https://www.qiansheng-exploration.com",
        "https://www.qiansheng-exploration.com/join",
        "https://www.minowellness.com",  # no
        "https://www.qschip.com",
        "https://liepin.com/company/10482793",  # guess - skip
    ]
    for i,u in enumerate(q_urls[:4]):
        name=f"qiansheng_{i}"
        try:
            resp=page.goto(u, wait_until="domcontentloaded", timeout=20000)
            s=resp.status if resp else None
            page.wait_for_timeout(3000)
            html=page.content()
            txt=save(name,html)
            print(f"{name}: {u} status={s} len={len(html)}",flush=True)
            print(txt[:400],flush=True)
            results[name]={"url":u,"status":s,"len":len(html),"preview":txt[:400]}
        except Exception as e:
            print(f"{name} err: {e}",flush=True); results[name]={"error":str(e)}
        time.sleep(1)

    ctx.close(); b.close(); p.stop()
    with open("/pulp/find-job/live4_results.json","w") as f: json.dump(results,f,ensure_ascii=False,indent=2)
    print("\nDONE4",flush=True)

if __name__=="__main__":
    main()
