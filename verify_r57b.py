#!/usr/bin/env python3
"""Round 57b: fetch official sites + careers via shine (China mainland IP, direct)."""
import requests, html, re

HD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def clean(t):
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t)
    return t

def fetch(url, timeout=25):
    try:
        r = requests.get(url, headers=HD, timeout=timeout, allow_redirects=True)
        return r.status_code, r.text, r.url
    except Exception as e:
        return None, str(e), url

def links_of(t, keywords):
    ls = re.findall(r'href="([^"]+)"', t)
    return [l for l in ls if any(k in l.lower() for k in keywords)][:20]

# ---- 1. Speechocean ----
print("=" * 60)
print("1. SPEEOCEAN (海天瑞声)")
print("=" * 60)
for url in [
    "https://www.speechocean.com/",
    "https://www.speechocean.com/careers",
    "https://www.speechocean.com/contact-us",
    "https://www.speechocean.com/about-us",
    "http://www.speechocean.com/",
]:
    sc, t, fu = fetch(url)
    if sc is None:
        print(f"  {url} -> ERR {t[:80]}")
    else:
        print(f"  {url} -> HTTP {sc} final={fu} len={len(t)}")
        cl = links_of(t, ["career", "job", "zhaopin", "hr", "contact", "join", "recruit"])
        if cl:
            print("    links:", cl)
        txt = clean(t)
        # find email
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", txt)
        if emails:
            print("    emails:", list(set(emails))[:8])
        # find address / phone
        for kw in ["海淀区", "知春路", "领航", "电话", "010-", "hr@", "zhaopin@"]:
            idx = txt.find(kw)
            if idx >= 0:
                print(f"    [{kw}]:", txt[max(0, idx - 20):idx + 80])
print()

# ---- 2. Lightwheel ----
print("=" * 60)
print("2. LIGHTWHEEL AI (光轮智能)")
print("=" * 60)
for url in [
    "https://www.lightwheel.ai/careers",
    "https://www.lightwheel.ai/about",
    "https://www.lightwheel.ai/contact",
]:
    sc, t, fu = fetch(url)
    if sc is None:
        print(f"  {url} -> ERR {t[:80]}")
    else:
        print(f"  {url} -> HTTP {sc} len={len(t)}")
        cl = links_of(t, ["mokahr", "job", "apply", "position", "zhipin", "boss", "hire", "lever", "greenhouse"])
        if cl:
            print("    links:", cl)
        txt = clean(t)
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", txt)
        if emails:
            print("    emails:", list(set(emails))[:8])
print()

# ---- 3. 星忆科技 - search Baidu for official site ----
print("=" * 60)
print("3. 星忆科技 - Baidu search for official site")
print("=" * 60)
sc, t, fu = fetch("https://www.baidu.com/s?wd=" + requests.utils.quote("星忆科技 北京 官网 仿真"))
if sc:
    txt = clean(t)
    # baidu results contain URLs
    urls = re.findall(r"https?://[^\s\"'<>]+", t)
    interesting = [u for u in urls if not any(b in u for b in ["baidu.com", "baiducontent", "bdstatic", "baidubox"])][:15]
    print("  result URLs:", interesting)
    idx = txt.find("星忆")
    print("  snip:", txt[idx:idx + 300] if idx >= 0 else txt[:300])
print()

# also baidu for 海天瑞声 招聘
print("=== Baidu: 海天瑞声 招聘 ===")
sc, t, fu = fetch("https://www.baidu.com/s?wd=" + requests.utils.quote("海天瑞声 招聘 数据平台 工程师"))
if sc:
    txt = clean(t)
    urls = re.findall(r"https?://[^\s\"'<>]+", t)
    interesting = [u for u in urls if not any(b in u for b in ["baidu.com", "baiducontent", "bdstatic", "baidubox"])][:15]
    print("  URLs:", interesting)
    idx = txt.find("海天瑞声")
    print("  snip:", txt[idx:idx + 400] if idx >= 0 else txt[:400])
