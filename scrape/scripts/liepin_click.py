import asyncio, json, re
from playwright.async_api import async_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SOFT_IDS=["1981229439","1982624437","1983257091"]

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx=await b.new_context(user_agent=UA,proxy={"server":PROXY},viewport={"width":1366,"height":900},locale="zh-CN")
        # do NOT block resources on detail (js/css needed for render); block only heavy media
        await ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image","media","font") else r.continue_())
        page=await ctx.new_page()
        await page.goto("https://www.liepin.com/zhaopin/?key=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9&curPage=0",wait_until="domcontentloaded",timeout=45000)
        await page.wait_for_timeout(5500)
        results=[]
        for jid in SOFT_IDS:
            print("CLICK job",jid,flush=True)
            # find link with this job id
            link=await page.query_selector(f'a[href*="/job/{jid}"]')
            if not link:
                print("  not found on list; trying direct nav with referrer",flush=True)
                # set referrer via extra headers
                d=await detail_direct(ctx,jid)
                results.append({"jid":jid,"detail":d,"method":"direct"})
                continue
            # click opens new tab sometimes
            try:
                async with ctx.expect_page(timeout=15000) as newpage_info:
                    await link.click()
                np=await newpage_info.value
                await np.wait_for_load_state("domcontentloaded",timeout=30000)
                await np.wait_for_timeout(3000)
                d=await extract(np)
                results.append({"jid":jid,"detail":d,"method":"click-newtab"})
                await np.close()
            except Exception as e:
                print("  click err",e,flush=True)
                # maybe same-tab nav
                await page.wait_for_timeout(2000)
                d=await extract(page)
                results.append({"jid":jid,"detail":d,"method":"click-sametab"})
            await asyncio.sleep(2.0)
        open("/pulp/find-job/out/liepin_click_details.json","w").write(json.dumps(results,ensure_ascii=False,indent=2))
        for r in results:
            print("="*60)
            print("JID",r["jid"],"method",r["method"])
            d=r["detail"]
            print("TITLE:",d.get("title",""))
            full=d.get("full","")
            print("FULL:",full[:2500])
        await b.close()

async def extract(page):
    return await page.evaluate("""()=>({
      title: document.title,
      desc: (document.querySelector('.job-intro-container, .job-description, [class*="job-description"], [class*="job-intro"], .content, .job-detail')||{}).innerText || '',
      full: (document.body.innerText||'').slice(0,7000)
    })""")

async def detail_direct(ctx,jid):
    page=await ctx.new_page()
    try:
        await page.goto(f"https://www.liepin.com/job/{jid}.shtml",wait_until="domcontentloaded",timeout=40000,referer="https://www.liepin.com/zhaopin/?key=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9")
        await page.wait_for_timeout(3500)
        return await extract(page)
    except Exception as e:
        return {"error":str(e)}
    finally:
        await page.close()

asyncio.run(main())
