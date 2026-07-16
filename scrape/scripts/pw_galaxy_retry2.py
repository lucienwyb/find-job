import json, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        viewport={'width':1920,'height':1080}
    )
    page = context.new_page()
    try:
        url = "https://www.liepin.com/company/9614836/"
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        time.sleep(8)
        
        text = page.inner_text('body')
        print(f"Text length: {len(text)}")
        
        if '行为异常' in text or '安全' in text[:100]:
            print("STILL BLOCKED")
            print(text[:200])
        else:
            # Save full text
            with open('/pulp/find-job/results/galaxy-liepin-full2.txt', 'w') as f:
                f.write(text)
            
            # Extract all job-salary pairs
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            jobs = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if i+1 < len(lines) and 'k·' in lines[i+1] and len(line) < 80:
                    title = line
                    salary = lines[i+1]
                    location = lines[i+2] if i+2 < len(lines) and '区' in lines[i+2] else ''
                    exp = lines[i+3] if i+3 < len(lines) and ('经验' in lines[i+3] or '以上' in lines[i+3] or '不限' in lines[i+3]) else ''
                    edu = lines[i+4] if i+4 < len(lines) and ('本科' in lines[i+4] or '大专' in lines[i+4] or '硕士' in lines[i+4]) else ''
                    jobs.append({'title': title, 'salary': salary, 'location': location, 'exp': exp, 'edu': edu})
                    i += 5 if edu else (4 if exp else (3 if location else 2))
                else:
                    i += 1
            
            print(f"\nExtracted {len(jobs)} jobs:")
            for j in jobs:
                print(f"  {j['title']:45s} | {j['salary']:15s} | {j['location']:20s} | {j['exp']:12s} | {j['edu']}")
            
            # Filter for relevant positions
            keywords = ['内核', 'kernel', '嵌入式', 'embedded', 'BSP', '驱动', 'driver', 'Linux', '系统', '底层', 'eBPF', 'FPGA', '固件', 'firmware', '系统工程师']
            print(f"\n=== Matching positions ===")
            for j in jobs:
                if any(kw.lower() in j['title'].lower() for kw in keywords):
                    print(f"  MATCH: {j['title']} | {j['salary']} | {j['location']} | {j['exp']} | {j['edu']}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
