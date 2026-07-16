import json, time, re
from playwright.sync_api import sync_playwright

PORTALS = [
    ("星动纪元", "k0fqxcszc9.jobs.feishu.cn"),
    ("清程极智", "chitu-ai.jobs.feishu.cn"),
    ("零一万物", "01ai.jobs.feishu.cn"),
]
PROXY = "http://100.66.66.64:8765"

def run():
    all_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": PROXY})
        for name, host in PORTALS:
            print(f"\n========== {name} ({host}) ==========", flush=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
            )
            page = ctx.new_page()

            captured_posts_url = []
            captured_posts_body = []

            def on_response(response):
                url = response.url
                if "search/job/posts" in url:
                    captured_posts_url.append(url)
                    try:
                        captured_posts_body.append(response.text())
                        print(f"  [捕获 job/posts 响应] len={len(captured_posts_body[-1])}", flush=True)
                    except Exception as e:
                        captured_posts_body.append("")
                        print(f"  [捕获响应失败] {e}", flush=True)

            page.on("response", on_response)

            try:
                page.goto(f"https://{host}/", timeout=45000, wait_until="networkidle")
            except Exception as e:
                print(f"goto err: {e}", flush=True)
                try:
                    page.goto(f"https://{host}/", timeout=45000, wait_until="domcontentloaded")
                    page.wait_for_timeout(5000)
                except Exception as e2:
                    print(f"goto err2: {e2}", flush=True)

            # 滚动触发懒加载
            try:
                for _ in range(8):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            # 如果还没捕获到，尝试点击导航栏"岗位"类入口
            if not captured_posts_body:
                print("未捕获到job/posts，尝试点击导航...", flush=True)
                for sel in ["text=岗位", "text=职位", "text=社招", "text=全部岗位", "text=All Positions",
                            "a:has-text('岗位')", "a:has-text('职位')", "[class*='position']", "[class*='job']"]:
                    try:
                        page.click(sel, timeout=2000)
                        page.wait_for_timeout(3000)
                        if captured_posts_body:
                            print(f"  点击 {sel} 后捕获到!", flush=True)
                            break
                    except Exception:
                        continue

            # 再滚动
            try:
                for _ in range(5):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            # 如果有了带_signature的URL，用修改limit=200重新fetch
            if captured_posts_url:
                base_url = captured_posts_url[-1]
                # 修改limit和offset
                new_url = re.sub(r'limit=\d+', 'limit=200', base_url)
                new_url = re.sub(r'offset=\d+', 'offset=0', new_url)
                print(f"用签名URL重fetch(limit=200): {new_url[:100]}...", flush=True)
                try:
                    resp = page.evaluate("""async (u) => {
                        const r = await fetch(u, {credentials:'include'});
                        return {status: r.status, body: await r.text()};
                    }""", new_url)
                    print(f"重fetch status={resp['status']} bodylen={len(resp['body'])}", flush=True)
                    if resp["status"] == 200 and resp["body"].startswith("{"):
                        captured_posts_body = [resp["body"]]
                except Exception as e:
                    print(f"重fetch err: {e}", flush=True)

            # 最终结果
            body = captured_posts_body[-1] if captured_posts_body else ""
            all_data[name] = {"host": host, "body": body}

            # 保存截图备用
            try:
                page.screenshot(path=f"/pulp/find-job/{name}_screenshot.png", full_page=False)
            except Exception:
                pass

            ctx.close()
        browser.close()

    # 保存原始
    with open("/pulp/find-job/all_positions_raw.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    # 解析
    print("\n\n======== 岗位清单 ========", flush=True)
    for name, v in all_data.items():
        body = v.get("body", "")
        if not body:
            print(f"\n----- {name}: 无数据 -----\n", flush=True)
            continue
        try:
            data = json.loads(body)
        except Exception as e:
            print(f"\n----- {name}: JSON解析失败 {e} -----\n", flush=True)
            print(body[:300], flush=True)
            continue
        posts = data.get("data", {}).get("job_post_list", [])
        print(f"\n----- {name}: {len(posts)} 岗位 -----", flush=True)
        for p in posts:
            title = p.get("title","")
            pid = p.get("id","")
            pub = p.get("publish_time","")
            cities = [c.get("name","") for c in (p.get("city_list") or [])]
            city = "/".join(cities) if cities else ""
            jf = p.get("job_function")
            jf_name = jf.get("name","") if isinstance(jf, dict) else ""
            jc = p.get("job_category")
            jc_name = jc.get("name","") if isinstance(jc, dict) else ""
            desc = (p.get("description","") or "")[:200]
            req = (p.get("requirement","") or "")[:200]
            print(json.dumps({"title":title, "id":pid, "pub":pub, "city":city, "job_function":jf_name, "category":jc_name, "desc":desc, "req":req}, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    run()
