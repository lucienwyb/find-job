#!/usr/bin/env python3
"""Round 57e: CNINFO for 688787 + 36kr for 星忆 + tianyancha company page guess."""
import requests, html, re, json, socket

HD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def clean(t):
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t)

def post_json(url, data, headers=None):
    try:
        r = requests.post(url, json=data, headers={**HD, "Content-Type": "application/json", **(headers or {})}, timeout=20)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)[:120]

# 1. CNINFO search for 688787 海天瑞声 - find official website from company profile
print("=== CNINFO: 688787 海天瑞声 ===")
sc, body = post_json("http://www.cninfo.com.cn/new/data/szse_stock.json", {})
if sc:
    try:
        d = json.loads(body)
        for s in d.get("stockList", []):
            if s.get("code") == "688787":
                print("  found:", s)
                break
        else:
            print("  not in stockList, keys:", list(d.keys())[:5])
    except Exception as e:
        print("  parse err", e, body[:200])
else:
    print("  HTTP", sc, body[:150])

# CNINFO company announcement search
print("\n=== CNINFO announcement search 688787 ===")
try:
    r = requests.post("http://www.cninfo.com.cn/new/hisAnnouncement/query",
        data={"stock": "688787,9900044100", "tabName": "fulltext", "pageSize": "5", "pageNum": "1", "category": "category_ndbg_szsh"},
        headers={**HD, "Content-Type": "application/x-www-form-urlencoded"}, timeout=20)
    d = r.json()
    anns = d.get("announcements", [])
    print(f"  HTTP {r.status_code}, {len(anns)} announcements")
    for a in anns[:3]:
        print(f"    - {a.get('announcementTitle','')} | {a.get('adjunctUrl','')}")
except Exception as e:
    print("  ERR", str(e)[:150])

# 2. SSE stock page for 688787
print("\n=== SSE: 688787 ===")
try:
    r = requests.get("https://www.sse.com.cn/disclosure/listedinfo/announcement/?securityCode=688787", headers=HD, timeout=20)
    print(f"  HTTP {r.status_code} len {len(r.text)}")
except Exception as e:
    print("  ERR", str(e)[:120])

# 3. 36kr search for 星忆科技
print("\n=== 36kr: 星忆科技 ===")
try:
    u = "https://www.36kr.com/search/articles/" + requests.utils.quote("星忆科技")
    r = requests.get(u, headers=HD, timeout=20)
    txt = clean(r.text)
    idx = txt.find("星忆")
    print(f"  HTTP {r.status_code} snip: {txt[idx:idx+400] if idx>=0 else txt[:200]}")
    urls = re.findall(r'https?://[^\s"<>]+', r.text)
    print("  urls:", [u for u in urls if "36kr" in u or "xingyi" in u.lower() or "star" in u.lower()][:8])
except Exception as e:
    print("  ERR", str(e)[:120])

# 4. 天眼查 company detail via search autocomplete API
print("\n=== TYC autocomplete: 星忆科技 ===")
try:
    r = requests.get("https://www.tianyancha.com/s/suggest.json",
        params={"key": "星忆科技"}, headers={**HD, "Referer": "https://www.tianyancha.com/"}, timeout=15)
    print(f"  HTTP {r.status_code} body: {r.text[:500]}")
except Exception as e:
    print("  ERR", str(e)[:120])

print("\n=== TYC autocomplete: 海天瑞声 ===")
try:
    r = requests.get("https://www.tianyancha.com/s/suggest.json",
        params={"key": "海天瑞声"}, headers={**HD, "Referer": "https://www.tianyancha.com/"}, timeout=15)
    print(f"  HTTP {r.status_code} body: {r.text[:500]}")
except Exception as e:
    print("  ERR", str(e)[:120])

print("\n=== TYC autocomplete: 光轮智能 ===")
try:
    r = requests.get("https://www.tianyancha.com/s/suggest.json",
        params={"key": "光轮智能"}, headers={**HD, "Referer": "https://www.tianyancha.com/"}, timeout=15)
    print(f"  HTTP {r.status_code} body: {r.text[:500]}")
except Exception as e:
    print("  ERR", str(e)[:120])
