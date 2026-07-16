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

            all_posts = []  # 累积所有页的岗位
            total_seen = set()

            def on_response(response):
                url = response.url
                if "search/job/posts" in url:
                    try:
                        body = response.text()
                        data = json.loads(body)
                        posts = data.get("data", {}).get("job_post_list", [])
                        for p_ in posts:
                            pid = p_.get("id","")
                            if pid and pid not in total_seen:
                                total_seen.add(pid)
                                all_posts.append(p_)
                        print(f"  [job/posts] 捕获 {len(posts)} 条, 累积 {len(all_posts)} 条", flush=True)
                    except Exception as e:
                        print(f"  [解析失败] {e}", flush=True)

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

            # 滚动触发
            try:
                for _ in range(5):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            # 如果没有捕获到，点击"岗位"
            if not all_posts:
                print("未捕获到，尝试点击岗位...", flush=True)
                for sel in ["text=岗位", "text=职位", "text=社招", "text=全部岗位"]:
                    try:
                        page.click(sel, timeout=2000)
                        page.wait_for_timeout(3000)
                        if all_posts:
                            break
                    except Exception:
                        continue

            # 尝试翻页：找"下一页"/"加载更多"/页码按钮
            # 飞书Hire通常有分页器，尝试点击下一页直到没有新数据
            max_pages = 20
            for page_idx in range(max_pages):
                prev_count = len(all_posts)
                # 尝试多种翻页选择器
                clicked = False
                for sel in [
                    "button:has-text('下一页')",
                    "a:has-text('下一页')",
                    "[class*='next']:not([disabled])",
                    "li[class*='next']:not([disabled])",
                    "button[aria-label='next']",
                    ".ant-pagination-next:not(.ant-pagination-disabled)",
                    "[class*='pagination'] [class*='next']",
                ]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=1000):
                            el.click(timeout=2000)
                            clicked = True
                            page.wait_for_timeout(2500)
                            break
                    except Exception:
                        continue

                if not clicked:
                    # 尝试滚动到列表底部触发加载
                    try:
                        page.mouse.wheel(0, 5000)
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass

                if len(all_posts) == prev_count:
                    # 没有新数据，可能到底了
                    print(f"  第{page_idx+1}页无新数据，停止翻页", flush=True)
                    break

            print(f"总计捕获 {len(all_posts)} 条岗位", flush=True)
            all_data[name] = {"host": host, "posts": all_posts}
            ctx.close()
        browser.close()

    # 保存
    with open("/pulp/find-job/all_positions_full.json", "w", encoding="utf-8") as f:
        out = {}
        for name, v in all_data.items():
            out[name] = {"host": v["host"], "posts": v["posts"]}
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 解析显示
    print("\n\n======== 完整岗位清单 ========", flush=True)
    for name, v in all_data.items():
        posts = v["posts"]
        print(f"\n----- {name}: {len(posts)} 岗位 -----", flush=True)
        for p in posts:
            title = p.get("title","")
            pub = p.get("publish_time","")
            cities = [c.get("name","") for c in (p.get("city_list") or [])]
            city = "/".join(cities) if cities else ""
            jc = p.get("job_category")
            jc_name = jc.get("name","") if isinstance(jc,dict) else ""
            print(f'  [{pub}] {title} | {city} | {jc_name}', flush=True)

if __name__ == "__main__":
    run()
