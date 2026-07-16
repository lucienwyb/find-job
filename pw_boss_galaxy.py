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
        # Search for 银河航天 on Boss直聘
        page.goto("https://www.zhipin.com/web/geek/job?query=%E9%93%B6%E6%B2%B3%E8%88%AA%E5%A4%A9&city=101010100", timeout=30000, wait_until='domcontentloaded')
        time.sleep(8)
        
        title = page.title()
        text = page.inner_text('body')
        print(f"Title: {title}")
        print(f"Text length: {len(text)}")
        
        if '安全验证' in text or '验证' in text[:200]:
            print("BLOCKED by Boss直聘 verification")
        
        print(text[:8000])
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
