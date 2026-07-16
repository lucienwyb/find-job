import asyncio, json, re
from playwright.async_api import async_playwright

PROXY="http://100.66.66.64:8765"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SEL='.job-list-box .job-card-wrap, .job-list-box li, [class*="job-card"], .list-item, .job-card-pc-container'

LIST_JS = """
() => {
  const out=[];
  document.querySelectorAll('""" + SEL + """').forEach(c => {
    const a = c.querySelector('a[href*="/job/"]');
    if (!a) return;
    const href = a.href.split('?')[0];
    const title = (a.innerText || '').trim().split('\\n')[0];
    const ctx = (c.innerText || '').replace(/\\n+/g, ' | ').slice(0, 300);
    out.push({href: href, title: title, ctx: ctx});
  });
  return out;
}
"""

DETAIL_JS = """
() => {
  const desc = document.querySelector('.job-intro-container, .job-description, .job-item-des, [class*="job-description"], [class*="job-intro"], .content, .job-detail');
  return {title: document.title, desc: desc ? desc.innerText : '', full: (document.body.innerText || '').slice(0, 6500)};
}
"""

def is_soft(title):
    if any(k in title for k in ["软件","嵌入式","FPGA","固件","算法","星载","飞行软件","测控","姿轨控","载荷","5G","通信","综合电子","onboard","RTOS","VxWorks"]):
        return True
    if any(k in title for k in ["开发工程师","程序","Linux","C++"]) and not any(n in title for n in ["HRBP","招聘","薪酬"]):
        return True
    return False

async def collect(ctx):
    page=await ctx.new_page()
    jobs={}
    for pg in range(0,4):
        url=f"https://www.liepin.com/zhaopin/?key=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9&curPage={pg}"
        print("LIST",pg,flush=True)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print("goto err",pg,e,flush=True); break
        try:
            await page.wait_for_selector(SEL, timeout=15000)
        except Exception:
            print("  no cards sel; dump html",flush=True)
            open(f"/pulp/find-job/out/lp_list_{pg}.html","w",encoding="utf-8").write(await page.content())
        await page.wait_for_timeout(3500)
        cards=await page.evaluate(LIST_JS)
        new=0
        for c in cards:
            m=re.search(r'/job/(\d+)',c['href']); jid=m.group(1) if m else c['href']
            if jid not in jobs:
                jobs[jid]={**c,'jid':jid}; new+=1
        print(f"  page{pg}: cards={len(cards)} new={new} total={len(jobs)}",flush=True)
        if new==0: break
    await page.close()
    return list(jobs.values())

async def detail(ctx,url):
    page=await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(3000)
        return await page.evaluate(DETAIL_JS)
    except Exception as e:
        return {"error":str(e)}
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx=await b.new_context(user_agent=UA,proxy={"server":PROXY},viewport={"width":1366,"height":900},locale="zh-CN")
        await ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image","media","font") else r.continue_())
        jobs=await collect(ctx)
        open("/pulp/find-job/out/liepin_jobs_all.json","w").write(json.dumps(jobs,ensure_ascii=False,indent=2))
        print("=== ALL TITLES ===",flush=True)
        for j in jobs: print(f"  {j['jid']}  {j['title']}",flush=True)
        soft=[j for j in jobs if is_soft(j['title'])]
        print(f"=== SOFTWARE-RELEVANT: {len(soft)} ===",flush=True)
        for j in soft: print("  SOFT",j['jid'],j['title'], j['href'],flush=True)
        results=[]
        for j in soft:
            print("DETAIL",j['jid'],j['title'],flush=True)
            d=await detail(ctx,j['href'])
            results.append({**j,"detail":d})
            await asyncio.sleep(1.2)
        open("/pulp/find-job/out/liepin_soft_details.json","w").write(json.dumps(results,ensure_ascii=False,indent=2))
        await b.close()

asyncio.run(main())
