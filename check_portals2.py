#!/usr/bin/env python3
"""Deep check recruitment portals for new job postings after 2026-07-16."""
import asyncio
import re
import json
from playwright.async_api import async_playwright

TARGET_KEYWORDS = ["内核", "系统", "嵌入式", "eBPF", "Agent", "Infra", "基础设施",
                     "平台", "后端", "C++", "Rust", "底层", "驱动", "runtime",
                     "编译", "操作系统", "虚拟化", "分布式", "架构", "高性能",
                     "存储", "网络", "安全", "GPU", "CUDA", "推理", "训练"]

async def deep_check_mokahr(page, url, name):
    """Deep check mokahr portal with search and pagination."""
    print(f"\n{'='*60}")
    print(f"Checking {name}: {url}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        print(f"Page title: {await page.title()}")

        # Try to find and click "查看更多职位" or scroll to load all
        # First, try clicking through all pages
        all_jobs = []

        # Get current visible jobs
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Try to find job card elements
        # Mokahr typically has job items in specific selectors
        job_items = await page.query_selector_all(".job-item, .position-item, [class*='job'], [class*='position'], [class*='Job'], li[class*='item']")
        print(f"Job item elements found: {len(job_items)}")

        # Try clicking "查看更多职位" (view more)
        try:
            more_btn = await page.query_selector("text=查看更多职位")
            if more_btn:
                for i in range(10):  # click up to 10 times
                    await more_btn.click()
                    await page.wait_for_timeout(1500)
                    print(f"  Clicked '查看更多' #{i+1}")
        except Exception as e:
            print(f"  No 'more' button: {e}")

        # Try paginating
        for page_num in range(1, 20):
            try:
                # Look for next page button
                next_btn = await page.query_selector(".next, [class*='next'], button:has-text('下一页'), a:has-text('下一页')")
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                    print(f"  Navigated to page {page_num+1}")
                else:
                    break
            except:
                break

        # Get final text
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        print(f"\n--- All lines ({len(lines)}) ---")
        for l in lines:
            print(f"  {l}")

        # Search for relevant keywords
        relevant = []
        for i, line in enumerate(lines):
            for kw in TARGET_KEYWORDS:
                if kw.lower() in line.lower():
                    relevant.append((kw, i, line))
                    break

        print(f"\n--- Relevant lines ({len(relevant)}) ---")
        for kw, idx, line in relevant:
            print(f"  [{kw}] L{idx}: {line}")

        # Look for dates
        dates = re.findall(r'(2026[-/]\d{2}[-/]\d{2}|\d{4}-\d{2}-\d{2})', text)
        print(f"\n--- Dates found: {dates}")

        return text
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return ""

async def deep_check_feishu(page, url, name):
    """Check feishu hire portal with job list navigation."""
    print(f"\n{'='*60}")
    print(f"Checking {name}: {url}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        print(f"Page title: {await page.title()}")

        # Try to click "职位" or "探索职位" to see job list
        for selector in ["text=职位", "text=探索职位", "text=查看职位", "text=职位列表", "a:has-text('职位')"]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(3000)
                    print(f"  Clicked: {selector}")
                    break
            except:
                continue

        # Get text
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        print(f"\n--- All lines ({len(lines)}) ---")
        for l in lines:
            print(f"  {l}")

        relevant = []
        for i, line in enumerate(lines):
            for kw in TARGET_KEYWORDS:
                if kw.lower() in line.lower():
                    relevant.append((kw, i, line))
                    break

        print(f"\n--- Relevant lines ({len(relevant)}) ---")
        for kw, idx, line in relevant:
            print(f"  [{kw}] L{idx}: {line}")

        dates = re.findall(r'(2026[-/]\d{2}[-/]\d{2}|\d{4}-\d{2}-\d{2})', text)
        print(f"\n--- Dates found: {dates}")

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

        # 1. 月之暗面 mokahr - deep browse
        await deep_check_mokahr(page, "https://app.mokahr.com/apply/moonshot/148506", "月之暗面 Moonshot")

        # 2. 银河通用 mokahr - retry with longer timeout
        await deep_check_mokahr(page, "https://app.mokahr.com/apply/yinhetongyong/165929", "银河通用 Yinhetongyong")

        # 3. 智谱 mokahr - need to navigate to job list
        await deep_check_mokahr(page, "https://app.mokahr.com/apply/zphz/148983", "智谱 Zhipu")

        # 4. 寒武纪 mokahr
        await deep_check_mokahr(page, "https://app.mokahr.com/apply/cambricon/1113", "寒武纪 Cambricon")

        # 5. 星动纪元 feishu - try different URL formats
        await deep_check_feishu(page, "https://jobs.feishu.cn/k0fqxcszc9", "星动纪元 Xingdong (v1)")
        await deep_check_feishu(page, "https://k0fqxcszc9.jobs.feishu.cn/", "星动纪元 Xingdong (v2)")

        # 6. 清程极智 feishu
        await deep_check_feishu(page, "https://jobs.feishu.cn/chitu-ai", "清程极智 Chitu-AI (v1)")
        await deep_check_feishu(page, "https://chitu-ai.jobs.feishu.cn/", "清程极智 Chitu-AI (v2)")

        # 7. 零一万物 feishu
        await deep_check_feishu(page, "https://01ai.jobs.feishu.cn/", "零一万物 01.AI")

        await browser.close()

asyncio.run(main())
