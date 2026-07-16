import asyncio, json, re
from playwright.async_api import async_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SOFT=["1981229439","1982624437","1983257091"]
DET_JS="""()=>{const sel='.job-intro-container, .job-description, .job-item-des, [class*="job-description"], [class*="job-intro"], .content, .job-detail, .job-requirements, .job-responsibilities';const el=document.querySelector(sel);return{title:document.title,desc:el?el.innerText:'',full:(document.body.innerText||'').slice(0,7500)};}"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        # fresh context, do NOT block resources this time (look human)
        ctx=await b.new_context(user_agent=UA,proxy={"server":PROXY},viewport={"width":1366,"height":900},locale="zh-CN",
            extra_http_headers={"Accept-Language":"zh-CN,zh;q=0.9"})
        # warm up homepage first
        page=await ctx.new_page()
        try:
            await page.goto("https://www.liepin.com/",wait_until="domcontentloaded",timeout=30000)
            await page.wait_for_timeout(2500)
        except Exception as e:
            print("warmup err",e,flush=True)
        # now go straight to a detail page
        results={}
        for jid in SOFT:
            url=f"https://www.liepin.com/job/{jid}.shtml"
            print("DETAIL",jid,flush=True)
            try:
                await page.goto(url,wait_until="domcontentloaded",timeout=40000)
                await page.wait_for_timeout(3500)
                t=await page.title()
                print("  title:",t,flush=True)
                if "验证" in t or "安全中心" in t:
                    print("  CAPTCHA - aborting",flush=True)
                    results[jid]={"captcha":True,"title":t}
                    break
                d=await page.evaluate(DET_JS)
                results[jid]=d
                print("  desc len:",len(d.get("desc","")),flush=True)
            except Exception as e:
                print("  err",e,flush=True); results[jid]={"error":str(e)}
            await asyncio.sleep(1.5)
        open("/pulp/find-job/out/liepin_final_details.json","w").write(json.dumps(results,ensure_ascii=False,indent=2))
        for jid,d in results.items():
            print("="*60); print("JID",jid)
            print("TITLE:",d.get("title",""))
            print("DESC:",(d.get("desc","") or "")[:1500])
            print("FULL:",(d.get("full","") or "")[:2500])
        await b.close()
asyncio.run(main())
