import asyncio, json, re, sys
from playwright.async_api import async_playwright

PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = await b.new_context(user_agent=UA, proxy={"server":PROXY}, viewport={"width":1366,"height":900}, locale="zh-CN")
        # block images/fonts/media for speed
        await ctx.route("**/*", lambda route: route.abort() if route.request.resource_type in ("image","media","font") else route.continue_())
        page = await ctx.new_page()
        url="https://www.liepin.com/zhaopin/?key=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9&imscid=R3"
        print("GET",url, flush=True)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            print("goto err",e, flush=True)
        await page.wait_for_timeout(6000)
        html=await page.content()
        open("/pulp/find-job/out/liepin_rendered.html","w",encoding="utf-8").write(html)
        # extract job cards
        jobs = await page.evaluate("""() => {
          const out=[];
          const cards = document.querySelectorAll('.job-list-box .job-card-wrap, .job-list-box li, [class*="job-card"], .list-item');
          cards.forEach(c=>{
            const txt=c.innerText||'';
            const a=c.querySelector('a[href*="/job/"], a[href*="liepin.com/job"]');
            out.push({text:txt.slice(0,400), href: a?a.href:''});
          });
          return out;
        }""")
        print("cards found:",len(jobs), flush=True)
        for j in jobs[:40]:
            print(json.dumps(j,ensure_ascii=False), flush=True)
        await b.close()

asyncio.run(main())
