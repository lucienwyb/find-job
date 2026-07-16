#!/usr/bin/env python3
"""Targeted check for specific portals that need deeper navigation."""
import asyncio
import re
import json
from playwright.async_api import async_playwright

TARGET_KEYWORDS = ["内核", "系统", "嵌入式", "eBPF", "Agent", "Infra", "基础设施",
                     "平台", "后端", "C++", "Rust", "底层", "驱动", "runtime",
                     "编译", "操作系统", "虚拟化", "分布式", "架构", "高性能",
                     "存储", "网络", "安全", "GPU", "CUDA", "推理", "训练",
                     "机器人", "控制", "SLAM", "运动", "感知", "规划"]

async def check_yinhetongyong(page):
    """银河通用 - click into 软件类 to see job list with dates."""
    print(f"\n{'='*60}")
    print("银河通用 Yinhetongyong - deep job list check")
    try:
        await page.goto("https://app.mokahr.com/apply/yinhetongyong/165929", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Click 软件类 (30 jobs - most likely to have relevant positions)
        try:
            software_link = await page.query_selector("text=软件类")
            if software_link:
                await software_link.click()
                await page.wait_for_timeout(4000)
                print("  Clicked 软件类")
        except:
            print("  Could not click 软件类")

        # Scroll to load more
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

        # Try clicking 查看更多
        for _ in range(10):
            try:
                more = await page.query_selector("text=查看更多职位")
                if more:
                    await more.click()
                    await page.wait_for_timeout(1500)
                else:
                    break
            except:
                break

        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Extract jobs with dates
        jobs_with_dates = []
        for i, line in enumerate(lines):
            if '发布于' in line:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    date = date_match.group(1)
                    for j in range(i-1, max(0, i-5), -1):
                        prev = lines[j]
                        if prev and '发布于' not in prev and '急' != prev and '全职' not in prev:
                            jobs_with_dates.append((date, prev))
                            break

        print(f"\n--- Jobs with dates ({len(jobs_with_dates)}) ---")
        for date, title in sorted(jobs_with_dates, reverse=True):
            relevant = any(kw.lower() in title.lower() for kw in TARGET_KEYWORDS)
            marker = " ★" if relevant else ""
            print(f"  {date} | {title}{marker}")

        print(f"\n--- All lines ({len(lines)}) ---")
        for l in lines:
            print(f"  {l}")

    except Exception as e:
        print(f"ERROR: {e}")

async def check_cambricon(page):
    """寒武纪 - get job list with dates by going to specific URL."""
    print(f"\n{'='*60}")
    print("寒武纪 Cambricon - deep job list check")
    try:
        # Try the direct jobs URL with hash
        await page.goto("https://app.mokahr.com/apply/cambricon/1113", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Try to get all jobs - first look for all job items
        # The page shows ~15 jobs per page. Let's extract dates from job items
        # Try clicking through all pages
        all_jobs = []
        for page_num in range(1, 30):
            text = await page.inner_text("body")
            lines = [l.strip() for l in text.split('\n') if l.strip()]

            for i, line in enumerate(lines):
                if '发布于' in line:
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                    if date_match:
                        date = date_match.group(1)
                        for j in range(i-1, max(0, i-5), -1):
                            prev = lines[j]
                            if prev and '发布于' not in prev and '急' != prev and '全职' not in prev:
                                all_jobs.append((date, prev, page_num))
                                break

            # Try next page
            try:
                next_btn = await page.query_selector(".next:not(.disabled), [class*='next']:not([class*='disabled'])")
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                else:
                    # Try clicking page number
                    next_page = await page.query_selector(f"text={page_num+1}")
                    if next_page:
                        await next_page.click()
                        await page.wait_for_timeout(2000)
                    else:
                        break
            except:
                break

        print(f"\n--- All jobs with dates ({len(all_jobs)}) ---")
        seen = set()
        for date, title, pg in sorted(all_jobs, key=lambda x: x[0], reverse=True):
            key = f"{date}_{title}"
            if key not in seen:
                seen.add(key)
                relevant = any(kw.lower() in title.lower() for kw in TARGET_KEYWORDS)
                marker = " ★" if relevant else ""
                print(f"  {date} | {title}{marker}")

        # Also print current page text
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        print(f"\n--- Current page lines ({len(lines)}) ---")
        for l in lines:
            print(f"  {l}")

    except Exception as e:
        print(f"ERROR: {e}")

async def check_feishu_api(page, base_url, name):
    """Check feishu hire portal via XHR API for job list with dates."""
    print(f"\n{'='*60}")
    print(f"{name} - Feishu API check")
    try:
        # Capture XHR requests
        api_responses = []

        async def handle_response(response):
            url = response.url
            if 'api' in url or 'position' in url or 'job' in url:
                try:
                    body = await response.text()
                    if body and len(body) > 10:
                        api_responses.append((url, body[:5000]))
                except:
                    pass

        page.on("response", handle_response)

        await page.goto(base_url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # Try clicking 职位
        for selector in ["text=职位", "text=探索职位", "a:has-text('职位')"]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    break
            except:
                continue

        # Scroll to load
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

        print(f"\n--- API responses ({len(api_responses)}) ---")
        for url, body in api_responses:
            print(f"\n  URL: {url}")
            # Try to parse JSON
            try:
                data = json.loads(body)
                print(f"  JSON keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                # Look for job/position data
                if isinstance(data, dict):
                    for key in ['data', 'positions', 'jobs', 'position_list', 'job_list']:
                        if key in data:
                            print(f"  {key}: {str(data[key])[:500]}")
            except:
                # Print raw text, looking for dates
                dates = re.findall(r'(2026[-/]\d{2}[-/]\d{2})', body)
                if dates:
                    print(f"  Dates found: {dates}")
                print(f"  Body preview: {body[:500]}")

        # Get page text
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        print(f"\n--- Page text ({len(lines)} lines) ---")
        for l in lines[:100]:
            print(f"  {l}")

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

        # 银河通用
        await check_yinhetongyong(page)

        # 寒武纪
        await check_cambricon(page)

        # Feishu portals - try API approach
        await check_feishu_api(page, "https://k0fqxcszc9.jobs.feishu.cn/", "星动纪元")
        await check_feishu_api(page, "https://chitu-ai.jobs.feishu.cn/", "清程极智")
        await check_feishu_api(page, "https://01ai.jobs.feishu.cn/", "零一万物")

        await browser.close()

asyncio.run(main())
