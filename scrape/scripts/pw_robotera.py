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
        url = "https://www.robotera.com/"
        page.goto(url, timeout=30000, wait_until='networkidle')
        time.sleep(3)
        
        # Try clicking "加入我们"
        try:
            join_link = page.locator('text=加入我们')
            print(f"Found '加入我们' elements: {join_link.count()}")
            if join_link.count() > 0:
                join_link.first.click()
                time.sleep(5)
                print(f"After click, URL: {page.url}")
                text = page.inner_text('body')
                print(f"Page text length: {len(text)}")
                print(text[:5000])
        except Exception as e:
            print(f"Click error: {e}")
        
        # Also try direct URL patterns
        for path in ['/about/joinus', '/about/careers', '/recruit', '/hr', '/about-us/join-us', '/join', '/career']:
            try:
                resp = page.goto(f"https://www.robotera.com{path}", timeout=10000, wait_until='domcontentloaded')
                time.sleep(2)
                text = page.inner_text('body')
                if len(text) > 200 and '404' not in text[:100]:
                    print(f"\n=== Found page at {path} ({len(text)} chars) ===")
                    print(text[:3000])
            except:
                pass
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
