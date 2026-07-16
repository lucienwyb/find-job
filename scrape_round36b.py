#!/usr/bin/env python3
"""Round 36b: Targeted scrapes for breakthroughs found."""
import sys, json, re, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

def launch():
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage","--disable-blink-features=AutomationControlled"], proxy={"server": PROXY})
    return p, b

def new_ctx(b):
    return b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN", ignore_https_errors=True)

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S|re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S|re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;"," ",txt); txt=re.sub(r"&amp;","&",txt); txt=re.sub(r"&[a-z]+;"," ",txt)
    return re.sub(r"\s+"," ",txt).strip()

def save(name, html):
    txt = clean(html)
    with open(f"/pulp/find-job/r36b_{name}.html","w") as f: f.write(html)
    with open(f"/pulp/find-job/r36b_{name}.txt","w") as f: f.write(txt[:80000])
    return txt

# ============================================================
# GALAXY AEROSPACE via mokahr — test 3 slugs
# ============================================================
def scrape_galaxy_moka():
    print("\n\n###### GALAXY via MOKAHR ######", flush=True)
    p, b = launch()
    ctx = new_ctx(b)

    for slug in ["galaxy-aerospace", "yinhehangtian", "galaxyspace"]:
        page = ctx.new_page()
        nc = []
        def on_resp(resp, nc=nc):
            try:
                ct = resp.headers.get('content-type','')
                url = resp.url
                if any(t in ct for t in ['json','text','javascript']):
                    body = resp.text()
                    if body and len(body) > 100:
                        nc.append({"url":url,"status":resp.status,"ct":ct[:30],"len":len(body),"body":body[:6000]})
            except: pass
        page.on("response", on_resp)

        url = f"https://app.mokahr.com/social-recruitment/{slug}"
        print(f"\n--- {slug} ---", flush=True)
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"  status={resp.status if resp else None}", flush=True)
            page.wait_for_timeout(10000)
            for _ in range(15):
                page.mouse.wheel(0,2000); page.wait_for_timeout(400)
            html = page.content()
            txt = save(f"galaxy_{slug}", html)
            print(f"  html={len(html)} txt={len(txt)}", flush=True)

            # Check if real content
            if any(k in txt for k in ['职位','岗位','工程师','招聘']):
                print(f"  *** REAL CONTENT ***", flush=True)
                # Print job-related text
                for kw in ['嵌入式','系统','Infra','驱动','内核','Linux','C++','架构','工程师','平台','后端','软件开发','算法']:
                    hits = re.findall(r'.{0,8}'+kw+r'.{0,30}', txt)
                    if hits: print(f"  [{kw}]: {hits[:3]}", flush=True)

                # Save API captures
                with open(f"/pulp/find-job/r36b_galaxy_{slug}_api.json","w") as f:
                    json.dump(nc, f, ensure_ascii=False, indent=2)
                # Show job API responses
                for c in nc:
                    if any(k in c['url'] for k in ['jobs','position','module','group']):
                        print(f"  API: {c['url'][:120]} len={c['len']}", flush=True)
                        if 'data' in c['body'][:200]:
                            print(f"    body: {c['body'][:500]}", flush=True)

                # Try clicking into job categories
                job_links = page.query_selector_all("a[href*='job'], a[href*='position'], div[class*='job']")
                print(f"  Found {len(job_links)} clickable job elements", flush=True)

                # Try to click 软件类 / 嵌入式
                for cat in ["软件类","软件","嵌入式","系统","驱动","开发"]:
                    try:
                        loc = page.locator(f"text={cat}").first
                        if loc.count() > 0:
                            loc.click(timeout=5000)
                            page.wait_for_timeout(5000)
                            html2 = page.content()
                            txt2 = clean(html2)
                            print(f"  After click '{cat}': txt_len={len(txt2)}", flush=True)
                            # Extract job names
                            texts = re.findall(r'>([^<]{4,80})<', html2)
                            jobs = [t.strip() for t in texts if any(k in t for k in ['工程师','开发','架构','系统','平台','嵌入式','驱动','C++','Linux','算法','前端','后端','测试','运维','安全','数据']) and '社会招聘' not in t and len(t.strip())>4]
                            if jobs:
                                print(f"  JOBS FOUND ({len(jobs)}): {jobs[:20]}", flush=True)
                            save(f"galaxy_{slug}_{cat}", html2)
                            break
                    except Exception as e:
                        print(f"  click '{cat}' err: {e}", flush=True)
                page.close()
                if any(k in txt for k in ['工程师','职位','银河航天']):
                    break  # Found the real one
            else:
                print(f"  No real job content, text preview: {txt[:300]}", flush=True)
                page.close()
        except Exception as e:
            print(f"  err: {e}", flush=True)
            page.close()

    ctx.close(); b.close(); p.stop()

# ============================================================
# GALBOT — click into 软件类 jobs, get individual JDs
# ============================================================
def scrape_galbot_deep():
    print("\n\n###### GALBOT DEEP ######", flush=True)
    p, b = launch()
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = []
    def on_resp(resp, nc=nc):
        try:
            ct = resp.headers.get('content-type','')
            url = resp.url
            if any(t in ct for t in ['json','text','javascript']):
                body = resp.text()
                if body and len(body) > 100:
                    nc.append({"url":url,"status":resp.status,"ct":ct[:30],"len":len(body),"body":body[:8000]})
        except: pass
    page.on("response", on_resp)

    url = "https://app.mokahr.com/social-recruitment/yinhetongyong/165929"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(10000)
        html = page.content()
        txt = clean(html)
        print(f"  initial: html={len(html)} txt={len(txt)}", flush=True)

        # Click 软件类 to see software jobs
        for cat in ["软件类","软件"]:
            try:
                loc = page.locator(f"text={cat}").first
                if loc.count() > 0:
                    loc.click(timeout=5000)
                    page.wait_for_timeout(8000)
                    html2 = page.content()
                    txt2 = clean(html2)
                    save(f"galbot_software", html2)
                    print(f"  After click '{cat}': txt={len(txt2)}", flush=True)
                    # Extract job names from rendered DOM
                    texts = re.findall(r'>([^<]{4,80})<', html2)
                    jobs = [t.strip() for t in texts if any(k in t for k in ['工程师','开发','架构','系统','平台','嵌入式','驱动','C++','C ','Linux','算法','前端','后端','测试','运维','安全','数据','专家','实习','技术','软件','产品','项目','经理']) and '银河通用' not in t and len(t.strip())>4]
                    if jobs:
                        print(f"  JOBS ({len(jobs)}): {jobs[:25]}", flush=True)
                    break
            except Exception as e:
                print(f"  click '{cat}' err: {e}", flush=True)

        # Try clicking individual job links
        links = page.query_selector_all("a[href]")
        job_links = []
        for l in links:
            href = l.get_attribute("href") or ""
            text = l.inner_text()[:80]
            if any(k in text for k in ['工程师','开发','架构','系统','平台','嵌入式','驱动','C++','Linux','算法','前端','后端','运维','安全','数据','软件']):
                job_links.append((href, text))
        print(f"  Found {len(job_links)} job links", flush=True)

        # Click into first few matching jobs to get JD
        for href, text in job_links[:5]:
            try:
                full = href if href.startswith("http") else f"https://app.mokahr.com{href}"
                print(f"\n  >>> Job: {text} -> {full}", flush=True)
                page.goto(full, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(6000)
                jhtml = page.content()
                jtxt = clean(jhtml)
                print(f"  JD html={len(jhtml)} txt={len(jtxt)}", flush=True)
                # Extract JD content
                for kw in ['职责','要求','任职','资格','技术','经验','学历','薪资','salary','k·','万','月薪','岗位描述','job']:
                    hits = re.findall(r'.{0,5}'+kw+r'.{0,60}', jtxt)
                    if hits: print(f"    [{kw}]: {hits[:2]}", flush=True)
                # Print relevant snippet
                idx = jtxt.find('职责')
                if idx < 0: idx = jtxt.find('要求')
                if idx >= 0:
                    print(f"    JD: {jtxt[idx:idx+500]}", flush=True)
                save(f"galbot_jd_{href.split('/')[-1][:20]}", jhtml)
                page.go_back(timeout=15000)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"    err: {e}", flush=True)

        # Save API captures
        with open("/pulp/find-job/r36b_galbot_api.json","w") as f:
            json.dump(nc, f, ensure_ascii=False, indent=2)
        for c in nc:
            if any(k in c['url'] for k in ['jobs','position','detail','module','group','job']):
                print(f"  API: {c['url'][:120]} len={c['len']}", flush=True)
    except Exception as e:
        print(f"  err: {e}", flush=True)

    ctx.close(); b.close(); p.stop()

# ============================================================
# 01.AI — careers.html
# ============================================================
def scrape_01ai_careers():
    print("\n\n###### 01.AI CAREERS ######", flush=True)
    p, b = launch()
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = []
    def on_resp(resp, nc=nc):
        try:
            ct = resp.headers.get('content-type','')
            url = resp.url
            if any(t in ct for t in ['json','text','javascript']):
                body = resp.text()
                if body and len(body) > 100:
                    nc.append({"url":url,"status":resp.status,"ct":ct[:30],"len":len(body),"body":body[:6000]})
        except: pass
    page.on("response", on_resp)

    url = "https://www.01.ai/careers.html"
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print(f"  status={resp.status if resp else None}", flush=True)
        page.wait_for_timeout(8000)
        for _ in range(10):
            page.mouse.wheel(0,1500); page.wait_for_timeout(500)
        html = page.content()
        txt = save("01ai_careers", html)
        print(f"  html={len(html)} txt={len(txt)}", flush=True)

        if any(k in txt for k in ['职位','岗位','工程师','招聘','Job']):
            print(f"  *** REAL CONTENT ***", flush=True)
            print(txt[:2000], flush=True)
            for kw in ['系统','Infra','基础设施','后端','Agent','平台','架构','嵌入式','驱动','C++','Linux','算法','前端','全栈','安全','运维','工程师','架构师']:
                hits = re.findall(r'.{0,10}'+kw+r'.{0,30}', txt)
                if hits: print(f"  [{kw}]: {hits[:3]}", flush=True)
            # Extract job names
            texts = re.findall(r'>([^<]{4,80})<', html)
            jobs = [t.strip() for t in texts if any(k in t for k in ['工程师','开发','架构','系统','平台','Agent','算法','前端','后端','运维','安全','数据','产品','经理']) and len(t.strip())>4]
            if jobs: print(f"  JOBS ({len(jobs)}): {jobs[:20]}", flush=True)
            # Look for feishu hire links
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
            feishu = [h for h in hrefs if any(k in h.lower() for k in ['feishu','hire','job','moka','apply'])]
            if feishu: print(f"  Feishu/Hire links: {feishu[:5]}", flush=True)
        else:
            print(f"  No job content. txt preview: {txt[:500]}", flush=True)

        with open("/pulp/find-job/r36b_01ai_api.json","w") as f:
            json.dump(nc, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  err: {e}", flush=True)
    ctx.close(); b.close(); p.stop()

# ============================================================
# HORIZON — mokahr with correct slug
# ============================================================
def scrape_horizon_moka():
    print("\n\n###### HORIZON via MOKAHR ######", flush=True)
    p, b = launch()
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = []
    def on_resp(resp, nc=nc):
        try:
            ct = resp.headers.get('content-type','')
            url = resp.url
            if any(t in ct for t in ['json','text','javascript']):
                body = resp.text()
                if body and len(body) > 100:
                    nc.append({"url":url,"status":resp.status,"ct":ct[:30],"len":len(body),"body":body[:6000]})
        except: pass
    page.on("response", on_resp)

    # Try multiple slugs
    for slug in ["horizon-robotics", "horizonrobotics", "horizon", "horizonroboticsinc"]:
        url = f"https://app.mokahr.com/social-recruitment/{slug}"
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
            print(f"\n  {slug}: status={resp.status if resp else None}", flush=True)
            page.wait_for_timeout(8000)
            html = page.content()
            txt = clean(html)
            print(f"  html={len(html)} txt={len(txt)}", flush=True)
            if any(k in txt for k in ['职位','岗位','工程师','地平线','Horizon']):
                print(f"  *** REAL CONTENT ***", flush=True)
                save(f"horizon_{slug}", html)
                for kw in ['系统','Infra','嵌入式','驱动','内核','Linux','C++','架构','工程师','平台','后端','算法','BSP','底层','自动驾驶','智能']:
                    hits = re.findall(r'.{0,8}'+kw+r'.{0,30}', txt)
                    if hits: print(f"  [{kw}]: {hits[:3]}", flush=True)
                # Extract job names
                texts = re.findall(r'>([^<]{4,80})<', html)
                jobs = [t.strip() for t in texts if any(k in t for k in ['工程师','开发','架构','系统','平台','嵌入式','驱动','C++','Linux','算法','前端','后端','测试','运维','安全','数据','BSP']) and len(t.strip())>4]
                if jobs: print(f"  JOBS ({len(jobs)}): {jobs[:20]}", flush=True)

                with open(f"/pulp/find-job/r36b_horizon_api.json","w") as f:
                    json.dump(nc, f, ensure_ascii=False, indent=2)
                for c in nc:
                    if any(k in c['url'] for k in ['jobs','position','module','group','detail']):
                        print(f"  API: {c['url'][:120]} len={c['len']}", flush=True)
                break
            else:
                print(f"  txt preview: {txt[:200]}", flush=True)
        except Exception as e:
            print(f"  {slug} err: {e}", flush=True)

    ctx.close(); b.close(); p.stop()

# ============================================================
# MOONSHOT — try to interact with careers page
# ============================================================
def scrape_moonshot_deep():
    print("\n\n###### MOONSHOT DEEP ######", flush=True)
    p, b = launch()
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = []
    def on_resp(resp, nc=nc):
        try:
            ct = resp.headers.get('content-type','')
            url = resp.url
            if any(t in ct for t in ['json','text','javascript','x-componen']):
                body = resp.text()
                if body and len(body) > 50:
                    nc.append({"url":url,"status":resp.status,"ct":ct[:30],"len":len(body),"body":body[:8000]})
        except: pass
    page.on("response", on_resp)

    # The careers.kimi.com/social page shows a landing page
    # Try to find the actual job board URL
    url = "https://careers.kimi.com/social"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(10000)

        # Look for all links and buttons
        html = page.content()
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
        print(f"  All hrefs: {[h for h in hrefs if not h.startswith('/careers-assets')][:20]}", flush=True)

        # Try clicking "社会招聘" or "Social Recruitment"
        for txt_btn in ["社会招聘","Social Recruitment","Social","社招"]:
            try:
                loc = page.locator(f"text={txt_btn}").first
                if loc.count() > 0:
                    loc.click(timeout=5000)
                    page.wait_for_timeout(8000)
                    html2 = page.content()
                    txt2 = clean(html2)
                    print(f"  After click '{txt_btn}': url={page.url} txt={len(txt2)}", flush=True)
                    if any(k in txt2 for k in ['工程师','职位','岗位']):
                        print(f"  *** GOT JOBS ***", flush=True)
                        print(txt2[:2000], flush=True)
                        save("moonshot_social", html2)
                    break
            except: pass

        # Also try the mokahr portal
        for slug in ["moonshot", "moonshot-ai", "kimi"]:
            try:
                murl = f"https://app.mokahr.com/social-recruitment/{slug}"
                resp = page.goto(murl, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(8000)
                mhtml = page.content()
                mtxt = clean(mhtml)
                print(f"\n  mokahr/{slug}: status={resp.status if resp else None} txt={len(mtxt)}", flush=True)
                if any(k in mtxt for k in ['职位','岗位','工程师','月之暗面','Moonshot']):
                    print(f"  *** MOKAHR REAL CONTENT ***", flush=True)
                    save(f"moonshot_moka_{slug}", mhtml)
                    for kw in ['系统','Infra','后端','Agent','平台','架构','C++','Linux','算法','工程师','前端','运维','数据']:
                        hits = re.findall(r'.{0,8}'+kw+r'.{0,30}', mtxt)
                        if hits: print(f"  [{kw}]: {hits[:3]}", flush=True)
                    # Job names
                    texts = re.findall(r'>([^<]{4,80})<', mhtml)
                    jobs = [t.strip() for t in texts if any(k in t for k in ['工程师','开发','架构','系统','平台','Agent','算法','前端','后端','运维','安全','数据']) and len(t.strip())>4]
                    if jobs: print(f"  JOBS ({len(jobs)}): {jobs[:20]}", flush=True)
                    break
            except: pass

        with open("/pulp/find-job/r36b_moonshot_api.json","w") as f:
            json.dump(nc, f, ensure_ascii=False, indent=2)
        # Show RSC responses
        for c in nc:
            if 'x-componen' in c['ct'] or '_rsc' in c['url']:
                print(f"  RSC: {c['url'][:100]} len={c['len']} body={c['body'][:300]}", flush=True)
    except Exception as e:
        print(f"  err: {e}", flush=True)
    ctx.close(); b.close(); p.stop()

# ============================================================
# QIANSHENG — search for correct domain
# ============================================================
def scrape_qiansheng_search():
    print("\n\n###### QIANSHENG SEARCH ######", flush=True)
    p, b = launch()
    ctx = new_ctx(b)
    page = ctx.new_page()

    # Try multiple possible domains and mokahr
    urls = [
        "https://app.mokahr.com/social-recruitment/qiansheng-exploration",
        "https://app.mokahr.com/social-recruitment/qianshangaerospace",
        "https://app.mokahr.com/social-recruitment/qian-ao",
        "https://app.mokahr.com/social-recruitment/qiansheng-explorer",
        "https://app.mokahr.com/social-recruitment/beijingqiansheng",
        "https://www.qian-ao.com",
        "https://www.qian-ao.com/careers",
        "https://www.qianao.com",
        "https://qiansheng.aero",
    ]
    for u in urls:
        try:
            resp = page.goto(u, wait_until="domcontentloaded", timeout=15000)
            status = resp.status if resp else None
            page.wait_for_timeout(4000)
            html = page.content()
            txt = clean(html)
            print(f"  {u}: status={status} txt={len(txt)}", flush=True)
            if any(k in txt for k in ['职位','岗位','工程师','千乘','招聘']):
                print(f"  *** REAL CONTENT ***", flush=True)
                save("qiansheng_found", html)
                print(txt[:1000], flush=True)
                break
            elif len(txt) > 100:
                print(f"  preview: {txt[:200]}", flush=True)
        except Exception as e:
            print(f"  {u}: err={str(e)[:80]}", flush=True)

    ctx.close(); b.close(); p.stop()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all","galaxy"): scrape_galaxy_moka()
    if mode in ("all","galbot"): scrape_galbot_deep()
    if mode in ("all","01ai"): scrape_01ai_careers()
    if mode in ("all","horizon"): scrape_horizon_moka()
    if mode in ("all","moonshot"): scrape_moonshot_deep()
    if mode in ("all","qiansheng"): scrape_qiansheng_search()
    print("\n\nDONE ROUND36b", flush=True)
