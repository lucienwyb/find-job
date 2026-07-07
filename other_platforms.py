import asyncio, json, re
from playwright.async_api import async_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

async def fetch(ctx, url, wait=5500, label=""):
    page=await ctx.new_page()
    try:
        await page.goto(url,wait_until="domcontentloaded",timeout=40000)
        await page.wait_for_timeout(wait)
        title=await page.title()
        body=await page.evaluate("document.body.innerText||''")
        html=await page.content()
        print(f"== {label} ==",flush=True)
        print("  url:",url,flush=True)
        print("  title:",title,flush=True)
        # detect captcha / anti-bot
        low=body[:200]
        print("  head:",low.replace("\n"," | "),flush=True)
        open(f"/pulp/find-job/out/{label}.html","w",encoding="utf-8").write(html)
        return page,title,body
    except Exception as e:
        print("  err",e,flush=True)
        await page.close()
        return None,"",""

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx=await b.new_context(user_agent=UA,proxy={"server":PROXY},viewport={"width":1366,"height":900},locale="zh-CN")
        await ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image","media","font") else r.continue_())
        # 1. BOSS直聘 search
        await fetch(ctx,"https://www.zhipin.com/web/geek/job?query=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9&city=101010100",label="zhipin_search")
        await asyncio.sleep(1.5)
        # 2. kanzhun search
        await fetch(ctx,"https://www.kanzhun.com/search/?query=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9&type=company",label="kanzhun_search")
        await asyncio.sleep(1.5)
        # 3. kanzhun company search alt
        await fetch(ctx,"https://www.kanzhun.com/s/?q=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9",label="kanzhun_s")
        await b.close()
asyncio.run(main())
