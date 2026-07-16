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
        # Try Boss直聘 search
        page.goto("https://www.zhipin.com/web/geek/job?query=千乘探索&city=100010000", timeout=30000, wait_until='domcontentloaded')
        time.sleep(5)
        text = page.inner_text('body')
        print(f"Boss text ({len(text)} chars):")
        print(text[:5000])
        
        # Also try liepin company search API
        print("\n=== Liepin company search API ===")
        page.goto("https://www.liepin.com/company/search/?key=千乘探索", timeout=30000, wait_until='domcontentloaded')
        time.sleep(3)
        text2 = page.inner_text('body')
        print(f"Liepin company search ({len(text2)} chars):")
        print(text2[:3000])
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
