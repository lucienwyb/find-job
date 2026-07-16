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
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        time.sleep(8)  # Wait for SPA to render
        
        # Get all links
        links = page.eval_on_selector_all('a', '''els => els.map(e => ({href: e.href, text: e.innerText.trim()})).filter(l => l.href && l.text)''')
        print(f"All links ({len(links)}):")
        for l in links:
            print(f"  {l['text'][:40]:40s} -> {l['href'][:100]}")
        
        # Try clicking "加入我们"
        print("\n=== Trying to click '加入我们' ===")
        join_elements = page.locator('text=加入我们')
        print(f"Found {join_elements.count()} '加入我们' elements")
        if join_elements.count() > 0:
            # Get href
            hrefs = page.eval_on_selector_all('a', '''els => els.filter(e => e.innerText.includes('加入我们')).map(e => ({href: e.href, text: e.innerText.trim()}))''')
            print(f"Join links: {json.dumps(hrefs, ensure_ascii=False)}")
            
            if hrefs:
                target = hrefs[0]['href']
                print(f"\nNavigating to: {target}")
                page.goto(target, timeout=30000, wait_until='domcontentloaded')
                time.sleep(5)
                text = page.inner_text('body')
                print(f"Page text ({len(text)} chars):")
                print(text[:5000])
            else:
                # Try clicking directly
                join_elements.first.click()
                time.sleep(5)
                print(f"After click, URL: {page.url}")
                text = page.inner_text('body')
                print(text[:5000])
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
