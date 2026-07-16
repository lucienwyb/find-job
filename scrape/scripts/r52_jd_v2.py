#!/usr/bin/env python3
"""Round 52 v2: Capture JD for remaining high-match jobs.
Cambricon: 高性能通信库研发工程师, AI网络研发工程师, 芯片应用工程师-固件方向
  (also retry 高性能计算库研发工程师, 高性能算法库工程师 - may be on later pages)
Zhipu: Agent Infra 开发工程师, 推理Infra工程师, 训练Infra工程师, Agent Infra 运维开发工程师

Strategy: locate job card elements by CSS class, click the matching one.
Cambricon job cards: class contains "item-" inside ".jobs-".
Zhipu: different portal layout.
"""
import sys, json, re, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT = "/pulp/find-job/scrape/data"

def launch(p):
    return p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled", "--disable-gpu"],
        proxy={"server": PROXY})

def new_ctx(b):
    return b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 1100}, locale="zh-CN",
        ignore_https_errors=True)

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt); txt = re.sub(r"&amp;", "&", txt)
    return re.sub(r"\s+", " ", txt).replace("&", "&").strip()


def click_job_by_text(page, title, item_selector):
    """Click a job card whose innerText contains `title`.
    item_selector: CSS selector for job card elements."""
    try:
        items = page.locator(item_selector)
        n = items.count()
        for i in range(n):
            try:
                inner = items.nth(i).inner_text(timeout=1500)
            except:
                continue
            if title in inner or title.replace(" ","") in inner.replace(" ",""):
                # found it
                items.nth(i).scroll_into_view_if_needed(timeout=3000)
                page.wait_for_timeout(400)
                items.nth(i).click(timeout=5000)
                page.wait_for_timeout(5000)
                return True
        return False
    except Exception as e:
        print(f"      click err: {e}", flush=True)
        return False


def capture_current_jd(page, title):
    """After a click opened detail, capture the JD text."""
    html = page.content()
    txt = clean(html)
    # Extract duty + requirement
    duty = ""; req = ""
    # duty
    for pat in [r'(岗位职责[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)',
                r'(工作职责[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)',
                r'(职位描述[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|分享|收藏)',
                r'(\【工作职责\】[\s\S]{20,2500}?)(?:任职要求|任职资格|岗位要求|职位要求|加分项|申请职位|公司信息|\【)']:
        m = re.search(pat, txt)
        if m: duty = m.group(1).strip(); break
    # requirement
    for pat in [r'(任职要求[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|岗位职责|工作职责|职位描述|$)',
                r'(任职资格[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|岗位职责|工作职责|职位描述|$)',
                r'(岗位要求[\s\S]{15,2500}?)(?:加分项|申请职位|公司信息|分享|收藏|岗位职责|工作职责|职位描述|$)']:
        m = re.search(pat, txt)
        if m: req = m.group(1).strip(); break
    # bonus
    bonus = ""
    bm = re.search(r'(加分项[\s\S]{10,1500}?)(?:申请职位|公司信息|分享|收藏|最新职位|更多|京公网)', txt)
    if bm: bonus = bm.group(1).strip()
    # team intro
    team = ""
    tm = re.search(r'(\【团队介绍\】[\s\S]{10,1500}?)(?:\【工作职责\】|\【岗位职责\】|工作职责|岗位职责)', txt)
    if tm: team = tm.group(1).strip()
    return {"duty": duty, "requirement": req, "bonus": bonus, "team": team,
            "txt": txt, "txt_len": len(txt)}


def scrape_cambricon():
    print("\n###### Cambricon v2 ######", flush=True)
    targets = ["高性能通信库研发工程师", "AI网络研发工程师", "芯片应用工程师-固件方向",
               "高性能计算库研发工程师", "高性能算法库工程师"]
    results = []
    with sync_playwright() as p:
        b = launch(p); ctx = new_ctx(b); page = ctx.new_page()
        page.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(18000)
        # job card selector: mokahr apply portal uses class containing "item-"
        # Try a few selectors
        for sel in ['[class*="item-1VApSE59s2"]', '[class*="job-111nXxBXHx"]', '.jobs-W8moAs8f06 > div', '[class*="item-"]']:
            cnt = page.locator(sel).count()
            print(f"  selector {sel}: {cnt} items", flush=True)
            if cnt > 3: break
        item_sel = sel

        # Need to load all jobs - click "查看更多职位" or paginate
        # First scroll the job list area
        for i in range(6):
            page.mouse.wheel(0, 3000); page.wait_for_timeout(800)
        # check if "查看更多职位" / "下一页" exists
        for btn_text in ["查看更多职位", "下一页", ">", "›"]:
            try:
                loc = page.locator(f"text={btn_text}").first
                if loc.count() > 0:
                    loc.click(timeout=3000); page.wait_for_timeout(4000)
                    print(f"  clicked '{btn_text}'", flush=True)
            except: pass

        # Try clicking each target on page 1, then paginate to page 2,3...
        for target in targets:
            print(f"\n  >> {target}", flush=True)
            found = False
            for pg in range(1, 6):
                # try click on current page
                ok = click_job_by_text(page, target, item_sel)
                if ok:
                    jd = capture_current_jd(page, target)
                    jd["target"] = target; jd["page_found"] = pg; jd["clicked"] = True
                    print(f"     found on page {pg}: duty={len(jd['duty'])} req={len(jd['requirement'])} bonus={len(jd['bonus'])}", flush=True)
                    results.append(jd)
                    safe = re.sub(r'[^\w一-鿿]','_', target)[:30]
                    with open(f"{OUT}/cambricon_r52_jd_{safe}.txt","w") as f: f.write(jd["txt"])
                    found = True
                    # go back to list
                    try:
                        back = page.locator("text=返回职位列表").first
                        if back.count()>0: back.click(timeout=3000); page.wait_for_timeout(3000)
                    except: pass
                    break
                else:
                    # paginate to next
                    try:
                        nxt = page.locator(f"text={pg+1}").first
                        if nxt.count() > 0:
                            nxt.click(timeout=3000); page.wait_for_timeout(4000)
                            print(f"     -> page {pg+1}", flush=True)
                        else:
                            break
                    except: break
            if not found:
                print(f"     NOT FOUND in any page", flush=True)
                results.append({"target": target, "clicked": False, "found": False})
                # reload page1
                try:
                    pg1 = page.locator("text=1").first
                    if pg1.count()>0: pg1.click(timeout=2000); page.wait_for_timeout(3000)
                except: pass

        ctx.close(); b.close()
    with open(f"{OUT}/cambricon_r52_jd_v2.json","w") as f:
        json.dump({"company":"Cambricon","scrapeDate":"2026-07-16","targets":results}, f, ensure_ascii=False, indent=2)
    return results


def scrape_zhipu():
    print("\n###### Zhipu v2 ######", flush=True)
    targets = ["Agent Infra 开发工程师", "推理Infra工程师", "训练Infra工程师", "Agent Infra 运维开发工程师"]
    results = []
    with sync_playwright() as p:
        b = launch(p); ctx = new_ctx(b); page = ctx.new_page()
        page.goto("https://app.mokahr.com/social-recruitment/zphz/148983", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(20000)
        html = page.content(); txt = clean(html)
        print(f"  Initial txt={len(txt)}", flush=True)

        # Zhipu portal: job list with "发布于" dates. Job cards may be in a scrollable list.
        # Find job card selectors
        for sel in ['[class*="position"]', '[class*="job-item"]', '[class*="job-list"] > div',
                    '[class*="list-item"]', 'li[class*="item"]', '[class*="card"]', '[class*="job"]']:
            cnt = page.locator(sel).count()
            if cnt > 2:
                print(f"  selector {sel}: {cnt}", flush=True)
                break

        # The zhipu jobs render with "发布于" - scroll the list to load all
        # Scroll the main container
        for i in range(12):
            page.mouse.wheel(0, 2500); page.wait_for_timeout(900)
        txt2 = clean(page.content())
        print(f"  After scroll txt={len(txt2)} 发布于 count={txt2.count('发布于')}", flush=True)

        # Now try clicking each target
        for target in targets:
            print(f"\n  >> {target}", flush=True)
            # Search for target in page text
            cur_txt = clean(page.content())
            in_list = target in cur_txt or target.replace(" ","") in cur_txt.replace(" ","")
            print(f"     in_list={in_list}", flush=True)
            if not in_list:
                # may need to scroll/paginate more - try clicking page numbers
                for pg in range(2, 9):
                    try:
                        btn = page.locator(f"text={pg}").first
                        if btn.count()>0:
                            btn.click(timeout=3000); page.wait_for_timeout(3500)
                            t = clean(page.content())
                            if target in t or target.replace(" ","") in t.replace(" ",""):
                                print(f"     found on page {pg}", flush=True)
                                break
                    except: pass
            # try clicking via get_by_text
            ok = False
            try:
                loc = page.get_by_text(target, exact=False)
                n = loc.count()
                print(f"     get_by_text matches: {n}", flush=True)
                for i in range(min(n, 4)):
                    try:
                        el = loc.nth(i)
                        el.scroll_into_view_if_needed(timeout=3000)
                        page.wait_for_timeout(400)
                        el.click(timeout=5000)
                        page.wait_for_timeout(5000)
                        jd = capture_current_jd(page, target)
                        if len(jd["duty"]) > 20 or len(jd["requirement"]) > 20 or "职位描述" in jd["txt"] or "工作职责" in jd["txt"] or "岗位职责" in jd["txt"]:
                            jd["target"] = target; jd["clicked"] = True
                            print(f"     JD captured: duty={len(jd['duty'])} req={len(jd['requirement'])} team={len(jd['team'])}", flush=True)
                            results.append(jd)
                            safe = re.sub(r'[^\w一-鿿]','_', target)[:30]
                            with open(f"{OUT}/zhipu_r52_jd_{safe}.txt","w") as f: f.write(jd["txt"])
                            ok = True
                            break
                    except Exception as e:
                        print(f"     click {i} err: {e}", flush=True)
                        continue
            except Exception as e:
                print(f"     locator err: {e}", flush=True)
            if not ok:
                results.append({"target": target, "clicked": False, "in_list": in_list})

        ctx.close(); b.close()
    with open(f"{OUT}/zhipu_r52_jd_v2.json","w") as f:
        json.dump({"company":"Zhipu","scrapeDate":"2026-07-16","targets":results}, f, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    scrape_cambricon()
    scrape_zhipu()
    print("\n=== DONE v2 ===", flush=True)
