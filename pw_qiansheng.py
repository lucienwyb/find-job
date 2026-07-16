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
        # Try liepin company page for Qiansheng
        url = "https://www.liepin.com/company/9663406/"
        page.goto(url, timeout=60000, wait_until='networkidle')
        time.sleep(3)
        
        title = page.title()
        text = page.inner_text('body')
        print(f"=== Liepin Qiansheng ===")
        print(f"Title: {title}")
        print(f"Text length: {len(text)}")
        print(text[:8000])
        
    except Exception as e:
        print(f"Liepin error: {e}")
    
    # Try 智联招聘
    try:
        page.goto("https://www.zhaopin.com/companydetail/jobs-CZ498004880.htm", timeout=30000, wait_until='domcontentloaded')
        time.sleep(5)
        text2 = page.inner_text('body')
        print(f"\n=== 智联招聘 Qiansheng ===")
        print(f"Text length: {len(text2)}")
        print(text2[:8000])
    except Exception as e:
        print(f"Zhaopin error: {e}")
    
    browser.close()
