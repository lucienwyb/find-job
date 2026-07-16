#!/usr/bin/env python3
"""Scrape career portals for 7 companies using playwright."""
import json
import os
import time
import re
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

COMPANIES = {
    "4paradigm": {
        "name": "第四范式 (4Paradigm)",
        "urls": [
            "https://app.mokahr.com/apply/4paradigm",
            "https://www.4paradigm.com/about/",
        ],
    },
    "modelbest": {
        "name": "面壁智能 (ModelBest)",
        "urls": [
            "https://www.modelbest.cn/",
            "https://app.mokahr.com/apply/modelbest",
        ],
    },
    "deepglint": {
        "name": "格灵深瞳 (Deepglint)",
        "urls": [
            "https://www.deepglint.com/joinus/",
            "https://app.mokahr.com/apply/deepglint",
        ],
    },
    "dptechnology": {
        "name": "深势科技 (DP Technology)",
        "urls": [
            "https://www.dptechnology.com.cn/",
            "https://www.dptechnology.com.cn/careers",
            "https://www.dptechnology.com.cn/joinus",
        ],
    },
    "geovis": {
        "name": "中科星图 (GEO)",
        "urls": [
            "https://www.geovis.com.cn/",
        ],
    },
    "baichuan": {
        "name": "百川智能 (Baichuan)",
        "urls": [
            "https://www.baichuan-ai.com/",
        ],
    },
    "cambricon": {
        "name": "寒武纪 (Cambricon)",
        "urls": [
            "https://www.cambricon.com/",
        ],
    },
}

KEYWORDS = [
    "kernel", "ebpf", "系统", "infra", "基础设施", "架构", "嵌入式", "embedded",
    "edge", "边缘", "driver", "驱动", "platform", "平台", "OS", "操作系统",
    "runtime", "容器", "container", "虚拟化", "virtualization", "agent",
    "training", "推理", "inference", "HPC", "高性能计算", "cuda", "gpu",
    "底层", "low-level", "system", "芯片", "chip", "编译器", "compiler",
    "调度", "schedule", "分布式", "distributed", "存储", "storage",
    "RDMA", "nccl", "kubernetes", "k8s", "云原生", "cloud-native",
]


def extract_jobs_from_page(page):
    """Extract job listings from rendered page."""
    jobs = []
    # Try to find job listings in various formats
    # Method 1: Look for job cards/list items
    job_selectors = [
        '[class*="job"]', '[class*="position"]', '[class*="Job"]',
        '[class*="Position"]', '[data-job-id]', '[class*="recruit"]',
        '[class*="career"]', '.job-item', '.position-item',
        '[class*="vacancy"]', '[class*="opening"]',
    ]
    for selector in job_selectors:
        try:
            elements = page.query_selector_all(selector)
            for el in elements:
                text = el.inner_text().strip()
                if text and len(text) > 10:
                    jobs.append(text[:500])
        except:
            pass
    return list(set(jobs))  # dedupe


def capture_api_responses(page, url):
    """Capture API responses that contain job data."""
    api_data = []

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                body = response.text()
                if body and len(body) > 50:
                    # Check if it looks like job data
                    lower = body.lower()
                    if any(k in lower for k in ['job', 'position', 'recruit', 'title', 'department']):
                        api_data.append({
                            'url': response.url,
                            'body': body[:5000]
                        })
        except:
            pass

    page.on("response", handle_response)
    return api_data


def scrape_company(browser, key, config):
    """Scrape a single company's career portal."""
    results = {
        "company": config["name"],
        "key": key,
        "urls_tried": [],
        "portal_accessible": False,
        "total_positions": 0,
        "matching_positions": [],
        "recent_positions": [],
        "page_text": "",
        "api_data": [],
        "error": None,
    }

    for url in config["urls"]:
        page = browser.new_page()
        api_data = []

        def handle_response(response):
            try:
                ct = response.headers.get('content-type', '')
                if 'json' in ct:
                    body = response.text()
                    if body and len(body) > 50:
                        lower = body.lower()
                        if any(k in lower for k in ['job', 'position', 'recruit', 'title', 'department', 'vacanc', 'opening']):
                            api_data.append({
                                'url': response.url[:300],
                                'body': body[:8000]
                            })
            except:
                pass

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)  # extra time for SPA rendering

            title = page.title()
            body_text = page.inner_text("body")
            results["urls_tried"].append({
                "url": url,
                "status": "ok",
                "title": title,
                "body_length": len(body_text),
            })

            # Check if portal is accessible (not error page)
            if "页面不存在" in body_text or "已关停" in body_text or "404" in title:
                results["urls_tried"][-1]["status"] = "error_page"
            else:
                results["portal_accessible"] = True
                results["page_text"] = body_text[:10000]

            # Add captured API data
            if api_data:
                results["api_data"].extend(api_data)

            # Extract jobs from page
            jobs = extract_jobs_from_page(page)
            if jobs:
                results["page_jobs"] = jobs

        except Exception as e:
            results["urls_tried"].append({
                "url": url,
                "status": "error",
                "error": str(e)[:200],
            })
        finally:
            page.close()

    return results


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
        )

        all_results = {}
        for key, config in COMPANIES.items():
            print(f"\n{'='*60}")
            print(f"Scraping: {config['name']}")
            print(f"{'='*60}")

            result = scrape_company(browser, key, config)
            all_results[key] = result

            # Save individual results
            filepath = f"/pulp/find-job/r44_{key}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Saved to {filepath}")

            # Quick summary
            print(f"  Portal accessible: {result['portal_accessible']}")
            print(f"  API data entries: {len(result.get('api_data', []))}")
            print(f"  Page text length: {len(result.get('page_text', ''))}")

        # Save combined results
        with open("/pulp/find-job/r44_all_results.json", 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        browser.close()

    print("\n\nDone! Results saved to /pulp/find-job/r44_*.json")


if __name__ == "__main__":
    main()
