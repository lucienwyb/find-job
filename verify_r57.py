#!/usr/bin/env python3
"""Round 57: verify 3 companies via tianyancha on shine (China mainland IP)."""
import requests, html, re, json

HD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def tyc_search(q):
    u = "https://www.tianyancha.com/search?key=" + requests.utils.quote(q)
    r = requests.get(u, headers=HD, timeout=25)
    t = r.text
    links = re.findall(r'href="(/company/[0-9a-f]+)"', t)
    t2 = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t2 = re.sub(r"<style.*?</style>", "", t2, flags=re.S)
    t2 = re.sub(r"<[^>]+>", " ", t2)
    t2 = html.unescape(t2)
    t2 = re.sub(r"\s+", " ", t2)
    idx = t2.find(q)
    snip = t2[max(0, idx - 60):idx + 500] if idx >= 0 else t2[:500]
    return {"status": r.status_code, "links": links[:6], "snip": snip}

def tyc_company(path):
    u = "https://www.tianyancha.com" + path
    r = requests.get(u, headers=HD, timeout=25)
    t = r.text
    t2 = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t2 = re.sub(r"<style.*?</style>", "", t2, flags=re.S)
    t2 = re.sub(r"<[^>]+>", " ", t2)
    t2 = html.unescape(t2)
    t2 = re.sub(r"\s+", " ", t2)
    # extract fields
    fields = {}
    for label in ["法定代表人", "注册资本", "成立日期", "企业地址", "经营范围", "电话", "邮箱", "网址", "英文名", "曾用名"]:
        m = re.search(re.escape(label) + r"[：:\s]*([^,，；;]{2,120})", t2)
        if m:
            fields[label] = m.group(1).strip()
    return {"status": r.status_code, "fields": fields, "len": len(t)}

for q in ["海天瑞声科技股份有限公司", "光轮智能", "星忆科技"]:
    res = tyc_search(q)
    print("=== SEARCH:", q, "HTTP", res["status"], "===")
    print("links:", res["links"])
    print("snip:", res["snip"][:450])
    # go into first company page if a link found
    if res["links"]:
        c = tyc_company(res["links"][0])
        print("--- COMPANY PAGE:", res["links"][0], "HTTP", c["status"], "---")
        for k, v in c["fields"].items():
            print("  ", k, ":", v)
    print()
