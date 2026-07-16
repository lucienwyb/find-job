#!/usr/bin/env python3
"""Scrape all recruitment portals for new jobs after 2025-07-16."""
import json, time, re, sys
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"

# Keywords for matching (kernel/system/embedded/eBPF/Agent/Infra)
KEYWORDS = [
    '内核', 'kernel', 'eBPF', 'ebpf', 'BPF', '系统软件', 'system software',
    '嵌入式', 'embedded', 'BSP', '驱动', 'driver', '存储', 'storage',
    '分布式', 'distributed', 'Agent', 'infra', 'Infra', '基础设施',
    '虚拟化', 'virtualization', '容器', 'container', 'Runtime',
    '高性能', 'high performance', '底层', 'low-level', '操作系统',
    'OS', '固件', 'firmware', '硬件', 'hardware', '异构', '加速',
    '编译器', 'compiler', 'CUDA', '算子', 'op',
]

def match_job(title, desc=""):
    text = (title + " " + desc).lower()
    for kw in KEYWORDS:
        if kw.lower() in text:
            return True
    return False

def parse_date(s):
    """Try to parse various date formats."""
    if not s:
        return None
    # Try YYYY-MM-DD
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(s))
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # Try YYYY/MM/DD
    m = re.search(r'(\d{4})/(\d{2})/(\d{2})', str(s))
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return str(s)

def is_after_716(date_str):
    """Check if date is after 2025-07-16."""
    if not date_str:
        return False
    d = parse_date(date_str)
    if d and d >= "2025-07-16":
        return True
    return False

def scrape_mokahr(page, url, name, page_count=10):
    """Scrape mokahr site - capture XHR API calls."""
    jobs = []

    # Intercept API responses
    api_responses = []

    def handle_response(response):
        if '/api/' in response.url and 'job' in response.url.lower():
            try:
                body = response.json()
                api_responses.append(body)
            except:
                pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except:
        pass

    time.sleep(3)

    # Try to get jobs from intercepted API responses
    for resp in api_responses:
        if isinstance(resp, dict) and 'data' in resp:
            data = resp['data']
            if isinstance(data, dict):
                job_list = data.get('jobList') or data.get('list') or data.get('jobs') or []
                for j in job_list:
                    jobs.append({
                        'name': j.get('name') or j.get('title') or '',
                        'department': j.get('department') or j.get('departmentName') or '',
                        'city': j.get('city') or j.get('cityName') or '',
                        'updateTime': j.get('updateTime') or j.get('createTime') or j.get('publishDate') or '',
                        'id': j.get('id') or j.get('jobId') or '',
                    })

    # Also try to extract from DOM
    if not jobs:
        try:
            # Wait for job list to render
            page.wait_for_selector('[class*="job"], [class*="position"], [class*="Job"]', timeout=10000)
        except:
            pass

        # Try various selectors
        for selector in ['[class*="job-item"]', '[class*="position-item"]', '.job-list-item', '[data-job-id]']:
            elements = page.query_selector_all(selector)
            if elements:
                for el in elements:
                    try:
                        text = el.inner_text()
                        jobs.append({'name': text[:200], 'department': '', 'city': '', 'updateTime': '', 'id': ''})
                    except:
                        pass
                break

    # If we have pagination, try more pages
    total_from_api = 0
    for resp in api_responses:
        if isinstance(resp, dict) and 'data' in resp and isinstance(resp['data'], dict):
            total_from_api = resp['data'].get('totalCount', 0) or resp['data'].get('total', 0)

    # Try clicking through pages for more jobs
    if jobs and len(jobs) < total_from_api and total_from_api > 0:
        for p in range(2, min(page_count + 1, (total_from_api // 20) + 2)):
            try:
                # Click next page
                next_btn = page.query_selector('[class*="next"], [class*="pagination"] [class*="next"]')
                if next_btn:
                    next_btn.click()
                    time.sleep(2)
                    # Re-capture
                    for resp in api_responses[-1:]:
                        pass  # Already captured by handler
            except:
                pass

    page.remove_listener("response", handle_response)

    return {
        'site': name,
        'url': url,
        'total_from_api': total_from_api,
        'jobs_found': len(jobs),
        'jobs': jobs,
    }

def scrape_feishu(page, url, name):
    """Scrape Feishu Hire site."""
    jobs = []
    api_responses = []

    def handle_response(response):
        if 'api' in response.url.lower() or 'position' in response.url.lower() or 'job' in response.url.lower():
            try:
                body = response.json()
                if isinstance(body, dict) and 'data' in body:
                    api_responses.append(body)
            except:
                pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except:
        pass

    time.sleep(5)

    # Scroll to load more
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Extract from API responses
    for resp in api_responses:
        if isinstance(resp, dict) and 'data' in resp:
            data = resp['data']
            if isinstance(data, dict):
                positions = data.get('positions') or data.get('job_list') or data.get('list') or data.get('jobs') or []
                if isinstance(positions, list):
                    for j in positions:
                        jobs.append({
                            'name': j.get('name') or j.get('title') or j.get('position_name') or '',
                            'department': j.get('department') or j.get('department_name') or '',
                            'city': j.get('city') or j.get('city_name') or j.get('location') or '',
                            'updateTime': j.get('update_time') or j.get('create_time') or j.get('publish_time') or '',
                            'id': j.get('id') or j.get('position_id') or '',
                        })
            elif isinstance(data, list):
                for j in data:
                    jobs.append({
                        'name': j.get('name') or j.get('title') or '',
                        'department': j.get('department') or '',
                        'city': j.get('city') or '',
                        'updateTime': j.get('update_time') or j.get('create_time') or '',
                        'id': j.get('id') or '',
                    })

    # Also try DOM extraction
    if not jobs:
        try:
            elements = page.query_selector_all('[class*="position"], [class*="job-item"], [class*="card"]')
            for el in elements:
                try:
                    text = el.inner_text()
                    if len(text) > 5 and len(text) < 300:
                        jobs.append({'name': text[:200], 'department': '', 'city': '', 'updateTime': '', 'id': ''})
                except:
                    pass
        except:
            pass

    page.remove_listener("response", handle_response)
    return {
        'site': name,
        'url': url,
        'jobs_found': len(jobs),
        'jobs': jobs,
    }

def scrape_hotjob(page, url, name):
    """Scrape hotjob.cn site."""
    jobs = []
    api_responses = []

    def handle_response(response):
        if 'api' in response.url.lower() or 'job' in response.url.lower():
            try:
                body = response.json()
                api_responses.append({'url': response.url, 'body': body})
            except:
                pass

    page.on("response", handle_response)

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except:
        pass

    time.sleep(3)

    # Extract from API
    for resp in api_responses:
        body = resp['body']
        if isinstance(body, dict):
            data = body.get('data') or body
            if isinstance(data, dict):
                job_list = data.get('jobList') or data.get('list') or data.get('jobs') or data.get('items') or []
                if isinstance(job_list, list):
                    for j in job_list:
                        jobs.append({
                            'name': j.get('name') or j.get('title') or j.get('jobName') or '',
                            'department': j.get('department') or j.get('departmentName') or '',
                            'city': j.get('city') or j.get('cityName') or j.get('workPlace') or '',
                            'updateTime': j.get('updateTime') or j.get('createTime') or j.get('publishDate') or j.get('lastModifyTime') or '',
                            'id': j.get('id') or j.get('jobId') or '',
                        })

    page.remove_listener("response", handle_response)
    return {
        'site': name,
        'url': url,
        'jobs_found': len(jobs),
        'jobs': jobs,
    }


def main():
    sites = [
        # Mokahr sites
        {
            'type': 'mokahr',
            'name': '月之暗面 Moonshot',
            'url': 'https://app.mokahr.com/apply/moonshot/148506',
        },
        {
            'type': 'mokahr',
            'name': '银河通用 Yinhe',
            'url': 'https://app.mokahr.com/social-recruitment/yinhetongyong/165929',
        },
        {
            'type': 'mokahr',
            'name': '智谱 Zhipu',
            'url': 'https://app.mokahr.com/social-recruitment/zphz/148983',
        },
        {
            'type': 'mokahr',
            'name': '寒武纪 Cambricon',
            'url': 'https://app.mokahr.com/apply/cambricon/1113',
        },
        # Hotjob site
        {
            'type': 'hotjob',
            'name': '地平线 Horizon',
            'url': 'https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a',
        },
        # Feishu sites
        {
            'type': 'feishu',
            'name': '星动纪元 Robotera',
            'url': 'https://k0fqxcszc9.jobs.feishu.cn',
        },
        {
            'type': 'feishu',
            'name': '清程极智 Chitu',
            'url': 'https://chitu-ai.jobs.feishu.cn',
        },
        {
            'type': 'feishu',
            'name': '零一万物 01AI',
            'url': 'https://01ai.jobs.feishu.cn',
        },
    ]

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": PROXY}
        )

        for site in sites:
            print(f"\n{'='*60}")
            print(f"Scraping: {site['name']}")
            print(f"URL: {site['url']}")
            print(f"{'='*60}")

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                if site['type'] == 'mokahr':
                    result = scrape_mokahr(page, site['url'], site['name'])
                elif site['type'] == 'feishu':
                    result = scrape_feishu(page, site['url'], site['name'])
                elif site['type'] == 'hotjob':
                    result = scrape_hotjob(page, site['url'], site['name'])

                results.append(result)

                # Print summary
                print(f"Total from API: {result.get('total_from_api', 'N/A')}")
                print(f"Jobs found: {result['jobs_found']}")

                # Show matching jobs
                matched = []
                for j in result['jobs']:
                    if match_job(j.get('name', '')):
                        matched.append(j)
                        date = j.get('updateTime', '')
                        print(f"  MATCH: {j['name']} | dept={j.get('department','')} | city={j.get('city','')} | date={date}")

                # Show dates
                dates = [j.get('updateTime','') for j in result['jobs'] if j.get('updateTime')]
                if dates:
                    print(f"  Date range: {min(dates)} ~ {max(dates)}")

                # Show all jobs if few
                if result['jobs_found'] <= 30:
                    for j in result['jobs']:
                        print(f"  - {j['name']} | {j.get('department','')} | {j.get('city','')} | {j.get('updateTime','')}")

            except Exception as e:
                print(f"ERROR: {e}")
                results.append({'site': site['name'], 'error': str(e), 'jobs': []})

            context.close()
            time.sleep(1)

        browser.close()

    # Save full results
    with open('/pulp/find-job/scrape_results_r52.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n\nResults saved to /pulp/find-job/scrape_results_r52.json")

if __name__ == '__main__':
    main()
