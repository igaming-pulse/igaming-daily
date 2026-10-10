#!/usr/bin/env python3
"""
v6.4 第一層＋第二層收集：在 Claude 開跑前，先把「當天有哪些新聞」整理成候選清單。

第一層（免費）：sources.md 裡「抓取方式＝WP-API／RSS」的來源，全部用 curl 抓，
               拿到每篇文章的**精確發布時間**。不花 Firecrawl、不花 Claude 額度。
               另外直接解析 BigWinBoard 新作列表（依上線日排序）。
第二層（Firecrawl）：「抓取方式＝Firecrawl、頻率＝每日」的固定高價值站，加上
               rotate_sources.py 當天的輪掃批次，抓 markdown 存檔給 Claude 讀。

為什麼要有這支（2026-09-27 定案）：
  v6.x 靠 Claude 自己開列表頁、自己解析，連續多天發生「站有掃、條目沒解析出來」
  （iGB、Yogonet、Focus 反覆掛零），又得逐則回頭查發布時間。改成程式先把
  「標題＋網址＋精確時間」備好，Claude 只做判斷、排序、查證與寫稿。

輸出：
  state/harvest/<DATE>.json       全部候選（含窗內／窗外旗標、預判分類、來源健檢）
  state/harvest/<DATE>.md         給 Claude 讀的精簡版：依預判分類分組，只列窗內＋近 7 天 Slot
  state/harvest/<DATE>-lists/     第二層 Firecrawl 抓回的列表頁 markdown

用法：
  python3 scripts/harvest.py                         # 今天，窗＝現在往前推 24h
  python3 scripts/harvest.py --date 2026-09-26       # 指定日報日期，窗＝D-1 02:30～D 02:30
  python3 scripts/harvest.py --no-firecrawl          # 只跑第一層
"""
import argparse
import concurrent.futures as cf
import html
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import unquote as urllib_unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_MD = os.path.join(ROOT, "sources", "sources.md")
OUT_DIR = os.path.join(ROOT, "state", "harvest")
TPE = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SLOT_LOOKBACK_DAYS = 7          # Slot 候選往回看幾天（餵庫存用）
OTHER_LOOKBACK_DAYS = 3         # 其他分類往回看幾天（庫存保鮮期 3 天）
TRIGGERS = os.path.join(ROOT, "state", "triggers.json")
EVENT_MAX_PER_DAY = 3           # 事件觸發每天最多抓幾個（每個關鍵字每週最多一次）
EXPO_LEAD_DAYS = 14             # 展會：開展前 14 天到閉展日每天抓
EXPO_MAX_PER_DAY = 2
WEEKLY_FIXED = 3                # 每週一固定輪幾個「每週／事件」來源

# v6.5 Firecrawl 用量分級（2026-09-28 使用者定案）：開跑前查剩餘點數，
# 今日預算 ＝（剩餘 − 保留 20）÷ 距離重置天數，依預算決定今天的抓取強度
CREDIT_RESERVE = 20
CREDIT_FLOOR = 100              # 剩餘低於這個數字，不管預算多少一律保命
TIERS = [  # (名稱, 預算下限, 輪掃, 事件觸發, 展會, 週一固定, 文章上限, 說明)
    ("🟢 充裕", 30, 3, 3, 2, 3, 22, "全開"),
    ("🟡 標準", 20, 2, 2, 1, 2, 16, "輪掃 2、觸發減量"),
    ("🟠 節約", 15, 0, 1, 1, 0, 10, "停輪掃；文章只給 Slot／非 Slot，其他分類用 WebSearch"),
    ("🔴 保命", -10 ** 9, 0, 0, 0, 0, 0, "只抓 iGamingToday；文章 0，配圖改用 WebFetch 免費抓"),
]

# 綜合型媒體（菲律賓在地）整站新聞很多，只留跟博弈有關的
GENERAL_MEDIA = {"GMA News", "Rappler", "SunStar", "BusinessWorld"}
GAMING_KW = re.compile(
    r"casino|gaming|gambl|betting|\bbet\b|pagcor|e-?games|e-?sabong|online sabong|digiplus|bingoplus|"
    r"arenaplus|gamezone|okbet|ok bet|casino ?plus|playtime|bet88|pt gaming|peryagame|bloomberry|solaire|"
    r"okada|city of dreams|resorts world manila|newport world|travellers|\bslot|jackpot|lottery|pcso|stl\b",
    re.I)

# 雜訊：彩券開獎、體育賠率／賽事預測、純體育贊助 —— 日報不收，直接濾掉
NOISE = re.compile(
    r"estrazion|superenalotto|\blotto\b|10elotto|simbolotto|million ?day|vincicasa|win for life|eurojackpot|"
    r"gl(ü|ue)cksspirale|gewinnzahlen|lotterie|powerball|mega millions|euromillions|lottery results|"
    r"pronostico|\bquote\b|quota maggiorata|\bodds\b.*\b(vs|v)\b|prediction:|picks? (for|today)|"
    r"nations league|serie a|premier league|nfl week|mlb|nba|nhl|rassegna stampa|assenze", re.I)

# 預判分類：只是幫 Claude 分組，最後歸類由 Claude 依 SKILL.md 決定
CAT_RULES = [
    ("cat4", re.compile(r"philippin|pagcor|manila|digiplus|bingoplus|arenaplus|gamezone|okbet|casino ?plus|"
                        r"playtime|bet88|pt gaming|peryagame|bloomberry|solaire|okada|e-?sabong|filipino|cebu|pcso", re.I)),
    ("cat1", re.compile(r"\bslots?\b|\breleases?\b|\blaunch(es)?\b [A-Z]|releases?\b.*\b(game|title)|launch(es|ed)?\b.*\b(game|title)|"
                        r"megaways|hold ?(&|and) ?(win|spin)|free spins|max win|rtp\b|reels?\b|cabinet|"
                        r"g2e|new (game|title)s?\b|premiere|debut", re.I)),
    ("cat2", re.compile(r"crash|plinko|mines\b|aviator|live (casino|dealer|game)|game show|roulette|"
                        r"blackjack|baccarat|poker|bingo|keno|scratch|instant win|table game", re.I)),
    ("cat5", re.compile(r"\bggr\b|revenue|report|survey|study|data|market share|forecast|trends?\b|"
                        r"q[1-4]\b|h[12]\b|year[- ]on[- ]year|%|billion|million", re.I)),
]


def sh(url, timeout=20):
    try:
        r = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout), url],
                           capture_output=True, text=True, errors="ignore")
        return r.stdout
    except Exception:
        return ""


def clean(s, n=None):
    s = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if n else s


def parse_dt(s):
    s = (s or "").strip()
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(TPE)


def read_sources():
    rows, cur = [], None
    for line in open(SOURCES_MD, encoding="utf-8"):
        h = re.match(r"^##\s+(.+?)（\d+）", line)
        if h:
            cur = h.group(1).strip()
            continue
        if cur and line.startswith("| ") and "---" not in line:
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 6 and c[0] != "名稱":
                rows.append({"cat": cur, "name": c[0], "url": c[1], "way": c[2], "freq": c[3], "endpoint": c[4],
                             "trigger": c[5].replace("¦", "|") if len(c) >= 8 else "",
                             "dates": c[6] if len(c) >= 8 else ""})
    return rows


def fetch_wp(src, since):
    after = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    url = f"{src['endpoint']}?after={after}&per_page=100&_fields=date_gmt,link,title,excerpt"
    body = sh(url)
    try:
        posts = json.loads(body)
    except Exception:
        return None, f"WP-API 回應不是 JSON（{clean(body, 40)!r}）"
    if not isinstance(posts, list):
        return None, f"WP-API 回應異常（{str(posts)[:60]}）"
    def txt(v):
        return v.get("rendered", "") if isinstance(v, dict) else str(v or "")
    out = []
    for p in posts:
        if not isinstance(p, dict):
            continue
        dt = parse_dt(str(p.get("date_gmt", "")) + "Z")
        if dt and p.get("link"):
            out.append({"title": clean(txt(p.get("title"))), "url": p["link"], "dt": dt,
                        "excerpt": clean(txt(p.get("excerpt")), 220)})
    return out, None


def fetch_rss(src, since):
    body = sh(src["endpoint"])
    items = re.findall(r"<(?:item|entry)[ >](.*?)</(?:item|entry)>", body, re.S)
    if not items:
        return None, "RSS 沒有條目（可能被擋或網址失效）"
    out = []
    for it in items:
        t = re.search(r"<title[^>]*>(.*?)</title>", it, re.S)
        d = re.search(r"<(?:pubDate|published|dc:date|updated)>(.*?)</", it, re.S)
        l = re.search(r"<link>(.*?)</link>|<link[^>]*href=\"([^\"]+)\"", it, re.S)
        ds = re.search(r"<(?:description|summary|content:encoded)[^>]*>(.*?)</", it, re.S)
        dt = parse_dt(d.group(1)) if d else None
        if not dt:
            continue
        out.append({"title": clean(t.group(1) if t else ""), "url": clean((l.group(1) or l.group(2)) if l else ""),
                    "dt": dt, "excerpt": clean(ds.group(1) if ds else "", 220)})
    return out, None


def fetch_bigwinboard():
    """BigWinBoard 新作列表：依「上線日」排序（上線日不是文章發布時間，只精確到日）。"""
    body = sh("https://www.bigwinboard.com/new-slots/", 25)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    lines = [x.strip() for x in html.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n") if x.strip()]
    out = []
    for i, x in enumerate(lines):
        m = re.match(r"^(?:Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|Aug(?:ust)?)\.? \d{1,2},? 20\d\d", x)
        if m and i >= 2:
            try:
                d = datetime.strptime(re.sub(r"\.|,", "", m.group(0)).replace("September", "Sep").replace("October", "Oct")
                                      .replace("November", "Nov").replace("December", "Dec").replace("August", "Aug"),
                                      "%b %d %Y").replace(tzinfo=TPE)
            except Exception:
                continue
            out.append({"title": f"{lines[i-2]} — {lines[i-1]}", "url": "https://www.bigwinboard.com/new-slots/",
                        "dt": d, "excerpt": f"BigWinBoard 上線日 {m.group(0)}{'（TBC 未定）' if 'TBC' in x else ''}",
                        "date_only": True, "tbc": "TBC" in x})
    return (out, None) if out else (None, "BigWinBoard 新作列表解析不到條目")


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _mdy(txt):
    """'September 28, 2026'／'Sep 28 2026'／'28 Sep 2026' → datetime（台北 00:00）。"""
    m = re.search(r"([A-Z][a-z]{2,8})\.? (\d{1,2}),? (20\d\d)", txt) or None
    if m:
        mon, day, yr = m.group(1)[:3].lower(), int(m.group(2)), int(m.group(3))
    else:
        m = re.search(r"(\d{1,2}) ([A-Z][a-z]{2,8})\.? (20\d\d)", txt)
        if not m:
            return None
        day, mon, yr = int(m.group(1)), m.group(2)[:3].lower(), int(m.group(3))
    if mon not in MONTHS:
        return None
    return datetime(yr, MONTHS[mon], day, tzinfo=TPE)


def fetch_slotslaunch(body=None):
    """v6.5 SlotsLaunch 上線日曆（免費 curl）：每款遊戲都有上線日，今天起往後排；上線日只精確到日。
    結構：<h2> September 28, 2026 </h2> 之後一張張 data-name="遊戲名" 的卡片，卡片內有遊戲頁連結與廠商連結。"""
    body = body if body is not None else sh("https://slotslaunch.com/calendar", 25)
    marks = [(m.start(), "date", m.group(1)) for m in re.finditer(r"<h2[^>]*>\s*([A-Z][a-z]+ \d{1,2}, 20\d\d)\s*</h2>", body)]
    marks += [(m.start(), "card", html.unescape(m.group(1))) for m in re.finditer(r'data-name="([^"]+)"', body)]
    marks.sort()
    out, cur, seen, names_seen = [], None, set(), set()
    for k, (pos, kind, val) in enumerate(marks):
        if kind == "date":
            cur = _mdy(val)
            continue
        if not cur or (cur, val) in names_seen:
            continue            # 每張卡片 data-name 會出現兩次，只看第一次
        names_seen.add((cur, val))
        seg = body[pos:pos + 5000]
        g = re.search(r'href="(https://slotslaunch\.com/([a-z0-9-]+)/[a-z0-9-]+)"', seg)
        if not g or g.group(2) in ("tournaments", "games", "providers") or g.group(1) in seen:
            continue
        seen.add(g.group(1))
        gp = re.search(r'href="https://slotslaunch\.com/' + re.escape(g.group(2)) + r'"[^>]*>\s*([^<]+?)\s*<', seg)
        soon = "Coming Soon" in seg
        out.append({"title": f"{val} — {html.unescape(gp.group(1)) if gp else g.group(2)}", "url": g.group(1), "dt": cur,
                    "date_only": True,
                    "excerpt": f"SlotsLaunch 上線日 {cur:%Y-%m-%d}{'（Coming Soon，尚未開放試玩）' if soon else ''}"})
    return (out, None) if out else (None, "SlotsLaunch 上線日曆解析不到條目")


def parse_igamingtoday(md):
    """v6.5 iGamingToday 首頁（Firecrawl markdown）：「## [標題](網址)」後面幾行是「September 27, 2026」。"""
    out, seen = [], set()
    lines = md.splitlines()
    for i, x in enumerate(lines):
        m = re.match(r"\s*##\s*\[([^\]]+)\]\((https://www\.igamingtoday\.com/[^\s)\"]+)", x)
        if not m or m.group(2) in seen:
            continue
        dt = None
        for y in lines[i + 1:i + 12]:
            if y.strip():
                dt = _mdy(y.strip()) if re.fullmatch(r"\s*[A-Z][a-z]+ \d{1,2}, 20\d\d\s*", y) else None
                if dt:
                    break
        if dt:
            seen.add(m.group(2))
            out.append({"title": clean(m.group(1)), "url": m.group(2), "dt": dt, "date_only": True,
                        "excerpt": "iGamingToday（次要來源，不可當唯一來源）"})
    return out


def fetch_sitemap(src, since):
    """v6.5.2 官網 sitemap（2026-10-11，Play'n GO 改用 Wix、RSS 消失後新增）。
    /games/<slug> 的 lastmod ＝ 遊戲上線日（Play'n GO 實測，排到隔年）→ 當 Slot 上線日曆；
    /post/<slug>、/news/<slug> 的 lastmod ＝ 文章日期。只精確到日；標題由網址 slug 還原。"""
    body = sh(src["endpoint"], 25)
    rows = re.findall(r"<url>(.*?)</url>", body, re.S)
    if not rows:
        return None, "sitemap 解析不到 <url>（可能被擋或網址失效）"
    out = []
    for u in rows:
        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", u)
        mod = re.search(r"<lastmod>\s*(\d{4}-\d{2}-\d{2})", u)
        if not loc or not mod or mod.group(1).startswith("9999"):
            continue
        url = html.unescape(loc.group(1))
        kind = "game" if "/games/" in url else "post" if re.search(r"/(post|news|blog)/", url) else None
        if not kind:
            continue
        dt = datetime.fromisoformat(mod.group(1)).replace(tzinfo=TPE)
        if dt < since - timedelta(days=1):
            continue
        slug = urllib_unquote(url.rstrip("/").rsplit("/", 1)[-1])
        title = " ".join(w if w.isupper() else w[:1].upper() + w[1:] for w in slug.replace("-", " ").split())
        out.append({"title": f"{title} — {src['name']}" if kind == "game" else title, "url": url, "dt": dt,
                    "date_only": True, "force_cat": "cat1" if kind == "game" else None,
                    "excerpt": f"{src['name']} 官網上線日 {dt:%Y-%m-%d}" if kind == "game" else f"{src['name']} 官網文章（{dt:%Y-%m-%d}）"})
    return out, None


def guess_cat(title, excerpt):
    text = f"{title} {excerpt}"
    for cat, rx in CAT_RULES:
        if rx.search(title):
            return cat
    for cat, rx in CAT_RULES:
        if rx.search(text):
            return cat
    return "cat3"


def firecrawl(url, key):
    body = json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": False, "maxAge": 3600000})
    for attempt in range(3):
        r = subprocess.run(["curl", "-s", "-X", "POST", "https://api.firecrawl.dev/v1/scrape",
                            "-H", f"Authorization: Bearer {key}", "-H", "Content-Type: application/json",
                            "--max-time", "90", "-d", body], capture_output=True, text=True, errors="ignore")
        try:
            j = json.loads(r.stdout)
        except Exception:
            j = {}
        if j.get("success"):
            return j["data"].get("markdown", ""), None
        err = str(j.get("error", "無回應"))
        if "Rate limit" in err:
            time.sleep(15)
            continue
        return None, err[:120]
    return None, "Rate limit 重試 3 次仍失敗"


def credits_now(key):
    """Firecrawl 剩餘點數（v2 API）。失敗回 None。"""
    if not key:
        return None
    r = subprocess.run(["curl", "-s", "--max-time", "20", "-H", f"Authorization: Bearer {key}",
                        "https://api.firecrawl.dev/v2/team/credit-usage"], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)["data"]
        return {"remaining": int(d["remainingCredits"]), "plan": d.get("planCredits"),
                "period_end": (d.get("billingPeriodEnd") or "")[:10]}
    except Exception:
        return None


def pick_tier(cr, today):
    """回傳 (tier tuple, 說明 dict)。查不到額度就用「標準」。"""
    if not cr:
        t = TIERS[1]
        return t, {"tier": t[0], "budget": None, "note": "查不到剩餘點數，預設標準"}
    end = datetime.fromisoformat(cr["period_end"]).date() if cr["period_end"] else today + timedelta(days=30)
    days = max((end - today).days, 1)
    budget = (cr["remaining"] - CREDIT_RESERVE) // days
    t = TIERS[3] if cr["remaining"] < CREDIT_FLOOR else next(x for x in TIERS if budget >= x[1])
    return t, {"tier": t[0], "budget": int(budget), "remaining": cr["remaining"], "period_end": cr["period_end"],
               "days_to_reset": days, "reserve": CREDIT_RESERVE, "note": t[7]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--no-firecrawl", action="store_true")
    ap.add_argument("--anchor", help="窗的結束時刻 HH:MM（重跑舊日期時固定用 02:30）")
    ap.add_argument("--plan", action="store_true", help="只列出第二層今天會抓哪些目標，不呼叫 Firecrawl、不寫觸發紀錄")
    a = ap.parse_args()

    now = datetime.now(TPE)
    if a.date and (a.date != now.strftime("%Y-%m-%d") or a.anchor):
        d = datetime.fromisoformat(a.date).replace(tzinfo=TPE)
        hh, mm = (a.anchor or "02:30").split(":")
        w1 = d.replace(hour=int(hh), minute=int(mm))
    else:
        d = now
        w1 = now
    date = d.strftime("%Y-%m-%d")
    w0 = w1 - timedelta(hours=24)
    since = w1 - timedelta(days=SLOT_LOOKBACK_DAYS)

    srcs = read_sources()
    feeds, seen_ep = [], set()
    for s in srcs:
        if s["way"] in ("WP-API", "RSS", "Sitemap") and s["endpoint"] and s["endpoint"] not in seen_ep:
            seen_ep.add(s["endpoint"])
            feeds.append(s)

    health, items = [], []

    def job(s):
        fn = {"WP-API": fetch_wp, "Sitemap": fetch_sitemap}.get(s["way"], fetch_rss)
        try:
            res, err = fn(s, since)
        except Exception as e:  # 單一來源出錯不影響其他來源
            res, err = None, f"{type(e).__name__}: {e}"[:120]
        return s, res, err

    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(job, feeds))
    bwb, bwb_err = fetch_bigwinboard()
    results.append(({"name": "BigWinBoard 新作列表", "way": "程式解析", "cat": "產品分析／評測"}, bwb, bwb_err))
    try:
        sl, sl_err = fetch_slotslaunch()
    except Exception as e:  # noqa: BLE001
        sl, sl_err = None, f"{type(e).__name__}: {e}"[:120]
    results.append(({"name": "SlotsLaunch 上線日曆", "way": "程式解析", "cat": "產品分析／評測"}, sl, sl_err))

    def ingest(s, res, err):
        if res is None:
            health.append({"source": s["name"], "way": s["way"], "status": "失敗", "error": err, "total": 0, "in_window": 0})
            return
        n_in = 0
        for it in res:
            if it["dt"] > w1 + timedelta(minutes=1) and not it.get("date_only"):
                continue  # 窗後才發布的，不收（明天再算）
            if s["name"] in GENERAL_MEDIA and not GAMING_KW.search(f"{it['title']} {it['excerpt']}"):
                continue
            if NOISE.search(it["title"]):
                continue
            cat = it.get("force_cat") or ("cat1" if s["name"].startswith(("BigWinBoard", "SlotsLaunch"))
                                          else guess_cat(it["title"], it["excerpt"]))
            if it.get("date_only"):
                inw = w0.date() <= it["dt"].date() <= w1.date()
            else:
                inw = w0 <= it["dt"] < w1
            age_days = (w1 - it["dt"]).total_seconds() / 86400
            if age_days < -SLOT_LOOKBACK_DAYS:
                continue  # 上線日在 7 天以後的預告：日報不收（SKILL.md），也不列
            if not inw and not (cat == "cat1" and age_days <= SLOT_LOOKBACK_DAYS) \
                    and not (age_days <= OTHER_LOOKBACK_DAYS):
                continue
            n_in += inw
            items.append({"source": s["name"], "title": it["title"], "url": it["url"],
                          "published": it["dt"].strftime("%Y-%m-%d %H:%M") if not it.get("date_only") else it["dt"].strftime("%Y-%m-%d"),
                          "date_only": bool(it.get("date_only")), "tbc": bool(it.get("tbc")),
                          "in_window": inw, "guess": cat, "excerpt": it["excerpt"]})
        health.append({"source": s["name"], "way": s["way"], "status": "OK", "total": len(res), "in_window": n_in})

    for s, res, err in results:
        ingest(s, res, err)

    # 同一網址去重（Focus 的多個地區版共用同一個 feed 等）
    def dedupe(xs):
        uniq = {}
        for it in sorted(xs, key=lambda x: x["published"], reverse=True):
            uniq.setdefault(it["url"] if "bigwinboard.com/new-slots" not in it["url"] else it["title"], it)
        return list(uniq.values())
    items = dedupe(items)

    # ---------- 第二層：Firecrawl ----------
    lists = []
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip().strip('"').strip("'")
    cr0 = None if (a.no_firecrawl or a.plan) and not key else credits_now(key)
    tier, tinfo = pick_tier(cr0, d.date())
    _, _, n_rot, n_event, n_expo, n_weekly, art_cap, _ = tier
    spent_lists = 0
    if not a.no_firecrawl:
        targets = [s for s in srcs if s["way"] == "Firecrawl" and s["freq"] == "每日"]
        rot = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "rotate_sources.py"), "--date", date,
                              "--size", str(max(n_rot, 1))], capture_output=True, text=True).stdout if n_rot else ""
        for line in rot.splitlines():
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 3:
                    targets.append({"name": parts[0], "url": parts[2], "endpoint": "", "freq": "輪掃"})
        # ---------- v6.4.2 三種觸發：讓「每週／事件」「行事曆」來源有明確切入點 ----------
        week = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        try:
            trig_log = json.load(open(TRIGGERS, encoding="utf-8"))
        except Exception:
            trig_log = {}
        done_this_week = set(trig_log.get(week, []))
        extra = []
        # ① 事件觸發：當天窗內新聞提到觸發關鍵字 → 抓該機構官方頁（每個關鍵字每週最多一次）
        # 只比對標題（內文順帶提到不算）；菲律賓、亞洲機構優先，其次依來源表順序
        texts = [i["title"] for i in items if i["in_window"]]
        fired = []
        prio = lambda x: (0 if "PAGCOR" in x["name"] else 1 if any(k in x["name"] for k in ("DICJ", "Korea")) else 2)
        for s_ in sorted(srcs, key=prio):
            kw = s_.get("trigger")
            if not kw or s_["name"] in done_this_week or len(fired) >= min(EVENT_MAX_PER_DAY, n_event):
                continue
            rx = re.compile(kw, re.I)
            hit = next((t for t in texts if rx.search(t)), None)
            if hit:
                fired.append(s_["name"])
                extra.append({**s_, "freq": f"事件觸發（命中：{hit[:60]}）"})
        # ② 行事曆觸發：展會開展前 14 天到閉展日
        expo = []
        for s_ in srcs:
            for rng in re.split(r"[;；]", s_.get("dates") or ""):
                m = re.match(r"\s*(\d{4}-\d\d-\d\d)\s*[~～]\s*(\d{4}-\d\d-\d\d)", rng)
                if not m:
                    continue
                st, en = datetime.fromisoformat(m.group(1)).date(), datetime.fromisoformat(m.group(2)).date()
                if st - timedelta(days=EXPO_LEAD_DAYS) <= d.date() <= en:
                    expo.append((st, {**s_, "freq": f"行事曆觸發（展期 {st}～{en}）"}))
        expo.sort(key=lambda x: x[0])
        extra += [x[1] for x in expo[:min(EXPO_MAX_PER_DAY, n_expo)]]
        # ③ 固定週期：每週一從「每週／事件」來源輪 WEEKLY_FIXED 個（依 ISO 週數決定，無需狀態）
        if d.weekday() == 0 and n_weekly:
            pool = [s_ for s_ in srcs if s_["freq"] == "每週／事件" and s_["cat"] in ("監理機關／官方數據", "產業協會／技術認證機構")]
            if pool:
                k = d.isocalendar()[1] * WEEKLY_FIXED
                extra += [{**pool[(k + i) % len(pool)], "freq": "每週一固定週期"} for i in range(min(WEEKLY_FIXED, n_weekly, len(pool)))]
        targets += extra
        if a.plan:
            print(f"# Firecrawl 分級：{tinfo['tier']}｜今日預算 {tinfo['budget']}｜{tinfo['note']}")
            print(f"# 第二層計畫 {date}（{week}，週{'一二三四五六日'[d.weekday()]}）：共 {len(targets)} 個")
            for t in targets:
                print(f"  - {t['name']}｜{t['freq']}")
            return
        if fired:
            trig_log[week] = sorted(done_this_week | set(fired))
            trig_log = {k: v for k, v in trig_log.items() if k >= f"{(d - timedelta(days=60)).isocalendar()[0]}-W"}
            with open(TRIGGERS, "w", encoding="utf-8") as f:
                json.dump(trig_log, f, ensure_ascii=False, indent=1)

        ldir = os.path.join(OUT_DIR, f"{date}-lists")
        os.makedirs(ldir, exist_ok=True)
        for s in targets:
            if not key:
                lists.append({"source": s["name"], "status": "略過（沒有 FIRECRAWL_API_KEY）"})
                continue
            url = s.get("endpoint") or s["url"]
            md, err = firecrawl(url, key)
            spent_lists += 1
            fn = re.sub(r"[^\w\-]+", "_", s["name"])[:50] + ".md"
            if md and s["name"] == "iGamingToday":
                # v6.5：程式直接解析成候選，Claude 不用翻 1,500 行原文
                parsed = parse_igamingtoday(md)
                ingest({"name": "iGamingToday", "way": "Firecrawl＋程式解析"}, parsed or None,
                       None if parsed else "iGamingToday 列表頁解析不到條目")
            if md:
                with open(os.path.join(ldir, fn), "w", encoding="utf-8") as f:
                    f.write(f"<!-- {s['name']} | {url} | 抓取 {now:%Y-%m-%d %H:%M} -->\n{md}")
                lists.append({"source": s["name"], "freq": s["freq"], "status": "OK", "file": f"state/harvest/{date}-lists/{fn}", "chars": len(md)})
            else:
                lists.append({"source": s["name"], "freq": s["freq"], "status": "失敗", "error": err})
            time.sleep(3.5)  # Firecrawl 免費方案每分鐘 20 次

        # 📋 週六檢查點：從 EEGaming Slot 分類頁找最新一篇 Weekend Reels，整篇抓回來
        if d.weekday() == 5 and key and tier[0] != TIERS[3][0]:
            wr_url = next((i["url"] for i in items if "weekend reels" in i["title"].lower()
                           and "eegaming.org" in i["url"]), None)
            for x in ([] if wr_url else lists):
                if x.get("file") and "EEGaming" in x["source"]:
                    md_txt = open(os.path.join(ROOT, x["file"]), encoding="utf-8").read()
                    m = re.search(r"https://eegaming\.org/latest-news/\d{4}/\d\d/\d\d/\d+/weekend-reels[^)\s\"]*", md_txt)
                    wr_url = m.group(0) if m else None
            if wr_url:
                md, err = firecrawl(wr_url, key)
                spent_lists += 1
                if md:
                    with open(os.path.join(ldir, "WEEKEND_REELS.md"), "w", encoding="utf-8") as f:
                        f.write(f"<!-- Weekend Reels | {wr_url} | 抓取 {now:%Y-%m-%d %H:%M} -->\n{md}")
                    lists.append({"source": "📋 Weekend Reels（週六檢查點）", "freq": "每週六", "status": "OK",
                                  "file": f"state/harvest/{date}-lists/WEEKEND_REELS.md", "chars": len(md)})
                else:
                    lists.append({"source": "📋 Weekend Reels（週六檢查點）", "freq": "每週六", "status": "失敗", "error": err})
            else:
                lists.append({"source": "📋 Weekend Reels（週六檢查點）", "freq": "每週六", "status": "失敗",
                              "error": "EEGaming 分類頁裡找不到 weekend-reels 連結，請用 WebSearch 找本週那篇"})

    os.makedirs(OUT_DIR, exist_ok=True)
    items = dedupe(items)
    budget = tinfo["budget"]
    art_limit = art_cap if budget is None else max(0, min(art_cap, budget - spent_lists))
    tinfo.update({"lists_spent": spent_lists, "article_limit": art_limit})
    meta = {"date": date, "window": [w0.strftime("%Y-%m-%d %H:%M"), w1.strftime("%Y-%m-%d %H:%M")],
            "generated": now.strftime("%Y-%m-%d %H:%M"), "feeds": len(feeds), "firecrawl": tinfo}
    # 開跑時的剩餘點數記下來，health_alert.py 收尾再記一次 → 得到今天的實際用量
    if cr0 and not a.plan:
        cp = os.path.join(ROOT, "state", "health", "credits.json")
        try:
            hist = json.load(open(cp, encoding="utf-8"))
        except Exception:
            hist = {}
        rec = hist.get(date) if isinstance(hist.get(date), dict) else {}
        rec.setdefault("start", cr0["remaining"])
        hist[date] = rec
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(hist.items())[-40:]), f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, f"{date}.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "health": health, "lists": lists, "items": items}, f, ensure_ascii=False, indent=1)

    # ---------- 給 Claude 讀的精簡版 ----------
    names = {"cat1": "🎰 預判 Slot／新遊戲（含實體機）", "cat2": "🕹️ 預判 非 Slot", "cat3": "🤝 預判 主流動態",
             "cat4": "🇵🇭 預判 菲律賓", "cat5": "📊 預判 市場數據"}
    L = [f"# 候選清單 {date}", "",
         f"- 收集時間窗：{meta['window'][0]} ～ {meta['window'][1]}（台北）",
         f"- 第一層：{len(feeds)} 個 WP-API／RSS 來源＋BigWinBoard 新作列表；"
         f"成功 {sum(h['status']=='OK' for h in health)}、失敗 {sum(h['status']!='OK' for h in health)}",
         f"- 窗內候選 {sum(i['in_window'] for i in items)} 則；另列近 {SLOT_LOOKBACK_DAYS} 天 Slot 與近 {OTHER_LOOKBACK_DAYS} 天其他新聞供庫存參考",
         "- ⚠️ 預判分類只是關鍵字猜的，最後歸類以 SKILL.md 為準；發布時間是台北時間，BigWinBoard／SlotsLaunch 是遊戲上線日（只到日）",
         f"- 窗外近期候選（庫存參考）另存 `state/harvest/{date}-backlog.md`，需要補位時再讀",
         "",
         f"## 💳 Firecrawl 今日分級：{tinfo['tier']}",
         "",
         (f"- 剩餘 {tinfo['remaining']} 點，{tinfo['period_end']} 重置（{tinfo['days_to_reset']} 天）；"
          f"今日預算 ＝（{tinfo['remaining']} − 保留 {CREDIT_RESERVE}）÷ {tinfo['days_to_reset']} ＝ **{tinfo['budget']} 點**"
          if tinfo.get("remaining") is not None else f"- {tinfo['note']}"),
         f"- 程式已用 {spent_lists} 點抓列表頁 → **Claude 今天 Firecrawl 抓文章最多 {art_limit} 次**（硬上限，用完改 WebSearch／WebFetch）",
         f"- 本級規則：{tinfo['note']}",
         ""]
    B = [f"# 窗外近期候選 {date}（庫存參考，勿當當日新聞）", "",
         f"- Slot 近 {SLOT_LOOKBACK_DAYS} 天（含 7 天內將上線的預告）、其他近 {OTHER_LOOKBACK_DAYS} 天", ""]
    for cat in ["cat1", "cat2", "cat3", "cat4", "cat5"]:
        inw = [i for i in items if i["guess"] == cat and i["in_window"]]
        old = [i for i in items if i["guess"] == cat and not i["in_window"]]
        L.append(f"## {names[cat]}　窗內 {len(inw)}／窗外近期 {len(old)}")
        L.append("")
        per_src, skipped = {}, 0
        # 單一來源洗版只列前幾則：主流／數據區多是各國在地法規新聞（規則裡最低優先），每站 4 則；其他區 10 則
        cap = 4 if cat in ("cat3", "cat5") else 10
        cal = [i for i in inw if i["source"].startswith("SlotsLaunch")]
        for i in inw:
            if i in cal:
                continue
            per_src[i["source"]] = per_src.get(i["source"], 0) + 1
            if per_src[i["source"]] > cap and not i["source"].startswith(("BigWinBoard", "iGamingToday")):
                skipped += 1
                continue
            L.append(f"- ✅ {i['published']} | {i['source']} | {i['title']} | {i['url']}")
        if skipped:
            L.append(f"- （另有 {skipped} 則同來源議題未列出，完整清單見 {date}.json）")
        if cal:
            # SlotsLaunch 是上線日曆（資料庫，不是新聞稿）：精簡成一行一款，網址規則 slotslaunch.com/<廠商>/<遊戲>，完整見 json
            L.append("")
            L.append(f"  🗓️ SlotsLaunch 上線日曆（窗內 {len(cal)} 款；只能當線索，主來源要另找新聞稿／GP 官網／BigWinBoard）：")
            for dday in sorted({i["published"] for i in cal}):
                row = [i["title"].replace(" — ", "／") + ("⏳" if "Coming Soon" in i["excerpt"] else "")
                       for i in cal if i["published"] == dday]
                L.append(f"  - {dday}：" + "；".join(row))
        if old:
            L.append(f"- （窗外近期 {len(old)} 則見 {date}-backlog.md）")
            B.append(f"## {names[cat]}　{len(old)} 則")
            B.append("")
            for i in old[:40]:
                B.append(f"- {i['published']} | {i['source']} | {i['title']} | {i['url']}"
                         + (f" | {i['excerpt']}" if i["source"].startswith(("BigWinBoard", "SlotsLaunch")) else ""))
            B.append("")
        L.append("")
    if d.weekday() == 5:
        wk = sorted([i for i in items if i["source"].startswith("BigWinBoard") and
                     (w1.date() - datetime.strptime(i["published"][:10], "%Y-%m-%d").date()).days <= 6],
                    key=lambda i: i["published"])
        L.append(f"## 📋 週六檢查點：BigWinBoard 本週上線新作 {len(wk)} 款（與 Weekend Reels 一起比對漏收）")
        L.append("")
        for i in wk:
            L.append(f"- {i['published']} | {i['title']}" + ("（TBC）" if i.get("tbc") else ""))
        L.append("")
    L.append("## 📡 來源健檢")
    L.append("")
    bad = [h for h in health if h["status"] != "OK"]
    zero = [h for h in health if h["status"] == "OK" and not h["in_window"]]
    good = sorted((h for h in health if h["status"] == "OK" and h["in_window"]), key=lambda x: -x["in_window"])
    for h in bad:
        L.append(f"- ⚠️ {h['source']}（{h['way']}）：失敗　{h.get('error', '')}")
    for h in good:
        L.append(f"- {h['source']}（{h['way']}）：窗內 {h['in_window']}／回傳 {h['total']}")
    if zero:
        L.append(f"- 窗內 0 則（正常回傳）{len(zero)} 個：" + "、".join(h["source"] for h in zero))
    if lists:
        L += ["", "## 🔥 第二層 Firecrawl 列表頁", "",
              "iGamingToday 已由程式解析併入上方候選，不用讀原檔；其他（輪掃／觸發／Weekend Reels）請讀檔解析窗內條目：", ""]
        for x in lists:
            done = " ✅ 已解析" if x["source"] == "iGamingToday" and x["status"] == "OK" else ""
            L.append(f"- {x['source']}（{x.get('freq','')}）：{x['status']}{done}"
                     + (f" → 📖 請讀檔 `{x['file']}`" if x.get("file") and not done else "" if done else f"　{x.get('error','')}"))
    with open(os.path.join(OUT_DIR, f"{date}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(OUT_DIR, f"{date}-backlog.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(B) + "\n")

    print(f"✓ harvest {date}：窗 {meta['window'][0]}～{meta['window'][1]}，"
          f"來源 {len(feeds)}（失敗 {sum(h['status']!='OK' for h in health)}），"
          f"窗內候選 {sum(i['in_window'] for i in items)}，總候選 {len(items)}，"
          f"Firecrawl 列表 {sum(x['status']=='OK' for x in lists)}/{len(lists)}｜分級 {tinfo['tier']}、"
          f"今日預算 {tinfo['budget']}、文章上限 {art_limit}")
    print(f"  → state/harvest/{date}.md")


if __name__ == "__main__":
    main()
