#!/usr/bin/env python3
"""Round 55e: navigate to mokahr #/jobs full list, extract 高级系统软件 jobId."""
import json, time
from playwright.sync_api import sync_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True, proxy={"server":PROXY})
        pg=b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
        api=[]
        def on_resp(resp):
            u=resp.url
            if "website/jobs" in u or "group-by-job" in u or "jobs/module" in u or "jobs/v2" in u or "jobs/recent" in u:
                try: api.append({"url":u,"body":resp.json()})
                except: pass
        pg.on("response",on_resp)
        try: pg.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="networkidle", timeout=45000)
        except Exception as e: print("goto err",e)
        time.sleep(2)
        # click 查看更多职位
        try:
            pg.locator("text=\"查看更多职位\"").first.click(timeout=5000)
            print("clicked 查看更多职位")
        except Exception as e:
            print("click err, try direct nav:",e)
            try: pg.goto("https://app.mokahr.com/apply/cambricon/1113#/jobs", wait_until="networkidle", timeout=30000)
            except Exception as e2: print("nav err",e2)
        time.sleep(4)
        # the #/jobs page groups by department and may be collapsed; expand all + scroll
        for _ in range(20):
            try:
                pg.mouse.wheel(0,4000); time.sleep(0.5)
            except: pass
        # try clicking any "展开" expand buttons
        try:
            exps=pg.locator("text=展开").all()
            print("展开 buttons:",len(exps))
            for e in exps[:30]:
                try: e.click(timeout=1500); time.sleep(0.3)
                except: pass
        except: pass
        time.sleep(2)
        # collect ALL job links
        try:
            links=pg.eval_on_selector_all("a[href*='#/job/']","els=>els.map(e=>({href:e.href,text:(e.innerText||'').trim().split('\\n')[0]}))")
        except: links=[]
        seen=set(); uniq=[]
        for l in links:
            h=l.get("href","")
            if h and h not in seen: seen.add(h); uniq.append(l)
        print(f"\n total unique job links: {len(uniq)}")
        for l in uniq:
            if "系统软件" in l.get("text","") or "高级系统" in l.get("text","") or "bringup" in l.get("text","").lower():
                print(f"  >>> HIT: {l.get('text')} | {l.get('href')}")
        print("\n ALL titles:")
        for l in uniq: print("   ",l.get("text","")[:50],"|",l.get("href","").split("#/job/")[-1])
        with open("/pulp/find-job/scrape/data/r55e_cambricon_jobs.json","w") as f:
            json.dump({"links":uniq,"api_count":len(api)},f,ensure_ascii=False,indent=1)
        print(" api bodies:",len(api))
        b.close()

if __name__=="__main__": main()
