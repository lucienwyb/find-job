#!/usr/bin/env python3
"""Check recruitment portals for new job postings after 2026-07-16."""
import asyncio
import re
import json
from playwright.async_api import async_playwright

async def check_mokahr(page, url, name):
    """Check mokahr portal - necromancer frontend renders DOM as plaintext."""
    print(f"\n{'='*60}")
    print(f"Checking {name}: {url}")
    try:
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Get all job listings text
        content = await page.content()
        text = await page.inner_text("body")

        # Look for job titles with dates and keywords
        # Mokahr typically shows job cards with title, department, location, date
        print(f"Page title: {await page.title()}")
        print(f"Content length: {len(text)}")

        # Extract job listings - look for job-related keywords
        keywords = ["内核", "系统", "嵌入式", "eBPF", "Agent", "Infra", "基础设施",
                     "平台", "后端", "C++", "Rust", "底层", "驱动", "runtime",
                     "编译", "操作系统", "虚拟化", "分布式", "架构"]

        lines = text.split('\n')
        relevant = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) < 3:
                continue
            for kw in keywords:
                if kw.lower() in line_stripped.lower():
                    # Get context (surrounding lines)
                    context_start = max(0, i-2)
                    context_end = min(len(lines), i+5)
                    context = lines[context_start:context_end]
                    relevant.append((kw, context))
                    break

        # Also look for date patterns
        date_patterns = re.findall(r'(2026[-/]\d{2}[-/]\d{2}|\d{2}-\d{2}|\d+天前|今天|昨天)', text)

        # Print all non-empty lines for analysis
        print(f"\n--- All non-empty lines (first 200) ---")
        non_empty = [l.strip() for l in lines if l.strip()]
        for l in non_empty[:200]:
            print(f"  {l}")

        print(f"\n--- Date patterns found: {date_patterns[:20]}")
        print(f"--- Relevant job lines: {len(relevant)}")
        for kw, ctx in relevant[:20]:
            print(f"  [{kw}] {' | '.join(c.strip() for c in ctx)}")

        return text
    except Exception as e:
        print(f"ERROR: {e}")
        return ""

async def check_feishu(page, url, name):
    """Check feishu hire portal."""
    print(f"\n{'='*60}")
    print(f"Checking {name}: {url}")
    try:
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(5000)

        text = await page.inner_text("body")
        print(f"Page title: {await page.title()}")
        print(f"Content length: {len(text)}")

        keywords = ["内核", "系统", "嵌入式", "eBPF", "Agent", "Infra", "基础设施",
                     "平台", "后端", "C++", "Rust", "底层", "驱动", "runtime",
                     "编译", "操作系统", "虚拟化", "分布式", "架构"]

        lines = text.split('\n')
        non_empty = [l.strip() for l in lines if l.strip()]
        print(f"\n--- All non-empty lines (first 200) ---")
        for l in non_empty[:200]:
            print(f"  {l}")

        relevant = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            for kw in keywords:
                if kw.lower() in line_stripped.lower():
                    context_start = max(0, i-2)
                    context_end = min(len(lines), i+5)
                    context = lines[context_start:context_end]
                    relevant.append((kw, context))
                    break

        print(f"\n--- Relevant job lines: {len(relevant)}")
        for kw, ctx in relevant[:20]:
            print(f"  [{kw}] {' | '.join(c.strip() for c in ctx)}")

        return text
    except Exception as e:
        print(f"ERROR: {e}")
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

        # 1. 月之暗面 mokahr
        await check_mokahr(page, "https://app.mokahr.com/apply/moonshot/148506", "月之暗面 Moonshot")

        # 2. 银河通用 mokahr
        await check_mokahr(page, "https://app.mokahr.com/apply/yinhetongyong/165929", "银河通用 Yinhetongyong")

        # 3. 智谱 mokahr
        await check_mokahr(page, "https://app.mokahr.com/apply/zphz/148983", "智谱 Zhipu")

        # 4. 寒武纪 mokahr
        await check_mokahr(page, "https://app.mokahr.com/apply/cambricon/1113", "寒武纪 Cambricon")

        # 5. 星动纪元 feishu
        await check_feishu(page, "https://jobs.feishu.cn/k0fqxcszc9", "星动纪元 Xingdong")

        # 6. 清程极智 feishu
        await check_feishu(page, "https://jobs.feishu.cn/chitu-ai", "清程极智 Chitu-AI")

        # 7. 零一万物 feishu
        await check_feishu(page, "https://01ai.jobs.feishu.cn/", "零一万物 01.AI")

        await browser.close()

asyncio.run(main())
