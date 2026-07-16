#!/usr/bin/env python3
"""Batch 5: drill into job lists for zhipu/moonshot/robotera + horizon/qiansheng discovery."""
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
    with open(f"/pulp/find-job/live5_{name}.html","w") as f: f.write(html or "")
    with open(f"/pulp/find-job/live5_{name}.txt","w") as f: f.write(txt[:40000])
    return txt

def scroll_loop(page, n=12, wait=500):
    for _ in range(n):
        page.mouse.wheel(0, 1800); page.wait_for_timeout(wait)

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN")
    page = ctx.new_page()
    results = {}

    # --- Zhipu: go to joinus, click 社会招聘, then 算法/研发 ---
    print("\n===== ZHIPU drill =====",flush=True)
    try:
        page.goto("https://www.zhipuai.cn/zh/joinus", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        # click 社会招聘 tab
        for sel in ["text=社会招聘","a:has-text('社会招聘')","span:has-text('社会招聘')"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print("clicked 社会招聘",flush=True)
                    break
            except Exception: pass
        page.wait_for_timeout(4000)
        scroll_loop(page)
        html=page.content()
        txt=save("zhipu_social",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:1500],flush=True)
        # look for job titles
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        results["zhipu_social"]={"url":page.url,"len":len(html),"preview":txt[:1500]}
    except Exception as e:
        print(f"zhipu err: {e}",flush=True); results["zhipu_social"]={"error":str(e)}

    # --- Moonshot: careers.kimi.com ---
    print("\n===== MOONSHOT careers.kimi.com =====",flush=True)
    try:
        page.goto("https://careers.kimi.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)
        scroll_loop(page, n=15)
        html=page.content()
        txt=save("moonshot_careers",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:2000],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        results["moonshot_careers"]={"url":page.url,"len":len(html),"preview":txt[:2000]}
    except Exception as e:
        print(f"moonshot err: {e}",flush=True); results["moonshot_careers"]={"error":str(e)}

    # --- Robotera: join page, click 社会招聘 ---
    print("\n===== ROBOTERA drill =====",flush=True)
    try:
        page.goto("https://www.robotera.com/#/about/join", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        for sel in ["text=社会招聘","a:has-text('社会招聘')","span:has-text('社会招聘')","li:has-text('社会招聘')"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print("clicked 社会招聘",flush=True)
                    break
            except Exception: pass
        page.wait_for_timeout(5000)
        scroll_loop(page)
        html=page.content()
        txt=save("robotera_social",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:2000],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","BSP","SLAM","仿真"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        results["robotera_social"]={"url":page.url,"len":len(html),"preview":txt[:2000]}
    except Exception as e:
        print(f"robotera err: {e}",flush=True); results["robotera_social"]={"error":str(e)}

    # --- Horizon: try horizon.auto + liepin search ---
    print("\n===== HORIZON =====",flush=True)
    h_urls = ["https://www.horizon.auto","https://www.horizon.auto/join-us","https://www.horizon.auto/careers","https://horizon.auto/zh/join"]
    for i,u in enumerate(h_urls):
        name=f"horizon_{i}"
        try:
            resp=page.goto(u, wait_until="domcontentloaded", timeout=25000)
            s=resp.status if resp else None
            page.wait_for_timeout(4000)
            scroll_loop(page, n=8)
            html=page.content()
            txt=save(name,html)
            print(f"{name}: {u} status={s} len={len(html)}",flush=True)
            print(txt[:500],flush=True)
            hrefs=re.findall(r'href=["\']([^"\']+)["\']',html)
            career_hrefs=[h for h in hrefs if any(k in h.lower() for k in ['join','career','recruit','moka','hire','zhaopin'])]
            if career_hrefs: print(f"career hrefs: {career_hrefs[:8]}",flush=True)
            results[name]={"url":u,"status":s,"len":len(html),"preview":txt[:500],"hrefs":career_hrefs[:8]}
            if s==200 and len(html)>5000 and "404" not in txt[:100]:
                # check if it has job content
                if any(k in txt for k in ["职位","招聘","工程师","岗位"]):
                    print("HORIZON FOUND jobs",flush=True)
                    break
        except Exception as e:
            print(f"{name} err: {e}",flush=True); results[name]={"error":str(e)}
        time.sleep(1)

    # --- Qiansheng: liepin search ---
    print("\n===== QIANSHENG liepin search =====",flush=True)
    try:
        page.goto("https://www.liepin.com/", wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)
        # try search
        try:
            page.fill("input[placeholder*='搜']", "千乘探索", timeout=5000)
        except Exception:
            try:
                page.locator("input").first.fill("千乘探索", timeout=5000)
            except Exception: pass
        try:
            page.keyboard.press("Enter")
        except Exception: pass
        page.wait_for_timeout(5000)
        scroll_loop(page)
        html=page.content()
        txt=save("qiansheng_liepin",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:1000],flush=True)
        results["qiansheng_liepin"]={"url":page.url,"len":len(html),"preview":txt[:1000]}
    except Exception as e:
        print(f"qiansheng liepin err: {e}",flush=True); results["qiansheng_liepin"]={"error":str(e)}

    ctx.close(); b.close(); p.stop()
    with open("/pulp/find-job/live5_results.json","w") as f: json.dump(results,f,ensure_ascii=False,indent=2)
    print("\nDONE5",flush=True)

if __name__=="__main__":
    main()
