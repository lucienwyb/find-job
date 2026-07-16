#!/usr/bin/env python3
"""Round 55b: get all cambricon jobIds (click every department) + retry hotjob."""
import json, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def cambricon(p):
    print("\n[寒武纪 mokahr] click all departments")
    b = p.chromium.launch(headless=True, proxy={"server": PROXY})
    pg = b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
    captured=[]
    def on_resp(resp):
        u=resp.url
        if "website/jobs" in u or "group-by-job" in u or "jobs/module" in u:
            try:
                captured.append({"url":u,"body":resp.json()})
            except: pass
    pg.on("response", on_resp)
    try: pg.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="domcontentloaded", timeout=45000)
    except Exception as e: print("goto err",e)
    time.sleep(5)

    # Collect links, then click each department/category tab on the left sidebar
    all_links=[]
    def collect():
        try:
            a = pg.eval_on_selector_all("a[href*='#/job/']", "els=>els.map(e=>({href:e.href,text:(e.innerText||'').trim().split('\\n')[0]}))")
            return a
        except: return []

    # Try clicking department filter tabs. mokahr uses buttons/links with dept names.
    # First, dump clickable category elements to understand structure.
    try:
        cats = pg.eval_on_selector_all("[class*='epart'],[class*='ateg'],[class*='roup'],li,button", """
          els => els.filter(e => /部|组|中心|所有|全部/.test(e.innerText||''))
                 .map(e=>({tag:e.tagName, cls:e.className, txt:(e.innerText||'').trim().slice(0,40)})).slice(0,40)
        """)
        print(" candidate category elems:")
        for c in cats: print("   ",c.get("tag"),c.get("cls","")[:30],"|",c.get("txt",""))
    except Exception as e: print("cat dump err",e)

    # click each candidate that looks like a department name
    depts_clicked=[]
    try:
        els = pg.query_selector_all("[class*='epart'],[class*='ateg'],[class*='roup']")
        # broader: any element whose text is short and ends with 部
        targets = pg.eval_on_selector_all("li,div,button,span,a", """
          els => {
            const out=[];
            for(const e of els){
              const t=(e.innerText||'').trim();
              if(t && t.length<12 && /部$|中心$|组$/.test(t) && e.children.length===0){
                out.push({txt:t, cls:e.className});
              }
            }
            // dedupe by txt
            const seen=new Set(); return out.filter(o=>{if(seen.has(o.txt))return false;seen.add(o.txt);return true;});
          }
        """)
        print(" department-like texts:", [t.get("txt") for t in targets])
        for t in targets:
            txt=t.get("txt")
            try:
                # click element by text
                el = pg.query_selector(f"text='{txt}'")
                if el:
                    el.click()
                    time.sleep(1.2)
                    links=collect()
                    for l in links:
                        if l not in all_links: all_links.append(l)
                    depts_clicked.append(txt)
            except Exception as e: pass
    except Exception as e: print("click loop err",e)

    # fallback: scroll through and collect
    for _ in range(10):
        pg.mouse.wheel(0,4000); time.sleep(1)
    for l in collect():
        if l not in all_links: all_links.append(l)

    print(f" total unique job links: {len(all_links)}")
    for l in all_links:
        t=l.get("text","")
        if "系统软件" in t or "高级系统" in t:
            print(f"  >>> HIT: {t} | {l.get('href')}")
    with open("/pulp/find-job/scrape/data/r55b_cambricon_all.json","w") as f:
        json.dump({"links":all_links,"depts":depts_clicked,"api":captured},f,ensure_ascii=False,indent=1)
    print(" saved r55b_cambricon_all.json; depts clicked:",depts_clicked)
    b.close()
    return all_links

def horizon(p):
    print("\n[地平线 hotjob] broad intercept")
    b = p.chromium.launch(headless=True, proxy={"server": PROXY})
    pg = b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
    captured=[]
    def on_resp(resp):
        u=resp.url
        if "hotjob" in u and ("api" in u or "post" in u or "job" in u or "search" in u):
            ct=resp.headers.get("content-type","")
            if "json" in ct:
                try:
                    body=resp.json(); captured.append({"url":u,"body":body})
                    print(f"  [API json] {u[:130]}")
                except: pass
    pg.on("response", on_resp)
    # try several entry URLs
    for u in ["https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a/pb/social.html",
              "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a/"]:
        try:
            print("  goto",u)
            pg.goto(u, wait_until="domcontentloaded", timeout=40000)
            time.sleep(8)
            break
        except Exception as e: print("  goto err",e)
    # scroll & click postType categories
    for _ in range(5):
        try: pg.mouse.wheel(0,3000); time.sleep(1.2)
        except: pass
    # extract any job links from DOM
    jobs=[]
    try:
        jobs = pg.eval_on_selector_all("a", "els=>els.map(e=>({href:e.href,text:(e.innerText||'').trim().slice(0,60)})).filter(o=>o.text)")
    except Exception as e: print("  dom err",e)
    # find job list in captured json
    found=[]
    for c in captured:
        def find_list(o,d=0):
            if d>7:return
            if isinstance(o,list) and o and isinstance(o[0],dict) and any(k in o[0] for k in ("postId","postName","positionName")):
                found.extend(o)
            elif isinstance(o,dict):
                for v in o.values(): find_list(v,d+1)
        find_list(c["body"])
    seen=set(); uniq=[]
    for j in found:
        pid=j.get("postId")
        if pid and pid not in seen: seen.add(pid); uniq.append(j)
    print(f"  api jobs: {len(uniq)}; dom links: {len(jobs)}")
    for j in uniq:
        n=j.get("postName","")
        if "存储" in n or "分布式" in n:
            print(f"  >>> {n} | postId={j.get('postId')} | dept={j.get('department')} | place={j.get('workPlaceStr')} | pub={j.get('publishDate')}")
    for l in jobs:
        if "存储" in l.get("text","") or "分布式" in l.get("text",""):
            print(f"  >>> DOM: {l.get('text')} | {l.get('href')}")
    with open("/pulp/find-job/scrape/data/r55b_horizon.json","w") as f:
        json.dump({"api_jobs":uniq,"dom_links":jobs,"raw_api":captured},f,ensure_ascii=False,indent=1)
    print(" saved r55b_horizon.json")
    b.close()

def main():
    with sync_playwright() as p:
        cambricon(p)
        horizon(p)

if __name__=="__main__": main()
