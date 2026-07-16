#!/usr/bin/env python3
"""Round 55f: use mokahr portal search box to find 高级系统软件 jobId."""
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
            if "website/jobs" in u or "search" in u or "jobs/v2" in u or "keyword" in u:
                try: api.append({"url":u,"body":resp.json()})
                except: pass
        pg.on("response",on_resp)
        try: pg.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="networkidle", timeout=45000)
        except Exception as e: print("goto err",e)
        time.sleep(3)
        # find search input
        sel_tries=["input[placeholder*='搜索']","input[placeholder*='职位']","input[type='search']","input.search","[class*='earch'] input"]
        filled=False
        for s in sel_tries:
            try:
                el=pg.locator(s).first
                if el.count()>0:
                    el.click(); el.fill("系统软件"); filled=True
                    print(f"  filled search via selector: {s}")
                    break
            except: pass
        if not filled:
            # dump all inputs
            try:
                ins=pg.eval_on_selector_all("input","els=>els.map(e=>({ph:e.placeholder,type:e.type,cls:e.className}))")
                print("  inputs:",ins[:10])
            except: pass
        time.sleep(1)
        # press Enter / click search button
        try: pg.keyboard.press("Enter")
        except: pass
        try:
            pg.locator("text=搜索").first.click(timeout=2000)
        except: pass
        time.sleep(3)
        # collect job links now (search results)
        try:
            links=pg.eval_on_selector_all("a[href*='#/job/']","els=>els.map(e=>({href:e.href,text:(e.innerText||'').trim().split('\\n')[0]}))")
        except: links=[]
        seen=set(); uniq=[]
        for l in links:
            h=l.get("href","")
            if h and h not in seen: seen.add(h); uniq.append(l)
        print(f"\n search result job links: {len(uniq)}")
        for l in uniq:
            print("   ",l.get("text","")[:50],"|",l.get("href","").split("#/job/")[-1])
        with open("/pulp/find-job/scrape/data/r55f_cambricon_search.json","w") as f:
            json.dump({"links":uniq,"api":api},f,ensure_ascii=False,indent=1)
        print(" api bodies:",len(api))
        b.close()

if __name__=="__main__": main()
