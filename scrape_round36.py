#!/usr/bin/env python3
"""Round 36: Capture XHR/fetch JSON APIs from 8 recruitment SPA portals.
Key insight: these SPAs load jobs via API calls, not SSR. We capture network responses.
For galaxy.zhiye.com.cn: try WITHOUT proxy (domestic Chinese site, proxy was failing).
"""
import sys, json, re, time, urllib.parse
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

def launch(use_proxy=True):
    p = sync_playwright().start()
    args = ["--no-sandbox","--disable-dev-shm-usage","--disable-blink-features=AutomationControlled"]
    kwargs = {"headless": True, "args": args}
    if use_proxy:
        kwargs["proxy"] = {"server": PROXY}
    b = p.chromium.launch(**kwargs)
    return p, b

def new_ctx(b):
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width":1366,"height":1000}, locale="zh-CN",
        ignore_https_errors=True)
    return ctx

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S|re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S|re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;"," ",txt); txt=re.sub(r"&amp;","&",txt); txt=re.sub(r"&[a-z]+;"," ",txt)
    return re.sub(r"\s+"," ",txt).strip()

class NetCapture:
    """Captures all XHR/fetch responses with JSON or substantial text bodies."""
    def __init__(self):
        self.caps = []
    def on_response(self, resp):
        try:
            ct = resp.headers.get('content-type','')
            url = resp.url
            # Capture JSON, text, and javascript responses that look like data
            if any(t in ct for t in ['json','text','javascript','xml']):
                body = resp.text()
                if body and len(body) > 50:
                    # Filter for interesting responses
                    interesting = any(k in url.lower() for k in [
                        'job','position','list','search','api','social','tech','recruit',
                        'talent','hire','career','opening','vacancy','department','category',
                        'mokahr','zhiye','beisen','feishu','horizon','galaxy','moonshot',
                        'robotera','01ai','qiansheng','galbot','zhipu','necromancer'
                    ])
                    has_job_data = any(k in body[:3000] for k in [
                        '职位','岗位','工程师','招聘','Job Title','position_name',
                        'job_name','department','salary','薪资','月薪','k·','responsibility',
                        'requirement','qualification','jobList','positionList','job_list'
                    ])
                    if interesting or has_job_data or len(body) > 2000:
                        self.caps.append({
                            "url": url, "status": resp.status,
                            "ct": ct[:40], "len": len(body),
                            "body": body[:8000]
                        })
        except Exception:
            pass

def save_caps(name, caps):
    with open(f"/pulp/find-job/r36_{name}_api.json","w") as f:
        json.dump(caps, f, ensure_ascii=False, indent=2)
    # Print summary
    print(f"\n[{name}] captured {len(caps)} interesting responses:", flush=True)
    for c in caps:
        print(f"  {c['status']} {c['url'][:140]} ct={c['ct'][:15]} len={c['len']}", flush=True)
        # Show snippet if it looks like job data
        b = c['body']
        if any(k in b[:2000] for k in ['职位','岗位','工程师','jobList','positionList','job_name','salary','薪资']):
            print(f"    >>> JOB DATA: {b[:600]}", flush=True)

def scrape_page(page, nc, url, name, wait_ms=10000, scroll=True, click_texts=None):
    """Navigate, capture network, scroll, optionally click, save HTML."""
    print(f"\n{'='*60}\n[{name}] {url}\n{'='*60}", flush=True)
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else None
        print(f"  status={status}", flush=True)
    except Exception as e:
        print(f"  goto err: {e}", flush=True)
        return None, None

    page.wait_for_timeout(wait_ms)

    # Click specified texts
    if click_texts:
        for txt in click_texts:
            for sel in [f"text={txt}", f"a:has-text('{txt}')", f"div:has-text('{txt}')", f"span:has-text('{txt}')"]:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0:
                        loc.click(timeout=4000)
                        print(f"  clicked '{txt}' via {sel}", flush=True)
                        page.wait_for_timeout(5000)
                        break
                except Exception:
                    pass

    # Scroll to trigger lazy loading
    if scroll:
        for _ in range(20):
            try:
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(400)
            except Exception:
                break

    html = page.content()
    txt = clean(html)
    with open(f"/pulp/find-job/r36_{name}.html","w") as f: f.write(html)
    with open(f"/pulp/find-job/r36_{name}.txt","w") as f: f.write(txt[:60000])
    print(f"  html={len(html)} txt={len(txt)} url={page.url}", flush=True)

    # Keyword search
    keywords = ['嵌入式','系统','Infra','基础设施','后端','内核','Agent','平台','底层','架构',
                '驱动','C++','编译','Runtime','SRE','基础架构','架构师','Linux','eBPF','云计算',
                '机器人','具身','算法','前端','全栈','安全','运维','测试','simulator','仿真']
    for kw in keywords:
        hits = re.findall(r'.{0,10}'+kw+r'.{0,25}', txt)
        if hits:
            print(f"  [{kw}]: {hits[:2]}", flush=True)

    return html, txt

# ============================================================
# 1. GALAXY AEROSPACE — zhiye.com.cn (try WITHOUT proxy first)
# ============================================================
def scrape_galaxy():
    print("\n\n###### GALAXY AEROSPACE ######", flush=True)
    # Try without proxy (domestic site)
    p, b = launch(use_proxy=False)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    urls = [
        "https://galaxy.zhiye.com.cn/",
        "https://galaxy.zhiye.com.cn/social",
        "https://galaxy.zhiye.com.cn/social/jobs",
        "https://galaxy.zhiye.com.cn/zp",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "galaxy", wait_ms=8000)
        if html and len(html) > 500:
            # Check if we got real content
            if any(k in txt for k in ['职位','岗位','工程师','招聘']):
                print(f"  *** GOT REAL CONTENT from {u} ***", flush=True)
                break
    save_caps("galaxy", nc.caps)
    ctx.close(); b.close(); p.stop()

    # If direct failed, try with proxy
    if not nc.caps or all(c['len'] < 200 for c in nc.caps):
        print("\n  Direct failed, trying with proxy...", flush=True)
        p, b = launch(use_proxy=True)
        ctx = new_ctx(b)
        page = ctx.new_page()
        nc2 = NetCapture()
        page.on("response", nc2.on_response)
        for u in urls[:2]:
            scrape_page(page, nc2, u, "galaxy_proxy", wait_ms=8000)
        save_caps("galaxy_proxy", nc2.caps)
        ctx.close(); b.close(); p.stop()

# ============================================================
# 2. MOONSHOT — careers.kimi.com (Next.js, capture API routes)
# ============================================================
def scrape_moonshot():
    print("\n\n###### MOONSHOT / KIMI ######", flush=True)
    p, b = launch(use_proxy=True)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    urls = [
        "https://careers.kimi.com/social",
        "https://careers.kimi.com/social?category=tech",
        "https://careers.kimi.com/jobs",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "moonshot", wait_ms=10000,
                                click_texts=["技术类","技术","工程师"])
        if txt and any(k in txt for k in ['工程师','职位','岗位']):
            print(f"  *** GOT REAL CONTENT ***", flush=True)
            break

    # Try clicking through to individual job pages
    try:
        links = page.query_selector_all("a[href]")
        job_links = []
        for l in links[:100]:
            href = l.get_attribute("href") or ""
            text = l.inner_text()[:60]
            if any(k in text for k in ['工程师','架构','开发','Agent','Infra','系统','平台','后端']):
                job_links.append((href, text))
        print(f"  Found {len(job_links)} job-like links", flush=True)
        for href, text in job_links[:3]:
            full = href if href.startswith("http") else f"https://careers.kimi.com{href}"
            print(f"  Trying job: {text} -> {full}", flush=True)
            scrape_page(page, nc, full, f"moonshot_job", wait_ms=6000, scroll=False)
    except Exception as e:
        print(f"  job link err: {e}", flush=True)

    save_caps("moonshot", nc.caps)
    ctx.close(); b.close(); p.stop()

# ============================================================
# 3. HORIZON — find careers page
# ============================================================
def scrape_horizon():
    print("\n\n###### HORIZON ROBOTICS ######", flush=True)
    p, b = launch(use_proxy=True)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    # Try multiple possible career URLs
    urls = [
        "https://horizon.cc/careers",
        "https://horizon.cc/join",
        "https://horizon.cc/recruitment",
        "https://www.horizon.auto/careers",
        "https://www.horizon.auto/join-us",
        "https://app.mokahr.com/social-recruitment/horizonrobotics",
        "https://app.mokahr.com/campus-recruitment/horizonrobotics",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "horizon", wait_ms=8000)
        if txt and any(k in txt for k in ['职位','岗位','工程师','招聘','Job']):
            print(f"  *** GOT REAL CONTENT from {u} ***", flush=True)
            break

    save_caps("horizon", nc.caps)
    ctx.close(); b.close(); p.stop()

# ============================================================
# 4. ROBOTERA — find jobs API
# ============================================================
def scrape_robotera():
    print("\n\n###### ROBOT ERA ######", flush=True)
    p, b = launch(use_proxy=True)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    urls = [
        "https://www.robotera.com/#/about/join",
        "https://www.robotera.com/#/join",
        "https://www.robotera.com/#/career",
        "https://www.robotera.com/#/recruit",
        "https://app.mokahr.com/social-recruitment/robotera",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "robotera", wait_ms=10000,
                                click_texts=["社会招聘","社招","加入我们","招聘"])
        if txt and any(k in txt for k in ['职位','岗位','工程师','招聘','Job']):
            print(f"  *** GOT REAL CONTENT from {u} ***", flush=True)
            break

    save_caps("robotera", nc.caps)
    ctx.close(); b.close(); p.stop()

# ============================================================
# 5. 01AI — find careers / feishu hire
# ============================================================
def scrape_01ai():
    print("\n\n###### 01.AI ######", flush=True)
    p, b = launch(use_proxy=True)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    urls = [
        "https://www.01.ai/join",
        "https://www.01.ai/join-us",
        "https://www.01.ai/careers",
        "https://www.01.ai/about",
        # Feishu Hire portals
        "https://01ai.feishu.cn/hire",
        "https://app.feishu.cn/hire/01ai",
        "https://job.toutiao.com/01ai",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "01ai", wait_ms=8000)
        if txt and any(k in txt for k in ['职位','岗位','工程师','招聘','Job']):
            print(f"  *** GOT REAL CONTENT from {u} ***", flush=True)
            # Try to find career links in the page
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
            career_hrefs = [h for h in hrefs if any(k in h.lower() for k in ['join','career','recruit','hire','job','moka'])]
            if career_hrefs:
                print(f"  Career links found: {career_hrefs[:5]}", flush=True)
                for ch in career_hrefs[:2]:
                    full = ch if ch.startswith("http") else f"https://www.01.ai{ch}"
                    scrape_page(page, nc, full, "01ai_career", wait_ms=8000)
            break

    save_caps("01ai", nc.caps)
    ctx.close(); b.close(); p.stop()

# ============================================================
# 6. ZHIPU — mokahr (capture necromancer)
# ============================================================
def scrape_zhipu():
    print("\n\n###### ZHIPU ######", flush=True)
    p, b = launch(use_proxy=True)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    urls = [
        "https://app.mokahr.com/social-recruitment/zhipu",
        "https://app.mokahr.com/social-recruitment/zhipu/1867",
        "https://www.zhipuai.cn/zh/joinus",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "zhipu", wait_ms=10000,
                                click_texts=["算法/研发","研发","技术","社招"])
        if txt and any(k in txt for k in ['职位','岗位','工程师','jobList']):
            print(f"  *** GOT REAL CONTENT from {u} ***", flush=True)
            break

    save_caps("zhipu", nc.caps)
    ctx.close(); b.close(); p.stop()

# ============================================================
# 7. GALBOT — mokahr
# ============================================================
def scrape_galbot():
    print("\n\n###### GALBOT ######", flush=True)
    p, b = launch(use_proxy=True)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    urls = [
        "https://app.mokahr.com/social-recruitment/yinhetongyong/165929",
        "https://app.mokahr.com/social-recruitment/yinhetongyong",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "galbot", wait_ms=10000)
        if txt and any(k in txt for k in ['职位','岗位','工程师','jobList']):
            print(f"  *** GOT REAL CONTENT from {u} ***", flush=True)
            break

    save_caps("galbot", nc.caps)
    ctx.close(); b.close(); p.stop()

# ============================================================
# 8. QIANSHENG — official site
# ============================================================
def scrape_qiansheng():
    print("\n\n###### QIANSHENG ######", flush=True)
    p, b = launch(use_proxy=True)
    ctx = new_ctx(b)
    page = ctx.new_page()
    nc = NetCapture()
    page.on("response", nc.on_response)

    urls = [
        "https://www.qiansheng.com",
        "https://www.qiansheng.cn",
        "https://www.qianshangaerospace.com",
        "https://app.mokahr.com/social-recruitment/qiansheng",
        "https://galaxy.zhiye.com.cn/qiansheng",
    ]
    for u in urls:
        html, txt = scrape_page(page, nc, u, "qiansheng", wait_ms=8000,
                                click_texts=["加入我们","招聘","社招","社会招聘"])
        if txt and any(k in txt for k in ['职位','岗位','工程师','招聘']):
            print(f"  *** GOT REAL CONTENT from {u} ***", flush=True)
            break

    save_caps("qiansheng", nc.caps)
    ctx.close(); b.close(); p.stop()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all","galaxy"): scrape_galaxy()
    if mode in ("all","moonshot"): scrape_moonshot()
    if mode in ("all","horizon"): scrape_horizon()
    if mode in ("all","robotera"): scrape_robotera()
    if mode in ("all","01ai"): scrape_01ai()
    if mode in ("all","zhipu"): scrape_zhipu()
    if mode in ("all","galbot"): scrape_galbot()
    if mode in ("all","qiansheng"): scrape_qiansheng()
    print("\n\nDONE ROUND36", flush=True)
