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
        
        # Click on page 2
        try:
            page2 = page.locator('text=2')
            if page2.count() > 0:
                page2.last.click()
                time.sleep(3)
                text2 = page.inner_text('body')
                print("=== Page 2 ===")
                print(text2[:5000])
        except:
            pass
        
        # Get all links to individual job pages
        links = page.eval_on_selector_all('a', '''els => els.filter(e => e.href && e.href.includes('/jobs/') || e.href.includes('/position')).map(e => ({href: e.href, text: e.innerText.trim().substring(0,100)}))''')
        print(f"\n=== Job links ({len(links)}) ===")
        for l in links:
            print(f"  {l['text'][:60]:60s} -> {l['href'][:100]}")
        
        # Also try to click on the Linux BSP job to get details
        try:
            linux_job = page.locator('text=Linux系统软件及BSP驱动工程师')
            print(f"\nLinux BSP job elements: {linux_job.count()}")
            if linux_job.count() > 0:
                linux_job.first.click()
                time.sleep(5)
                detail_text = page.inner_text('body')
                print(f"\n=== Linux BSP Job Detail Page ===")
                print(detail_text[:5000])
                print(f"\nCurrent URL: {page.url}")
        except Exception as e:
            print(f"Click error: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
