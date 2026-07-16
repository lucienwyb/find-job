#!/usr/bin/env python3
"""Scrape Baichuan feishu portal for all job listings."""
import json
import os
import time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

KEYWORDS = [
    "kernel", "ebpf", "系统", "infra", "基础设施", "架构", "嵌入式", "embedded",
    "edge", "边缘", "driver", "驱动", "platform", "平台", "OS", "操作系统",
    "runtime", "容器", "container", "虚拟化", "virtualization", "agent",
    "training", "推理", "inference", "HPC", "高性能计算", "cuda", "gpu",
    "底层", "low-level", "system", "芯片", "chip", "编译器", "compiler",
    "调度", "schedule", "分布式", "distributed", "存储", "storage",
    "RDMA", "nccl", "kubernetes", "k8s", "云原生", "cloud-native",
    "Linux", "内核", "BPF", "网络", "network", "通信", "communication",
    "固件", "firmware", "硬件", "hardware",
]


def match_keywords(text):
    text_lower = text.lower()
    matched = []
    for kw in KEYWORDS:
        if kw.lower() in text_lower:
            matched.append(kw)
    return matched


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        context = browser.new_context()
        page = context.new_page()
        api_data = []

        def handle_response(response):
            try:
                ct = response.headers.get('content-type', '')
                url_lower = response.url.lower()
                if 'json' in ct or 'json' in url_lower:
                    body = response.text()
                    if body and len(body) > 100:
                        api_data.append({'url': response.url[:500], 'body': body[:80000]})
            except:
                pass

        page.on("response", handle_response)

        try:
            page.goto("https://cq6qe6bvfr6.jobs.feishu.cn/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(8)

            # Scroll to load more jobs
            for i in range(20):
                page.evaluate("window.scrollBy(0, 2000)")
                time.sleep(0.5)

            # Try clicking "load more" or pagination
            for btn_text in ["查看更多", "加载更多", "更多", "下一页", "Next"]:
                try:
                    btn = page.get_by_text(btn_text, exact=False)
                    if btn.count() > 0:
                        btn.first.click(timeout=3000)
                        time.sleep(3)
                except:
                    pass

            body = page.inner_text("body")
            print(f"Body length: {len(body)}")
            print(f"Title: {page.title()}")

            # Get all links
            links = page.eval_on_selector_all("a[href]", """
                elements => elements.map(e => ({text: e.innerText.trim().substring(0, 200), href: e.href}))
            """)
            print(f"Links: {len(links)}")

            # Find job links
            job_links = [l for l in links if '/position/' in l.get('href', '') or '/job/' in l.get('href', '')]
            print(f"Job links: {len(job_links)}")
            for jl in job_links:
                print(f"  [{jl['text'][:80]}] -> {jl['href'][:100]}")

        except Exception as e:
            print(f"Error: {e}")
            body = ""
            links = []

        # Analyze API data
        print(f"\n=== API calls captured ({len(api_data)}) ===")
        all_jobs = []

        for api in api_data:
            if 'search/job' in api['url'].lower() or 'job/post' in api['url'].lower():
                print(f"\n  Job API: {api['url'][:200]}")
                try:
                    data = json.loads(api['body'])
                    if data.get('code') == 0:
                        d = data.get('data', {})
                        count = d.get('count', 0)
                        job_list = d.get('job_post_list', [])
                        print(f"    Count: {count}, Jobs in response: {len(job_list)}")
                        all_jobs.extend(job_list)
                except:
                    print(f"    Body: {api['body'][:300]}")

        # Also check for other API patterns
        for api in api_data:
            if any(k in api['url'].lower() for k in ['job', 'position', 'recruit']) and 'search' not in api['url'].lower():
                try:
                    data = json.loads(api['body'])
                    if isinstance(data, dict) and data.get('code') == 0:
                        d = data.get('data', {})
                        if isinstance(d, dict):
                            for list_key in ['job_list', 'list', 'positions', 'jobs']:
                                if list_key in d:
                                    print(f"  Found {list_key} in {api['url'][:100]}: {len(d[list_key])} items")
                                    all_jobs.extend(d[list_key])
                except:
                    pass

        # Deduplicate by id
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            jid = job.get('id', job.get('title', ''))
            if jid and jid not in seen:
                seen.add(jid)
                unique_jobs.append(job)

        print(f"\n=== Total unique jobs: {len(unique_jobs)} ===")

        # Analyze jobs
        import datetime
        cutoff = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)

        matching_jobs = []
        recent_jobs = []

        for job in unique_jobs:
            title = job.get('title', '')
            desc = job.get('description', '')
            city = job.get('city_list', job.get('city_info', ''))
            if isinstance(city, list):
                city = ', '.join([c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in city])
            pub_time = job.get('publish_time', 0)

            text = f"{title} {desc}"
            matched = match_keywords(text)

            if matched:
                matching_jobs.append({
                    'title': title,
                    'description': desc[:500],
                    'city': city,
                    'publish_time': pub_time,
                    'matched_keywords': matched,
                    'id': job.get('id', ''),
                })

            # Check if recent
            if pub_time:
                dt = datetime.datetime.fromtimestamp(pub_time / 1000, tz=datetime.timezone.utc)
                if dt >= cutoff:
                    recent_jobs.append({
                        'title': title,
                        'date': dt.strftime('%Y-%m-%d'),
                        'id': job.get('id', ''),
                    })

        print(f"\n=== Matching positions ({len(matching_jobs)}) ===")
        for j in matching_jobs:
            pub_str = ''
            if j['publish_time']:
                dt = datetime.datetime.fromtimestamp(j['publish_time'] / 1000, tz=datetime.timezone.utc)
                pub_str = dt.strftime('%Y-%m-%d')
            print(f"  [{', '.join(j['matched_keywords'])}] {j['title']} | {j['city']} | {pub_str}")

        print(f"\n=== Recent positions (after 2026-07-16) ({len(recent_jobs)}) ===")
        for j in recent_jobs:
            print(f"  {j['date']} | {j['title']}")

        # Print all jobs with dates
        print(f"\n=== All jobs with dates ===")
        for job in sorted(unique_jobs, key=lambda x: x.get('publish_time', 0), reverse=True):
            title = job.get('title', '')
            pub_time = job.get('publish_time', 0)
            if pub_time:
                dt = datetime.datetime.fromtimestamp(pub_time / 1000, tz=datetime.timezone.utc)
                pub_str = dt.strftime('%Y-%m-%d')
            else:
                pub_str = 'N/A'
            print(f"  {pub_str} | {title}")

        # Save result
        result = {
            "company": "baichuan",
            "portal_url": "https://cq6qe6bvfr6.jobs.feishu.cn/",
            "total_positions": len(unique_jobs),
            "matching_positions": matching_jobs,
            "recent_positions": recent_jobs,
            "all_jobs": [{"title": j.get('title',''), "id": j.get('id',''), "publish_time": j.get('publish_time',0), "city_list": j.get('city_list',[]), "description": j.get('description','')[:200]} for j in unique_jobs],
        }
        with open("/pulp/find-job/r44_baichuan.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to /pulp/find-job/r44_baichuan.json")

        page.close()
        browser.close()

    print("Done!")


if __name__ == "__main__":
    main()
