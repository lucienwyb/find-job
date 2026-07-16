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
        # Try liepin company page
        url = "https://www.liepin.com/company/9614836/"
        page.goto(url, timeout=60000, wait_until='networkidle')
        time.sleep(3)
        title = page.title()
        text = page.inner_text('body')
        print(json.dumps({'url': url, 'title': title, 'text': text[:15000]}, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
    finally:
        browser.close()
