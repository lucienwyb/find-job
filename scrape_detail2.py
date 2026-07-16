#!/usr/bin/env python3
"""Deep scrape of found career portals with API capture."""
import json
import os
import time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"


def scrape_with_api(browser, url, wait=8, scroll_times=10):
    """Scrape a page with full API capture and scrolling."""
    api_data = []
    page = browser.new_page()

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            url_lower = response.url.lower()
            if 'json' in ct or 'json' in url_lower:
                body = response.text()
                if body and len(body) > 50:
                    api_data.append({
                        'url': response.url[:500],
                        'status': response.status,
                        'body': body[:50000]
                    })
        except:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(wait)

        if scroll_times:
            for _ in range(scroll_times):
                page.evaluate("window.scrollBy(0, 1500)")
                time.sleep(0.5)

        title = page.title()
        try:
            body_text = page.inner_text("body")
        except:
            body_text = ""

        links = []
        try:
            links = page.eval_on_selector_all("a[href]", """
                elements => elements.map(e => ({
                    text: e.innerText.trim().substring(0, 200),
                    href: e.href
                }))
            """)
        except:
            pass

        page.close()
        return {
            "url": url,
            "status": "ok",
            "title": title,
            "body_text": body_text[:50000],
            "links": links[:500],
            "api_data": api_data,
        }
    except Exception as e:
        page.close()
        return {
            "url": url,
            "status": "error",
            "error": str(e)[:300],
            "api_data": api_data,
            "body_text": "",
            "links": [],
        }


def analyze_jobs(result):
    """Analyze API data and body text for job listings."""
    KEYWORDS = [
        "kernel", "ebpf", "系统", "infra", "基础设施", "架构", "嵌入式", "embedded",
        "edge", "边缘", "driver", "驱动", "platform", "平台", "OS", "操作系统",
        "runtime", "容器", "container", "虚拟化", "virtualization", "agent",
        "training", "推理", "inference", "HPC", "高性能计算", "cuda", "gpu",
        "底层", "low-level", "system", "芯片", "chip", "编译器", "compiler",
        "调度", "schedule", "分布式", "distributed", "存储", "storage",
        "RDMA", "nccl", "kubernetes", "k8s", "云原生", "cloud-native",
    ]

    all_jobs = []
    total_count = 0

    # Parse API data for job listings
    for api in result.get("api_data", []):
        try:
            data = json.loads(api["body"])
        except:
            continue

        # Mokahr API pattern
        if isinstance(data, dict) and "data" in data:
            d = data["data"]
            if isinstance(d, dict):
                if "totalCount" in d:
                    total_count = max(total_count, d["totalCount"])
                if "total" in d:
                    total_count = max(total_count, d["total"])
                if "jobList" in d:
                    for job in d["jobList"]:
                        all_jobs.append(self._extract_job_mokahr(job))
                if "list" in d:
                    for item in d["list"]:
                        all_jobs.append(self._extract_job_generic(item))

            # Feishu API pattern
            if isinstance(d, dict) and "job_list" in d:
                for job in d["job_list"]:
                    all_jobs.append(self._extract_job_feishu(job))

        # Zhiye API pattern
        if isinstance(data, dict) and "Data" in data:
            d = data["Data"]
            if isinstance(d, dict):
                if "Total" in data:
                    total_count = max(total_count, data["Total"])
                if "Rows" in d:
                    for job in d["Rows"]:
                        all_jobs.append(self._extract_job_zhiye(job))

    # Also look at body text for job listings
    body = result.get("body_text", "")

    # Keyword matching
    keyword_matches = []
    for kw in KEYWORDS:
        if kw.lower() in body.lower():
            idx = body.lower().find(kw.lower())
            start = max(0, idx - 100)
            end = min(len(body), idx + 200)
            keyword_matches.append({
                "keyword": kw,
                "context": body[start:end].replace("\n", " ").strip()[:300]
            })

    return {
        "total_positions": total_count,
        "extracted_jobs": all_jobs,
        "keyword_matches": keyword_matches,
    }


def extract_job_mokahr(job):
    """Extract job info from mokahr API response."""
    return {
        "title": job.get("name") or job.get("title") or "",
        "department": job.get("department") or job.get("departmentName") or "",
        "location": job.get("workLocation") or job.get("city") or job.get("location") or "",
        "update_time": job.get("updateTime") or job.get("publishTime") or job.get("lastModifyTime") or "",
        "id": job.get("id") or job.get("jobId") or "",
    }


def extract_job_generic(item):
    """Extract job info from generic API response."""
    return {
        "title": item.get("name") or item.get("title") or item.get("jobName") or "",
        "department": item.get("department") or item.get("departmentName") or "",
        "location": item.get("workLocation") or item.get("city") or item.get("location") or "",
        "update_time": item.get("updateTime") or item.get("publishTime") or "",
        "id": item.get("id") or "",
    }


def extract_job_feishu(job):
    """Extract job info from feishu API response."""
    return {
        "title": job.get("title") or job.get("name") or "",
        "department": job.get("department") or "",
        "location": job.get("city") or job.get("location") or "",
        "update_time": job.get("update_time") or job.get("publish_time") or "",
        "id": job.get("id") or "",
    }


def extract_job_zhiye(job):
    """Extract job info from zhiye API response."""
    return {
        "title": job.get("Name") or job.get("JobAdName") or "",
        "department": job.get("DepartmentName") or "",
        "location": job.get("WorkPlace") or job.get("WorkAddress") or "",
        "update_time": job.get("UpdateTime") or job.get("PublishDate") or "",
        "id": job.get("Id") or job.get("JobAdId") or "",
    }


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    targets = [
        # Cambricon - full mokahr portal
        ("cambricon", "https://app.mokahr.com/apply/cambricon/1113#/?anchorName=007", 10, 15),
        # DP Technology - feishu portal
        ("dptechnology", "https://dptechnology.jobs.feishu.cn/index", 10, 10),
        # Geovis - zhiye portal
        ("geovis", "https://geovis.zhiye.com/home", 10, 10),
        # Deepglint - zhiye portal (check if 0 jobs is real)
        ("deepglint", "https://deepglint.zhiye.com/social/jobs", 10, 10),
        # Baichuan - try different career URLs
        ("baichuan", "https://www.baichuan-ai.com/about", 8, 5),
        # 4Paradigm - search for career links on main site
        ("4paradigm", "https://www.4paradigm.com/", 8, 5),
        # ModelBest - last attempt
        ("modelbest", "https://www.modelbest.cn/", 8, 5),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        for key, url, wait_time, scroll in targets:
            print(f"\n{'='*60}")
            print(f"Scraping: {key} -> {url}")
            print(f"{'='*60}")

            result = scrape_with_api(browser, url, wait=wait_time, scroll_times=scroll)

            print(f"  Status: {result['status']}")
            print(f"  Title: {result.get('title','')}")
            print(f"  Body length: {len(result.get('body_text',''))}")
            print(f"  Links: {len(result.get('links',[]))}")
            print(f"  API data: {len(result.get('api_data',[]))}")

            # Show career links
            links = result.get("links", [])
            career_links = []
            for link in links:
                text = link.get('text', '')
                href = link.get('href', '')
                combined = (text + href).lower()
                if any(k in combined for k in ['join', 'career', 'job', 'recruit', '社招', '校招', '招聘', '加入', 'talent', 'hire', 'mokahr', 'zhiye', 'feishu', 'position', '职位', '工程师', '开发']):
                    career_links.append(link)
            if career_links:
                print(f"  Career links ({len(career_links)}):")
                for cl in career_links[:40]:
                    print(f"    [{cl['text'][:60]}] -> {cl['href'][:120]}")

            # Analyze API data
            for api in result.get("api_data", []):
                api_url = api["url"]
                # Only show interesting APIs
                if any(k in api_url.lower() for k in ['job', 'position', 'recruit', 'apply', 'search']):
                    print(f"\n  JOB API: {api_url[:200]}")
                    try:
                        data = json.loads(api["body"])
                        if isinstance(data, dict):
                            print(f"    Keys: {list(data.keys())[:20]}")
                            if "data" in data and isinstance(data["data"], dict):
                                print(f"    Data keys: {list(data['data'].keys())[:20]}")
                                if "totalCount" in data["data"]:
                                    print(f"    Total positions: {data['data']['totalCount']}")
                                if "Total" in data:
                                    print(f"    Total: {data['Total']}")
                                if "total" in data["data"]:
                                    print(f"    total: {data['data']['total']}")
                                # Check for job lists
                                for list_key in ["jobList", "list", "Rows", "rows", "job_list", "jobs"]:
                                    if list_key in data["data"]:
                                        items = data["data"][list_key]
                                        print(f"    {list_key}: {len(items)} items")
                                        for item in items[:5]:
                                            title = item.get("name") or item.get("title") or item.get("Name") or item.get("JobAdName") or "N/A"
                                            dept = item.get("department") or item.get("DepartmentName") or item.get("departmentName") or ""
                                            loc = item.get("workLocation") or item.get("city") or item.get("WorkPlace") or ""
                                            print(f"      - {title} | {dept} | {loc}")
                            elif isinstance(data.get("data"), list):
                                print(f"    Data is list with {len(data['data'])} items")
                                for item in data["data"][:5]:
                                    print(f"      - {json.dumps(item, ensure_ascii=False)[:200]}")
                    except:
                        print(f"    Body (first 300): {api['body'][:300]}")

            # Show body text snippet
            body = result.get("body_text", "")
            if len(body) > 100:
                print(f"\n  Body snippet: {body[:500].replace(chr(10), ' ')}")

            # Save result
            filepath = f"/pulp/find-job/r44_{key}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved to {filepath}")

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
