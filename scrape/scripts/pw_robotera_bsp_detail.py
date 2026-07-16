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
        url = "https://k0fqxcszc9.jobs.feishu.cn/index/position/7571785644297521459/detail"
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        time.sleep(5)
        text = page.inner_text('body')
        print("=== Linux系统软件及BSP驱动工程师 - Full Detail ===")
        print(text)
        print(f"\nURL: {page.url}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
