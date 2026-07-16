#!/usr/bin/env python3
"""Batch 3: URL discovery for blocked sites + galaxy liepin full scroll."""
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

def try_fetch(page, url, wait_ms=12000, scroll_n=12):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else None
    except Exception as e:
        return None, f"goto error: {e}", ""
    try: page.wait_for_load_state("networkidle", timeout=wait_ms)
    except Exception: pass
    for _ in range(scroll_n):
        page.mouse.wheel(0, 1800); page.wait_for_timeout(500)
    return status, "ok", page.content()

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN")
    page = ctx.new_page()
    results = {}

    # Zhipu: try multiple
    zhipu_urls = [
        "https://www.zhipu.cn/joinus",
        "https://jobs.zhipu.cn",
        "https://www.zhipuai.cn/joinus",
        "https://app.mokahr.com/social-recruitment/zhipu",
    ]
    for i,u in enumerate(zhipu_urls):
        name=f"zhipu_{i}"
        print(f"\n== {name}: {u} ==",flush=True)
        s,msg,html=try_fetch(page,u)
        print(f"status={s} len={len(html)}",flush=True)
        txt=clean(html) if html else ""
        with open(f"/pulp/find-job/live3_{name}.txt","w") as f: f.write(txt[:20000])
        print(txt[:600],flush=True)
        results[name]={"status":s,"len":len(html or ""),"preview":txt[:600]}
        if s==200 and len(html)>2000: break
        time.sleep(1)

    # Moonshot
    moon_urls = ["https://www.moonshot.cn/joinus","https://www.moonshot.cn/careers","https://www.moonshot.cn/about","https://kimi.com/about/joinus"]
    for i,u in enumerate(moon_urls):
        name=f"moonshot_{i}"
        print(f"\n== {name}: {u} ==",flush=True)
        s,msg,html=try_fetch(page,u)
        print(f"status={s} len={len(html)}",flush=True)
        txt=clean(html) if html else ""
        with open(f"/pulp/find-job/live3_{name}.txt","w") as f: f.write(txt[:20000])
        print(txt[:600],flush=True)
        results[name]={"status":s,"len":len(html or ""),"preview":txt[:600]}
        if s==200 and len(html)>3000 and "nginx" not in txt[:200].lower(): break
        time.sleep(1)

    # Horizon
    h_urls = ["https://www.horizon.cc/join-us","https://www.horizon.cc/careers","https://www.horizonauto.com/join-us","https://app.mokahr.com/social-recruitment/horizonrobotics","https://horizon.zhiye.com.cn"]
    for i,u in enumerate(h_urls):
        name=f"horizon_{i}"
        print(f"\n== {name}: {u} ==",flush=True)
        s,msg,html=try_fetch(page,u)
        print(f"status={s} len={len(html)}",flush=True)
        txt=clean(html) if html else ""
        with open(f"/pulp/find-job/live3_{name}.txt","w") as f: f.write(txt[:20000])
        print(txt[:600],flush=True)
        results[name]={"status":s,"len":len(html or ""),"preview":txt[:600]}
        if s==200 and len(html)>3000 and "404" not in txt[:200]: break
        time.sleep(1)

    # Qiansheng
    q_urls = ["https://www.qianshengai.com","https://www.qianshengai.com/join","https://www.qianshengai.com/careers","https://www.qian-sheng.com","https://www.qiansheng.com"]
    for i,u in enumerate(q_urls):
        name=f"qiansheng_{i}"
        print(f"\n== {name}: {u} ==",flush=True)
        s,msg,html=try_fetch(page,u)
        print(f"status={s} len={len(html)}",flush=True)
        txt=clean(html) if html else ""
        with open(f"/pulp/find-job/live3_{name}.txt","w") as f: f.write(txt[:20000])
        print(txt[:600],flush=True)
        results[name]={"status":s,"len":len(html or ""),"preview":txt[:600]}
        if s==200 and len(html)>2000: break
        time.sleep(1)

    # Robotera: find actual careers page (the /join-us had no jobs, only footer)
    r_urls = ["https://www.robotera.com/join-us","https://www.robotera.com/careers","https://www.robotera.com/about","https://www.robotera.com"]
    for i,u in enumerate(r_urls):
        name=f"robotera_{i}"
        print(f"\n== {name}: {u} ==",flush=True)
        s,msg,html=try_fetch(page,u)
        print(f"status={s} len={len(html)}",flush=True)
        txt=clean(html) if html else ""
        with open(f"/pulp/find-job/live3_{name}.txt","w") as f: f.write(txt[:20000])
        print(txt[:800],flush=True)
        results[name]={"status":s,"len":len(html or ""),"preview":txt[:800]}
        if s==200 and ("职位" in txt or "招聘" in txt or "工程师" in txt): break
        time.sleep(1)

    # Galaxy liepin full scroll to get all jobs
    print("\n== galaxy_liepin_full ==",flush=True)
    s,msg,html=try_fetch(page,"https://liepin.com/company/9614836",scroll_n=30)
    print(f"status={s} len={len(html)}",flush=True)
    txt=clean(html)
    with open("/pulp/find-job/live3_galaxy_liepin_full.txt","w") as f: f.write(txt[:40000])
    # extract all embedded/system/驱动
    for kw in ["嵌入式","驱动","BSP","星载","载荷","FPGA","系统软件","内核","底层","平台软件","Agent","应用软件"]:
        hits=re.findall(r'.{0,10}'+kw+r'.{0,20}', txt)
        if hits: print(f"[{kw}]:", hits[:5],flush=True)
    results["galaxy_liepin_full"]={"status":s,"len":len(html or "")}

    ctx.close(); b.close(); p.stop()
    with open("/pulp/find-job/live3_results.json","w") as f: json.dump(results,f,ensure_ascii=False,indent=2)
    print("\nDONE3",flush=True)

if __name__=="__main__":
    main()
