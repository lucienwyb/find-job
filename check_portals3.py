#!/usr/bin/env python3
"""Deep check recruitment portals - navigate to actual job lists."""
import asyncio
import re
from playwright.async_api import async_playwright

TARGET_KEYWORDS = ["内核", "系统", "嵌入式", "eBPF", "Agent", "Infra", "基础设施",
                     "平台", "后端", "C++", "Rust", "底层", "驱动", "runtime",
                     "编译", "操作系统", "虚拟化", "分布式", "架构", "高性能",
                     "存储", "网络", "安全", "GPU", "CUDA", "推理", "训练",
                     "机器人", "控制", "SLAM", "运动", "感知", "规划"]

async def check_portal_jobs(page, url, name, job_list_url=None):
    """Navigate to job list page and extract all jobs with dates."""
    print(f"\n{'='*60}")
    print(f"Checking {name}: {url}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Try to navigate to job list page
        if job_list_url:
            await page.goto(job_list_url, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
        else:
            # Try clicking "社招职位" or "职位列表" or similar
            for selector in ["text=社招职位", "text=职位列表", "text=热招职位", "text=在招职位",
                           "a:has-text('社招职位')", "a:has-text('职位')", ".job-list", "#job-list"]:
                try:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(3000)
                        print(f"  Clicked: {selector}")
                        break
                except:
                    continue

        # Scroll down to load more
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

        # Try to click "查看更多" or "加载更多"
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

        # Get text
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Extract job titles with dates
        jobs_with_dates = []
        for i, line in enumerate(lines):
            if '发布于' in line:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    date = date_match.group(1)
                    # Find job title - look backwards
                    for j in range(i-1, max(0, i-5), -1):
                        prev = lines[j]
                        if prev and '发布于' not in prev and '急' != prev and '全职' not in prev:
                            jobs_with_dates.append((date, prev))
                            break

        # Print all jobs with dates
        print(f"\n--- Jobs with dates ({len(jobs_with_dates)}) ---")
        for date, title in sorted(jobs_with_dates, reverse=True):
            relevant = any(kw.lower() in title.lower() for kw in TARGET_KEYWORDS)
            marker = " ★" if relevant else ""
            print(f"  {date} | {title}{marker}")

        # Also look for job titles without dates (feishu portals)
        # Print all non-empty lines for context
        print(f"\n--- All non-empty lines ({len(lines)}) ---")
        for l in lines:
            print(f"  {l}")

        # Check for relevant keywords
        relevant_jobs = []
        for i, line in enumerate(lines):
            for kw in TARGET_KEYWORDS:
                if kw.lower() in line.lower():
                    relevant_jobs.append((kw, i, line))
                    break

        print(f"\n--- Relevant lines ({len(relevant_jobs)}) ---")
        for kw, idx, line in relevant_jobs[:30]:
            print(f"  [{kw}] L{idx}: {line}")

        return text
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return ""

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

        # 银河通用 - click into 软件类 job list
        print("\n\n########## 银河通用 ##########")
        await check_portal_jobs(page, "https://app.mokahr.com/apply/yinhetongyong/165929", "银河通用")

        # 智谱 - navigate to job list
        print("\n\n########## 智谱 ##########")
        await check_portal_jobs(page, "https://app.mokahr.com/apply/zphz/148983", "智谱",
                                job_list_url="https://app.mokahr.com/apply/zphz/148983#/jobs")

        # 寒武纪 - need to get full job list with dates
        print("\n\n########## 寒武纪 ##########")
        await check_portal_jobs(page, "https://app.mokahr.com/apply/cambricon/1113", "寒武纪",
                                job_list_url="https://app.mokahr.com/apply/cambricon/1113#/jobs")

        # 星动纪元 feishu v2 - get job list
        print("\n\n########## 星动纪元 ##########")
        await check_portal_jobs(page, "https://k0fqxcszc9.jobs.feishu.cn/", "星动纪元")

        # 清程极智 feishu v2
        print("\n\n########## 清程极智 ##########")
        await check_portal_jobs(page, "https://chitu-ai.jobs.feishu.cn/", "清程极智")

        # 零一万物 feishu
        print("\n\n########## 零一万物 ##########")
        await check_portal_jobs(page, "https://01ai.jobs.feishu.cn/", "零一万物")

        await browser.close()

asyncio.run(main())
