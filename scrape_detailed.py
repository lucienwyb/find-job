#!/usr/bin/env python3
"""Deep scrape: capture all XHR/API responses with full job details."""
import json, time, re
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def capture_all_api(page):
    """Capture all API responses."""
    api_data = []

    def on_response(response):
        url = response.url
        ct = response.headers.get('content-type', '')
        if 'json' in ct or 'api' in url.lower():
            try:
                body = response.json()
                api_data.append({'url': url, 'body': body})
            except:
                pass

    page.on("response", on_response)
    return api_data, on_response

def find_jobs_in_json(obj, depth=0):
    """Recursively find job-like lists in JSON."""
    results = []
    if depth > 5:
        return results
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                # Check if this looks like a job
                name = item.get('name') or item.get('title') or item.get('jobName') or item.get('position_name') or item.get('jobTitle') or ''
                if name and len(str(name)) > 2 and len(str(name)) < 200:
                    results.append({
                        'name': str(name),
                        'department': str(item.get('department') or item.get('departmentName') or item.get('department_name') or ''),
                        'city': str(item.get('city') or item.get('cityName') or item.get('city_name') or item.get('workPlace') or item.get('location') or ''),
                        'updateTime': str(item.get('updateTime') or item.get('update_time') or item.get('createTime') or item.get('create_time') or item.get('publishDate') or item.get('publish_date') or item.get('publishTime') or item.get('lastModifyTime') or ''),
                        'id': str(item.get('id') or item.get('jobId') or item.get('position_id') or item.get('job_id') or ''),
                    })
            results.extend(find_jobs_in_json(item, depth+1))
    elif isinstance(obj, dict):
        for v in obj.values():
            results.extend(find_jobs_in_json(v, depth+1))
    return results

def scrape_mokahr_detailed(p, name, url):
    """Scrape mokahr with category clicking."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    api_data, handler = capture_all_api(page)

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except:
        pass
    time.sleep(5)

    # Click on categories to load jobs
    categories = page.query_selector_all('[class*="category"], [class*="filter"], [class*="tab"]')
    print(f"Found {len(categories)} category/tab elements")

    # Try clicking into job categories
    # For mokahr, the job list is loaded via API when you click a category
    # Let's try clicking all clickable elements that look like job categories
    clickable = page.query_selector_all('div[class*="job"], span[class*="job"], div[class*="position"], a[class*="position"]')
    print(f"Found {len(clickable)} clickable job elements")

    # Scroll to load more
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Also try clicking "查看更多" or "展开" buttons
    try:
        more_btns = page.query_selector_all('text=查看更多')
        for btn in more_btns:
            try:
                btn.click()
                time.sleep(2)
            except:
                pass
    except:
        pass

    # Try clicking category links
    try:
        cat_links = page.query_selector_all('[class*="category-item"], [class*="filter-item"], [class*="tab-item"]')
        for link in cat_links[:10]:  # Limit to first 10 categories
            try:
                link.click()
                time.sleep(2)
            except:
                pass
    except:
        pass

    time.sleep(2)

    # Now extract all jobs from captured API responses
    all_jobs = []
    seen_names = set()
    for resp in api_data:
        jobs = find_jobs_in_json(resp['body'])
        for j in jobs:
            if j['name'] not in seen_names:
                seen_names.add(j['name'])
                all_jobs.append(j)

    page.remove_listener("response", handler)

    # Also try to get jobs from DOM
    if not all_jobs:
        # Try various DOM selectors
        for sel in ['[class*="job-name"]', '[class*="position-name"]', '[class*="job-title"]',
                     '[class*="JobName"]', '[class*="PositionName"]', '.job-card', '[class*="card"]']:
            els = page.query_selector_all(sel)
            if els:
                for el in els:
                    try:
                        text = el.inner_text().strip()
                        if text and len(text) > 2 and len(text) < 200 and text not in seen_names:
                            seen_names.add(text)
                            all_jobs.append({'name': text, 'department': '', 'city': '', 'updateTime': '', 'id': ''})
                    except:
                        pass

    # Print API URLs for debugging
    print(f"API calls captured: {len(api_data)}")
    for resp in api_data[:5]:
        print(f"  API: {resp['url'][:120]}")

    print(f"\nTotal unique jobs: {len(all_jobs)}")

    # Print all jobs with dates
    for j in all_jobs:
        date = j.get('updateTime', '')
        print(f"  - {j['name']} | dept={j.get('department','')} | city={j.get('city','')} | date={date}")

    context.close()
    browser.close()
    return all_jobs

def scrape_feishu_detailed(p, name, url):
    """Scrape feishu hire site with pagination."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    api_data, handler = capture_all_api(page)

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except:
        pass
    time.sleep(5)

    # Click into location/category to load jobs
    try:
        loc_links = page.query_selector_all('[class*="location"], [class*="city"], [class*="category"]')
        for link in loc_links[:5]:
            try:
                link.click()
                time.sleep(2)
            except:
                pass
    except:
        pass

    # Scroll to load all positions
    for _ in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Try clicking "加载更多" or pagination
    for _ in range(5):
        try:
            more = page.query_selector('text=加载更多')
            if more:
                more.click()
                time.sleep(2)
            else:
                break
        except:
            break

    time.sleep(2)

    # Extract from API
    all_jobs = []
    seen_names = set()
    for resp in api_data:
        jobs = find_jobs_in_json(resp['body'])
        for j in jobs:
            if j['name'] not in seen_names:
                seen_names.add(j['name'])
                all_jobs.append(j)

    page.remove_listener("response", handler)

    # DOM fallback
    if not all_jobs:
        for sel in ['[class*="position-name"]', '[class*="job-name"]', '[class*="title"]',
                     '[class*="PositionName"]', '[class*="card-title"]']:
            els = page.query_selector_all(sel)
            if els:
                for el in els:
                    try:
                        text = el.inner_text().strip()
                        if text and len(text) > 2 and len(text) < 200 and text not in seen_names:
                            seen_names.add(text)
                            all_jobs.append({'name': text, 'department': '', 'city': '', 'updateTime': '', 'id': ''})
                    except:
                        pass

    print(f"API calls captured: {len(api_data)}")
    for resp in api_data[:10]:
        print(f"  API: {resp['url'][:150]}")

    print(f"\nTotal unique jobs: {len(all_jobs)}")
    for j in all_jobs:
        date = j.get('updateTime', '')
        print(f"  - {j['name']} | dept={j.get('department','')} | city={j.get('city','')} | date={date}")

    context.close()
    browser.close()
    return all_jobs

def scrape_hotjob_detailed(p, name, url):
    """Scrape hotjob.cn site."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    api_data, handler = capture_all_api(page)

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except:
        pass
    time.sleep(5)

    # Scroll
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    # Try pagination
    for _ in range(10):
        try:
            next_btn = page.query_selector('[class*="next"], [class*="pagination-next"]')
            if next_btn:
                next_btn.click()
                time.sleep(2)
            else:
                break
        except:
            break

    time.sleep(2)

    # Extract from API
    all_jobs = []
    seen_names = set()
    for resp in api_data:
        jobs = find_jobs_in_json(resp['body'])
        for j in jobs:
            if j['name'] not in seen_names:
                seen_names.add(j['name'])
                all_jobs.append(j)

    page.remove_listener("response", handler)

    print(f"API calls captured: {len(api_data)}")
    for resp in api_data[:10]:
        print(f"  API: {resp['url'][:150]}")

    print(f"\nTotal unique jobs: {len(all_jobs)}")
    for j in all_jobs[:50]:
        date = j.get('updateTime', '')
        print(f"  - {j['name']} | dept={j.get('department','')} | city={j.get('city','')} | date={date}")

    if len(all_jobs) > 50:
        print(f"  ... and {len(all_jobs)-50} more")

    context.close()
    browser.close()
    return all_jobs


def main():
    with sync_playwright() as p:
        # 1. Moonshot
        moonshot_jobs = scrape_mokahr_detailed(p, "月之暗面 Moonshot",
            "https://app.mokahr.com/apply/moonshot/148506")

        # 2. Yinhe
        yinhe_jobs = scrape_mokahr_detailed(p, "银河通用 Yinhe",
            "https://app.mokahr.com/social-recruitment/yinhetongyong/165929")

        # 3. Zhipu
        zhipu_jobs = scrape_mokahr_detailed(p, "智谱 Zhipu",
            "https://app.mokahr.com/social-recruitment/zphz/148983")

        # 4. Cambricon
        cambricon_jobs = scrape_mokahr_detailed(p, "寒武纪 Cambricon",
            "https://app.mokahr.com/apply/cambricon/1113")

        # 5. Horizon
        horizon_jobs = scrape_hotjob_detailed(p, "地平线 Horizon",
            "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a")

        # 6. Robotera
        robotera_jobs = scrape_feishu_detailed(p, "星动纪元 Robotera",
            "https://k0fqxcszc9.jobs.feishu.cn")

        # 7. Chitu
        chitu_jobs = scrape_feishu_detailed(p, "清程极智 Chitu",
            "https://chitu-ai.jobs.feishu.cn")

        # 8. 01AI
        onai_jobs = scrape_feishu_detailed(p, "零一万物 01AI",
            "https://01ai.jobs.feishu.cn")

    # Save
    all_data = {
        'moonshot': moonshot_jobs,
        'yinhe': yinhe_jobs,
        'zhipu': zhipu_jobs,
        'cambricon': cambricon_jobs,
        'horizon': horizon_jobs,
        'robotera': robotera_jobs,
        'chitu': chitu_jobs,
        '01ai': onai_jobs,
    }
    with open('/pulp/find-job/scrape_r52_detailed.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\nSaved to /pulp/find-job/scrape_r52_detailed.json")

if __name__ == '__main__':
    main()
