#!/usr/bin/env python3
"""Round 52: Capture JD details for key high-match jobs on Cambricon + Zhipu mokahr portals.
Goal: click into specific job cards, capture full JD (responsibilities + requirements),
verify jobs are still online (not closed).

Targets:
- Cambricon (cambricon/1113): 高性能通信库研发工程师, AI编译器研发工程师,
  AI网络研发工程师, 芯片应用工程师-固件方向, 高性能计算库研发工程师,
  高性能算法库工程师, 深度学习框架图编译工程师
- Zhipu (zphz/148983): Agent Infra 开发工程师, 推理Infra工程师,
  Agent Infra 运维开发工程师, 训练Infra工程师
"""
import sys, json, re, time, os
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
OUT = "/pulp/find-job/scrape/data"

def launch(p):
    b = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled",
              "--disable-gpu"],
        proxy={"server": PROXY})
    return b

def new_ctx(b):
    return b.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 1100},
        locale="zh-CN",
        ignore_https_errors=True)

def clean(html):
    txt = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    txt = re.sub(r"&[a-z]+;", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def click_job_and_capture(page, target_title, clean_fn):
    """Find a job card matching target_title, click it, capture JD detail panel.
    Returns dict with title, jd_text, status or None if not found."""
    # Wait for job list to render
    page.wait_for_timeout(3000)

    # Try multiple selector strategies to find the job card
    # Strategy 1: text-based locator
    candidates = []
    # mokahr job cards: look for elements containing the title text
    # Use get_by_text with substring
    try:
        loc = page.get_by_text(target_title, exact=False)
        n = loc.count()
        for i in range(min(n, 5)):
            try:
                el = loc.nth(i)
                # scroll into view and click
                el.scroll_into_view_if_needed(timeout=3000)
                page.wait_for_timeout(500)
                el.click(timeout=4000)
                page.wait_for_timeout(4000)
                html = page.content()
                txt = clean_fn(html)
                # Check if a detail panel appeared (look for 岗位职责/任职要求/职位描述)
                has_jd = any(k in txt for k in ['岗位职责', '任职要求', '职位描述', '工作职责', '任职资格', '要求'])
                return {
                    "target": target_title,
                    "clicked": True,
                    "has_jd_panel": has_jd,
                    "txt_len": len(txt),
                    "txt": txt,
                    "html_len": len(html),
                }
            except Exception as e:
                candidates.append(f"click_err:{e}")
                continue
        return {"target": target_title, "clicked": False, "note": "locator found but click failed", "errs": candidates}
    except Exception as e:
        return {"target": target_title, "clicked": False, "note": f"locator error: {e}"}


def extract_jd_segment(full_txt, title):
    """From the full page text after clicking a job, extract the JD portion.
    Mokahr detail panel typically shows: title, dept, location, then 岗位职责:... 任职要求:..."""
    # Find the title position and extract ~3000 chars after it that contain JD
    # But after click, the detail might be in a sidebar; the full text includes list + detail.
    # Try to find the JD block by keywords.
    jd = ""
    # Look for 岗位职责 or 职位描述 followed by content until 任职要求/任职资格/职位要求
    patterns = [
        r'(岗位职责[：:][\s\S]{50,2000}?)(?:任职要求|任职资格|职位要求|岗位要求|申请职位|分享|收藏)',
        r'(工作职责[：:][\s\S]{50,2000}?)(?:任职要求|任职资格|职位要求|岗位要求|申请职位|分享|收藏)',
        r'(职位描述[：:][\s\S]{50,2000}?)(?:任职要求|任职资格|职位要求|岗位要求|申请职位|分享|收藏)',
    ]
    req_patterns = [
        r'(任职要求[：:][\s\S]{30,2000}?)(?:申请职位|分享|收藏|岗位职责|工作职责|职位描述|$)',
        r'(任职资格[：:][\s\S]{30,2000}?)(?:申请职位|分享|收藏|岗位职责|工作职责|职位描述|$)',
        r'(岗位要求[：:][\s\S]{30,2000}?)(?:申请职位|分享|收藏|岗位职责|工作职责|职位描述|$)',
    ]
    for pat in patterns:
        m = re.search(pat, full_txt)
        if m:
            jd = m.group(1)
            break
    req = ""
    for pat in req_patterns:
        m = re.search(pat, full_txt)
        if m:
            req = m.group(1)
            break
    return {"duty": jd.strip(), "requirement": req.strip()}


def scrape_portal(name, url, targets, out_prefix):
    print(f"\n{'='*60}", flush=True)
    print(f"###### {name} ######", flush=True)
    print(f"URL: {url}", flush=True)
    print(f"{'='*60}", flush=True)

    results = []
    with sync_playwright() as p:
        b = launch(p)
        ctx = new_ctx(b)
        page = ctx.new_page()

        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"  HTTP: {resp.status if resp else 'None'}", flush=True)
        except Exception as e:
            print(f"  goto error: {e}", flush=True)
            ctx.close(); b.close()
            return results

        print("  Waiting 18s for render...", flush=True)
        page.wait_for_timeout(18000)

        html = page.content()
        txt = clean(html)
        print(f"  Initial: html={len(html)} txt={len(txt)}", flush=True)

        # Check portal alive
        alive_keys = ['职位', '岗位', '工程师', '招聘', '社招']
        if not any(k in txt for k in alive_keys):
            print("  No job content, waiting 15s more...", flush=True)
            page.wait_for_timeout(15000)
            html = page.content(); txt = clean(html)
            print(f"  After wait: html={len(html)} txt={len(txt)}", flush=True)

        # Save initial page
        with open(f"{OUT}/{out_prefix}_r52_list.html", "w") as f: f.write(html)
        with open(f"{OUT}/{out_prefix}_r52_list.txt", "w") as f: f.write(txt)

        # Verify which targets are present in the list (still online)
        print(f"\n  --- Verifying target jobs online ---", flush=True)
        online = []
        for t in targets:
            present = t in txt
            # also check without spaces
            present2 = t.replace(" ", "") in txt.replace(" ", "")
            status = "ONLINE" if (present or present2) else "NOT_IN_LIST"
            print(f"    [{status}] {t}", flush=True)
            online.append({"title": t, "in_list": present or present2})

        # Now click each target to capture JD
        # For mokahr, need to make sure all jobs are loaded (pagination/scroll)
        # Scroll through pages to ensure target jobs are in DOM
        print(f"\n  --- Scrolling to load all jobs ---", flush=True)
        for i in range(8):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1200)
        # try clicking next page buttons
        for pg in range(2, 8):
            try:
                # mokahr pagination: look for page number buttons
                btn = page.locator(f"text={pg}").first
                if btn.count() > 0:
                    btn.click(timeout=3000)
                    page.wait_for_timeout(4000)
                    print(f"    Clicked page {pg}", flush=True)
            except:
                pass

        # Re-capture full list text after pagination
        full_html = page.content()
        full_txt = clean(full_html)
        with open(f"{OUT}/{out_prefix}_r52_fulllist.txt", "w") as f: f.write(full_txt)

        # Click each target job
        print(f"\n  --- Clicking targets to capture JD ---", flush=True)
        for t in targets:
            print(f"\n  >> Target: {t}", flush=True)
            # re-navigate to page 1 first to reset
            try:
                pg1 = page.locator("text=1").first
                if pg1.count() > 0:
                    pg1.click(timeout=2000)
                    page.wait_for_timeout(2000)
            except:
                pass

            res = click_job_and_capture(page, t, clean)
            jd_seg = extract_jd_segment(res.get("txt", ""), t) if res.get("txt") else {"duty":"","requirement":""}
            res["jd_duty"] = jd_seg["duty"]
            res["jd_requirement"] = jd_seg["requirement"]
            res["in_list"] = next((o["in_list"] for o in online if o["title"]==t), None)
            print(f"     clicked={res.get('clicked')} has_jd={res.get('has_jd_panel')} duty_len={len(jd_seg['duty'])} req_len={len(jd_seg['requirement'])}", flush=True)
            results.append(res)
            # save the captured text
            safe = re.sub(r'[^\w一-鿿]','_', t)[:30]
            with open(f"{OUT}/{out_prefix}_r52_jd_{safe}.txt", "w") as f:
                f.write(res.get("txt",""))
            page.wait_for_timeout(1500)

        ctx.close()
        b.close()

    # Save results JSON
    out_json = {
        "company": name, "portal": url, "scrapeDate": "2026-07-16",
        "targets": results,
    }
    with open(f"{OUT}/{out_prefix}_r52_jd.json", "w") as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved {out_prefix}_r52_jd.json", flush=True)
    return results


if __name__ == "__main__":
    # Cambricon
    cam_targets = [
        "高性能通信库研发工程师",
        "AI编译器研发工程师",
        "AI网络研发工程师",
        "芯片应用工程师-固件方向",
        "高性能计算库研发工程师",
        "高性能算法库工程师",
        "深度学习框架图编译工程师",
    ]
    scrape_portal(
        "Cambricon 寒武纪",
        "https://app.mokahr.com/apply/cambricon/1113",
        cam_targets, "cambricon")

    # Zhipu
    zhipu_targets = [
        "Agent Infra 开发工程师",
        "推理Infra工程师",
        "Agent Infra 运维开发工程师",
        "训练Infra工程师",
    ]
    scrape_portal(
        "Zhipu 智谱",
        "https://app.mokahr.com/social-recruitment/zphz/148983",
        zhipu_targets, "zhipu")

    print("\n\n=== DONE ===", flush=True)
