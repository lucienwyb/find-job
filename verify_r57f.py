#!/usr/bin/env python3
"""Round 57f: render tianyancha search via playwright for 星忆科技 + 光轮智能 company detail."""
import requests, html, re, json

HD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def raw_search(q):
    """Fetch tianyancha search raw HTML and extract company links + embedded data."""
    u = "https://www.tianyancha.com/search?key=" + requests.utils.quote(q)
    r = requests.get(u, headers=HD, timeout=25)
    t = r.text
    # save raw for inspection
    with open("/tmp/tyc_%s.html" % q[:4], "w") as f:
        f.write(t)
    # look for company IDs in various patterns
    # pattern 1: /company/XXXXX
    p1 = re.findall(r'/company/([0-9a-zA-Z]+)', t)
    # pattern 2: data-href or json with companyNo
    p2 = re.findall(r'"companyNo":"?([0-9a-zA-Z]+)"?', t)
    # pattern 3: search result JSON
    p3 = re.findall(r'"gid":"?([0-9]+)"?', t)
    # look for phone, email, website in raw
    phones = re.findall(r'1[3-9]\d{9}', t)
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', t)
    websites = re.findall(r'(?:website|网址|官网)["：:\s]*(https?://[^\s"<>\\]+)', t, re.I)
    # also look for the company name + nearby text
    t2 = re.sub(r'<[^>]+>', ' ', t)
    t2 = html.unescape(t2)
    t2 = re.sub(r'\s+', ' ', t2)
    idx = t2.find(q)
    snip = t2[max(0, idx - 30):idx + 300] if idx >= 0 else "(not found in text)"
    return {
        "company_paths": list(set(p1))[:5],
        "companyNo": list(set(p2))[:5],
        "gid": list(set(p3))[:5],
        "phones": list(set(phones))[:3],
        "emails": list(set(emails))[:3],
        "websites": websites[:3],
        "snip": snip,
        "html_len": len(t),
    }

for q in ["星忆科技", "北京星忆科技有限公司", "光轮智能", "北京光轮智能科技有限公司"]:
    print("=" * 50)
    print("  SEARCH:", q)
    print("=" * 50)
    r = raw_search(q)
    for k, v in r.items():
        print(f"  {k}: {v}")
    print()
