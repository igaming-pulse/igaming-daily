#!/usr/bin/env python3
"""
免費抓文章資訊（2026-10-11）：入選新聞查證時先用這支，抓不到才用 Firecrawl。

用 curl 讀網頁原始碼，取出：
  - 發布時間：article:published_time／og:published_time／JSON-LD datePublished／<time datetime>（不取 dateModified）
  - 配圖：og:image（twitter:image 備援）
  - 標題、摘要（og:title、og:description）
  - 內文：<article> 或 <p> 段落的純文字（預設前 3,000 字，給 Claude 寫稿用）
被擋（403／Cloudflare 驗證）、需要 JavaScript（內文太短）時標 "need_firecrawl": true。

用法：
  python3 scripts/page_meta.py <網址> [<網址> …]           # 每個網址一行 JSON
  python3 scripts/page_meta.py --no-text <網址>             # 只要日期、配圖，不要內文
"""
import html
import json
import re
import subprocess
import sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
BLOCK_RX = re.compile(r"Just a moment|cf-browser-verification|Attention Required|Access denied|captcha", re.I)


def fetch(url):
    r = subprocess.run(["curl", "-sL", "--compressed", "-m", "25", "-A", UA, "-H", "Accept-Language: en,zh-TW;q=0.8",
                        "-w", "\n__STATUS__%{http_code}", url], capture_output=True, text=True, errors="ignore")
    body, _, status = r.stdout.rpartition("\n__STATUS__")
    return (int(status) if status.isdigit() else 0), body


def meta(body, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:property|name|itemprop)=["\']%s["\'][^>]*content=["\']([^"\']+)' % re.escape(n), body, re.I) \
            or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name|itemprop)=["\']%s["\']' % re.escape(n), body, re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""


def published(body):
    v = meta(body, "article:published_time", "og:published_time", "datePublished", "pubdate", "publish-date")
    if v:
        return v, "metadata"
    for blob in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', body, re.S | re.I):
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', blob)
        if m:
            return m.group(1), "JSON-LD"
    m = re.search(r'<time[^>]+datetime=["\']([^"\']+)', body, re.I)
    if m:
        return m.group(1), "time 標籤"
    return "", ""


def main_text(body, limit):
    b = re.sub(r"<(script|style|nav|footer|header|aside|form|noscript)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    art = re.search(r"<article[^>]*>(.*?)</article>", b, re.S | re.I)
    scope = art.group(1) if art else b
    paras = [html.unescape(re.sub(r"<[^>]+>", " ", p)) for p in re.findall(r"<p[^>]*>(.*?)</p>", scope, re.S | re.I)]
    paras = [re.sub(r"\s+", " ", p).strip() for p in paras]
    paras = [p for p in paras if len(p) > 40]
    return "\n".join(paras)[:limit]


_FEEDS = {}


def from_feed(url, want_text, limit):
    """網頁要 JavaScript 才看得到的站（EEGaming），改從它的 RSS 取完整內文、配圖、發布時間。"""
    feeds = {"eegaming.org": "https://eegaming.org/feed"}
    host = url.split("/")[2].replace("www.", "")
    if host not in feeds:
        return None
    if host not in _FEEDS:
        _FEEDS[host] = fetch(feeds[host])[1]
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    for it in re.findall(r"<item>(.*?)</item>", _FEEDS[host], re.S):
        link = re.search(r"<link>(.*?)</link>", it, re.S)
        if not link or slug not in link.group(1):
            continue
        g = lambda rx: (re.search(rx, it, re.S) or [None, ""])[1]
        content = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", g(r"<content:encoded>(.*?)</content:encoded>")))
        out = {"url": url, "status": 200, "title": html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", g(r"<title>(.*?)</title>"))).strip(),
               "published": g(r"<pubDate>(.*?)</pubDate>").strip(), "published_from": "RSS pubDate",
               "image": g(r'<media:content[^>]+url="([^"]+)"') or g(r'<enclosure[^>]+url="([^"]+)"'),
               "description": "", "need_firecrawl": False, "via": "RSS"}
        if want_text:
            out["text"] = main_text(content, limit) or re.sub(r"<[^>]+>", " ", content)[:limit]
        return out
    return None


def analyse(url, want_text=True, limit=3000):
    out = _analyse(url, want_text, limit)
    if out.get("need_firecrawl"):
        alt = from_feed(url, want_text, limit)
        if alt:
            return alt
    return out


def _analyse(url, want_text=True, limit=3000):
    status, body = fetch(url)
    out = {"url": url, "status": status}
    if status >= 400 or not body or BLOCK_RX.search(body[:5000]):
        out.update({"need_firecrawl": True, "reason": f"被擋或打不開（HTTP {status}）"})
        return out
    date, src = published(body)
    out.update({
        "title": meta(body, "og:title", "twitter:title") or html.unescape((re.search(r"<title>(.*?)</title>", body, re.S | re.I) or [None, ""])[1]).strip(),
        "published": date, "published_from": src,
        "image": meta(body, "og:image", "og:image:secure_url", "twitter:image"),
        "description": meta(body, "og:description", "description"),
    })
    if want_text:
        text = main_text(body, limit)
        out["text"] = text
        if len(text) < 300:
            out.update({"need_firecrawl": True, "reason": "內文太短（可能要 JavaScript 才看得到）"})
            return out
    out["need_firecrawl"] = False
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    want_text = "--no-text" not in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    for u in args:
        print(json.dumps(analyse(u, want_text), ensure_ascii=False))


if __name__ == "__main__":
    main()
