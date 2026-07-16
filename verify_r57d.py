#!/usr/bin/env python3
"""Round 57d: tianyancha mobile/search API for company official site + contact."""
import requests, html, re, json

HD = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def clean(t):
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t)

# Try tianyancha company search API (returns JSON)
def tyc_api(q):
    # The mobile search endpoint
    u = "https://www.tianyancha.com/cloud-tianyancha/api/searchBaseInfo/searchKeyWordV2"
    try:
        r = requests.get(u, params={"key": q}, headers={**HD, "Referer": "https://www.tianyancha.com/"}, timeout=20)
        return r.status_code, r.text[:800]
    except Exception as e:
        return None, str(e)[:120]

# Try the qcc (企查查) open search
def qcc_search(q):
    u = "https://www.qcc.com/api/datalist/searchkey"
    try:
        r = requests.get(u, params={"key": q}, headers={**HD, "Referer": "https://www.qcc.com/"}, timeout=20)
        return r.status_code, r.text[:800]
    except Exception as e:
        return None, str(e)[:120]

# Direct company page guess for tianyancha - need the numeric id
# Try fetching the search page and parse the JSON embedded in __NEXT_DATA__ or window.__INITIAL_STATE__
def tyc_search_next(q):
    u = "https://www.tianyancha.com/search?key=" + requests.utils.quote(q)
    try:
        r = requests.get(u, headers=HD, timeout=25)
        t = r.text
        # look for embedded JSON with company list
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', t, re.S)
        if m:
            try:
                d = json.loads(m.group(1))
                return "INITIAL_STATE", str(d)[:1000]
            except: pass
        m2 = re.search(r'__NEXT_DATA__"[^>]*>(\{.*?\})</script>', t, re.S)
        if m2:
            return "NEXT_DATA", m2.group(1)[:1000]
        # look for phone/email/website in raw
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", t)
        websites = re.findall(r'(?:官网|网址|website)["：:\s]*(https?://[^\s"<>]+)', t, re.I)
        return "raw", {"emails": list(set(emails))[:5], "websites": websites[:5]}
    except Exception as e:
        return "err", str(e)[:120]

for q, label in [("海天瑞声科技股份有限公司", "海天瑞声"), ("星忆科技", "星忆科技"), ("北京光轮智能科技有限公司", "光轮智能")]:
    print("=" * 50)
    print(f"  {label} ({q})")
    print("=" * 50)
    # method 1: tyc search page embedded data
    kind, res = tyc_search_next(q)
    print(f"  [tyc search] {kind}: {str(res)[:400]}")
    # method 2: qcc search
    sc, body = qcc_search(q)
    print(f"  [qcc api] HTTP {sc}: {body[:300]}")
    print()
