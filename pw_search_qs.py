import json, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        viewport={'width':1920,'height':1080}
    )
    page = context.new_page()
    try:
        page.goto("https://www.liepin.com/zhaopin/?key=%E5%8D%83%E4%B9%98%E6%8E%A2%E7%B4%A2", timeout=30000, wait_until='networkidle')
        time.sleep(3)
        text = page.inner_text('body')
        # Look for company/job mentions
        lines = [l.strip() for l in text.split('\n') if '千乘' in l or 'k·' in l]
        print(f"Found {len(lines)} relevant lines:")
        for l in lines[:30]:
            print(f"  {l[:120]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
