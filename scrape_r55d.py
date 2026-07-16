#!/usr/bin/env python3
"""Round 55d: navigate mokahr #/jobs (all jobs) to find 高级系统软件 jobId."""
import json, time
from playwright.sync_api import sync_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True, proxy={"server":PROXY})
        pg=b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
        # capture the (possibly paginated) website/jobs responses
        api=[]
        def on_resp(resp):
            u=resp.url
            if "website/jobs" in u or "group-by-job" in u or "jobs/module" in u or "jobs/v2" in u:
                try: api.append({"url":u,"body":resp.json()})
                except: pass
        pg.on("response",on_resp)
        try: pg.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="networkidle", timeout=45000)
        except Exception as e: print("goto err",e)
        time.sleep(3)
        # dump body HTML structure (nav area) — first 4000 chars
        try:
            html=pg.eval_on_selector_all("body","els=>els.map(e=>(e.innerHTML||''))")[0]
            # find nav-looking anchors & buttons
            import re
            anchors=re.findall(r'<a[^>]*href="([^"]*#/[^"]*)"[^>]*>([^<]{0,40})', html)
            print("anchors(#/):", anchors[:20])
            buttons=re.findall(r'<(?:button|div|li|span)[^>]*>([^<]{1,30})</', html)
            depts=[x.strip() for x in buttons if x.strip() and (x.strip().endswith('部') or x.strip().endswith('中心') or x.strip().endswith('组') or '全部' in x.strip() or '职位' in x.strip())]
            print("dept-ish texts:", depts[:30])
        except Exception as e: print("html dump err",e)

        # try clicking 全部职位 / 全部
        for label in ["全部职位","全部","查看全部","所有职位"]:
            try:
                loc=pg.locator(f"text=\"{label}\"").first
                if loc.count()>0:
                    loc.click(timeout=2000); time.sleep(1.5)
                    print(f"  clicked '{label}'")
            except: pass

        # try SPA route #/jobs
        for route in ["#/jobs","#/position","#/list"]:
            try:
                pg.goto("https://app.mokahr.com/apply/cambricon/1113"+route, wait_until="domcontentloaded", timeout=20000)
                time.sleep(2.5)
            except: pass

        # scroll extensively
        for _ in range(15):
            try: pg.mouse.wheel(0,4000); time.sleep(0.6)
            except: pass
        # collect all job links
        try:
            links=pg.eval_on_selector_all("a[href*='#/job/']","els=>els.map(e=>({href:e.href,text:(e.innerText||'').trim().split('\\n')[0]}))")
        except: links=[]
        seen=set(); uniq=[]
        for l in links:
            h=l.get("href","")
            if h and h not in seen: seen.add(h); uniq.append(l)
        print(f"\n total unique job links: {len(uniq)}")
        for l in uniq:
            if "系统软件" in l.get("text","") or "高级系统" in l.get("text",""):
                print(f"  >>> HIT: {l.get('text')} | {l.get('href')}")
        # also print all titles for reference
        print(" all titles:")
        for l in uniq: print("   ",l.get("text","")[:45])
        with open("/pulp/find-job/scrape/data/r55d_cambricon.json","w") as f:
            json.dump({"links":uniq,"api_count":len(api)},f,ensure_ascii=False,indent=1)
        print(" api bodies:",len(api))
        b.close()

if __name__=="__main__": main()
