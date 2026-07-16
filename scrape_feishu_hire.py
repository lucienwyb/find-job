import json, re, sys, time
from playwright.sync_api import sync_playwright

PORTALS = [
    ("星动纪元", "k0fqxcszc9.jobs.feishu.cn", "7154703376575596814"),
    ("清程极智", "chitu-ai.jobs.feishu.cn", "7343115810933688612"),
    ("零一万物", "01ai.jobs.feishu.cn", "7256966681745017145"),
]

PROXY = "http://100.66.66.64:8765"

def run():
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
        for name, host, wid in PORTALS:
            print(f"\n========== {name} ({host}) ==========", flush=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                locale="zh-CN",
            )
            page = ctx.new_page()
            captured = []  # list of (url, json_body)
            api_responses = []

            def on_response(response):
                url = response.url
                try:
                    ct = response.headers.get("content-type", "")
                except Exception:
                    ct = ""
                if "json" not in ct.lower():
                    return
                # 只关心XHR/fetch api
                if "/api/" not in url and "position" not in url.lower() and "job" not in url.lower() and "list" not in url.lower():
                    return
                try:
                    body = response.text()
                except Exception as e:
                    return
                if not body:
                    return
                api_responses.append((url, body))

            page.on("response", on_response)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            try:
                page.goto(f"https://{host}/", timeout=40000, wait_until="networkidle")
            except Exception as e:
                print(f"goto err: {e}", flush=True)
                try:
                    page.goto(f"https://{host}/", timeout=40000, wait_until="domcontentloaded")
                    page.wait_for_timeout(4000)
                except Exception as e2:
                    print(f"goto err2: {e2}", flush=True)

            # 滚动加载
            try:
                for _ in range(5):
                    page.mouse.wheel(0, 4000)
                    page.wait_for_timeout(1200)
            except Exception:
                pass
            # 尝试点击"全部岗位"或翻页
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass

            print(f"captured {len(api_responses)} json api responses", flush=True)
            for url, body in api_responses:
                print(f"  API: {url[:160]}", flush=True)
                print(f"  body[:300]: {body[:300]}", flush=True)

            results[name] = api_responses
            ctx.close()
        browser.close()

    # 保存原始数据
    with open("/pulp/find-job/raw_api_responses.json", "w", encoding="utf-8") as f:
        # results 含 body 字符串，序列化
        out = {n: [{"url": u, "body": b[:50000]} for u, b in lst] for n, lst in results.items()}
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nSaved raw_api_responses.json", flush=True)

    # 解析提取岗位
    print("\n\n======== 岗位提取 ========", flush=True)
    for name, host, wid in PORTALS:
        lst = results.get(name, [])
        positions = []
        for url, body in lst:
            try:
                data = json.loads(body)
            except Exception:
                continue
            # 递归找包含 position 列表的对象
            found = extract_positions(data)
            if found:
                positions.extend(found)
        # 去重
        seen = set()
        uniq = []
        for p in positions:
            key = p.get("title") or p.get("name") or ""
            if key and key not in seen:
                seen.add(key)
                uniq.append(p)
        print(f"\n----- {name}: {len(uniq)} 岗位 -----", flush=True)
        for p in uniq:
            print(json.dumps(p, ensure_ascii=False), flush=True)

def extract_positions(obj):
    """递归从JSON里提取岗位对象列表。岗位对象通常含 title/name + id 字段。"""
    out = []
    if isinstance(obj, list):
        # 如果这是一个岗位列表（元素含title/name字段）
        if obj and isinstance(obj[0], dict):
            first = obj[0]
            if any(k in first for k in ["title", "name", "position_name", "job_name"]):
                # 可能是岗位列表
                likely = True
                # 但要避免误判成其他列表，检查字段数
                if len(first) > 3:
                    for it in obj:
                        if isinstance(it, dict):
                            out.append(normalize_pos(it))
                if out:
                    return out
        for it in obj:
            out.extend(extract_positions(it))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(extract_positions(v))
    return out

def normalize_pos(d):
    title = d.get("title") or d.get("name") or d.get("position_name") or d.get("job_name") or d.get("position_title") or ""
    pid = d.get("id") or d.get("position_id") or d.get("job_id") or ""
    city = d.get("city") or d.get("location") or d.get("work_location") or ""
    # 发布日期字段
    pub = ""
    for k in ["publish_time","create_time","published_at","update_time","created_at","updated_at","gmt_create","gmt_modified","publish_date","open_time"]:
        if k in d and d[k]:
            pub = str(d[k]); break
    dept = d.get("department") or d.get("dept") or d.get("department_name") or ""
    desc = d.get("description") or d.get("desc") or d.get("job_description") or ""
    return {"title": title, "id": str(pid), "city": city, "pub": pub, "dept": dept, "desc": desc[:200]}

if __name__ == "__main__":
    run()
