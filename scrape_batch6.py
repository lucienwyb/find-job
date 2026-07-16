#!/usr/bin/env python3
"""Batch 6: final drill - moonshot job list, zhipu category, horizon nav, qiansheng boss."""
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
    with open(f"/pulp/find-job/live6_{name}.html","w") as f: f.write(html or "")
    with open(f"/pulp/find-job/live6_{name}.txt","w") as f: f.write(txt[:50000])
    return txt

def scroll_loop(page, n=15, wait=500):
    for _ in range(n):
        page.mouse.wheel(0, 1800); page.wait_for_timeout(wait)

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN")
    page = ctx.new_page()
    results = {}

    # capture API responses
    api_captures = []
    def on_response(resp):
        try:
            u = resp.url
            if any(k in u for k in ['/api/','/jobs','/position','/search','/list','recruitment']):
                ct = resp.headers.get('content-type','')
                if 'json' in ct or 'text' in ct:
                    try:
                        body = resp.text()
                        if body and len(body) > 50:
                            api_captures.append({"url":u,"status":resp.status,"len":len(body),"preview":body[:2000]})
                    except Exception: pass
        except Exception: pass
    page.on("response", on_response)

    # --- Moonshot: careers.kimi.com, click 加入我们 ---
    print("\n===== MOONSHOT careers.kimi.com join =====",flush=True)
    try:
        page.goto("https://careers.kimi.com/about-us", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        # click 加入我们 nav
        for sel in ["text=加入我们","a:has-text('加入我们')","text=Join Us","text=Jobs","text=职位"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print(f"clicked {sel}",flush=True)
                    break
            except Exception: pass
        page.wait_for_timeout(6000)
        scroll_loop(page, n=20, wait=600)
        html=page.content()
        txt=save("moonshot_jobs",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:2000],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构","C++","推理"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        results["moonshot_jobs"]={"url":page.url,"len":len(html),"preview":txt[:2000]}
    except Exception as e:
        print(f"moonshot err: {e}",flush=True); results["moonshot_jobs"]={"error":str(e)}

    # print captured APIs for moonshot
    print(f"\nMOONSHOT api captures: {len(api_captures)}",flush=True)
    for c in api_captures[-10:]:
        print(f"  {c['url'][:120]} status={c['status']} len={c['len']}",flush=True)
        if 'job' in c['url'].lower() or 'position' in c['url'].lower() or 'search' in c['url'].lower():
            print(f"    BODY: {c['preview'][:800]}",flush=True)
    # save api captures
    with open("/pulp/find-job/moonshot_api.json","w") as f: json.dump(api_captures,f,ensure_ascii=False,indent=2)
    api_captures.clear()

    # --- Zhipu: click 算法/研发 category ---
    print("\n===== ZHIPU category drill =====",flush=True)
    try:
        page.goto("https://www.zhipuai.cn/zh/joinus", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        # click 社会招聘 first
        for sel in ["text=社会招聘"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0: loc.click(timeout=4000)
            except Exception: pass
        page.wait_for_timeout(3000)
        # click 算法/研发 category
        for sel in ["text=算法/研发","text=算法/研发（社招）","text=研发","a:has-text('算法')","div:has-text('算法/研发')"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print(f"clicked {sel}",flush=True)
                    break
            except Exception: pass
        page.wait_for_timeout(6000)
        scroll_loop(page, n=20, wait=600)
        html=page.content()
        txt=save("zhipu_jobs",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:2000],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构","推理","C++"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        results["zhipu_jobs"]={"url":page.url,"len":len(html),"preview":txt[:2000]}
    except Exception as e:
        print(f"zhipu err: {e}",flush=True); results["zhipu_jobs"]={"error":str(e)}
    print(f"\nZHIPU api captures: {len(api_captures)}",flush=True)
    for c in api_captures[-8:]:
        print(f"  {c['url'][:120]} status={c['status']} len={c['len']}",flush=True)
        if any(k in c['url'].lower() for k in ['job','position','list','search','recruit']):
            print(f"    BODY: {c['preview'][:800]}",flush=True)
    with open("/pulp/find-job/zhipu_api.json","w") as f: json.dump(api_captures,f,ensure_ascii=False,indent=2)
    api_captures.clear()

    # --- Horizon: render homepage, find & click careers nav ---
    print("\n===== HORIZON nav =====",flush=True)
    try:
        page.goto("https://www.horizon.auto", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)
        # try clicking career-related nav
        for sel in ["text=加入我们","text=人才招聘","text=招贤纳士","text=Careers","text=Career","text=JOIN US","a:has-text('招')","text=关于我们"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print(f"clicked {sel}",flush=True)
                    page.wait_for_timeout(4000)
                    break
            except Exception: pass
        # try to find career links in current page
        html=page.content()
        hrefs=re.findall(r'href=["\']([^"\']+)["\']',html)
        career_hrefs=[h for h in hrefs if any(k in h.lower() for k in ['join','career','recruit','moka','hire','talent','zhaopin','social'])]
        print(f"url={page.url} career_hrefs={career_hrefs[:10]}",flush=True)
        save("horizon_nav",html)
        # visit any career href found
        if career_hrefs:
            target = career_hrefs[0]
            if target.startswith('/'): target = 'https://www.horizon.auto' + target
            page.goto(target, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(6000)
            scroll_loop(page, n=20, wait=600)
            html=page.content()
            txt=save("horizon_jobs",html)
            print(f"horizon jobs url={page.url} len={len(html)}",flush=True)
            print(txt[:1500],flush=True)
            for kw in ["系统","驱动","BSP","嵌入式","底层","平台","Agent"]:
                hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
                if hits: print(f"[{kw}]:",hits[:3],flush=True)
            results["horizon_jobs"]={"url":page.url,"len":len(html),"preview":txt[:1500]}
        else:
            results["horizon_jobs"]={"note":"no career href found","hrefs":career_hrefs[:10]}
    except Exception as e:
        print(f"horizon err: {e}",flush=True); results["horizon_jobs"]={"error":str(e)}
    print(f"\nHORIZON api captures: {len(api_captures)}",flush=True)
    for c in api_captures[-8:]:
        print(f"  {c['url'][:140]} status={c['status']} len={c['len']}",flush=True)
        if any(k in c['url'].lower() for k in ['job','position','list','recruit']):
            print(f"    BODY: {c['preview'][:800]}",flush=True)
    with open("/pulp/find-job/horizon_api.json","w") as f: json.dump(api_captures,f,ensure_ascii=False,indent=2)

    ctx.close(); b.close(); p.stop()
    with open("/pulp/find-job/live6_results.json","w") as f: json.dump(results,f,ensure_ascii=False,indent=2)
    print("\nDONE6",flush=True)

if __name__=="__main__":
    main()
