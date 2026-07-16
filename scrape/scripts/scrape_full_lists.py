#!/usr/bin/env python3
"""Use playwright to render full job list pages and capture all API responses."""
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
    "固件", "firmware", "硬件", "hardware", "C++", "C语言",
]


def match_keywords(text):
    text_lower = text.lower()
    matched = []
    for kw in KEYWORDS:
        if kw.lower() in text_lower:
            matched.append(kw)
    return matched


def scrape_full_jobs(browser, url, scroll_and_click=True, wait=10):
    """Render page, scroll, click 'more', and capture all API responses."""
    all_api_data = []
    page = browser.new_page()

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            url_lower = response.url.lower()
            if 'json' in ct or 'json' in url_lower:
                body = response.text()
                if body and len(body) > 50:
                    try:
                        data = json.loads(body)
                        # Check if it contains job data
                        s = json.dumps(data)
                        if any(k in s.lower() for k in ['job', 'position', 'recruit', 'title', 'department', '职位']):
                            all_api_data.append({
                                'url': response.url[:500],
                                'body': body[:100000]
                            })
                    except:
                        pass
        except:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(wait)

        if scroll_and_click:
            # Scroll and click "more" or "load more" buttons
            for i in range(20):
                # Scroll down
                page.evaluate("window.scrollBy(0, 2000)")
                time.sleep(0.5)

                # Try clicking "load more" / "查看更多" / "更多" buttons
                for btn_text in ["查看更多职位", "更多", "加载更多", "下一页", "Next", "Load More"]:
                    try:
                        btn = page.get_by_text(btn_text, exact=False)
                        if btn.count() > 0:
                            btn.first.click(timeout=3000)
                            time.sleep(3)
                            break
                    except:
                        pass

                # Also try clicking pagination
                try:
                    next_btn = page.locator('[class*="next"], [class*="pagination"] button:has-text("下一页"), .ant-pagination-next')
                    if next_btn.count() > 0:
                        next_btn.first.click(timeout=3000)
                        time.sleep(3)
                except:
                    pass

        # Get final body text
        try:
            body_text = page.inner_text("body")
        except:
            body_text = ""

        # Get all links
        try:
            links = page.eval_on_selector_all("a[href]", """
                elements => elements.map(e => ({
                    text: e.innerText.trim().substring(0, 200),
                    href: e.href
                }))
            """)
        except:
            links = []

        page.close()
        return {
            "status": "ok",
            "body_text": body_text[:50000],
            "links": links[:500],
            "api_data": all_api_data,
        }
    except Exception as e:
        page.close()
        return {
            "status": "error",
            "error": str(e)[:300],
            "api_data": all_api_data,
            "body_text": "",
            "links": [],
        }


def extract_jobs_from_api(api_data_list):
    """Extract job listings from captured API responses."""
    all_jobs = []

    for api in api_data_list:
        try:
            data = json.loads(api["body"])
        except:
            continue

        # Mokahr pattern
        if isinstance(data, dict) and "data" in data:
            d = data["data"]
            if isinstance(d, dict):
                # Look for job lists
                for list_key in ["jobList", "list", "jobs", "rows", "job_list", "post_list", "job_post_list"]:
                    if list_key in d:
                        for job in d[list_key]:
                            job_entry = {
                                "source_api": api["url"][:200],
                                "title": job.get("name") or job.get("title") or job.get("Name") or job.get("jobName") or job.get("JobAdName") or "",
                                "department": job.get("department") or job.get("departmentName") or job.get("DepartmentName") or job.get("department_name") or "",
                                "location": job.get("workLocation") or job.get("city") or job.get("location") or job.get("WorkPlace") or job.get("city_name") or "",
                                "description": job.get("description") or job.get("jobDescription") or job.get("Description") or "",
                                "update_time": job.get("updateTime") or job.get("publishTime") or job.get("UpdateTime") or job.get("PostDate") or job.get("update_time") or job.get("publish_time") or "",
                                "id": job.get("id") or job.get("jobId") or job.get("Id") or job.get("JobAdId") or "",
                                "_raw": {k: v for k, v in job.items() if k not in ["description", "requirement"]},
                            }
                            if job_entry["title"]:
                                all_jobs.append(job_entry)

                # Also check for totalCount
                for count_key in ["totalCount", "total", "count", "Total"]:
                    if count_key in d:
                        pass  # Just for reference

            elif isinstance(d, list):
                for job in d:
                    job_entry = {
                        "source_api": api["url"][:200],
                        "title": job.get("name") or job.get("title") or job.get("Name") or job.get("JobAdName") or "",
                        "department": job.get("department") or job.get("DepartmentName") or "",
                        "location": job.get("workLocation") or job.get("city") or job.get("WorkPlace") or "",
                        "description": job.get("description") or job.get("Description") or "",
                        "update_time": job.get("updateTime") or job.get("publishTime") or job.get("UpdateTime") or job.get("PostDate") or "",
                        "id": job.get("id") or job.get("Id") or "",
                        "_raw": {k: v for k, v in job.items() if k not in ["description", "requirement"]},
                    }
                    if job_entry["title"]:
                        all_jobs.append(job_entry)

        # Zhiye pattern (capitalized keys)
        if isinstance(data, dict) and "Data" in data:
            d = data["Data"]
            if isinstance(d, list):
                for job in d:
                    job_entry = {
                        "source_api": api["url"][:200],
                        "title": job.get("Name") or job.get("JobAdName") or "",
                        "department": job.get("DepartmentName") or "",
                        "location": job.get("WorkPlace") or job.get("WorkAddress") or "",
                        "description": job.get("Description") or "",
                        "update_time": job.get("UpdateTime") or job.get("PostDate") or "",
                        "id": job.get("Id") or job.get("JobAdId") or "",
                        "_raw": {k: v for k, v in job.items() if k not in ["Description", "Requirement"]},
                    }
                    if job_entry["title"]:
                        all_jobs.append(job_entry)
            elif isinstance(d, dict) and "Rows" in d:
                for job in d["Rows"]:
                    job_entry = {
                        "source_api": api["url"][:200],
                        "title": job.get("Name") or job.get("JobAdName") or "",
                        "department": job.get("DepartmentName") or "",
                        "location": job.get("WorkPlace") or "",
                        "description": job.get("Description") or "",
                        "update_time": job.get("UpdateTime") or job.get("PostDate") or "",
                        "id": job.get("Id") or job.get("JobAdId") or "",
                    }
                    if job_entry["title"]:
                        all_jobs.append(job_entry)

    # Deduplicate by id or title
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = job.get("id") or job["title"]
        if key and key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    targets = [
        # Cambricon - full job list page
        ("cambricon", "https://app.mokahr.com/apply/cambricon/1113#/jobs", 10),
        # DP Technology - full job list
        ("dptechnology", "https://dptechnology.jobs.feishu.cn/index", 10),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        for key, url, wait_time in targets:
            print(f"\n{'='*60}")
            print(f"Scraping: {key} -> {url}")
            print(f"{'='*60}")

            result = scrape_full_jobs(browser, url, scroll_and_click=True, wait=wait_time)

            print(f"  Status: {result['status']}")
            print(f"  Body length: {len(result.get('body_text',''))}")
            print(f"  API data entries: {len(result.get('api_data',[]))}")

            # Show API URLs
            for api in result.get("api_data", []):
                print(f"  API: {api['url'][:200]}")

            # Extract jobs from API data
            jobs = extract_jobs_from_api(result.get("api_data", []))
            print(f"\n  Total extracted jobs: {len(jobs)}")

            # Also extract from body text (links)
            body = result.get("body_text", "")
            links = result.get("links", [])

            # Find job links in the body/links
            job_links = []
            for link in links:
                text = link.get("text", "")
                href = link.get("href", "")
                if any(k in href for k in ["/job/", "/position/", "/jobs/"]):
                    job_links.append({"title": text[:100], "url": href})

            print(f"  Job links found: {len(job_links)}")

            # Match keywords
            matching_jobs = []
            for job in jobs:
                text = f"{job['title']} {job.get('department','')} {job.get('description','')}"
                matched = match_keywords(text)
                if matched:
                    job['matched_keywords'] = matched
                    matching_jobs.append(job)

            # Also match from job links
            for link in job_links:
                matched = match_keywords(link["title"])
                if matched:
                    matching_jobs.append({
                        "title": link["title"],
                        "url": link["url"],
                        "matched_keywords": matched,
                        "source": "link",
                    })

            print(f"  Matching jobs: {len(matching_jobs)}")
            for j in matching_jobs[:30]:
                title = j.get("title", "")
                dept = j.get("department", "")
                loc = j.get("location", "")
                kw = j.get("matched_keywords", [])
                print(f"    [{', '.join(kw)}] {title} | {dept} | {loc}")

            # Save results
            output = {
                "company": key,
                "total_positions": len(jobs),
                "total_job_links": len(job_links),
                "matching_positions": matching_jobs,
                "all_jobs": jobs[:100],  # Save first 100 jobs
                "job_links": job_links[:200],
                "body_text": body[:20000],
                "api_urls": [api["url"] for api in result.get("api_data", [])],
            }

            filepath = f"/pulp/find-job/r44_{key}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved to {filepath}")

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
