import json, time
from playwright.sync_api import sync_playwright

# All job detail URLs from the Feishu page
job_urls = [
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7525025339241810203/detail",  # 市场公关
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7516516540104542527/detail",  # 运动控制算法
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7509404813236259123/detail",  # 具身大模型
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7509063464293615922/detail",  # 大模型部署
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7483796570053363994/detail",  # MPC算法
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7459360833953433867/detail",  # 机械结构
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7439182066123852051/detail",  # 机械关节
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7418895406761249061/detail",  # 电机控制
    "https://k0fqxcszc9.jobs.feishu.cn/index/position/7342699402580936997/detail",  # 电机嵌入式
]

# Also need to find the Linux BSP and MCU embedded job URLs
# Try to get page 1 links
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        viewport={'width':1920,'height':1080}
    )
    page = context.new_page()
    
    # First go to page 1 and get all links
    page.goto("https://k0fqxcszc9.jobs.feishu.cn/index", timeout=30000, wait_until='domcontentloaded')
    time.sleep(8)
    
    # Get all job links on page 1
    links = page.eval_on_selector_all('a', '''els => els.filter(e => e.href && e.href.includes('/position/')).map(e => ({href: e.href, text: e.innerText.trim().substring(0,80)}))''')
    
    print(f"Page 1 links ({len(links)}):")
    for l in links:
        print(f"  {l['text'][:50]:50s} -> {l['href']}")
    
    # Now visit each unique job detail page and look for date info
    all_links = list(set([l['href'] for l in links])) + job_urls[:3]
    
    for url in all_links[:5]:
        try:
            page.goto(url, timeout=15000, wait_until='domcontentloaded')
            time.sleep(3)
            text = page.inner_text('body')
            # Look for date patterns
            import re
            dates = re.findall(r'20\d{2}[-./]\d{1,2}[-./]\d{1,2}', text)
            print(f"\n=== {url.split('/')[-2]} ===")
            if dates:
                print(f"  Dates found: {dates}")
            # Also look for 发布 or 更新 or 创建
            date_context = re.findall(r'(?:发布|更新|创建|日期|时间)[：:]\s*([^\n]{1,30})', text)
            if date_context:
                print(f"  Date context: {date_context}")
            # Print first 500 chars for context
            print(f"  Text preview: {text[:300]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    browser.close()
