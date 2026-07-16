#!/usr/bin/env python3
"""Round 55c: dump cambricon sidebar + decrypt necromancer; check hotjob page content."""
import json, time
from playwright.sync_api import sync_playwright

PROXY = "http://100.66.66.64:8765"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def cambricon(p):
    b = p.chromium.launch(headless=True, proxy={"server": PROXY})
    pg = b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
    necro=None
    def on_resp(resp):
        nonlocal necro
        u=resp.url
        if "website/jobs" in u:
            try:
                body=resp.json(); necro=body
            except: pass
    pg.on("response", on_resp)
    try: pg.goto("https://app.mokahr.com/apply/cambricon/1113", wait_until="networkidle", timeout=45000)
    except Exception as e: print("goto err",e)
    time.sleep(4)

    # 1. Dump the left sidebar / department nav HTML
    try:
        sidebar = pg.eval_on_selector_all("nav,aside,[class*='idebar'],[class*='epart'],[class*='ateg'],[class*='enu']",
            "els=>els.map(e=>({tag:e.tagName,cls:e.className,html:(e.outerHTML||'').slice(0,300)}))")
        print("sidebar-ish elems:", len(sidebar))
        for s in sidebar[:8]: print("  ",s.get("tag"),s.get("cls","")[:30],"|",s.get("html","")[:150])
    except Exception as e: print("sidebar dump err",e)

    # 2. Try decrypt necromancer via the page's own modules (it already decrypted for display)
    #    The mokahr SPA stores decrypted job list in a global/observable. Try common globals.
    decrypted=None
    try:
        decrypted = pg.evaluate("""()=>{
            // try to find the decrypt in loaded modules
            const keys = Object.keys(window).filter(k=>/decrypt|necro|crypto/i.test(k));
            return {windowKeys: keys.slice(0,20)};
        }""")
        print(" window candidate keys:", decrypted)
    except Exception as e: print(" eval err",e)

    # 3. Try standard mokahr necromancer decryption in Python (XOR with hex key)
    if necro:
        data=necro.get("data",""); key=necro.get("necromancer","")
        print(f" necro data len={len(data)} key={key}")
        import base64
        try:
            raw = base64.b64decode(data)
            # XOR with key bytes (interpret key as ascii chars cycling)
            kb = key.encode()
            dec = bytes(b ^ kb[i%len(kb)] for i,b in enumerate(raw))
            txt = dec.decode("utf-8","ignore")
            print("  XOR(ascii) preview:", txt[:200])
            if "系统软件" in txt or "jobId" in txt or "postName" in txt:
                print("  *** DECRYPT OK (ascii XOR) ***")
                with open("/pulp/find-job/scrape/data/r55c_cambricon_decrypted.json","w") as f: f.write(txt)
        except Exception as e: print("  b64 ascii xor err:",e)
        try:
            raw = base64.b64decode(data)
            kb = bytes.fromhex(key)
            dec = bytes(b ^ kb[i%len(kb)] for i,b in enumerate(raw))
            txt = dec.decode("utf-8","ignore")
            print("  XOR(hex) preview:", txt[:200])
            if "系统软件" in txt or "jobId" in txt:
                print("  *** DECRYPT OK (hex XOR) ***")
                with open("/pulp/find-job/scrape/data/r55c_cambricon_decrypted.json","w") as f: f.write(txt)
        except Exception as e: print("  b64 hex xor err:",e)

    # 4. Click each department: find all clickable dept buttons by scanning the rendered DOM
    all_links=[]
    def collect():
        try:
            return pg.eval_on_selector_all("a[href*='#/job/']","els=>els.map(e=>({href:e.href,text:(e.innerText||'').trim().split('\\n')[0]}))")
        except: return []
    # dump all elements with department-suggestive text and few children
    try:
        depts = pg.eval_on_selector_all("*","""els=>{
            const out=[];
            for(const e of els){
              const t=(e.innerText||'').trim();
              if(t.length>0 && t.length<14 && (/部$|中心$|组$/.test(t)) && e.children.length<=2){
                out.push({txt:t,tag:e.tagName,cls:(e.className||'').toString().slice(0,40)});
              }
            }
            const seen=new Set();return out.filter(o=>{if(seen.has(o.txt))return false;seen.add(o.txt);return true;});
        }""")
        print(" all dept-text elems:",[d.get("txt") for d in depts][:30])
        for d in depts:
            try:
                el = pg.query_selector(f":has-text('{d['txt']}')")
                # only click leaf elements
                leaf = pg.eval_on_selector_all(f"//*[normalize-space(text())='{d['txt']}']","els=>els.map(e=>({tag:e.tagName,cls:e.className}))[0]") if False else None
            except: pass
        # click by text via locator
        for d in depts:
            txt=d["txt"]
            try:
                loc = pg.locator(f"text=\"{txt}\"").first
                loc.click(timeout=2000)
                time.sleep(1.0)
                for l in collect():
                    if l not in all_links: all_links.append(l)
            except: pass
    except Exception as e: print(" dept click err",e)

    # fallback scroll
    for _ in range(8):
        pg.mouse.wheel(0,4000); time.sleep(0.8)
    for l in collect():
        if l not in all_links: all_links.append(l)
    print(f" total unique job links: {len(all_links)}")
    for l in all_links:
        if "系统软件" in l.get("text",""):
            print(f"  >>> HIT: {l.get('text')} | {l.get('href')}")
    with open("/pulp/find-job/scrape/data/r55c_cambricon.json","w") as f:
        json.dump({"links":all_links},f,ensure_ascii=False,indent=1)
    b.close()

def horizon(p):
    b = p.chromium.launch(headless=True, proxy={"server": PROXY})
    pg = b.new_context(user_agent=UA, viewport={"width":1920,"height":1080}).new_page()
    api=[]
    def on_resp(resp):
        u=resp.url
        if "hotjob" in u:
            ct=resp.headers.get("content-type","")
            if "json" in ct:
                try: api.append({"url":u,"body":resp.json()}); print("  [API]",u[:120])
                except: pass
    pg.on("response", on_resp)
    for u in ["https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a/pb/social.html",
              "https://wecruit.hotjob.cn/SU64819a4f2f9d2433ba8b043a"]:
        try:
            pg.goto(u, wait_until="networkidle", timeout=40000); time.sleep(5)
            # dump page text snippet
            txt = pg.eval_on_selector_all("body","els=>els.map(e=>(e.innerText||'').slice(0,300))")
            print("  page text:", (txt[0] if txt else "")[:200].replace("\n"," "))
            break
        except Exception as e: print("  goto err",e)
    # any api with jobs?
    found=[]
    for c in api:
        def fl(o,d=0):
            if d>7:return
            if isinstance(o,list) and o and isinstance(o[0],dict) and any(k in o[0] for k in ("postId","postName","positionName")):
                found.extend(o)
            elif isinstance(o,dict):
                for v in o.values(): fl(v,d+1)
        fl(c["body"])
    print(f"  api jobs found: {len(found)}")
    for j in found:
        n=j.get("postName","")
        if "存储" in n or "分布式" in n:
            print(f"  >>> {n} | postId={j.get('postId')} | dept={j.get('department')} | pub={j.get('publishDate')}")
    with open("/pulp/find-job/scrape/data/r55c_horizon.json","w") as f:
        json.dump({"api_jobs":found,"raw_api_urls":[c["url"] for c in api]},f,ensure_ascii=False,indent=1)
    b.close()

def main():
    with sync_playwright() as p:
        cambricon(p)
        horizon(p)

if __name__=="__main__": main()
