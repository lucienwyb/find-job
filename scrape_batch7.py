#!/usr/bin/env python3
"""Batch 7: broad XHR capture for moonshot/zhipu/horizon to find job APIs."""
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
    with open(f"/pulp/find-job/live7_{name}.html","w") as f: f.write(html or "")
    with open(f"/pulp/find-job/live7_{name}.txt","w") as f: f.write(txt[:50000])
    return txt

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN")
    page = ctx.new_page()
    results = {}

    def make_capture(name):
        caps = []
        def on_resp(resp):
            try:
                u = resp.url
                ct = resp.headers.get('content-type','')
                if 'json' in ct:
                    body = resp.text()
                    if body and len(body) > 30:
                        caps.append({"url":u,"status":resp.status,"len":len(body),"body":body[:3000]})
            except Exception: pass
        page.on("response", on_resp)
        return caps

    # --- Moonshot: broad capture, click 社会招聘 ---
    print("\n===== MOONSHOT broad =====",flush=True)
    caps = make_capture("moonshot")
    try:
        page.goto("https://careers.kimi.com/about-us", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        # click 社会招聘
        for sel in ["text=社会招聘","a:has-text('社会招聘')","text=社招"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print(f"clicked {sel}",flush=True)
                    break
            except Exception: pass
        page.wait_for_timeout(8000)
        for _ in range(15):
            page.mouse.wheel(0,1800); page.wait_for_timeout(500)
        html=page.content()
        txt=save("moonshot_social",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:2500],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构","推理","C++","编译","Runtime"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        results["moonshot"]={"url":page.url,"len":len(html),"preview":txt[:2500]}
    except Exception as e:
        print(f"moonshot err: {e}",flush=True); results["moonshot"]={"error":str(e)}
    page.remove_listener("response", lambda: None)
    print(f"\nMOONSHOT json captures: {len(caps)}",flush=True)
    for c in caps:
        print(f"  {c['url'][:150]}",flush=True)
        print(f"    {c['body'][:500]}",flush=True)
    with open("/pulp/find-job/moonshot_api7.json","w") as f: json.dump(caps,f,ensure_ascii=False,indent=2)

    # --- Zhipu: broad capture ---
    print("\n===== ZHIPU broad =====",flush=True)
    caps2 = make_capture("zhipu")
    try:
        page.goto("https://www.zhipuai.cn/zh/joinus", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)
        # click 社会招聘
        for sel in ["text=社会招聘","a:has-text('社会招聘')"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print(f"clicked {sel}",flush=True)
                    break
            except Exception: pass
        page.wait_for_timeout(5000)
        # try clicking the 算法/研发 card specifically (the category card, not text)
        # find clickable elements containing 算法/研发
        try:
            els = page.locator("a, div[role='button'], div[class*='card'], li")
            cnt = els.count()
            print(f"found {cnt} clickable elements",flush=True)
            for i in range(min(cnt, 80)):
                try:
                    txt_el = els.nth(i).inner_text(timeout=500)
                    if "算法/研发" in txt_el and "社招" in txt_el:
                        els.nth(i).click(timeout=4000)
                        print(f"clicked element {i}: {txt_el[:50]}",flush=True)
                        break
                except Exception: pass
        except Exception: pass
        page.wait_for_timeout(6000)
        for _ in range(15):
            page.mouse.wheel(0,1800); page.wait_for_timeout(500)
        html=page.content()
        txt=save("zhipu_social2",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:2500],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构","推理","编译"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        results["zhipu"]={"url":page.url,"len":len(html),"preview":txt[:2500]}
    except Exception as e:
        print(f"zhipu err: {e}",flush=True); results["zhipu"]={"error":str(e)}
    print(f"\nZHIPU json captures: {len(caps2)}",flush=True)
    for c in caps2:
        print(f"  {c['url'][:150]}",flush=True)
        print(f"    {c['body'][:500]}",flush=True)
    with open("/pulp/find-job/zhipu_api7.json","w") as f: json.dump(caps2,f,ensure_ascii=False,indent=2)

    # --- Horizon: broad capture, navigate and find careers ---
    print("\n===== HORIZON broad =====",flush=True)
    caps3 = make_capture("horizon")
    try:
        page.goto("https://www.horizon.auto", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)
        # Look for any element with career text and extract its onclick/href
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => ({href:e.href, text:e.innerText.trim().substring(0,30)}))")
        career_els = [h for h in hrefs if any(k in (h.get('text','')+h.get('href','')).lower() for k in ['join','career','招','recruit','talent','moka','hire'])]
        print(f"career elements: {career_els[:15]}",flush=True)
        # also try nav hover/click
        for sel in ["text=加入我们","text=人才招聘","text=招贤纳士","text=Careers","text=关于我们","text=About"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    # hover then look for submenu
                    loc.hover(timeout=3000)
                    page.wait_for_timeout(1500)
                    hrefs2 = page.eval_on_selector_all("a[href]", "els => els.map(e => ({href:e.href, text:e.innerText.trim().substring(0,30)}))")
                    new_career = [h for h in hrefs2 if any(k in (h.get('text','')+h.get('href','')).lower() for k in ['join','career','招','recruit','talent','moka','hire'])]
                    if new_career:
                        print(f"after hover {sel}: {new_career[:8]}",flush=True)
                        career_els.extend(new_career)
                    break
            except Exception: pass
        # visit first career href
        seen=set()
        for ce in career_els:
            h=ce.get('href','')
            if h and h not in seen and 'horizon' in h:
                seen.add(h)
                print(f"visiting {h}",flush=True)
                page.goto(h, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(6000)
                for _ in range(10):
                    page.mouse.wheel(0,1800); page.wait_for_timeout(500)
                html=page.content()
                txt=save("horizon_jobs2",html)
                print(f"  url={page.url} len={len(html)}",flush=True)
                if any(k in txt for k in ["职位","招聘","工程师","岗位","software","engineer"]):
                    print(txt[:1500],flush=True)
                    for kw in ["系统","驱动","BSP","嵌入式","底层","平台","Agent","baseband"]:
                        hits=re.findall(r'.{0,15}'+kw+r'.{0,25}', txt)
                        if hits: print(f"  [{kw}]:",hits[:3],flush=True)
                    results["horizon"]={"url":page.url,"len":len(html),"preview":txt[:1500]}
                    break
        else:
            results["horizon"]={"note":"no career page found","career_els":career_els[:10]}
    except Exception as e:
        print(f"horizon err: {e}",flush=True); results["horizon"]={"error":str(e)}
    print(f"\nHORIZON json captures: {len(caps3)}",flush=True)
    for c in caps3:
        print(f"  {c['url'][:150]}",flush=True)
        print(f"    {c['body'][:500]}",flush=True)
    with open("/pulp/find-job/horizon_api7.json","w") as f: json.dump(caps3,f,ensure_ascii=False,indent=2)

    ctx.close(); b.close(); p.stop()
    with open("/pulp/find-job/live7_results.json","w") as f: json.dump(results,f,ensure_ascii=False,indent=2)
    print("\nDONE7",flush=True)

if __name__=="__main__":
    main()
