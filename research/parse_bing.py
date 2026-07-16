import sys, re, html
from html.parser import HTMLParser

class AlgoExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_algo = False
        self.depth = 0
        self.in_h2 = False
        self.in_cite = False
        self.in_p = False
        self.cur = {}
        self.results = []
        self.buf = ""
        self.capture_target = None

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")
        if tag == "li" and "b_algo" in cls:
            self.in_algo = True
            self.depth = 0
            self.cur = {"title": "", "url": "", "snippet": ""}
            return
        if not self.in_algo:
            return
        if tag == "h2":
            self.in_h2 = True
            self.buf = ""
            # find href in nested a
        if tag == "a" and self.in_h2 and not self.cur["url"]:
            href = attrs_d.get("href", "")
            if href:
                self.cur["url"] = href
                self.capture_target = "title"
        if tag == "p":
            # snippet container
            self.in_p = True
            self.buf = ""
        if tag == "cite":
            self.in_cite = True

    def handle_endtag(self, tag):
        if not self.in_algo:
            return
        if tag == "h2" and self.in_h2:
            self.in_h2 = False
            self.cur["title"] = html.unescape(self.buf.strip())
        if tag == "p" and self.in_p:
            self.in_p = False
            if not self.cur["snippet"]:
                self.cur["snippet"] = html.unescape(self.buf.strip())
        if tag == "cite":
            self.in_cite = False
        if tag == "li" and self.in_algo:
            self.in_algo = False
            if self.cur.get("title") or self.cur.get("url"):
                self.results.append(self.cur)
            self.cur = {}

    def handle_data(self, data):
        if not self.in_algo:
            return
        if self.in_h2:
            self.buf += data
        if self.in_p:
            self.buf += data

with open(sys.argv[1], encoding="utf-8", errors="ignore") as f:
    text = f.read()

p = AlgoExtractor()
p.feed(text)
for i, r in enumerate(p.results[:15], 1):
    print(f"--- {i} ---")
    print("TITLE:", r["title"])
    print("URL:", r["url"])
    print("SNIP:", r["snippet"][:300])
    print()
