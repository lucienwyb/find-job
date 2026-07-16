#!/usr/bin/env python3
"""Call APIs directly from page context to get all jobs."""
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


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)
    cutoff = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        # === BAICHUAN: Call feishu API directly from page ===
        print("="*60)
        print("BAICHUAN: Calling feishu API directly")
        print("="*60)

        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto("https://cq6qe6bvfr6.jobs.feishu.cn/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(5)

            # Call the API directly from page context
            all_jobs = []
            for offset in range(0, 50, 10):
                result = page.evaluate(f"""
                    async () => {{
                        try {{
                            const params = new URLSearchParams({{
                                keyword: '',
                                limit: '10',
                                offset: '{offset}',
                                job_category_id_list: '',
                                tag_id_list: '',
                                location_code_list: '',
                                subject_id_list: '',
                                recruitment_id_list: '',
                                portal_type: '6',
                                job_function_id_list: '',
                            }});
                            const resp = await fetch('/api/v1/search/job/posts?' + params.toString());
                            const data = await resp.json();
                            return JSON.stringify(data);
                        }} catch(e) {{
                            return JSON.stringify({{error: e.message}});
                        }}
                    }}
                """)

                data = json.loads(result)
                if data.get('code') == 0:
                    d = data.get('data', {})
                    count = d.get('count', 0)
                    job_list = d.get('job_post_list', [])
                    print(f"  Offset {offset}: {len(job_list)} jobs (total: {count})")
                    all_jobs.extend(job_list)
                    if len(all_jobs) >= count or len(job_list) == 0:
                        break
                else:
                    print(f"  Offset {offset}: error - {data.get('message', '')}")
                    break

                time.sleep(0.5)

            # Deduplicate
            seen = set()
            unique = []
            for job in all_jobs:
                jid = job.get('id', '')
                if jid and jid not in seen:
                    seen.add(jid)
                    unique.append(job)

            print(f"\n  Total unique jobs: {len(unique)}")

            # Analyze
            matching = []
            recent = []
            for job in unique:
                title = job.get('title', '')
                desc = job.get('description', '')
                pub_time = job.get('publish_time', 0)

                text = f"{title} {desc}"
                matched = match_keywords(text)
                if matched:
                    city_list = job.get('city_list', [])
                    city = ', '.join([c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in city_list]) if city_list else ''
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
                        recent.append({'title': title, 'date': dt.strftime('%Y-%m-%d')})

            print(f"\n  Matching positions ({len(matching)}):")
            for j in matching:
                pub_str = ''
                if j['publish_time']:
                    dt = datetime.datetime.fromtimestamp(j['publish_time'] / 1000, tz=datetime.timezone.utc)
                    pub_str = dt.strftime('%Y-%m-%d')
                print(f"    [{', '.join(j['matched_keywords'])}] {j['title']} | {j['city']} | {pub_str}")

            print(f"\n  Recent positions (after 2026-07-16) ({len(recent)}):")
            for j in recent:
                print(f"    {j['date']} | {j['title']}")

            print(f"\n  All {len(unique)} jobs:")
            for job in sorted(unique, key=lambda x: x.get('publish_time', 0), reverse=True):
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
                "total_positions": len(unique),
                "matching_positions": matching,
                "recent_positions": recent,
                "all_jobs": [{"title": j.get('title',''), "publish_time": j.get('publish_time',0), "id": j.get('id','')} for j in unique],
            }
            with open("/pulp/find-job/r44_baichuan.json", 'w', encoding='utf-8') as f:
                json.dump(baichuan_result, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved to /pulp/find-job/r44_baichuan.json")

        except Exception as e:
            print(f"  Error: {e}")

        page.close()

        # === CAMBRICON: Check API response body ===
        print(f"\n{'='*60}")
        print("CAMBRICON: Check API response")
        print("="*60)

        context2 = browser.new_context()
        page2 = context2.new_page()

        api_body = None

        def capture_api(response):
            nonlocal api_body
            if 'ats-apply/website/jobs' in response.url:
                try:
                    api_body = response.text()
                except:
                    pass

        page2.on("response", capture_api)

        try:
            page2.goto("https://app.mokahr.com/apply/cambricon/1113#/jobs", wait_until="domcontentloaded", timeout=45000)
            time.sleep(10)

            if api_body:
                print(f"  API body length: {len(api_body)}")
                try:
                    data = json.loads(api_body)
                    print(f"  Keys: {list(data.keys())}")

                    # Navigate the data structure
                    d = data.get('data', {})
                    if isinstance(d, dict):
                        print(f"  Data keys: {list(d.keys())[:30]}")
                        for k, v in d.items():
                            if isinstance(v, list):
                                print(f"    {k}: list of {len(v)}")
                                if v and isinstance(v[0], dict):
                                    print(f"      First item: {json.dumps(v[0], ensure_ascii=False)[:500]}")
                            elif isinstance(v, dict):
                                print(f"    {k}: dict with keys {list(v.keys())[:20]}")
                            else:
                                print(f"    {k}: {str(v)[:200]}")
                    elif isinstance(d, list):
                        print(f"  Data is list: {len(d)} items")
                        if d:
                            print(f"  First item: {json.dumps(d[0], ensure_ascii=False)[:500]}")
                    else:
                        print(f"  Data type: {type(d)}")
                        print(f"  Data: {str(d)[:1000]}")

                    # Save raw API response
                    with open("/pulp/find-job/r44_cambricon_api.json", 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"  Saved raw API to /pulp/find-job/r44_cambricon_api.json")
                except Exception as e:
                    print(f"  Parse error: {e}")
                    print(f"  Body: {api_body[:500]}")

            # Also get all job links
            links = page2.eval_on_selector_all("a[href]", """
                elements => elements.map(e => ({text: e.innerText.trim().substring(0, 200), href: e.href}))
            """)
            job_links = [l for l in links if '/job/' in l.get('href', '')]

            # Count unique jobs
            unique_job_ids = set()
            for l in job_links:
                if '/job/' in l['href']:
                    job_id = l['href'].split('/job/')[-1]
                    unique_job_ids.add(job_id)

            print(f"\n  Unique job IDs: {len(unique_job_ids)}")
            print(f"  Job links: {len(job_links)}")

            # Save job links
            cambricon_result = {
                "company": "cambricon",
                "portal_url": "https://app.mokahr.com/apply/cambricon/1113",
                "total_positions_visible": len(unique_job_ids),
                "job_links": job_links,
            }
            with open("/pulp/find-job/r44_cambricon.json", 'w', encoding='utf-8') as f:
                json.dump(cambricon_result, f, ensure_ascii=False, indent=2)
            print(f"  Saved to /pulp/find-job/r44_cambricon.json")

        except Exception as e:
            print(f"  Error: {e}")

        page2.close()
        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
