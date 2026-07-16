#!/usr/bin/env python3
"""Batch 9: moonshot 技术类 jobs + 01ai careers."""
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
    with open(f"/pulp/find-job/live9_{name}.html","w") as f: f.write(html or "")
    with open(f"/pulp/find-job/live9_{name}.txt","w") as f: f.write(txt[:50000])
    return txt

def main():
    p, b = launch()
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN")
    page = ctx.new_page()

    caps=[]
    def on_resp(resp):
        try:
            ct=resp.headers.get('content-type','')
            if 'json' in ct or 'javascript' in ct:
                body=resp.text()
                if body and len(body)>30:
                    caps.append({"url":resp.url,"status":resp.status,"ct":ct,"len":len(body),"body":body[:5000]})
        except Exception: pass
    page.on("response", on_resp)

    # --- Moonshot /social, click 技术类 ---
    print("===== MOONSHOT 技术类 =====",flush=True)
    try:
        page.goto("https://careers.kimi.com/social", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(8000)
        # click 技术类
        for sel in ["text=技术类","text=技术","a:has-text('技术类')","div:has-text('技术类')"]:
            try:
                loc=page.locator(sel).first
                if loc.count()>0:
                    loc.click(timeout=4000)
                    print(f"clicked {sel}",flush=True)
                    break
            except Exception: pass
        page.wait_for_timeout(8000)
        for _ in range(25):
            page.mouse.wheel(0,1800); page.wait_for_timeout(600)
        html=page.content()
        txt=save("moonshot_tech",html)
        print(f"url={page.url} len={len(html)}",flush=True)
        print(txt[:3000],flush=True)
        for kw in ["系统","Infra","基础设施","后端","内核","Agent","平台","嵌入式","驱动","底层","架构","推理","C++","编译","Runtime","SRE","基础架构","架构师"]:
            hits=re.findall(r'.{0,15}'+kw+r'.{0,30}', txt)
            if hits: print(f"[{kw}]:",hits[:3],flush=True)
        # also extract job-looking text from raw HTML
        texts = re.findall(r'>([^<]{4,60})<', html)
        jobs=[t.strip() for t in texts if any(k in t for k in ['工程师','架构','开发','Infra','Agent','系统','平台','后端','前端','算法','基础']) and '社会招聘' not in t and '技术类' not in t]
        if jobs: print("JOB-LIKE TEXT:", jobs[:30],flush=True)
    except Exception as e:
        print(f"moonshot err: {e}",flush=True)
    print(f"\nMOONSHOT caps: {len(caps)}",flush=True)
    for c in caps:
        if any(k in c['url'].lower() for k in ['job','position','list','search','api','social','tech']) or c['len']>500:
            print(f"  {c['url'][:160]} ct={c['ct'][:20]} len={c['len']}",flush=True)
            print(f"  BODY: {c['body'][:1200]}",flush=True)
    with open("/pulp/find-job/moonshot_api9.json","w") as f: json.dump(caps,f,ensure_ascii=False,indent=2)
    caps.clear()

    # --- 01ai: find careers ---
    print("\n===== 01AI =====",flush=True)
    o_urls = ["https://www.01.ai/join","https://www.01.ai/careers","https://www.01.ai/about","https://www.01.ai"]
    for i,u in enumerate(o_urls):
        try:
            resp=page.goto(u, wait_until="domcontentloaded", timeout=25000)
            s=resp.status if resp else None
            page.wait_for_timeout(5000)
            for _ in range(8):
                page.mouse.wheel(0,1500); page.wait_for_timeout(500)
            html=page.content()
            txt=save(f"01ai_{i}",html)
            print(f"01ai_{i}: {u} status={s} len={len(html)}",flush=True)
            hrefs=re.findall(r'href=["\']([^"\']+)["\']',html)
            career_hrefs=[h for h in hrefs if any(k in h.lower() for k in ['join','career','recruit','moka','hire','zhaopin','job','talent'])]
            if career_hrefs: print(f"  career hrefs: {career_hrefs[:8]}",flush=True)
            # check for job content
            if any(k in txt for k in ['职位','岗位','工程师','招聘']):
                print(f"  HAS JOBS",flush=True)
                print(txt[:1000],flush=True)
                for kw in ['系统','Infra','基础设施','后端','Agent','平台','架构','嵌入式','驱动']:
                    hits=re.findall(r'.{0,15}'+kw+r'.{0,25}',txt)
                    if hits: print(f"  [{kw}]:",hits[:3],flush=True)
                break
        except Exception as e:
            print(f"01ai_{i} err: {e}",flush=True)
        time.sleep(1)

    ctx.close(); b.close(); p.stop()
    print("\nDONE9",flush=True)

if __name__=="__main__":
    main()
