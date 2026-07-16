#!/usr/bin/env python3
"""Load all jobs via scroll pagination, capture every job/posts response, aggregate + save."""
import json, time, datetime
from playwright.sync_api import sync_playwright

URL = "https://01ai.jobs.feishu.cn/index/position/list"
OUT = "/pulp/find-job/r44_01ai.json"

def ts_to_date(ms):
    if not ms: return None
    return datetime.datetime.utcfromtimestamp(ms/1000).strftime("%Y-%m-%d %H:%M:%S UTC")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = ctx.new_page()
        api_responses = []
        def on_response(resp):
            if "search/job/posts" in resp.url:
                try:
                    body = resp.text()
                    api_responses.append({"url": resp.url, "body": body})
                except Exception:
                    pass
        page.on("response", on_response)

        print("[*] goto", flush=True)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("[!] goto:", e, flush=True)
        time.sleep(5)

        # Scroll repeatedly to trigger pagination until no new jobs load
        prev_count = 0
        for i in range(15):
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except Exception:
                pass
            time.sleep(2)
            # count rendered job titles via innerText
            try:
                # try clicking "加载更多" / load more if present
                btn = page.query_selector('text=加载更多') or page.query_selector('text=更多')
                if btn:
                    btn.click(timeout=3000)
                    time.sleep(2)
            except Exception:
                pass
            cur = len(api_responses)
            print(f"  scroll {i}: api calls so far={cur}", flush=True)
            if cur == prev_count and i > 2:
                # no new calls for a while, try a few more
                pass
            prev_count = cur

        print(f"\n[*] total job/posts API calls captured: {len(api_responses)}", flush=True)

        # Parse all responses, dedupe by job id
        all_jobs = {}
        for r in api_responses:
            try:
                d = json.loads(r["body"])
                posts = d.get("data",{}).get("job_post_list",[]) or []
                for jp in posts:
                    jid = jp.get("id")
                    if jid and jid not in all_jobs:
                        all_jobs[jid] = jp
            except Exception as e:
                print("  parse err:", e, flush=True)

        print(f"[*] unique jobs aggregated: {len(all_jobs)}", flush=True)

        # Build clean records
        records = []
        for jid, jp in all_jobs.items():
            cities = [c.get("name") for c in (jp.get("city_list") or [])]
            rc = jp.get("recruit_type") or {}
            jc = jp.get("job_category") or {}
            rec = {
                "id": jid,
                "title": jp.get("title"),
                "publish_time_ms": jp.get("publish_time"),
                "publish_date": ts_to_date(jp.get("publish_time")),
                "recruit_type": rc.get("name"),
                "job_category": jc.get("name"),
                "cities": cities,
                "description": (jp.get("description") or "")[:300],
                "requirement": (jp.get("requirement") or "")[:300],
            }
            records.append(rec)

        # sort by publish_time desc
        records.sort(key=lambda r: r.get("publish_time_ms") or 0, reverse=True)

        with open(OUT, "w") as f:
            json.dump({"total": len(records), "jobs": records, "raw_api_responses": api_responses}, f, ensure_ascii=False, indent=2)
        print(f"[*] saved {len(records)} jobs to {OUT}", flush=True)

        # Print summary
        print("\n=== ALL JOBS (sorted by publish_date desc) ===", flush=True)
        for r in records:
            print(f"  {r['publish_date']} | {r['title']} | {','.join(r['cities'])} | {r['recruit_type']} | {r['job_category']}", flush=True)

        # Highlight matching positions
        keywords = ["kernel","eBPF","系统","嵌入式","Infra","Agent","平台","runtime","SRE","内核","底层","基础设施","平台"]
        print("\n=== MATCHING POSITIONS (kernel/eBPF/system/infra/agent/platform/runtime/SRE) ===", flush=True)
        for r in records:
            blob = (r["title"] + " " + r["description"] + " " + r["requirement"]).lower()
            hits = [k for k in ["kernel","ebpf","系统","嵌入式","infra","agent","平台","runtime","sre","内核","底层","基础设施"] if k.lower() in blob]
            if hits:
                print(f"  [{','.join(hits)}] {r['title']} | {','.join(r['cities'])} | {r['publish_date']}", flush=True)

        # Jobs published on or after 2026-07-16
        print("\n=== JOBS PUBLISHED ON OR AFTER 2026-07-16 ===", flush=True)
        cutoff = 1784160000000  # 2026-07-16 00:00:00 UTC approx
        for r in records:
            if (r.get("publish_time_ms") or 0) >= cutoff:
                print(f"  {r['publish_date']} | {r['title']} | {','.join(r['cities'])}", flush=True)
        # also show ones close: 2026-07-13 to 2026-07-16
        print("\n=== JOBS PUBLISHED 2026-07-13 ~ 2026-07-16 ===", flush=True)
        lo = 1783900800000  # 2026-07-13
        for r in records:
            t = r.get("publish_time_ms") or 0
            if lo <= t:
                print(f"  {r['publish_date']} | {r['title']} | {','.join(r['cities'])}", flush=True)

        browser.close()

if __name__ == "__main__":
    main()
