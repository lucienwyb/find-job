#!/usr/bin/env python3
"""Round 57c: targeted - DNS, baidu, qcc for the 3 companies."""
import requests, html, re, socket

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

def baidu(wd):
    try:
        u = "https://www.baidu.com/s?wd=" + requests.utils.quote(wd)
        r = requests.get(u, headers=HD, timeout=20)
        t = r.text
        txt = clean(t)
        # extract result titles/snippets: baidu wraps results; grab text around keyword
        # find all http urls that look like real sites
        urls = re.findall(r"https?://(?!www\.baidu\.com|baidu\.com|mip\.baidu|bdstatic|baiducontent)[^\s\"'<>]+\.[a-z]{2,}[^\s\"'<>]*", t)
        seen = []
        for u in urls:
            base = re.match(r"https?://([^/]+)", u)
            if base and base.group(1) not in seen:
                seen.append(base.group(1))
        return seen[:12], txt
    except Exception as e:
        return [], str(e)

# 1. DNS check for speechocean
print("=== DNS: speechocean.com ===")
try:
    print("  A:", socket.gethostbyname("www.speechocean.com"))
except Exception as e:
    print("  ERR:", e)
try:
    print("  A (no www):", socket.gethostbyname("speechocean.com"))
except Exception as e:
    print("  ERR:", e)

# 2. Baidu: 海天瑞声 官网 招聘
print("\n=== Baidu: 海天瑞声 官网 ===")
seen, txt = baidu("海天瑞声 官网 招聘")
print("  domains:", seen)
idx = txt.find("海天瑞声")
print("  snip:", txt[idx:idx+350] if idx >= 0 else "(not found)")

# 3. Baidu: 海天瑞声 招聘 邮箱
print("\n=== Baidu: 海天瑞声 招聘 邮箱 hr ===")
seen, txt = baidu("海天瑞声科技 招聘邮箱 hr@speechocean")
print("  domains:", seen)
emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", txt)
print("  emails:", list(set(emails))[:8])
idx = txt.find("speechocean")
print("  snip:", txt[max(0,idx-30):idx+250] if idx >= 0 else "(not found)")

# 4. Baidu: 星忆科技 官网
print("\n=== Baidu: 星忆科技 北京 官网 仿真 ===")
seen, txt = baidu("星忆科技 北京 官网 仿真 多模态")
print("  domains:", seen)
idx = txt.find("星忆")
print("  snip:", txt[idx:idx+350] if idx >= 0 else "(not found)")

# 5. Baidu: 星忆科技 宋知珩
print("\n=== Baidu: 星忆科技 宋知珩 智元 ===")
seen, txt = baidu("星忆科技 宋知珩 智元 EgoScale")
print("  domains:", seen)
idx = txt.find("星忆")
print("  snip:", txt[idx:idx+350] if idx >= 0 else "(not found)")
idx2 = txt.find("宋知珩")
print("  snip2:", txt[idx2:idx2+350] if idx2 >= 0 else "(宋知珩 not found)")

# 6. qcc (企查查) search for 星忆科技
print("\n=== qcc: 星忆科技 ===")
try:
    u = "https://www.qcc.com/web/search?key=" + requests.utils.quote("星忆科技")
    r = requests.get(u, headers=HD, timeout=20)
    txt = clean(r.text)
    # qcc puts company name + key info
    idx = txt.find("星忆")
    print("  HTTP", r.status_code, "snip:", txt[idx:idx+400] if idx >= 0 else txt[:300])
    links = re.findall(r'/firm/([a-z0-9]+)', r.text)
    print("  firm links:", links[:5])
except Exception as e:
    print("  ERR:", e)

# 7. Lightwheel BOSS zhipin search
print("\n=== Baidu: 光轮智能 招聘 BOSS直聘 ===")
seen, txt = baidu("光轮智能 lightwheel 招聘 BOSS直聘 工程师")
print("  domains:", seen)
idx = txt.find("光轮")
print("  snip:", txt[idx:idx+350] if idx >= 0 else "(not found)")
