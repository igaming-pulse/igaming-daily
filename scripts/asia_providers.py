#!/usr/bin/env python3
"""亞洲廠商官網新作（v6.7.3，2026-11-13）

菲律賓 Top200 的主力廠商（JILI、PG Soft、FA CHAI、Yellow Bat、5G、OMNIPLAY（尊博））多半不發英文新聞稿，
歐美媒體很少報，所以直接從官網「新遊戲」資料抓。每家回傳 harvest.py 共用的條目格式：
  {"title": "遊戲名 — 廠商", "url", "dt"(台北 00:00), "date_only": True, "force_cat": "cat1", "excerpt"}

| 廠商 | 抓法 | 日期 |
|---|---|---|
| PG Soft | 官方 API GetGamesBannerList → 遊戲頁 __NUXT__ 的 ct | 建檔日（≈上線日） |
| Yellow Bat | WP-API /wp/v2/games（一定要 www） | 發佈日 |
| 5G Games | 官網 Game Launch 新聞頁 <time datetime> | 上線公告日 |
| JILI | 官網遊戲列表，記下看過的 ID；新 ID 才抓詳情頁 | 只到「月」→ 用首見日 |
| OMNIPLAY（尊博） | 官網遊戲列表 → games-detail 的 Release Date | 上線日 |
| FA CHAI | 官網 news/category/game（擋台灣、美國 IP，只能 Firecrawl，每天 1 點） | 發佈日 |
| JDB | 官網擋地區、Firecrawl 也沒資料 → sources 表的 Google News：JDB Gaming（不在這支） | 新聞日 |

詳情頁的日期存在 state/asia-providers.json，同一款只抓一次。
"""
import html
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "state", "asia-providers.json")
TPE = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
JILI_MAX_AGE_MONTHS = 3      # 新 ID 的官網 Publish Time 超過 3 個月 → 舊作重新上架，不當新作


def get(url, timeout=25):
    try:
        return subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout), url],
                              capture_output=True, text=True, errors="ignore").stdout
    except Exception:  # noqa: BLE001
        return ""


def _txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _day(s):
    """'2026-11-10T17:28:20'／'2026/10/15'／'2026-11-11' → 台北 00:00。"""
    m = re.search(r"(20\d\d)[-/.](\d{1,2})[-/.](\d{1,2})", s or "")
    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=TPE) if m else None


def _item(name, gp, url, dt, how, extra=""):
    return {"title": f"{name} — {gp}", "url": url, "dt": dt, "date_only": True, "force_cat": "cat1",
            "excerpt": f"{gp} {how} {dt:%Y-%m-%d}{extra}"}


def load_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1, sort_keys=True)


# ---------- PG Soft ----------
def parse_pg_list(body):
    games = json.loads(body)["dt"]["gbl"]
    return [(str(g["gid"]), html.unescape(g["gn"]).replace("’", "'")) for g in games if g.get("gid") and g.get("gn")]


def parse_pg_ct(body, gid):
    m = re.search(r"gid:" + re.escape(str(gid)) + r",[^{}]*?ct:\"([^\"]+)\"", body)
    return m.group(1)[:10] if m else None


def fetch_pgsoft(cache, getter=get):
    body = getter("https://api.pgsoft.com/Game/GetGamesBannerList/Language/1/live/true")
    try:
        games = parse_pg_list(body)
    except Exception:  # noqa: BLE001
        return None, "PG Soft 遊戲 API 回應異常"
    c = cache.setdefault("pgsoft", {})
    out = []
    for gid, name in games:
        url = f"https://www.pgsoft.com/en/games/{gid}/"
        if gid not in c:
            c[gid] = parse_pg_ct(getter(url), gid)
        dt = _day(c[gid])
        if dt:
            out.append(_item(name, "PG Soft", url, dt, "官網上線日"))
    return out, None


# ---------- Yellow Bat ----------
def parse_yb(body):
    out = []
    for p in json.loads(body):
        dt = _day(p.get("date"))
        name = _txt((p.get("title") or {}).get("rendered", "")).replace("’", "'")
        if dt and name and p.get("link"):
            out.append(_item(name, "Yellow Bat", p["link"], dt, "官網上線日"))
    return out


def fetch_yellowbat(cache, getter=get):
    body = getter("https://www.yellowbat.com/wp-json/wp/v2/games?per_page=20&orderby=date&order=desc&_fields=date,title,link")
    try:
        return parse_yb(body), None
    except Exception:  # noqa: BLE001
        return None, "Yellow Bat games API 回應不是 JSON"


# ---------- 5G Games ----------
def parse_5g(body):
    out, seen = [], set()
    for blk in re.findall(r"<a\b[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", body, re.S):
        href, inner = blk
        t = re.search(r"<time datetime=\"([\d-]+)\"", inner)
        h = re.search(r"<h3[^>]*>(.*?)</h3>", inner, re.S)
        if not t or not h:
            continue
        head = _txt(h.group(1))
        alt = re.search(r"alt=\"5G GAMES (.+?) official", inner)
        name = _txt(alt.group(1)) if alt else head
        name = re.split(r" Online (?:Casino|Slot)| Slot Game| by 5G| -|:", name, flags=re.I)[0].strip()
        url = href if href.startswith("http") else "https://www.5ggames.com" + href
        if (name, t.group(1)) in seen:
            continue
        seen.add((name, t.group(1)))
        out.append(_item(name, "5G Games", url, _day(t.group(1)), "官網上線日", f"｜{head[:90]}"))
    return out


def fetch_5g(cache, getter=get):
    out = parse_5g(getter("https://www.5ggames.com/en/news/game-launch/"))
    return (out, None) if out else (None, "5G Game Launch 頁解析不到條目")


# ---------- JILI ----------
def parse_jili_list(body):
    return dict(re.findall(r"id=\"game(\d+)\".*?class=\"subtitle\">([^<]+)<", body, re.S))


def parse_jili_month(body):
    m = re.search(r"Publish Time\s*(?:<[^>]+>\s*)*(20\d\d)\.(\d{1,2})", body)
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else None


def fetch_jili(cache, today, getter=get):
    games = parse_jili_list(getter("https://jiligames.com/games"))
    if len(games) < 50:
        return None, f"JILI 遊戲列表只解析到 {len(games)} 款（改版或被擋）"
    c = cache.setdefault("jili", {})
    seen = c.setdefault("seen", {})
    t = today.strftime("%Y-%m-%d")
    if not seen:   # 第一次跑：現有遊戲全部記成基準，不當新作
        c["baseline"] = t
        for gid, name in games.items():
            seen[gid] = {"name": _txt(name), "first": None}
        return [], None
    out = []
    for gid, name in games.items():
        if gid not in seen:
            seen[gid] = {"name": _txt(name), "first": t,
                         "month": parse_jili_month(getter(f"https://jiligames.com/PlusIntro/{gid}?showGame=false"))}
        r = seen[gid]
        if not r.get("first"):
            continue
        mon = r.get("month")
        if mon:
            y, m = map(int, mon.split("-"))
            if (today.year - y) * 12 + today.month - m > JILI_MAX_AGE_MONTHS:
                continue
        out.append({"title": f"{r['name']} — JILI", "url": f"https://jiligames.com/PlusIntro/{gid}",
                    "dt": datetime.fromisoformat(r["first"]).replace(tzinfo=TPE), "date_only": True, "force_cat": "cat1",
                    "excerpt": f"JILI 官網首見 {r['first']}（官網 Publish Time 只到月：{mon or '未標'}）"})
    return out, None


# ---------- OMNIPLAY（尊博） ----------
def parse_op_list(body):
    out = {}
    for gid, name in re.findall(r"games-detail/([\w-]+)\"\s+title=\"([^\"]+)\"", body):
        out.setdefault(gid, _txt(name))
    return out


def parse_op_date(body):
    m = re.search(r"Release Date\s*(?:<[^>]+>\s*)*(20\d\d/\d{1,2}/\d{1,2})", body)
    return m.group(1).replace("/", "-") if m else None


def fetch_omniplay(cache, getter=get):
    games = parse_op_list(getter("https://www.omniplaygaming.com/games"))
    if not games:
        return None, "OMNIPLAY 遊戲列表解析不到條目"
    c = cache.setdefault("omniplay", {})
    out = []
    for gid, name in games.items():
        url = f"https://www.omniplaygaming.com/games-detail/{gid}"
        if not c.get(gid):
            c[gid] = parse_op_date(getter(url))
        dt = _day(c[gid])
        if dt:
            out.append(_item(name.title() if name.isupper() else name, "OMNIPLAY（尊博）", url, dt, "官網上線日"))
    return out, None


# ---------- FA CHAI（Firecrawl markdown） ----------
def parse_fachai(md):
    out = []
    lines = md.splitlines()
    for i, x in enumerate(lines):
        if not re.fullmatch(r"\s*20\d\d/\d\d/\d\d\s*", x):
            continue
        name = url = None
        for y in reversed(lines[max(0, i - 8):i]):
            m = re.search(r"!\[(.+?) slot cover image", y)
            if m:
                name = m.group(1).strip()
                u = re.search(r"\]\((https://fachaigaming\.com/en/news/game/[^)\s]+)\)", y)
                url = u.group(1) if u else None
                break
        if not name:
            continue
        head = next((y.lstrip("# ").strip() for y in lines[i + 1:i + 5] if y.strip()), "")
        if not url:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            url = f"https://fachaigaming.com/en/news/game/{slug}"
        nm = name.title() if name.isupper() else name
        out.append(_item(nm, "FA CHAI", url, _day(x), "官網新作公告", f"｜{head[:90]}"))
    return out


def fetch_fachai(firecrawl):
    """firecrawl：(url) -> (markdown, err)。官網擋台灣、美國 IP，只能走 Firecrawl（每天 1 點）。"""
    md, err = firecrawl("https://fachaigaming.com/en/news/category/game")
    if not md:
        return None, f"FA CHAI 新聞頁 Firecrawl 失敗：{err}"
    items = parse_fachai(md)
    return (items, None) if items else (None, "FA CHAI 新聞頁解析不到條目")


def fetch_all(today, getter=get):
    """免費的 5 家（FA CHAI 另外由 harvest.py 在 Firecrawl 段呼叫 fetch_fachai）。回傳 [(來源名, 條目或 None, 錯誤)]。"""
    import concurrent.futures as cf
    cache = load_cache()
    jobs = {"PG Soft 官網新作": lambda: fetch_pgsoft(cache, getter),
            "Yellow Bat 官網新作": lambda: fetch_yellowbat(cache, getter),
            "5G Games 官網新作": lambda: fetch_5g(cache, getter),
            "JILI 官網新作": lambda: fetch_jili(cache, today, getter),
            "OMNIPLAY（尊博）官網新作": lambda: fetch_omniplay(cache, getter)}

    def run(fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            return None, f"{type(e).__name__}: {e}"[:120]

    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {k: ex.submit(run, fn) for k, fn in jobs.items()}
        res = [(k, *futs[k].result()) for k in jobs]
    save_cache(cache)
    return res


if __name__ == "__main__":
    import sys
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    fc = None
    if key and "--firecrawl" in sys.argv:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from harvest import firecrawl as _fc
        fc = lambda u: _fc(u, key)  # noqa: E731
    rs = fetch_all(datetime.now(TPE))
    if fc:
        rs.append(("FA CHAI 官網新作", *fetch_fachai(fc)))
    for name, items, err in rs:
        print(f"## {name}：{'失敗 ' + err if items is None else f'{len(items)} 款'}")
        for it in sorted(items or [], key=lambda x: x["dt"], reverse=True)[:6]:
            print(f"  {it['dt']:%Y-%m-%d}  {it['title']}  {it['url']}")
    print(f"Firecrawl 用了 {1 if fc else 0} 點")
