#!/usr/bin/env python3
"""Batch 8: moonshot /social + zhipu job list final attempt."""
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
    with open(f"/pulp/find-job/live8_{name}.html","w") as f: f.write(html or "")
    with open(f"/pulp/find-job/live8_{name}.txt","w") as f: f.write(txt[:50000])
    return txt

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN")
    page = ctx.new_page()

    # capture json
    caps=[]
    def on_resp(resp):
        try:
            ct=resp.headers.get('content-type','')
            if 'json' in ct:
                body=resp.text()
                if body and len(body)>30:
                    caps.append({"url":resp.url,"status":resp.status,"len":len(body),"body":body[:4000]})
        except Exception: pass
    page.on("response", on_resp)

    # --- Moonshot /social ---
    print("===== MOONSHOT /social =====",flush=True)
    try:
        page.goto("https://careers.kimi.com/social", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(8000)
        for _ in range(20):
            page.mouse.wheel(0,1800); page.wait_for_timeout(500)
        html=page.content()
        txt=save("moonshot_social",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:3000],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构","推理","C++","编译","Runtime","SRE","基础架构"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,30}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
    except Exception as e:
        print(f"moonshot err: {e}",flush=True)
    print(f"\nMOONSHOT caps: {len(caps)}",flush=True)
    for c in caps:
        print(f"  {c['url'][:150]} len={c['len']}",flush=True)
        if any(k in c['url'].lower() for k in ['job','position','list','search','social']):
            print(f"  BODY: {c['body'][:1500]}",flush=True)
    with open("/pulp/find-job/moonshot_api8.json","w") as f: json.dump(caps,f,ensure_ascii=False,indent=2)
    caps.clear()

    # --- Zhipu: try clicking category card, also try /zh/joinus?category= ---
    print("\n===== ZHIPU =====",flush=True)
    try:
        page.goto("https://www.zhipuai.cn/zh/joinus", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)
        # click 社会招聘
        try:
            page.locator("text=社会招聘").first.click(timeout=4000)
            page.wait_for_timeout(3000)
        except Exception: pass
        # find all clickable elements with 算法/研发 and click
        els = page.locator("a, div[role='button'], div[class*='card'], div[class*='item'], li, span")
        cnt = min(els.count(), 120)
        clicked=False
        for i in range(cnt):
            try:
                t = els.nth(i).inner_text(timeout=300)
                if "算法/研发" in t and len(t) < 80:
                    els.nth(i).click(timeout=4000)
                    print(f"clicked el {i}: {t[:60]}",flush=True)
                    clicked=True
                    break
            except Exception: pass
        if not clicked:
            # try clicking any element containing 算法
            try:
                page.locator("text=算法/研发（社招）").first.click(timeout=4000)
                print("clicked 算法/研发（社招）",flush=True)
            except Exception as e:
                print(f"click err: {e}",flush=True)
        page.wait_for_timeout(8000)
        for _ in range(20):
            page.mouse.wheel(0,1800); page.wait_for_timeout(500)
        html=page.content()
        txt=save("zhipu_social",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:3000],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构","推理","编译","C++"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,30}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
    except Exception as e:
        print(f"zhipu err: {e}",flush=True)
    print(f"\nZHIPU caps: {len(caps)}",flush=True)
    for c in caps:
        print(f"  {c['url'][:150]} len={c['len']}",flush=True)
        if any(k in c['url'].lower() for k in ['job','position','list','recruit','joinus','category']):
            print(f"  BODY: {c['body'][:1500]}",flush=True)
    with open("/pulp/find-job/zhipu_api8.json","w") as f: json.dump(caps,f,ensure_ascii=False,indent=2)

    ctx.close(); b.close(); p.stop()
    print("\nDONE8",flush=True)

if __name__=="__main__":
    main()
