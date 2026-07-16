#!/usr/bin/env python3
"""Click through all pagination pages (1-6) to capture all 52 jobs with publish dates."""
import json, time, datetime
from playwright.sync_api import sync_playwright

URL = "https://01ai.jobs.feishu.cn/index/position/list"
OUT = "/pulp/find-job/r44_01ai.json"

def ts_to_date(ms):
    if not ms: return None
    return datetime.datetime.fromtimestamp(ms/1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN", viewport={"width":1440,"height":900},
        )
        page = ctx.new_page()
        api_responses = []
        def on_response(resp):
            if "search/job/posts" in resp.url:
                try:
                    body = resp.text()
                    api_responses.append({"url": resp.url, "body": body})
                except Exception: pass
        page.on("response", on_response)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print("[!] goto:", e, flush=True)
        time.sleep(5)
        print(f"[*] page 1 loaded, api calls: {len(api_responses)}", flush=True)

        # Click through pages 2..6
        for pg in range(2, 8):
            try:
                # click the pagination item by text
                locator = page.locator(f'.atsx-pagination-item-{pg} a, li.atsx-pagination-item-{pg}')
                if locator.count() == 0:
                    # fallback: text match
                    locator = page.locator(f'a:has-text("{pg}")')
                locator.first.click(timeout=8000)
                time.sleep(4)
                print(f"[*] clicked page {pg}, api calls: {len(api_responses)}", flush=True)
            except Exception as e:
                print(f"[!] page {pg} click err: {e}", flush=True)
                break

        print(f"\n[*] total API calls: {len(api_responses)}", flush=True)

        # Aggregate
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

        print(f"[*] unique jobs: {len(all_jobs)}", flush=True)

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
                "description": (jp.get("description") or "")[:500],
                "requirement": (jp.get("requirement") or "")[:500],
            }
            records.append(rec)

        records.sort(key=lambda r: r.get("publish_time_ms") or 0, reverse=True)

        with open(OUT, "w") as f:
            json.dump({"total": len(records), "captured_at": "2026-07-16", "jobs": records}, f, ensure_ascii=False, indent=2)
        print(f"[*] saved {len(records)} jobs to {OUT}\n", flush=True)

        print("=== ALL JOBS (by publish_date desc) ===", flush=True)
        for r in records:
            print(f"  {r['publish_date']} | {r['title']} | {','.join(r['cities'])} | {r['recruit_type']} | {r['job_category']}", flush=True)

        # matching positions
        print("\n=== MATCHING (kernel/eBPF/system/embedded/infra/agent/platform/runtime/SRE) ===", flush=True)
        for r in records:
            blob = (r["title"] + " " + r["description"] + " " + r["requirement"]).lower()
            hits = [k for k in ["kernel","ebpf","系统","嵌入式","infra","agent","平台","runtime","sre","内核","底层","基础设施","分布式","后端","backend"] if k.lower() in blob]
            if hits:
                print(f"  [{','.join(hits)}] {r['title']} | {','.join(r['cities'])} | {r['recruit_type']} | {r['publish_date']}", flush=True)

        # Beijing count
        bj = [r for r in records if "北京" in r["cities"]]
        print(f"\n=== Beijing jobs: {len(bj)} ===", flush=True)

        # published on/after 2026-07-16
        cutoff = 1784160000000  # 2026-07-16 00:00:00 UTC
        new_jobs = [r for r in records if (r.get("publish_time_ms") or 0) >= cutoff]
        print(f"\n=== Published on/after 2026-07-16: {len(new_jobs)} ===", flush=True)
        for r in new_jobs:
            print(f"  {r['publish_date']} | {r['title']} | {','.join(r['cities'])}", flush=True)

        # published 2026-07-13..07-16
        lo = 1783900800000
        recent = [r for r in records if lo <= (r.get("publish_time_ms") or 0)]
        print(f"\n=== Published 2026-07-13 ~ 07-16: {len(recent)} ===", flush=True)
        for r in recent:
            print(f"  {r['publish_date']} | {r['title']} | {','.join(r['cities'])}", flush=True)

        browser.close()

if __name__ == "__main__":
    main()
