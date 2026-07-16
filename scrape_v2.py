#!/usr/bin/env python3
"""Scrape using Playwright to capture ALL XHR responses including full response bodies."""
import json, time, re
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def scrape_site(p, name, url, site_type, extra_actions=None):
    """Scrape a site capturing all API responses with full bodies."""
    print(f"\n{'='*60}")
    print(f"[{name}] {url}")
    print(f"{'='*60}")

    browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
    context = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    all_responses = []

    def on_response(response):
        url = response.url
        # Skip static assets, sentry, monitoring
        if any(x in url for x in ['.css', '.js', '.png', '.jpg', '.svg', '.ico',
                                   'sentry', 'starling', 'snssdk', 'monitor',
                                   'captcha', 'favicon', '.woff', '.gif']):
            return
        try:
            body = response.json()
            all_responses.append({'url': url, 'body': body, 'status': response.status})
        except:
            # Try text
            try:
                body = response.text()
                if len(body) < 50000:
                    all_responses.append({'url': url, 'body_text': body[:5000], 'status': response.status})
            except:
                pass

    page.on("response", on_response)

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        print(f"  goto error: {e}")

    time.sleep(5)

    # Perform extra actions if specified
    if extra_actions:
        extra_actions(page)

    # Try to click into categories/locations to trigger job list API
    if site_type == 'mokahr':
        # Try to find and click on job category links
        try:
            # Click on all clickable items that might be categories
            items = page.query_selector_all('div, span, a')
            for item in items:
                try:
                    text = item.inner_text().strip()
                    if text and ('软件' in text or '算法' in text or '硬件' in text or
                                 '北京' in text or '内核' in text or '系统' in text or
                                 '驱动' in text or '嵌入式' in text or 'infra' in text.lower() or
                                 'Agent' in text or '平台' in text or '基础' in text):
                        if len(text) < 50:
                            print(f"  Clicking: {text}")
                            item.click()
                            time.sleep(2)
                            break
                except:
                    pass
        except:
            pass

        # Try clicking "查看更多" buttons
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

    elif site_type == 'feishu':
        # Click on location/city to load positions
        try:
            # Try clicking on 北京
            city_els = page.query_selector_all('text=北京')
            for el in city_els[:1]:
                try:
                    el.click()
                    time.sleep(3)
                except:
                    pass
        except:
            pass

        # Scroll to trigger lazy loading
        for _ in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        # Try clicking load more
        try:
            load_more = page.query_selector('text=加载更多')
            if load_more:
                load_more.click()
                time.sleep(2)
        except:
            pass

    elif site_type == 'hotjob':
        # Try to navigate and wait for API
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

    time.sleep(3)

    page.remove_listener("response", on_response)

    # Analyze captured responses
    print(f"\n  Captured {len(all_responses)} API responses")
    all_jobs = []
    seen_ids = set()

    for resp in all_responses:
        url = resp['url']
        body = resp.get('body')

        if body is None:
            continue

        # Deep search for job-like objects
        def extract_jobs(obj, path=""):
            jobs = []
            if isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, dict):
                        name = (item.get('name') or item.get('title') or item.get('jobName') or
                                item.get('position_name') or item.get('jobTitle') or
                                item.get('titleName') or item.get('positionName') or '')
                        if name and isinstance(name, str) and len(name) > 2 and len(name) < 200:
                            # Filter out obvious non-job entries
                            skip = ['captcha', 'js_error', 'http', 'performance', 'resource',
                                    'pageview', 'action', 'blank_screen', 'custom', '隐私', 'protocol',
                                    'privacy']
                            if not any(s in name.lower() for s in skip):
                                job_id = str(item.get('id') or item.get('jobId') or item.get('position_id') or item.get('job_id') or name)
                                if job_id not in seen_ids:
                                    seen_ids.add(job_id)
                                    jobs.append({
                                        'name': name,
                                        'department': str(item.get('department') or item.get('departmentName') or item.get('department_name') or item.get('departmentNameStr') or ''),
                                        'city': str(item.get('city') or item.get('cityName') or item.get('city_name') or item.get('workPlace') or item.get('location') or item.get('cityNameStr') or ''),
                                        'updateTime': str(item.get('updateTime') or item.get('update_time') or item.get('createTime') or item.get('create_time') or item.get('publishDate') or item.get('publish_date') or item.get('publishTime') or item.get('publish_time') or item.get('lastModifyTime') or item.get('modifyTime') or ''),
                                        'id': job_id,
                                    })
                    jobs.extend(extract_jobs(item, f"{path}[{i}]"))
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    jobs.extend(extract_jobs(v, f"{path}.{k}"))
            return jobs

        jobs = extract_jobs(body)
        if jobs:
            print(f"  From {url[:100]}")
            print(f"    Found {len(jobs)} jobs")
            for j in jobs:
                date = j.get('updateTime', '')
                # Format timestamp if numeric
                if date and date.isdigit():
                    ts = int(date)
                    if ts > 1000000000000:  # milliseconds
                        ts = ts // 1000
                    if ts > 1000000000:
                        from datetime import datetime
                        date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                        j['updateTime'] = date
                all_jobs.append(j)
                print(f"    -> {j['name']} | dept={j.get('department','')} | city={j.get('city','')} | date={date}")

    # Also check text responses
    for resp in all_responses:
        if 'body' not in resp and 'body_text' in resp:
            text = resp['body_text']
            # Look for JSON-like job data
            if 'jobName' in text or 'position_name' in text or 'jobTitle' in text:
                print(f"  Text response with job data: {resp['url'][:100]}")
                print(f"    {text[:500]}")

    print(f"\n  TOTAL unique jobs: {len(all_jobs)}")

    # Print API URLs for debugging
    print(f"\n  All API URLs:")
    for resp in all_responses:
        print(f"    [{resp.get('status','?')}] {resp['url'][:150]}")

    context.close()
    browser.close()
    return all_jobs


def main():
    with sync_playwright() as p:
        # 1. Moonshot
        moonshot = scrape_site(p, "月之暗面 Moonshot",
            "https://app.mokahr.com/apply/moonshot/148506", 'mokahr')

        # 2. Yinhe
        yinhe = scrape_site(p, "银河通用 Yinhe",
            "https://app.mokahr.com/social-recruitment/yinhetongyong/165929", 'mokahr')

        # 3. Zhipu
        zhipu = scrape_site(p, "智谱 Zhipu",
            "https://app.mokahr.com/social-recruitment/zphz/148983", 'mokahr')

        # 4. Cambricon
        cambricon = scrape_site(p, "寒武纪 Cambricon",
            "https://app.mokahr.com/apply/cambricon/1113", 'mokahr')

        # 5. Horizon
        horizon = scrape_site(p, "地平线 Horizon",
            "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a", 'hotjob')

        # 6. Robotera
        robotera = scrape_site(p, "星动纪元 Robotera",
            "https://k0fqxcszc9.jobs.feishu.cn", 'feishu')

        # 7. Chitu
        chitu = scrape_site(p, "清程极智 Chitu",
            "https://chitu-ai.jobs.feishu.cn", 'feishu')

        # 8. 01AI
        onai = scrape_site(p, "零一万物 01AI",
            "https://01ai.jobs.feishu.cn", 'feishu')

    # Save
    all_data = {
        'moonshot': moonshot,
        'yinhe': yinhe,
        'zhipu': zhipu,
        'cambricon': cambricon,
        'horizon': horizon,
        'robotera': robotera,
        'chitu': chitu,
        '01ai': onai,
    }
    with open('/pulp/find-job/scrape_r52_v2.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\n\nSaved to /pulp/find-job/scrape_r52_v2.json")

if __name__ == '__main__':
    main()
