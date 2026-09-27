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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_MD = os.path.join(ROOT, "sources", "sources.md")
OUT_DIR = os.path.join(ROOT, "state", "harvest")
TPE = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SLOT_LOOKBACK_DAYS = 7          # Slot 候選往回看幾天（餵庫存用）
OTHER_LOOKBACK_DAYS = 3         # 其他分類往回看幾天（庫存保鮮期 3 天）

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
                rows.append({"cat": cur, "name": c[0], "url": c[1], "way": c[2], "freq": c[3], "endpoint": c[4]})
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--no-firecrawl", action="store_true")
    ap.add_argument("--anchor", help="窗的結束時刻 HH:MM（重跑舊日期時固定用 02:30）")
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
        if s["way"] in ("WP-API", "RSS") and s["endpoint"] and s["endpoint"] not in seen_ep:
            seen_ep.add(s["endpoint"])
            feeds.append(s)

    health, items = [], []

    def job(s):
        fn = fetch_wp if s["way"] == "WP-API" else fetch_rss
        try:
            res, err = fn(s, since)
        except Exception as e:  # 單一來源出錯不影響其他來源
            res, err = None, f"{type(e).__name__}: {e}"[:120]
        return s, res, err

    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(job, feeds))
    bwb, bwb_err = fetch_bigwinboard()
    results.append(({"name": "BigWinBoard 新作列表", "way": "HTML", "cat": "產品分析／評測"}, bwb, bwb_err))

    for s, res, err in results:
        if res is None:
            health.append({"source": s["name"], "way": s["way"], "status": "失敗", "error": err, "total": 0, "in_window": 0})
            continue
        n_in = 0
        for it in res:
            if it["dt"] > w1 + timedelta(minutes=1) and not it.get("date_only"):
                continue  # 窗後才發布的，不收（明天再算）
            if s["name"] in GENERAL_MEDIA and not GAMING_KW.search(f"{it['title']} {it['excerpt']}"):
                continue
            if NOISE.search(it["title"]):
                continue
            cat = "cat1" if s["name"].startswith("BigWinBoard") else guess_cat(it["title"], it["excerpt"])
            if it.get("date_only"):
                inw = w0.date() <= it["dt"].date() <= w1.date()
            else:
                inw = w0 <= it["dt"] < w1
            age_days = (w1 - it["dt"]).total_seconds() / 86400
            if not inw and not (cat == "cat1" and age_days <= SLOT_LOOKBACK_DAYS) \
                    and not (age_days <= OTHER_LOOKBACK_DAYS):
                continue
            n_in += inw
            items.append({"source": s["name"], "title": it["title"], "url": it["url"],
                          "published": it["dt"].strftime("%Y-%m-%d %H:%M") if not it.get("date_only") else it["dt"].strftime("%Y-%m-%d"),
                          "date_only": bool(it.get("date_only")), "tbc": bool(it.get("tbc")),
                          "in_window": inw, "guess": cat, "excerpt": it["excerpt"]})
        health.append({"source": s["name"], "way": s["way"], "status": "OK", "total": len(res), "in_window": n_in})

    # 同一網址去重（Focus 的多個地區版共用同一個 feed 等）
    uniq = {}
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        uniq.setdefault(it["url"] if "bigwinboard.com/new-slots" not in it["url"] else it["title"], it)
    items = list(uniq.values())

    # ---------- 第二層：Firecrawl ----------
    lists = []
    if not a.no_firecrawl:
        key = os.environ.get("FIRECRAWL_API_KEY", "").strip().strip('"').strip("'")
        targets = [s for s in srcs if s["way"] == "Firecrawl" and s["freq"] == "每日"]
        rot = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "rotate_sources.py"), "--date", date],
                             capture_output=True, text=True).stdout
        for line in rot.splitlines():
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 3:
                    targets.append({"name": parts[0], "url": parts[2], "endpoint": "", "freq": "輪掃"})
        ldir = os.path.join(OUT_DIR, f"{date}-lists")
        os.makedirs(ldir, exist_ok=True)
        for s in targets:
            if not key:
                lists.append({"source": s["name"], "status": "略過（沒有 FIRECRAWL_API_KEY）"})
                continue
            url = s.get("endpoint") or s["url"]
            md, err = firecrawl(url, key)
            fn = re.sub(r"[^\w\-]+", "_", s["name"])[:50] + ".md"
            if md:
                with open(os.path.join(ldir, fn), "w", encoding="utf-8") as f:
                    f.write(f"<!-- {s['name']} | {url} | 抓取 {now:%Y-%m-%d %H:%M} -->\n{md}")
                lists.append({"source": s["name"], "freq": s["freq"], "status": "OK", "file": f"state/harvest/{date}-lists/{fn}", "chars": len(md)})
            else:
                lists.append({"source": s["name"], "freq": s["freq"], "status": "失敗", "error": err})
            time.sleep(3.5)  # Firecrawl 免費方案每分鐘 20 次

        # 📋 週六檢查點：從 EEGaming Slot 分類頁找最新一篇 Weekend Reels，整篇抓回來
        if d.weekday() == 5 and key:
            wr_url = None
            for x in lists:
                if x.get("file") and "EEGaming" in x["source"]:
                    md_txt = open(os.path.join(ROOT, x["file"]), encoding="utf-8").read()
                    m = re.search(r"https://eegaming\.org/latest-news/\d{4}/\d\d/\d\d/\d+/weekend-reels[^)\s\"]*", md_txt)
                    wr_url = m.group(0) if m else None
            if wr_url:
                md, err = firecrawl(wr_url, key)
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
    meta = {"date": date, "window": [w0.strftime("%Y-%m-%d %H:%M"), w1.strftime("%Y-%m-%d %H:%M")],
            "generated": now.strftime("%Y-%m-%d %H:%M"), "feeds": len(feeds)}
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
         "- ⚠️ 預判分類只是關鍵字猜的，最後歸類以 SKILL.md 為準；發布時間是台北時間，BigWinBoard 是遊戲上線日（只到日）",
         ""]
    for cat in ["cat1", "cat2", "cat3", "cat4", "cat5"]:
        inw = [i for i in items if i["guess"] == cat and i["in_window"]]
        old = [i for i in items if i["guess"] == cat and not i["in_window"]]
        L.append(f"## {names[cat]}　窗內 {len(inw)}／窗外近期 {len(old)}")
        L.append("")
        per_src, skipped = {}, 0
        for i in inw:
            per_src[i["source"]] = per_src.get(i["source"], 0) + 1
            if per_src[i["source"]] > 10:  # 單一來源洗版（例：巴西禁令當天 BNLData 發了 30 篇）只列前 10
                skipped += 1
                continue
            L.append(f"- ✅ {i['published']} | {i['source']} | {i['title']} | {i['url']}")
        if skipped:
            L.append(f"- （另有 {skipped} 則同來源重複議題未列出，完整清單見 {date}.json）")
        if old:
            L.append("")
            L.append("  窗外近期（庫存候選，勿當當日新聞）：")
            for i in old[:25]:
                L.append(f"  - {i['published']} | {i['source']} | {i['title']} | {i['url']}")
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
    for h in sorted(health, key=lambda x: (x["status"] == "OK", -x["in_window"])):
        L.append(f"- {h['source']}（{h['way']}）：{h['status']}，窗內 {h['in_window']}／回傳 {h['total']}"
                 + (f"　⚠️ {h['error']}" if h.get("error") else ""))
    if lists:
        L += ["", "## 🔥 第二層 Firecrawl 列表頁（請逐一讀檔解析窗內條目）", ""]
        for x in lists:
            L.append(f"- {x['source']}（{x.get('freq','')}）：{x['status']}" + (f" → `{x['file']}`" if x.get("file") else f"　{x.get('error','')}"))
    with open(os.path.join(OUT_DIR, f"{date}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"✓ harvest {date}：窗 {meta['window'][0]}～{meta['window'][1]}，"
          f"來源 {len(feeds)}（失敗 {sum(h['status']!='OK' for h in health)}），"
          f"窗內候選 {sum(i['in_window'] for i in items)}，總候選 {len(items)}，"
          f"Firecrawl 列表 {sum(x['status']=='OK' for x in lists)}/{len(lists)}")
    print(f"  → state/harvest/{date}.md")


if __name__ == "__main__":
    main()
