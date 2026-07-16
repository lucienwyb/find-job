#!/usr/bin/env python3
"""Round 55: fetch live jobIds for two target jobs.
1. 地平线 hotjob: intercept api/v1/search/job/posts -> find 分布式存储研发工程师 postId
2. 寒武纪 mokahr: render portal, extract job links -> find 高级系统软件开发工程师 jobId
"""
import json, time, sys
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def scrape_horizon(p):
    print("\n" + "="*60)
    print("[地平线 hotjob]")
    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    ctx = browser.new_context(user_agent=UA, viewport={"width":1920,"height":1080})
    page = ctx.new_page()
    captured = []
    def on_response(resp):
        u = resp.url
        if "search/job/posts" in u or ("hotjob" in u and "api" in u):
            try:
                body = resp.json()
                captured.append({"url":u, "body":body})
                print(f"  [API] {u[:120]}")
            except Exception as e:
                print(f"  [API non-json] {u[:120]} {e}")
    page.on("response", on_response)
    url = "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a/pb/social.html"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print("  goto err:", e)
    time.sleep(8)
    # try clicking through postType categories / scroll to trigger full list
    try:
        # the portal may paginate; try interacting
        for _ in range(3):
            page.mouse.wheel(0, 3000)
            time.sleep(1.5)
    except: pass
    # dump captured
    jobs = []
    for c in captured:
        b = c["body"]
        # find list of jobs
        def find_list(o, depth=0):
            if depth>6: return
            if isinstance(o, list) and o and isinstance(o[0], dict) and any(k in o[0] for k in ("postId","postName","positionName")):
                jobs.extend(o)
            elif isinstance(o, dict):
                for v in o.values(): find_list(v, depth+1)
        find_list(b)
    # dedupe by postId
    seen=set(); uniq=[]
    for j in jobs:
        pid=j.get("postId")
        if pid and pid not in seen:
            seen.add(pid); uniq.append(j)
    print(f"  total jobs captured: {len(uniq)}")
    # find storage / distributed jobs
    for j in uniq:
        n=j.get("postName","")
        if "存储" in n or "分布式" in n:
            print(f"  >>> {n} | postId={j.get('postId')} | dept={j.get('department')} | place={j.get('workPlaceStr')} | publishDate={j.get('publishDate')}")
    # save full list
    with open("/pulp/find-job/scrape/data/r55_horizon.json","w") as f:
        json.dump(uniq, f, ensure_ascii=False, indent=1)
    print("  saved scrape/data/r55_horizon.json")
    browser.close()
    return uniq

def scrape_cambricon(p):
    print("\n" + "="*60)
    print("[寒武纪 mokahr]")
    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    ctx = browser.new_context(user_agent=UA, viewport={"width":1920,"height":1080})
    page = ctx.new_page()
    captured=[]
    def on_response(resp):
        u=resp.url
        if any(x in u for x in ["website/jobs","group-by-job","jobs/module","jobs/v2","jobs/recent","jobmap"]):
            try:
                b=resp.json()
                captured.append({"url":u,"body":b})
                print(f"  [API] {u[:130]}")
            except Exception as e:
                print(f"  [API non-json] {u[:130]}")
    page.on("response", on_response)
    url="https://app.mokahr.com/apply/cambricon/1113"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print("  goto err:",e)
    time.sleep(6)
    # scroll to load all jobs
    try:
        for _ in range(8):
            page.mouse.wheel(0, 4000)
            time.sleep(1.2)
    except: pass
    # extract job links from DOM (mokahr job cards link to /apply/cambricon/1113/job/<id>)
    links=[]
    try:
        anchors = page.eval_on_selector_all("a[href*='/job/']", """
          els => els.map(e => ({href: e.href, text: (e.innerText||'').trim().split('\\n')[0]}))
        """)
        links = anchors
    except Exception as e:
        print("  link extract err:", e)
    print(f"  job links found in DOM: {len(links)}")
    # find 高级系统软件
    seen=set(); uniq_links=[]
    for l in links:
        h=l.get("href","")
        if h and h not in seen:
            seen.add(h); uniq_links.append(l)
    for l in uniq_links:
        t=l.get("text","")
        if "系统软件" in t or "高级系统" in t:
            print(f"  >>> {t} | href={l.get('href')}")
    # also try to extract from necromancer-decrypted DOM all job titles
    try:
        all_titles = page.eval_on_selector_all("[class*='job'],[class*='position'],[class*='title']", """
          els => els.slice(0,200).map(e => (e.innerText||'').trim().split('\\n')[0]).filter(Boolean)
        """)
        hits=[t for t in all_titles if "系统软件" in t]
        if hits:
            print("  DOM title hits for 系统软件:", hits[:5])
    except: pass
    # save captured API bodies
    with open("/pulp/find-job/scrape/data/r55_cambricon_api.json","w") as f:
        json.dump(captured, f, ensure_ascii=False, indent=1)
    with open("/pulp/find-job/scrape/data/r55_cambricon_links.json","w") as f:
        json.dump(uniq_links, f, ensure_ascii=False, indent=1)
    print("  saved scrape/data/r55_cambricon_api.json + links.json")
    browser.close()
    return uniq_links, captured

def main():
    with sync_playwright() as p:
        hz = scrape_horizon(p)
        cb_links, cb_api = scrape_cambricon(p)
    print("\n=== SUMMARY ===")
    print(f"horizon jobs: {len(hz)}")
    print(f"cambricon links: {len(cb_links)}, api bodies: {len(cb_api)}")

if __name__=="__main__":
    main()
