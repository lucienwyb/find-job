#!/usr/bin/env python3
"""Final targeted check - Feishu API timestamps + Cambricon job list dates."""
import asyncio
import re
import json
from playwright.async_api import async_playwright

TARGET_KEYWORDS = ["内核", "系统", "嵌入式", "eBPF", "Agent", "Infra", "基础设施",
                     "平台", "后端", "C++", "Rust", "底层", "驱动", "runtime",
                     "编译", "操作系统", "虚拟化", "分布式", "架构", "高性能",
                     "存储", "网络", "安全", "GPU", "CUDA", "推理", "训练",
                     "机器人", "控制", "SLAM", "运动", "感知", "规划"]

async def check_feishu_jobs_api(page, base_url, name):
    """Check feishu hire portal - capture full API response with timestamps."""
    print(f"\n{'='*60}")
    print(f"{name} - Feishu API job check with timestamps")
    try:
        api_data = []

        async def handle_response(response):
            url = response.url
            if 'search/job/posts' in url:
                try:
                    body = await response.text()
                    api_data.append(('search', url, body))
                except:
                    pass

        page.on("response", handle_response)

        await page.goto(base_url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # Click 职位 if needed
        for selector in ["text=职位", "a:has-text('职位')"]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    break
            except:
                continue

        # Wait for API
        await page.wait_for_timeout(3000)

        # If no API captured, try loading page 2
        if not api_data:
            # Try clicking next page or loading all
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

        # Try paginating through all jobs
        for offset in range(10, 100, 10):
            try:
                # Look for page numbers and click next
                next = await page.query_selector(f"text={offset//10 + 1}")
                if next:
                    await next.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
            except:
                break

        print(f"\n--- API responses ({len(api_data)}) ---")
        all_jobs = []
        for api_type, url, body in api_data:
            try:
                data = json.loads(body)
                if 'data' in data and 'job_post_list' in data['data']:
                    posts = data['data']['job_post_list']
                    print(f"\n  Found {len(posts)} jobs in API response")
                    for post in posts:
                        title = post.get('title', '')
                        post_id = post.get('id', '')
                        # Look for timestamp fields
                        create_time = post.get('create_time', '')
                        update_time = post.get('update_time', '')
                        publish_time = post.get('publish_time', '')
                        modify_time = post.get('modify_time', '')
                        create_timestamp = post.get('create_timestamp', '')
                        # Check all keys for time-related fields
                        time_fields = {k: v for k, v in post.items() if 'time' in k.lower() or 'date' in k.lower() or 'create' in k.lower() or 'update' in k.lower() or 'publish' in k.lower()}
                        all_jobs.append({
                            'title': title,
                            'id': post_id,
                            'time_fields': time_fields,
                            'all_keys': list(post.keys())
                        })
            except:
                pass

        print(f"\n--- All jobs ({len(all_jobs)}) ---")
        for job in all_jobs:
            relevant = any(kw.lower() in job['title'].lower() for kw in TARGET_KEYWORDS)
            marker = " ★" if relevant else ""
            print(f"  {job['title']}{marker}")
            if job['time_fields']:
                print(f"    Time fields: {job['time_fields']}")
            else:
                print(f"    No time fields found. Keys: {job['all_keys']}")

    except Exception as e:
        print(f"ERROR: {e}")

async def check_cambricon_list(page):
    """寒武纪 - stay on list page and extract dates from list items."""
    print(f"\n{'='*60}")
    print("寒武纪 Cambricon - list page with dates")
    try:
        await page.goto("https://app.mokahr.com/apply/cambricon/1113", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # DO NOT click any job - stay on list view
        # The list page should show jobs with dates
        # Try clicking 搜索职位 to get to the list view
        # First, let's see what the page looks like

        # Try to click on the job list tab
        for selector in ["text=社会招聘开放职位", "text=搜索职位", "text=职位列表"]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    print(f"  Clicked: {selector}")
                    break
            except:
                continue

        # Get all text and look for dates
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        print(f"\n--- All lines ({len(lines)}) ---")
        for l in lines:
            print(f"  {l}")

        # Look for date patterns
        dates = re.findall(r'(2026[-/]\d{2}[-/]\d{2})', text)
        print(f"\n--- Dates found: {dates}")

        # Look for 发布于 pattern
        for i, line in enumerate(lines):
            if '发布' in line or '2026' in line:
                print(f"  L{i}: {line}")

    except Exception as e:
        print(f"ERROR: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Cambricon
        await check_cambricon_list(page)

        # Feishu portals
        await check_feishu_jobs_api(page, "https://k0fqxcszc9.jobs.feishu.cn/", "星动纪元")
        await check_feishu_jobs_api(page, "https://chitu-ai.jobs.feishu.cn/", "清程极智")
        await check_feishu_jobs_api(page, "https://01ai.jobs.feishu.cn/", "零一万物")

        await browser.close()

asyncio.run(main())
