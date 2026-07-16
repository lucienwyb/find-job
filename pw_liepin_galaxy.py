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
        url = "https://www.liepin.com/company/9614836/"
        page.goto(url, timeout=60000, wait_until='networkidle')
        time.sleep(3)
        
        # Click on "职位" tab
        try:
            job_tab = page.locator('text=职位(193)')
            if job_tab.count() == 0:
                job_tab = page.locator('text=职位')
            if job_tab.count() > 0:
                job_tab.first.click()
                time.sleep(3)
        except:
            pass
        
        # Scroll to load all jobs
        for _ in range(10):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
        
        # Extract all text to find job listings
        text = page.inner_text('body')
        
        # Save full text
        with open('/pulp/find-job/results/liepin-galaxy-full.txt', 'w') as f:
            f.write(text)
        
        # Print relevant sections - look for job titles with salary
        lines = text.split('\n')
        in_jobs = False
        job_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if 'k·' in line or '工程师' in line or '开发' in line or '驱动' in line or '内核' in line or '嵌入式' in line or 'BSP' in line or 'Linux' in line or '系统' in line or 'kernel' in line.lower():
                if line and len(line) < 200:
                    job_lines.append(line)
        
        print(f"Found {len(job_lines)} job-related lines:")
        for j in job_lines[:80]:
            print(f"  {j}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
