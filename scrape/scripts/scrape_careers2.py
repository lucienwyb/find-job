#!/usr/bin/env python3
"""Scrape career portals for 7 companies using playwright - v2."""
import json
import os
import time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

COMPANIES = {
    "4paradigm": {
        "name": "第四范式 (4Paradigm)",
        "urls": [
            "https://www.4paradigm.com/about/",
            "https://www.4paradigm.com/",
            "https://app.mokahr.com/apply/4paradigm",
        ],
    },
    "modelbest": {
        "name": "面壁智能 (ModelBest)",
        "urls": [
            "https://www.modelbest.cn/",
            "https://www.modelbest.cn/about",
            "https://www.modelbest.cn/about.html",
            "https://www.modelbest.cn/join-us",
        ],
    },
    "deepglint": {
        "name": "格灵深瞳 (Deepglint)",
        "urls": [
            "https://www.deepglint.com/joinus/",
            "https://www.deepglint.com/",
        ],
    },
    "dptechnology": {
        "name": "深势科技 (DP Technology)",
        "urls": [
            "https://www.dptechnology.com.cn/careers",
            "https://www.dptechnology.com.cn/",
        ],
    },
    "geovis": {
        "name": "中科星图 (GEO)",
        "urls": [
            "https://www.geovis.com.cn/",
            "https://www.geovis.com.cn/about/",
        ],
    },
    "baichuan": {
        "name": "百川智能 (Baichuan)",
        "urls": [
            "https://www.baichuan-ai.com/",
            "https://www.baichuan-ai.com/about",
            "https://www.baichuan-ai.com/about/",
            "https://www.baichuan-ai.com/career",
            "https://www.baichuan-ai.com/joinus",
        ],
    },
    "cambricon": {
        "name": "寒武纪 (Cambricon)",
        "urls": [
            "https://www.cambricon.com/",
            "https://www.cambricon.com/about/",
            "https://www.cambricon.com/careers",
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


def scrape_url(page, url):
    """Scrape a single URL, capturing API responses."""
    api_data = []

    def handle_response(response):
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                body = response.text()
                if body and len(body) > 100:
                    lower = body.lower()
                    if any(k in lower for k in ['job', 'position', 'recruit', 'department', 'vacanc', 'opening', 'hire']):
                        api_data.append({
                            'url': response.url[:300],
                            'body': body[:15000]
                        })
        except:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(5)  # Wait for SPA rendering

        title = page.title()
        try:
            body_text = page.inner_text("body")
        except:
            body_text = ""

        return {
            "url": url,
            "status": "ok",
            "title": title,
            "body_length": len(body_text),
            "body_text": body_text[:20000],
            "api_data": api_data,
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "error": str(e)[:300],
            "api_data": api_data,
        }


def analyze_results(result):
    """Analyze scraped results for matching positions."""
    matches = []
    all_text = result.get("body_text", "")
    api_text = ""

    # Check API data for job listings
    for api in result.get("api_data", []):
        api_text += api.get("body", "") + "\n"

    combined = all_text + "\n" + api_text

    # Search for keywords
    for kw in KEYWORDS:
        if kw.lower() in combined.lower():
            # Find surrounding context
            idx = combined.lower().find(kw.lower())
            start = max(0, idx - 100)
            end = min(len(combined), idx + 200)
            context = combined[start:end].replace("\n", " ").strip()
            matches.append({"keyword": kw, "context": context})

    # Count total positions (look for patterns like job titles)
    position_count = 0
    for api in result.get("api_data", []):
        try:
            data = json.loads(api["body"])
            # Try to find job count
            if isinstance(data, dict):
                if "totalCount" in data:
                    position_count = max(position_count, data["totalCount"])
                if "total" in data:
                    position_count = max(position_count, data["total"])
                if "data" in data and isinstance(data["data"], dict):
                    if "totalCount" in data["data"]:
                        position_count = max(position_count, data["data"]["totalCount"])
                    if "total" in data["data"]:
                        position_count = max(position_count, data["data"]["total"])
        except:
            pass

    return {
        "keyword_matches": matches[:30],
        "estimated_total_positions": position_count,
    }


def main():
    os.makedirs("/pulp/find-job", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        all_results = {}
        for key, config in COMPANIES.items():
            print(f"\n{'='*60}")
            print(f"Scraping: {config['name']}")
            print(f"{'='*60}")

            result = {
                "company": config["name"],
                "key": key,
                "urls_tried": [],
                "portal_accessible": False,
                "body_text": "",
                "api_data": [],
            }

            for url in config["urls"]:
                page = browser.new_page()
                r = scrape_url(page, url)
                result["urls_tried"].append({k: v for k, v in r.items() if k not in ["body_text", "api_data"]})

                if r["status"] == "ok":
                    if "页面不存在" not in r.get("body_text", "") and "已关停" not in r.get("title", "") and "404" not in r.get("title", ""):
                        result["portal_accessible"] = True
                        result["body_text"] = r.get("body_text", "")
                        result["api_data"] = r.get("api_data", [])
                        page.close()
                        break  # Found a working page

                for api in r.get("api_data", []):
                    result["api_data"].append(api)

                page.close()

            # Analyze
            analysis = analyze_results(result)
            result["analysis"] = analysis

            filepath = f"/pulp/find-job/r44_{key}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  Portal accessible: {result['portal_accessible']}")
            print(f"  API data entries: {len(result.get('api_data', []))}")
            print(f"  Keyword matches: {len(analysis['keyword_matches'])}")
            print(f"  Est. positions: {analysis['estimated_total_positions']}")
            print(f"Saved to {filepath}")

            all_results[key] = result

        with open("/pulp/find-job/r44_all_results.json", 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        browser.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
