import json, time
from playwright.sync_api import sync_playwright

PORTALS = [
    ("星动纪元", "k0fqxcszc9.jobs.feishu.cn"),
    ("清程极智", "chitu-ai.jobs.feishu.cn"),
    ("零一万物", "01ai.jobs.feishu.cn"),
]
PROXY = "http://100.66.66.64:8765"

def fetch_positions(page, host):
    """在页面上下文里直接fetch岗位API"""
    js = """
    async () => {
        const params = new URLSearchParams({
            keyword: '',
            limit: '200',
            offset: '0',
            job_category_id_list: '',
            tag_id_list: '',
            location_code_list: '',
            subject_id_list: '',
            recruitment_id_list: '',
            portal_type: '6',
            job_function_id_list: '',
            storefront_id_list: '',
            portal_entrance: '1',
        });
        const url = '/api/v1/search/job/posts?' + params.toString();
        const resp = await fetch(url, {credentials: 'include'});
        const txt = await resp.text();
        return {status: resp.status, body: txt};
    }
    """
    result = page.evaluate(js)
    return result

def run():
    all_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
        for name, host in PORTALS:
            print(f"\n========== {name} ({host}) ==========", flush=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                locale="zh-CN",
            )
            page = ctx.new_page()
            # 记录实际发出的search请求URL（含_signature）以备用
            captured_urls = []
            def on_request(req):
                if "search/job/posts" in req.url:
                    captured_urls.append(req.url)
            page.on("request", on_request)

            try:
                page.goto(f"https://{host}/", timeout=45000, wait_until="networkidle")
            except Exception as e:
                print(f"goto err: {e}", flush=True)
                try:
                    page.goto(f"https://{host}/", timeout=45000, wait_until="domcontentloaded")
                    page.wait_for_timeout(5000)
                except Exception as e2:
                    print(f"goto err2: {e2}", flush=True)

            # 等页面加载完，尝试滚动触发
            try:
                for _ in range(3):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(1500)
            except Exception:
                pass

            # 方法1: 直接fetch
            print("尝试直接fetch...", flush=True)
            result = None
            try:
                result = fetch_positions(page, host)
            except Exception as e:
                print(f"fetch err: {e}", flush=True)

            if result:
                print(f"fetch status={result['status']} bodylen={len(result['body'])}", flush=True)
                # 如果直接fetch成功
                all_data[name] = {"host": host, "captured_url": captured_urls[-1] if captured_urls else "", "fetch_result": result}
            else:
                # 方法2: 用捕获到的带_signature的URL重新请求
                if captured_urls:
                    print(f"用捕获URL重试: {captured_urls[-1][:120]}", flush=True)
                    # 修改limit
                    url = captured_urls[-1]
                    import re
                    url = re.sub(r'limit=\d+', 'limit=200', url)
                    url = re.sub(r'offset=\d+', 'offset=0', url)
                    try:
                        resp = page.evaluate("""async (u) => {
                            const r = await fetch(u, {credentials:'include'});
                            return {status: r.status, body: await r.text()};
                        }""", url)
                        print(f"重试 status={resp['status']} bodylen={len(resp['body'])}", flush=True)
                        all_data[name] = {"host": host, "captured_url": url, "fetch_result": resp}
                    except Exception as e:
                        print(f"重试err: {e}", flush=True)
                        all_data[name] = {"host": host, "captured_url": captured_urls[-1], "fetch_result": None}
                else:
                    # 方法3: 触发更多交互
                    print("未捕获到请求，尝试点击岗位tab...", flush=True)
                    try:
                        # 点击可能的"全部岗位"链接
                        page.click("text=岗位", timeout=3000)
                        page.wait_for_timeout(3000)
                    except Exception:
                        pass
                    try:
                        result = fetch_positions(page, host)
                        if result:
                            all_data[name] = {"host": host, "captured_url": "", "fetch_result": result}
                    except Exception as e:
                        print(f"方法3err: {e}", flush=True)
                        all_data[name] = {"host": host, "captured_url": "", "fetch_result": None}

            ctx.close()
        browser.close()

    # 保存
    with open("/pulp/find-job/all_positions_raw.json", "w", encoding="utf-8") as f:
        out = {}
        for name, v in all_data.items():
            out[name] = {"host": v["host"], "captured_url": v["captured_url"]}
            if v.get("fetch_result"):
                out[name]["status"] = v["fetch_result"]["status"]
                out[name]["body"] = v["fetch_result"]["body"][:100000]
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 解析
    print("\n\n======== 岗位清单 ========", flush=True)
    for name, v in all_data.items():
        fr = v.get("fetch_result")
        if not fr:
            print(f"\n----- {name}: 无数据 -----\n", flush=True)
            continue
        try:
            data = json.loads(fr["body"])
        except Exception as e:
            print(f"\n----- {name}: JSON解析失败 {e} -----\n", flush=True)
            print(fr["body"][:500], flush=True)
            continue
        posts = data.get("data", {}).get("job_post_list", [])
        print(f"\n----- {name}: {len(posts)} 岗位 -----", flush=True)
        for p in posts:
            title = p.get("title","")
            pid = p.get("id","")
            pub = p.get("publish_time","")
            cities = [c.get("name","") for c in (p.get("city_list") or [])]
            city = "/".join(cities) if cities else ""
            # job_function / job_category
            jf = p.get("job_function")
            jf_name = jf.get("name","") if isinstance(jf, dict) else ""
            jc = p.get("job_category")
            jc_name = jc.get("name","") if isinstance(jc, dict) else ""
            desc = (p.get("description","") or "")[:300]
            print(json.dumps({"title":title, "id":pid, "pub":pub, "city":city, "job_function":jf_name, "category":jc_name, "desc":desc}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    run()
