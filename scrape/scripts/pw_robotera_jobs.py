import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width':1920,'height':1080}
    )
    page = context.new_page()
    
    # Try liepin search for 星动纪元
    try:
        page.goto("https://www.liepin.com/zhaopin/?key=%E6%98%9F%E5%8A%A8%E7%BA%AA%E5%85%83", timeout=30000, wait_until='domcontentloaded')
        time.sleep(5)
        text = page.inner_text('body')
        print(f"=== Liepin search 星动纪元 ({len(text)} chars) ===")
        lines = [l.strip() for l in text.split('\n') if l.strip() and ('k·' in l or '星动' in l or '工程师' in l or '开发' in l or '嵌入式' in l or 'BSP' in l or '驱动' in l)]
        for l in lines[:50]:
            print(f"  {l[:120]}")
    except Exception as e:
        print(f"Liepin search error: {e}")
    
    # Try jobui for RobotEra
    try:
        page.goto("https://www.jobui.com/company/PC10999998/", timeout=20000, wait_until='domcontentloaded')
        time.sleep(3)
        text2 = page.inner_text('body')
        print(f"\n=== Jobui RobotEra ({len(text2)} chars) ===")
        print(text2[:3000])
    except Exception as e:
        print(f"Jobui error: {e}")
    
    # Try searching jobui for 星动纪元
    try:
        page.goto("https://www.jobui.com/jobs/?key=%E6%98%9F%E5%8A%A8%E7%BA%AA%E5%85%83", timeout=20000, wait_until='domcontentloaded')
        time.sleep(3)
        text3 = page.inner_text('body')
        print(f"\n=== Jobui search ({len(text3)} chars) ===")
        print(text3[:3000])
    except Exception as e:
        print(f"Jobui search error: {e}")
    
    browser.close()
