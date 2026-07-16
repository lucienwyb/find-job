import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width':1920,'height':1080}
    )
    page = context.new_page()
    
    # Intercept API calls
    api_responses = []
    def handle_response(response):
        if 'api' in response.url and ('job' in response.url.lower() or 'position' in response.url.lower() or 'company' in response.url.lower()):
            try:
                body = response.text()
                if len(body) > 100:
                    api_responses.append({'url': response.url, 'status': response.status, 'body': body[:50000]})
            except:
                pass
    page.on('response', handle_response)
    
    try:
        url = "https://www.liepin.com/company/9614836/"
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        time.sleep(5)
        
        # Click 职位 tab
        try:
            tabs = page.locator('text=职位')
            print(f"职位 tabs found: {tabs.count()}")
            if tabs.count() > 0:
                tabs.first.click()
                time.sleep(3)
        except Exception as e:
            print(f"Tab click: {e}")
        
        # Scroll to load all
        for _ in range(15):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
        
        # Extract job data from page structure
        # Try to find job cards
        jobs = page.eval_on_selector_all('.job-title, .job-item, .position-item, a[href*="/job/"]', '''els => {
            return els.map(e => ({
                text: e.innerText.trim().substring(0, 300),
                href: e.href || ''
            }))
        }''')
        
        print(f"\nFound {len(jobs)} job elements:")
        for j in jobs:
            if j['text'] and len(j['text']) > 2:
                print(f"  {j['text'][:150]}")
                if j['href'] and 'job' in j['href']:
                    print(f"    URL: {j['href'][:100]}")
        
        # Save API responses
        print(f"\n\n=== API responses captured: {len(api_responses)} ===")
        for r in api_responses[:5]:
            print(f"URL: {r['url'][:120]}")
            print(f"Status: {r['status']}, Body length: {len(r['body'])}")
            # Try to parse as JSON
            try:
                data = json.loads(r['body'])
                print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
            except:
                print(r['body'][:1000])
            print("---")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
