import asyncio, json, re
from playwright.async_api import async_playwright
PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SEL='.job-list-box .job-card-wrap, .job-list-box li, [class*="job-card"], .list-item'
LIST_JS="""()=>{const out=[];document.querySelectorAll('"""+SEL+"""').forEach(c=>{const a=c.querySelector('a[href*="/job/"]');if(!a)return;const h=a.href.split('?')[0];const t=(a.innerText||'').trim().split('\\n')[0];const compEl=c.querySelector('a[href*="/company/"]');const comp=compEl?compEl.innerText:'';const compHref=compEl?compEl.href:'';out.push({href:h,title:t,comp:comp,compHref:compHref,ctx:(c.innerText||'').replace(/\\n+/g,' | ').slice(0,260)});});return out;}"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx=await b.new_context(user_agent=UA,proxy={"server":PROXY},viewport={"width":1366,"height":900},locale="zh-CN")
        await ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image","media","font") else r.continue_())
        page=await ctx.new_page()
        await page.goto("https://www.liepin.com/zhaopin/?key=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9&curPage=0",wait_until="domcontentloaded",timeout=45000)
        await page.wait_for_timeout(6500)
        title=await page.title()
        print("page title:",title,flush=True)
        cards=await page.evaluate(LIST_JS)
        print("cards:",len(cards),flush=True)
        # company page
        comp_href=None
        for c in cards:
            if c.get("compHref"): comp_href=c["compHref"]; break
        print("company page:",comp_href,flush=True)
        # dedup titles
        seen={}
        for c in cards:
            m=re.search(r'/job/(\d+)',c["href"]); jid=m.group(1) if m else c["href"]
            seen[jid]=c
        soft_kw=["软件","嵌入式","FPGA","星载","飞行","测控","姿轨控","载荷","5G","通信","综合电子","算法","RTOS","VxWorks","Linux","C++","固件","onboard","开发"]
        print("=== ALL JOBS ===",flush=True)
        for jid,c in seen.items():
            flag=" <== SOFT" if any(k in c["title"] for k in soft_kw) else ""
            print(f"  {jid} | {c['title']} | comp={c.get('comp','')} | {c.get('compHref','')}{flag}",flush=True)
        # try company page for full list
        if comp_href:
            print("FETCH company page:",comp_href,flush=True)
            p2=await ctx.new_page()
            try:
                await p2.goto(comp_href,wait_until="domcontentloaded",timeout=35000)
                await p2.wait_for_timeout(4000)
                print("  company title:",await p2.title(),flush=True)
                ccards=await p2.evaluate(LIST_JS)
                print("  company-page cards:",len(ccards),flush=True)
                for c in ccards[:10]: print("   ",c["title"],c["href"],flush=True)
            except Exception as e:
                print("  company err",e,flush=True)
            await p2.close()
        await b.close()
asyncio.run(main())
