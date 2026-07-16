from bs4 import BeautifulSoup
import re, json

SITES = ["moonshot","yinhe","zhipu","cambricon"]

for name in SITES:
    html = open(f"/pulp/find-job/{name}_dom.html").read()
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("[class*=job-item]")
    print(f"\n===== {name}: {len(items)} jobs =====")
    for it in items:
        a = it.find("a", href=True)
        href = a["href"] if a else ""
        jobId = href.split("/job/")[-1] if "/job/" in href else href
        # title
        title_el = it.select_one("[class*=title]")
        # get text, strip urgent tag
        urgent = ""
        title = ""
        if title_el:
            spans = title_el.find_all("span")
            parts = []
            for s in spans:
                t = s.get_text(strip=True)
                if t == "急":
                    urgent = "[急]"
                elif t:
                    parts.append(t)
            title = " ".join(parts) if parts else title_el.get_text(" ", strip=True)
        # location / status
        loc_el = it.select_one("[class*=status]")
        loc = loc_el.get_text(" ", strip=True) if loc_el else ""
        print(f"  {urgent} {title} | {loc} | id={jobId}")
