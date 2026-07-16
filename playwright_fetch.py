import sys, json, time
from playwright.sync_api import sync_playwright

def fetch(url, wait_for=None, wait_ms=5000, extract_links=False, extract_text=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width':1920,'height':1080}
        )
        page = context.new_page()
        try:
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            time.sleep(wait_ms / 1000.0)
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10000)
                except:
                    pass
            title = page.title()
            html = page.content()
            result = {'url': url, 'title': title, 'html_len': len(html)}
            if extract_links:
                links = page.eval_on_selector_all('a', '''els => els.map(e => ({href: e.href, text: e.innerText.trim()}))''')
                result['links'] = links
            if extract_text:
                result['text'] = page.inner_text('body')
            result['html'] = html
            return result
        except Exception as e:
            return {'url': url, 'error': str(e)}
        finally:
            browser.close()

if __name__ == '__main__':
    url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'html'
    wait = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    result = fetch(url, wait_ms=wait, extract_links=(mode=='links'), extract_text=(mode=='text'))
    # Print without html for text/links mode
    if mode == 'text':
        print(json.dumps({'url': result.get('url'), 'title': result.get('title'), 'text': result.get('text','')[:10000], 'error': result.get('error')}, ensure_ascii=False, indent=2))
    elif mode == 'links':
        print(json.dumps({'url': result.get('url'), 'title': result.get('title'), 'links': result.get('links',[]), 'error': result.get('error')}, ensure_ascii=False, indent=2))
    else:
        # save full html to file, print summary
        fname = sys.argv[4] if len(sys.argv) > 4 else '/tmp/pw_output.html'
        with open(fname, 'w') as f:
            f.write(result.get('html',''))
        print(json.dumps({'url': result.get('url'), 'title': result.get('title'), 'html_len': result.get('html_len',0), 'saved_to': fname, 'error': result.get('error')}, ensure_ascii=False, indent=2))
