#!/usr/bin/env python3
"""Round 57g: fetch tianyancha company detail pages for 星忆科技 + 光轮智能."""
import requests, html, re, json

HD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.tianyancha.com/",
}

def company_detail(cid):
    u = "https://www.tianyancha.com/company/%s" % cid
    try:
        r = requests.get(u, headers=HD, timeout=25)
        t = r.text
        t2 = re.sub(r"<script.*?</script>", "", t, flags=re.S)
        t2 = re.sub(r"<style.*?</style>", "", t2, flags=re.S)
        t2 = re.sub(r"<[^>]+>", " ", t2)
        t2 = html.unescape(t2)
        t2 = re.sub(r"\s+", " ", t2)
        # extract title
        m = re.search(r"<title>(.*?)</title>", t, re.S)
        title = m.group(1).strip() if m else "none"
        # extract fields
        fields = {}
        for label in ["法定代表人", "注册资本", "成立日期", "企业地址", "经营范围", "电话", "邮箱", "网址", "英文名", "曾用名", "参保人数"]:
            mm = re.search(re.escape(label) + r"[：:\s]*([^,，；;。]{2,150})", t2)
            if mm:
                fields[label] = mm.group(1).strip()
        # also find emails/websites in raw
        emails = list(set(re.findall(r"[\w.+-]+@(?!tianyancha)[\w-]+\.[\w.-]+", t2)))
        return {"cid": cid, "status": r.status_code, "title": title, "fields": fields, "emails": emails[:5], "len": len(t)}
    except Exception as e:
        return {"cid": cid, "err": str(e)[:120]}

# 星忆科技 candidate IDs
print("##### 星忆科技 candidates #####")
for cid in ["3300048055", "7353021402", "6809991907"]:
    r = company_detail(cid)
    print(f"\n--- {cid} ---")
    for k, v in r.items():
        print(f"  {k}: {v}")

# 光轮智能 candidate IDs
print("\n\n##### 光轮智能 candidates #####")
for cid in ["8139176506", "8118016950", "7871259985"]:
    r = company_detail(cid)
    print(f"\n--- {cid} ---")
    for k, v in r.items():
        print(f"  {k}: {v}")
