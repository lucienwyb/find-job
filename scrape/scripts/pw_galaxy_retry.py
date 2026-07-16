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
        # Use the company main page which worked before
        url = "https://www.liepin.com/company/9614836/"
        page.goto(url, timeout=60000, wait_until='networkidle')
        time.sleep(5)
        
        # Get full page text  
        text = page.inner_text('body')
        
        # Save full text
        with open('/pulp/find-job/results/galaxy-liepin-full.txt', 'w') as f:
            f.write(text)
        
        print(f"Full text saved ({len(text)} chars)")
        
        # Parse job entries - look for patterns like "title\n salary\n location\n exp\n edu"
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        jobs = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if next line is a salary pattern
            if i+1 < len(lines) and 'k·' in lines[i+1] and len(line) < 100:
                title = line
                salary = lines[i+1]
                location = lines[i+2] if i+2 < len(lines) and '区' in lines[i+2] else ''
                exp = lines[i+3] if i+3 < len(lines) and ('经验' in lines[i+3] or '以上' in lines[i+3] or '不限' in lines[i+3]) else ''
                edu = lines[i+4] if i+4 < len(lines) and ('本科' in lines[i+4] or '大专' in lines[i+4] or '硕士' in lines[i+4]) else ''
                jobs.append({
                    'title': title,
                    'salary': salary,
                    'location': location,
                    'experience': exp,
                    'education': edu
                })
                i += 5 if edu else (4 if exp else (3 if location else 2))
            else:
                i += 1
        
        print(f"\nExtracted {len(jobs)} jobs:")
        for j in jobs:
            print(f"  {j['title']:45s} | {j['salary']:15s} | {j['location']:20s} | {j['experience']:12s} | {j['education']}")
        
        # Save as JSON
        with open('/pulp/find-job/results/galaxy-jobs.json', 'w') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        
        # Filter for relevant positions
        relevant_keywords = ['内核', 'kernel', '嵌入式', 'embedded', 'BSP', '驱动', 'driver', 'Linux', '系统', 'system', '底层', 'eBPF', 'FPGA', '固件', 'firmware']
        print(f"\n=== Relevant positions (kernel/system/embedded) ===")
        for j in jobs:
            title_lower = j['title'].lower()
            if any(kw.lower() in title_lower for kw in relevant_keywords):
                print(f"  MATCH: {j['title']} | {j['salary']} | {j['location']} | {j['experience']} | {j['education']}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
