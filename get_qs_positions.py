import re, json

positions = {}
for pid in [21587, 21588, 21589, 21590, 21591, 21592, 21593, 21594, 21595]:
    try:
        import subprocess
        result = subprocess.run(['curl', '-sL', '--max-time', '10', '-H', 'User-Agent: Mozilla/5.0', 
                                f'https://www.qxwq.org.cn/work/position/show/{pid}'],
                              capture_output=True, text=True, timeout=15,
                              env={'https_proxy': 'http://100.66.66.64:8765', 'http_proxy': 'http://100.66.66.64:8765'})
        html = result.stdout
        if len(html) < 1000:
            continue
        
        # Extract job details
        t = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.S)
        t = re.sub(r'<style[^>]*>.*?</style>', '', t, flags=re.S)
        t = re.sub(r'<[^>]+>', '\n', t)
        t = re.sub(r'\n\s*\n', '\n', t)
        t = re.sub(r'&nbsp;', ' ', t)
        
        # Check if this is a Qiansheng position
        if '千乘' not in t:
            continue
        
        # Extract job title, salary, date, location
        title_match = re.search(r'职位详情.*?北京千乘探索科技有限公司', t, re.S)
        
        # Find job title (usually after a nav breadcrumb)
        job_title = ''
        salary = ''
        update_date = ''
        location = ''
        exp = ''
        edu = ''
        job_desc = ''
        
        m = re.search(r'职位月薪：\s*([^\n]+)', t)
        if m: salary = m.group(1).strip()
        m = re.search(r'更新日期：\s*([^\n]+)', t)
        if m: update_date = m.group(1).strip()
        m = re.search(r'工作地点：\s*([^\n]+)', t)
        if m: location = m.group(1).strip()
        m = re.search(r'工作经验：\s*([^\n]+)', t)
        if m: exp = m.group(1).strip()
        m = re.search(r'最低学历：\s*([^\n]+)', t)
        if m: edu = m.group(1).strip()
        
        # Job title is usually before 职位月薪
        m = re.search(r'岗位职责\s*(.*?)(?:岗位要求|任职要求)', t, re.S)
        if m: job_desc = m.group(1).strip()[:500]
        
        # Find the job title - it's usually between breadcrumb and salary
        lines = [l.strip() for l in t.split('\n') if l.strip()]
        for i, line in enumerate(lines):
            if '职位月薪' in line:
                # Title is usually a few lines before
                for j in range(max(0, i-5), i):
                    if lines[j] and '千乘' not in lines[j] and '职位' not in lines[j] and '详情' not in lines[j] and '首页' not in lines[j] and '求职' not in lines[j] and len(lines[j]) < 30:
                        job_title = lines[j]
                        break
                break
        
        print(f"\n=== Position {pid} ===")
        print(f"  Title: {job_title}")
        print(f"  Salary: {salary}")
        print(f"  Date: {update_date}")
        print(f"  Location: {location}")
        print(f"  Experience: {exp}")
        print(f"  Education: {edu}")
        if job_desc:
            print(f"  Description: {job_desc[:200]}")
        
        positions[pid] = {
            'title': job_title,
            'salary': salary,
            'date': update_date,
            'location': location,
            'experience': exp,
            'education': edu,
            'description': job_desc
        }
    except Exception as e:
        print(f"Error for {pid}: {e}")

with open('/pulp/find-job/results/qiansheng-positions.json', 'w') as f:
    json.dump(positions, f, ensure_ascii=False, indent=2)
