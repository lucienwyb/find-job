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
        url = "https://k0fqxcszc9.jobs.feishu.cn/index"
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        time.sleep(8)
        
        title = page.title()
        text = page.inner_text('body')
        print(f"Title: {title}")
        print(f"Text length: {len(text)}")
        
        # Save full text
        with open('/pulp/find-job/results/robotera-feishu-full.txt', 'w') as f:
            f.write(text)
        
        print(text[:15000])
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
