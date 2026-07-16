#!/usr/bin/env python3
"""Round 55g: fetch cambricon job detail (JD+edu) + retry hotjob portal."""
import json, time
from playwright.sync_api import sync_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def cambricon_detail(p):
    b=p.chromium.launch(headless=True, proxy={"server":PROXY})
    pg=b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
    url="https://app.mokahr.com/apply/cambricon/1113#/job/088a8453-f76e-4e0a-bfd5-3225f05c3f0c"
    api=[]
    def on_resp(resp):
        u=resp.url
        if "job" in u and ("detail" in u or "088a8453" in u or "description" in u):
            try: api.append({"url":u,"body":resp.json()})
            except: pass
    pg.on("response",on_resp)
    try: pg.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e: print("goto err",e)
    time.sleep(4)
    # extract full job detail text from DOM
    try:
        txt=pg.eval_on_selector_all("body","els=>els.map(e=>(e.innerText||''))")[0]
        # trim to relevant section
        print("=== CAMBRICON JOB DETAIL (innerText) ===")
        print(txt[:3500])
        with open("/pulp/find-job/scrape/data/r55g_cambricon_detail.txt","w") as f: f.write(txt)
    except Exception as e: print("text err",e)
    print("\n api bodies:",len(api))
    for a in api: print("  ",a["url"][:130])
    b.close()

def horizon_retry(p):
    print("\n=== HOTJOB RETRY ===")
    b=p.chromium.launch(headless=True, proxy={"server":PROXY})
    pg=b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
    api=[]
    def on_resp(resp):
        u=resp.url
        if "hotjob" in u and "api" in u:
            try:
                body=resp.json(); api.append({"url":u,"body":body})
                print("  [API]",u[:120])
            except: pass
    pg.on("response",on_resp)
    # try the search/job/posts directly as the page would
    urls=["https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a/pb/social.html"]
    for u in urls:
        try:
            pg.goto(u, wait_until="domcontentloaded", timeout=35000)
            time.sleep(6)
            txt=pg.eval_on_selector_all("body","els=>els.map(e=>(e.innerText||'').slice(0,250))")[0] if pg.query_selector_all("body") else ""
            print("  page:",txt.replace("\n"," ")[:200])
            break
        except Exception as e: print("  goto err",e)
    # if blocked, try a direct job-search api POST from within page context
    found=[]
    for c in api:
        def fl(o,d=0):
            if d>7:return
            if isinstance(o,list) and o and isinstance(o[0],dict) and any(k in o[0] for k in ("postId","postName")):
                found.extend(o)
            elif isinstance(o,dict):
                for v in o.values(): fl(v,d+1)
        fl(c["body"])
    print("  api jobs:",len(found))
    for j in found:
        n=j.get("postName","")
        if "存储" in n or "分布式" in n:
            print(f"  >>> {n} | postId={j.get('postId')} | dept={j.get('department')} | pub={j.get('publishDate')}")
    b.close()

def main():
    with sync_playwright() as p:
        cambricon_detail(p)
        horizon_retry(p)

if __name__=="__main__": main()
