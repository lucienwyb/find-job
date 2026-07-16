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
        # Go to the company jobs page directly
        url = "https://www.liepin.com/company/9614836/jobs/"
        page.goto(url, timeout=60000, wait_until='networkidle')
        time.sleep(3)
        
        # Scroll to load more
        for _ in range(5):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
        
        # Try to find job items
        # Look for job title links
        jobs = page.eval_on_selector_all('a, .job-title, .job-card, li', '''els => {
            return els.filter(e => {
                const t = e.innerText || '';
                return t.includes('k·') || t.includes('工程师') || t.includes('开发') || t.includes('驱动') || t.includes('内核') || t.includes('嵌入式') || t.includes('BSP') || t.includes('Linux') || t.includes('系统');
            }).map(e => ({text: e.innerText.trim().substring(0, 200), href: e.href || ''}))
        }''')
        
        # Deduplicate
        seen = set()
        unique_jobs = []
        for j in jobs:
            key = j['text'][:50]
            if key not in seen:
                seen.add(key)
                unique_jobs.append(j)
        
        print(f"Found {len(unique_jobs)} job-related elements:")
        for j in unique_jobs:
            print(f"  {j['text'][:120]}")
            if j['href']:
                print(f"    -> {j['href'][:100]}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
