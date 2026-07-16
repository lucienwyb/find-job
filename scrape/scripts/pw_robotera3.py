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
        page.goto("https://www.robotera.com/", timeout=30000, wait_until='domcontentloaded')
        time.sleep(6)
        
        # Click "加入我们"
        page.locator('text=加入我们').first.click()
        time.sleep(3)
        
        # Now click "社会招聘"
        social = page.locator('text=社会招聘')
        print(f"社会招聘 elements: {social.count()}")
        if social.count() > 0:
            social.first.click()
            time.sleep(5)
            
            # Get all text
            text = page.inner_text('body')
            print(f"Text after social recruitment click ({len(text)} chars):")
            print(text[:8000])
            
            # Also get all links
            links = page.eval_on_selector_all('a', '''els => els.filter(e => e.href && e.innerText.trim()).map(e => ({href: e.href, text: e.innerText.trim().substring(0,100)}))''')
            print(f"\nLinks found: {len(links)}")
            for l in links:
                print(f"  {l['text'][:60]:60s} -> {l['href'][:100]}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
