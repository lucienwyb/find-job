#!/usr/bin/env python3
"""Get all Baichuan jobs and Cambricon job details."""
import json
import os
import time
import datetime
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


def scrape_feishu_all(browser, url, total_expected=30):
    """Scrape all jobs from a feishu portal by scrolling and paginating."""
    context = browser.new_context()
    page = context.new_page()
    api_data = []

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                body = response.text()
                if body and len(body) > 100:
                    if 'search/job' in response.url.lower() or 'job/post' in response.url.lower():
                        api_data.append({'url': response.url[:500], 'body': body[:80000]})
        except:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(8)

        # Scroll to load more
        for i in range(30):
            page.evaluate("window.scrollBy(0, 3000)")
            time.sleep(0.5)

        # Try clicking "load more" buttons
        for _ in range(10):
            clicked = False
            for btn_text in ["查看更多", "加载更多", "更多", "下一页", "Next", "展开更多"]:
                try:
                    btn = page.get_by_text(btn_text, exact=False)
                    if btn.count() > 0:
                        btn.first.click(timeout=3000)
                        time.sleep(2)
                        clicked = True
                        break
                except:
                    pass
            if not clicked:
                break

    except Exception as e:
        print(f"  Error: {e}")

    page.close()

    # Extract all jobs from API data
    all_jobs = []
    for api in api_data:
        try:
            data = json.loads(api['body'])
            if data.get('code') == 0:
                d = data.get('data', {})
                job_list = d.get('job_post_list', [])
                all_jobs.extend(job_list)
        except:
            pass

    # Deduplicate
    seen = set()
    unique = []
    for job in all_jobs:
        jid = job.get('id', '')
        if jid and jid not in seen:
            seen.add(jid)
            unique.append(job)

    return unique


def scrape_cambricon_all(browser):
    """Get all Cambricon jobs from mokahr by navigating to the jobs page."""
    context = browser.new_context()
    page = context.new_page()
    api_data = []
    job_links_data = []

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                body = response.text()
                if body and len(body) > 100:
                    api_data.append({'url': response.url[:500], 'body': body[:80000]})
        except:
            pass

    page.on("response", handle_response)

    try:
        page.goto("https://app.mokahr.com/apply/cambricon/1113#/jobs", wait_until="domcontentloaded", timeout=45000)
        time.sleep(10)

        # Scroll and click to load more
        for i in range(20):
            page.evaluate("window.scrollBy(0, 3000)")
            time.sleep(0.5)

        # Try clicking "more" or pagination
        for _ in range(10):
            for btn_text in ["查看更多职位", "更多", "加载更多", "下一页"]:
                try:
                    btn = page.get_by_text(btn_text, exact=False)
                    if btn.count() > 0:
                        btn.first.click(timeout=3000)
                        time.sleep(3)
                        break
                except:
                    pass

        # Get all links on the page
        links = page.eval_on_selector_all("a[href]", """
            elements => elements.map(e => ({text: e.innerText.trim().substring(0, 200), href: e.href}))
        """)
        job_links_data = [l for l in links if '/job/' in l.get('href', '')]

    except Exception as e:
        print(f"  Error: {e}")

    page.close()

    # Try to extract jobs from API data
    all_jobs = []
    for api in api_data:
        try:
            data = json.loads(api['body'])
            if 'data' in data:
                d = data['data']
                if isinstance(d, dict):
                    for list_key in ['jobList', 'list', 'jobs']:
                        if list_key in d:
                            all_jobs.extend(d[list_key])
        except:
            pass

    return all_jobs, job_links_data, api_data


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)
    cutoff = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        # === BAICHUAN: Get all 30 jobs ===
        print("="*60)
        print("BAICHUAN: Getting all 30 jobs")
        print("="*60)

        baichuan_jobs = scrape_feishu_all(browser, "https://cq6qe6bvfr6.jobs.feishu.cn/")
        print(f"  Captured {len(baichuan_jobs)} jobs")

        # Analyze
        matching = []
        recent = []
        for job in baichuan_jobs:
            title = job.get('title', '')
            desc = job.get('description', '')
            city = job.get('city_list', [])
            if isinstance(city, list):
                city = ', '.join([c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in city])
            pub_time = job.get('publish_time', 0)

            text = f"{title} {desc}"
            matched = match_keywords(text)
            if matched:
                matching.append({
                    'title': title,
                    'city': city,
                    'publish_time': pub_time,
                    'matched_keywords': matched,
                    'description': desc[:500],
                    'id': job.get('id', ''),
                })

            if pub_time:
                dt = datetime.datetime.fromtimestamp(pub_time / 1000, tz=datetime.timezone.utc)
                if dt >= cutoff:
                    recent.append({'title': title, 'date': dt.strftime('%Y-%m-%d'), 'id': job.get('id', '')})

        print(f"  Matching: {len(matching)}")
        for j in matching:
            pub_str = ''
            if j['publish_time']:
                dt = datetime.datetime.fromtimestamp(j['publish_time'] / 1000, tz=datetime.timezone.utc)
                pub_str = dt.strftime('%Y-%m-%d')
            print(f"    [{', '.join(j['matched_keywords'])}] {j['title']} | {j['city']} | {pub_str}")

        print(f"  Recent (after 2026-07-16): {len(recent)}")
        for j in recent:
            print(f"    {j['date']} | {j['title']}")

        # All jobs with dates
        print(f"\n  All {len(baichuan_jobs)} jobs:")
        for job in sorted(baichuan_jobs, key=lambda x: x.get('publish_time', 0), reverse=True):
            pub_time = job.get('publish_time', 0)
            if pub_time:
                dt = datetime.datetime.fromtimestamp(pub_time / 1000, tz=datetime.timezone.utc)
                pub_str = dt.strftime('%Y-%m-%d')
            else:
                pub_str = 'N/A'
            print(f"    {pub_str} | {job.get('title', '')}")

        # Save
        baichuan_result = {
            "company": "baichuan",
            "portal_url": "https://cq6qe6bvfr6.jobs.feishu.cn/",
            "total_positions": len(baichuan_jobs),
            "matching_positions": matching,
            "recent_positions": recent,
            "all_jobs": [{"title": j.get('title',''), "publish_time": j.get('publish_time',0), "id": j.get('id','')} for j in baichuan_jobs],
        }
        with open("/pulp/find-job/r44_baichuan.json", 'w', encoding='utf-8') as f:
            json.dump(baichuan_result, f, ensure_ascii=False, indent=2)
        print(f"  Saved to /pulp/find-job/r44_baichuan.json")

        # === CAMBRICON: Get all jobs with details ===
        print(f"\n{'='*60}")
        print("CAMBRICON: Getting all jobs")
        print("="*60)

        cam_jobs, cam_links, cam_api = scrape_cambricon_all(browser)
        print(f"  API jobs extracted: {len(cam_jobs)}")
        print(f"  Job links: {len(cam_links)}")

        # Print all job links with text
        print(f"\n  All Cambricon job links:")
        for link in cam_links:
            print(f"    {link['text'][:100].replace(chr(10), ' | ')}")

        # Try to extract job data from API
        print(f"\n  API data entries: {len(cam_api)}")
        for api in cam_api:
            print(f"    URL: {api['url'][:200]}")
            try:
                data = json.loads(api['body'])
                if isinstance(data, dict):
                    print(f"    Keys: {list(data.keys())[:15]}")
                    if 'data' in data:
                        d = data['data']
                        if isinstance(d, dict):
                            print(f"    Data keys: {list(d.keys())[:20]}")
                            for k in d:
                                if isinstance(d[k], list) and len(d[k]) > 0:
                                    print(f"    List '{k}': {len(d[k])} items")
                                    if isinstance(d[k][0], dict):
                                        print(f"      First item keys: {list(d[k][0].keys())[:20]}")
                                        # Print first few jobs
                                        for item in d[k][:3]:
                                            print(f"      {json.dumps(item, ensure_ascii=False)[:300]}")
            except:
                print(f"    Body: {api['body'][:300]}")

        # Save
        cambricon_result = {
            "company": "cambricon",
            "portal_url": "https://app.mokahr.com/apply/cambricon/1113",
            "total_job_links": len(cam_links),
            "job_links": cam_links,
            "api_data_count": len(cam_api),
        }
        with open("/pulp/find-job/r44_cambricon.json", 'w', encoding='utf-8') as f:
            json.dump(cambricon_result, f, ensure_ascii=False, indent=2)
        print(f"  Saved to /pulp/find-job/r44_cambricon.json")

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
