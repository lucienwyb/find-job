import asyncio, json, re
from playwright.async_api import async_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx=await b.new_context(user_agent=UA,proxy={"server":PROXY},viewport={"width":1366,"height":900},locale="zh-CN")
        await ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image","media","font") else r.continue_())
        page=await ctx.new_page()
        # jobui search for company 银河航天
        for url in [
            "https://www.jobui.com/jobs/?jobKw=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9",
            "https://www.jobui.com/company/%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9/",
            "https://www.jobui.com/sz/job/%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9/",
        ]:
            print("GET",url,flush=True)
            try:
                await page.goto(url,wait_until="domcontentloaded",timeout=35000)
            except Exception as e:
                print("  err",e,flush=True); continue
            await page.wait_for_timeout(4000)
            title=await page.title()
            print("  title:",title,flush=True)
            html=await page.content()
            slug=url.split("//")[1].split("/",2)[-1].replace("/","_")
            open(f"/pulp/find-job/out/jobui_{slug}.html","w",encoding="utf-8").write(html)
            txt=(await page.evaluate("document.body.innerText||''"))[:2500]
            print("  BODY:",txt.replace("\n"," | ")[:2000],flush=True)
        await b.close()
asyncio.run(main())
