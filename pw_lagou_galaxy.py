import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width':1920,'height':1080}
    )
    page = context.new_page()
    try:
        url = "https://www.lagou.com/jobs/list_%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9?city=%E5%85%A8%E5%9B%BD"
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        time.sleep(8)
        
        text = page.inner_text('body')
        print(f"Lagou text ({len(text)} chars):")
        
        # Save full text
        with open('/pulp/find-job/results/lagou-galaxy-full.txt', 'w') as f:
            f.write(text)
        
        # Extract job listings
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        job_lines = []
        for i, line in enumerate(lines):
            if any(kw in line for kw in ['嵌入式', 'Linux', '内核', 'BSP', '驱动', 'kernel', '系统工程师', 'FPGA', '固件', 'eBPF']):
                # Print context
                start = max(0, i-2)
                end = min(len(lines), i+5)
                for j in range(start, end):
                    marker = " >>>" if j == i else "    "
                    print(f"{marker} {lines[j][:120]}")
                print()
        
        # Also print all lines that look like job titles with salary
        print("\n=== All job-salary pairs ===")
        for i, line in enumerate(lines):
            if 'k' in line and ('-' in line) and len(line) < 30:
                # This might be a salary; print the preceding line as title
                if i > 0:
                    print(f"  {lines[i-1][:60]:60s} | {line}")
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
