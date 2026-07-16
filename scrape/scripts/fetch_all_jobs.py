#!/usr/bin/env python3
"""Fetch all job listings from APIs directly."""
import json
import os
import time
import urllib.request
import urllib.parse

PROXY = "http://100.66.66.64:8765"
os.makedirs("/pulp/find-job", exist_ok=True)

# Set up proxy
proxy_handler = urllib.request.ProxyHandler({
    'http': PROXY,
    'https': PROXY,
})
opener = urllib.request.build_opener(proxy_handler)

KEYWORDS = [
    "kernel", "ebpf", "系统", "infra", "基础设施", "架构", "嵌入式", "embedded",
    "edge", "边缘", "driver", "驱动", "platform", "平台", "OS", "操作系统",
    "runtime", "容器", "container", "虚拟化", "virtualization", "agent",
    "training", "推理", "inference", "HPC", "高性能计算", "cuda", "gpu",
    "底层", "low-level", "system", "芯片", "chip", "编译器", "compiler",
    "调度", "schedule", "分布式", "distributed", "存储", "storage",
    "RDMA", "nccl", "kubernetes", "k8s", "云原生", "cloud-native",
    "Linux", "内核", "BPF", "网络", "network", "通信", "communication",
    "固件", "firmware", "驱动", "硬件", "hardware",
]


def match_keywords(text):
    """Check if text matches any keywords."""
    text_lower = text.lower()
    matched = []
    for kw in KEYWORDS:
        if kw.lower() in text_lower:
            matched.append(kw)
    return matched


def fetch_url(url, headers=None, data=None, method='GET'):
    """Fetch URL with proxy."""
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data:
        req.data = data.encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    if method != 'GET':
        req.get_method = lambda: method
    try:
        resp = opener.open(req, timeout=30)
        return resp.read().decode('utf-8')
    except Exception as e:
        return json.dumps({"error": str(e)})


def fetch_cambricon():
    """Fetch Cambricon jobs from mokahr API."""
    print("\n=== CAMBRICON (mokahr) ===")

    # The mokahr API for job listings
    # Try different API endpoints
    headers = {
        'Accept': 'application/json',
        'Referer': 'https://app.mokahr.com/apply/cambricon/1113',
        'User-Agent': 'Mozilla/5.0',
    }

    all_jobs = []

    # Try the API endpoint captured during scraping
    api_url = "https://app.mokahr.com/api/outer/ats-apply/website/jobs"
    # Add parameters for pagination
    for page in range(1, 10):
        params = {
            'page': str(page),
            'limit': '50',
            'org_id': 'cambricon',
            'apply_id': '1113',
        }
        url = f"{api_url}?{urllib.parse.urlencode(params)}"
        print(f"  Fetching page {page}...")
        body = fetch_url(url, headers=headers)

        try:
            data = json.loads(body)
            if 'data' in data:
                d = data['data']
                if isinstance(d, dict):
                    job_list = d.get('jobList', d.get('list', d.get('jobs', [])))
                    if not job_list and isinstance(d, dict):
                        # Try different keys
                        for k in d:
                            if isinstance(d[k], list) and len(d[k]) > 0:
                                if isinstance(d[k][0], dict) and any(jk in str(d[k][0]).lower() for jk in ['title', 'name', 'job']):
                                    job_list = d[k]
                                    break

                    if job_list:
                        all_jobs.extend(job_list)
                        print(f"    Got {len(job_list)} jobs (total: {len(all_jobs)})")
                    else:
                        print(f"    No jobs found in response. Keys: {list(d.keys()) if isinstance(d, dict) else type(d)}")
                        print(f"    Data: {json.dumps(d, ensure_ascii=False)[:500]}")
                        break
                else:
                    print(f"    Unexpected data type: {type(d)}")
                    print(f"    Data: {json.dumps(d, ensure_ascii=False)[:500]}")
                    break
            else:
                print(f"    No 'data' key. Response: {body[:300]}")
                break
        except Exception as e:
            print(f"    Error: {e}")
            print(f"    Body: {body[:300]}")
            break

        time.sleep(0.5)

    # Also try the mokahr API with the apply endpoint
    if not all_jobs:
        print("  Trying alternative API...")
        # Try different URL patterns
        alt_urls = [
            "https://app.mokahr.com/api/apply/cambricon/jobs?page=1&limit=50",
            "https://app.mokahr.com/api/outer/ats-apply/website/jobs?applyId=1113&page=1&limit=50",
            "https://app.mokahr.com/api/outer/ats-apply/website/jobs?applyId=1113",
        ]
        for url in alt_urls:
            print(f"  Trying: {url[:100]}")
            body = fetch_url(url, headers=headers)
            try:
                data = json.loads(body)
                print(f"    Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if isinstance(data, dict) and 'data' in data:
                    d = data['data']
                    if isinstance(d, dict):
                        print(f"    Data keys: {list(d.keys())[:20]}")
                        for k in d:
                            if isinstance(d[k], list) and len(d[k]) > 0:
                                print(f"    Found list '{k}': {len(d[k])} items")
                                all_jobs = d[k]
                                break
                    elif isinstance(d, list):
                        print(f"    Data list: {len(d)} items")
                        all_jobs = d
                if all_jobs:
                    break
            except:
                print(f"    Body: {body[:300]}")

    return all_jobs


def fetch_dptechnology():
    """Fetch DP Technology jobs from feishu API."""
    print("\n=== DP TECHNOLOGY (feishu) ===")

    all_jobs = []
    headers = {
        'Accept': 'application/json',
        'Referer': 'https://dptechnology.jobs.feishu.cn/index',
        'User-Agent': 'Mozilla/5.0',
    }

    # Get CSRF token first
    csrf_body = fetch_url("https://dptechnology.jobs.feishu.cn/api/v1/csrf/token", headers=headers)
    try:
        csrf_data = json.loads(csrf_body)
        csrf_token = csrf_data.get('data', {}).get('token', '')
        headers['X-CSRF-Token'] = csrf_token
        print(f"  CSRF token: {csrf_token[:20]}...")
    except:
        print("  Failed to get CSRF token")

    for offset in range(0, 250, 10):
        params = {
            'keyword': '',
            'limit': '10',
            'offset': str(offset),
            'job_category_id_list': '',
            'tag_id_list': '',
            'location_code_list': '',
            'subject_id_list': '',
            'recruitment_id_list': '',
            'portal_type': '6',
            'job_function_id_list': '',
        }
        url = f"https://dptechnology.jobs.feishu.cn/api/v1/search/job/posts?{urllib.parse.urlencode(params)}"
        print(f"  Fetching offset {offset}...")
        body = fetch_url(url, headers=headers)

        try:
            data = json.loads(body)
            if data.get('code') == 0:
                d = data['data']
                job_list = d.get('job_post_list', [])
                count = d.get('count', 0)
                if job_list:
                    all_jobs.extend(job_list)
                    print(f"    Got {len(job_list)} jobs (total: {len(all_jobs)}/{count})")
                else:
                    print(f"    No more jobs")
                    break
            else:
                print(f"    API error: {data.get('message', '')}")
                break
        except Exception as e:
            print(f"    Error: {e}")
            print(f"    Body: {body[:300]}")
            break

        time.sleep(0.5)

    return all_jobs


def fetch_geovis():
    """Fetch Geovis jobs from zhiye API."""
    print("\n=== GEOVIS (zhiye) ===")

    all_jobs = []
    headers = {
        'Accept': 'application/json',
        'Referer': 'https://geovis.zhiye.com/social/jobs',
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/json',
    }

    # Zhiye API uses POST for job list
    for page in range(1, 15):
        data = {
            'portalId': 'cba2dbf5-bf6d-4470-86b8-25836d391e96',
            'categoryId': '1',  # social recruitment
            'pageIndex': page,
            'pageSize': 20,
        }

        url = "https://geovis.zhiye.com/api/Jobad/GetJobAdPageList"
        print(f"  Fetching page {page}...")
        body = fetch_url(url, headers=headers, data=json.dumps(data), method='POST')

        try:
            result = json.loads(body)
            if result.get('Code') == 200:
                d = result.get('Data', [])
                if isinstance(d, list) and len(d) > 0:
                    all_jobs.extend(d)
                    print(f"    Got {len(d)} jobs (total: {len(all_jobs)})")
                elif isinstance(d, dict) and 'Rows' in d:
                    rows = d['Rows']
                    all_jobs.extend(rows)
                    print(f"    Got {len(rows)} jobs (total: {len(all_jobs)})")
                else:
                    print(f"    Data: {json.dumps(d, ensure_ascii=False)[:300]}")
                    break
            else:
                print(f"    API returned: Code={result.get('Code')}")
                break
        except Exception as e:
            print(f"    Error: {e}")
            print(f"    Body: {body[:300]}")
            break

        time.sleep(0.5)

    return all_jobs


def analyze_and_save(company, all_jobs, job_extractor):
    """Analyze jobs and save results."""
    print(f"\n--- Analyzing {company} ({len(all_jobs)} total jobs) ---")

    matching_jobs = []
    for job in all_jobs:
        info = job_extractor(job)
        text = f"{info['title']} {info.get('department','')} {info.get('description','')}"
        matched = match_keywords(text)
        if matched:
            info['matched_keywords'] = matched
            matching_jobs.append(info)

    # Filter for Beijing jobs
    beijing_jobs = []
    for job in all_jobs:
        info = job_extractor(job)
        loc = info.get('location', '')
        if '北京' in loc or 'beijing' in loc.lower() or not loc:
            beijing_jobs.append(info)

    # Filter for Beijing matching jobs
    beijing_matching = [j for j in matching_jobs if '北京' in j.get('location', '') or not j.get('location')]

    result = {
        "company": company,
        "total_positions": len(all_jobs),
        "matching_positions": matching_jobs,
        "beijing_matching": beijing_matching,
        "beijing_total": len(beijing_jobs),
    }

    print(f"  Total positions: {len(all_jobs)}")
    print(f"  Matching (kernel/eBPF/system/etc): {len(matching_jobs)}")
    print(f"  Beijing matching: {len(beijing_matching)}")
    for j in matching_jobs[:20]:
        print(f"    [{', '.join(j['matched_keywords'])}] {j['title']} | {j.get('department','')} | {j.get('location','')}")

    filepath = f"/pulp/find-job/r44_{company}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Saved to {filepath}")

    return result


def main():
    os.environ['http_proxy'] = PROXY
    os.environ['https_proxy'] = PROXY

    # 1. Cambricon
    cambricon_jobs = fetch_cambricon()
    if cambricon_jobs:
        def cambricon_extractor(job):
            return {
                'title': job.get('name') or job.get('title') or job.get('jobName') or '',
                'department': job.get('department') or job.get('departmentName') or '',
                'location': job.get('workLocation') or job.get('city') or job.get('location') or '',
                'description': job.get('description') or job.get('jobDescription') or '',
                'update_time': job.get('updateTime') or job.get('publishTime') or '',
                'id': job.get('id') or job.get('jobId') or '',
            }
        analyze_and_save("cambricon", cambricon_jobs, cambricon_extractor)

    # 2. DP Technology
    dptechnology_jobs = fetch_dptechnology()
    if dptechnology_jobs:
        def dptechnology_extractor(job):
            return {
                'title': job.get('title') or job.get('name') or '',
                'department': job.get('department') or '',
                'location': job.get('city') or job.get('location') or '',
                'description': job.get('description') or '',
                'update_time': job.get('update_time') or job.get('publish_time') or job.get('create_time') or '',
                'id': job.get('id') or '',
            }
        analyze_and_save("dptechnology", dptechnology_jobs, dptechnology_extractor)

    # 3. Geovis
    geovis_jobs = fetch_geovis()
    if geovis_jobs:
        def geovis_extractor(job):
            return {
                'title': job.get('Name') or job.get('JobAdName') or '',
                'department': job.get('DepartmentName') or job.get('Org') or '',
                'location': job.get('WorkPlace') or job.get('WorkAddress') or '',
                'description': job.get('Description') or job.get('JobDescription') or '',
                'update_time': job.get('UpdateTime') or job.get('PostDate') or '',
                'id': job.get('Id') or job.get('JobAdId') or '',
            }
        analyze_and_save("geovis", geovis_jobs, geovis_extractor)

    print("\nDone!")


if __name__ == "__main__":
    main()
