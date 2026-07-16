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
        # Go to company jobs page
        url = "https://www.liepin.com/company/9614836/jobs/"
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        time.sleep(5)
        
        # Check current URL
        print(f"Current URL: {page.url}")
        print(f"Title: {page.title()}")
        
        # Get full text
        text = page.inner_text('body')
        print(f"Text length: {len(text)}")
        
        # Save full text
        with open('/pulp/find-job/results/liepin-galaxy-jobs.txt', 'w') as f:
            f.write(text)
        
        # Extract job-salary pairs
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Find job entries - they usually have title followed by salary, location, experience, education
        jobs = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Job titles often followed by salary pattern like "X-Yk·Z薪"
            if i+1 < len(lines) and 'k·' in lines[i+1]:
                title = line
                salary = lines[i+1]
                location = lines[i+2] if i+2 < len(lines) else ''
                exp = lines[i+3] if i+3 < len(lines) else ''
                edu = lines[i+4] if i+4 < len(lines) else ''
                jobs.append({
                    'title': title[:80],
                    'salary': salary,
                    'location': location[:50],
                    'experience': exp[:30],
                    'education': edu[:20]
                })
                i += 5
            else:
                i += 1
        
        print(f"\nExtracted {len(jobs)} jobs:")
        for j in jobs:
            print(f"  {j['title']:40s} | {j['salary']:15s} | {j['location']:20s} | {j['experience']:10s} | {j['education']}")
        
        # Save as JSON
        with open('/pulp/find-job/results/galaxy-jobs.json', 'w') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
