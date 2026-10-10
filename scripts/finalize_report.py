#!/usr/bin/env python3
"""
v6.5 定稿：Markdown → 檢查 → 固定模板 HTML（2026-09-28 定案，取代「每次現寫 HTML」）。

一支做完四件事，Claude 在步驟 2 只要跑這一行：
  python3 scripts/finalize_report.py --date <DATE>

  1. 解析  state/<DATE>-igaming-report.md → state/<DATE>-report.json（結構化，給檢查與日後分析用）
  2. 資料格式檢查：每則必備欄位、主來源日期是否在窗內／保鮮期內、cat1 參數 8 項、統計列…
  3. 連結與圖片檢查：來源連結 404／網域不存在 → 錯誤；配圖打不開 → 自動拿掉（不留破圖）
  4. 模糊比對去重：跟近 3 天日報、同一份日報內互比（Huff N´Puff＝Huff N' Puff）
  最後用固定模板寫 reports/<DATE>.html，檢查結果寫 state/<DATE>-qa.json。

結束碼：0＝沒有錯誤；1＝有「錯誤」（HTML 仍會寫出，確保一定有日報；Claude 依 SKILL.md 修正 .md 後重跑）。
「警告」不擋發布，會列進 qa.json，由 health_alert.py 視情況放進 Telegram 系統警報。

其他旗標：
  --md / --out     指定來源與輸出（重跑特別版、-v64 等）
  --no-links       跳過連結檢查（離線測試）
  --check-only     只檢查不寫 HTML
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_lib as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
FORBIDDEN = ["僅供內部", "品質備註", "爬找", "本窗偏淡", "週末偏淡", "抓取異常", "本窗無合格"]
FRESH = {"cat1": 7, "cat2": 3, "cat3": 3, "cat4": 3, "cat5": 3}
HOT_IP_DAYS = 30


class QA:
    def __init__(self):
        self.errors, self.warnings, self.fixes = [], [], []

    def err(self, where, msg):
        self.errors.append(f"{where}｜{msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}｜{msg}")

    def fix(self, where, msg):
        self.fixes.append(f"{where}｜{msg}")


# ─────────────────────────── 2. 資料格式檢查 ───────────────────────────

def check_schema(rep, day, qa):
    if rep["date"] != day.isoformat():
        qa.err("標頭", f"日期 {rep['date'] or '（讀不到）'} ≠ {day}")
    if not rep.get("stats"):
        qa.err("文末", "缺「本日日報查詢約 N1 個網站，其中提取 N2 個資料來源」統計列")
    total = 0
    seen_urls = {}
    cap = 3 if day.weekday() >= 5 else 7
    for sec in rep["sections"]:
        c = sec["cat"]
        n = len(sec["items"])
        total += n
        if c == "cat1" and n > cap and not rep.get("edition"):
            qa.warn("cat1", f"Slot {n} 款，超過{'週末' if cap == 2 else '平日'}上限 {cap}（窗內 B≥3 全收時可接受）")
        for i, it in enumerate(sec["items"], 1):
            w = f"{c}-{it['no']:02d} {it['title'][:24]}"
            if it["no"] != i:
                qa.warn(w, f"編號 {it['no']:02d} 應為 {i:02d}（每區從 01 起）")
            if not it["title"]:
                qa.err(w, "缺標題")
            if not it["body"]:
                qa.err(w, "缺內文段落")
            elif "對 PM 的意義" not in "".join(it["body"]):
                qa.warn(w, "內文缺「對 PM 的意義：…」")
            if not it["sources"]:
                qa.err(w, "「來源：」沒有可點擊的 [名稱](網址)")
            if not it["date"]:
                qa.err(w, "「來源：」行缺主來源日期（YYYY-MM-DD）")
            else:
                check_date(it, c, day, w, qa, special=bool(rep.get("edition")))
            for _, u in it["sources"]:
                if u in seen_urls and seen_urls[u] != w:
                    qa.warn(w, f"與 {seen_urls[u]} 用了同一個來源連結")
                seen_urls.setdefault(u, w)
            text = " ".join(it["body"] + [it["verify"], it["derive"]])
            for bad in FORBIDDEN:
                if bad in text:
                    qa.err(w, f"內文出現品質備註用語「{bad}」（這類話只能放 Telegram）")
            if c == "cat1":
                keys = [k for k, _ in it["spec"]]
                miss = [k for k in R.SLOT_SPEC_KEYS if k not in keys]
                if miss:
                    qa.err(w, f"參數缺 {'、'.join(miss)}（沒資料寫「未公布」）")
                if not it["derive"]:
                    qa.err(w, "缺「衍生調整：」（全新款寫「全新 IP，無衍生」）")
                if not re.search(r"\s[–—-]\s", it["title"]):
                    qa.warn(w, "標題應為「遊戲名 – 廠商」")
            elif c == "cat2":
                keys = [k for k, _ in it["spec"]]
                miss = [k for k in R.NONSLOT_SPEC_MIN if k not in keys]
                if miss:
                    qa.err(w, f"參數缺 {'、'.join(miss)}")
                for k in ("盤面", "消除/賠付", "波動"):
                    if k in keys:
                        qa.warn(w, f"非 Slot 不放「{k}」欄位")
            else:
                if not it["keyrow"]:
                    (qa.err if c in ("cat3", "cat4") else qa.warn)(w, "缺「重點：類型 … ｜ 對象 … ｜ 影響 …」")
                elif {k for k, _ in it["keyrow"]} < {"類型", "對象", "影響"}:
                    qa.warn(w, "「重點」應含 類型／對象／影響 三項")
            if c in ("cat1", "cat2") and not it["image_raw"]:
                qa.warn(w, "缺「圖片：」行（沒有就寫「圖片：無」）")
    if total > 22:
        qa.warn("總量", f"共 {total} 則，超過上限 22")
    if total < 6 and not rep.get("edition"):
        qa.warn("總量", f"只有 {total} 則，可能去重過頭或抓取不足")
    return total


def check_date(it, cat, day, w, qa, special=False):
    try:
        pd = date.fromisoformat(it["date"])
    except ValueError:
        qa.err(w, f"主來源日期格式錯誤：{it['date']}")
        return
    age = (day - pd).days
    lab = it["label"]
    if age < 0:
        qa.err(w, f"主來源日期 {pd} 在未來")
        return
    if lab.startswith(("📦", "📋")):
        lim = 14 if special else FRESH[cat]   # v6.6.1 特別版（近期新作總覽）放寬到 14 天
        if age > lim:
            qa.err(w, f"庫存補位主來源 {pd} 已超過保鮮期 {lim} 天")
    elif lab.startswith("🆕"):
        if age > HOT_IP_DAYS:
            qa.err(w, f"新作預告主來源 {pd} 超過 {HOT_IP_DAYS} 天")
        elif age > 7:
            qa.warn(w, f"新作預告主來源 {pd} 已 {age} 天（只有熱門 IP 可放寬到 {HOT_IP_DAYS} 天）")
    elif lab.startswith("🔁"):
        if age > 2:
            qa.warn(w, f"🔁 再展示的主來源 {pd} 應為窗內的新進展")
    else:
        # 窗＝今天 02:30 往前 24 小時；主來源當地日期最多落在前兩天（美東下午＝台北深夜）
        if age == 2:
            qa.warn(w, f"主來源 {pd} 是前兩天的當地日期，確認台北時間仍在窗內")
        elif age > 2:
            qa.err(w, f"主來源 {pd} 不在收集時間窗內（當日新聞要窗內；庫存補位要標 📦）")


# ─────────────────────────── 3. 連結與圖片檢查 ───────────────────────────

_CTX = ssl.create_default_context()


def probe(url, want_image=False, timeout=12):
    """回傳 (狀態碼或錯誤字串, content-type)。先 HEAD，不行再用小範圍 GET。"""
    last = ("error", "")
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={
            "User-Agent": UA, "Accept": "image/*,*/*;q=0.8" if want_image else "text/html,*/*;q=0.8",
            "Range": "bytes=0-2047"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                return r.status, r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            last = (e.code, e.headers.get("Content-Type", "") if e.headers else "")
            if e.code in (404, 410) and method == "GET":
                return last
        except urllib.error.URLError as e:
            reason = str(getattr(e, "reason", e))
            last = ("dns" if ("nodename" in reason or "Name or service" in reason) else "error:" + reason[:60], "")
        except Exception as e:  # noqa: BLE001 — 逾時、連線重置等一律記下
            last = ("error:" + type(e).__name__, "")
    return last


def check_links(rep, qa):
    jobs = []
    for sec in rep["sections"]:
        for it in sec["items"]:
            w = f"{sec['cat']}-{it['no']:02d} {it['title'][:24]}"
            for n, u in it["sources"]:
                jobs.append(("src", w, it, n, u))
            if sec["cat"] in ("cat1", "cat2") and it["image"]:
                jobs.append(("img", w, it, "配圖", it["image"]))
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda j: probe(j[4], want_image=j[0] == "img"), jobs))
    stat = {"checked": len(jobs), "ok": 0, "broken": 0, "blocked": 0, "images_dropped": 0}
    for (kind, w, it, n, u), (code, ctype) in zip(jobs, res):
        ok = isinstance(code, int) and code < 400
        if kind == "img":
            is_img = ok and not ctype.lower().startswith("text/")
            if is_img:
                stat["ok"] += 1
            else:
                it["image_dropped"] = True
                stat["images_dropped"] += 1
                qa.fix(w, f"配圖打不開（{code} {ctype.split(';')[0]}），已自動拿掉：{u}")
            continue
        if ok:
            stat["ok"] += 1
        elif code in (404, 410) or code == "dns":
            stat["broken"] += 1
            qa.err(w, f"來源連結失效（{code}）：{n} {u}")
        else:
            stat["blocked"] += 1
            qa.warn(w, f"來源連結無法自動驗證（{code}，多半是網站擋機器人）：{n} {u}")
    return stat


# ─────────────────────────── 4. 模糊比對去重 ───────────────────────────

def check_dupes(rep, day, qa):
    flat = [(s["cat"], it) for s in rep["sections"] for it in s["items"]]

    def split(t):
        parts = re.split(r"\s+[–—-]\s+", t, maxsplit=1)
        return parts[0], (parts[1] if len(parts) > 1 else "")

    for i, (ca, a) in enumerate(flat):
        ta, ga = split(a["title"])
        for cb, b in flat[i + 1:]:
            tb, gb = split(b["title"])
            if R.same_item(ta, ga, tb, gb, 0.9):
                qa.err(f"{cb}-{b['no']:02d} {tb[:24]}", f"與同份日報 {ca}-{a['no']:02d}「{ta[:24]}」疑似重複")
    inv_path = os.path.join(ROOT, "state", "inventory.json")
    if not os.path.exists(inv_path):
        return
    hist = json.load(open(inv_path, encoding="utf-8")).get("history", [])
    recent = [h for h in hist if 1 <= (day - date.fromisoformat(h["date"][:10])).days <= 3]
    for c, it in flat:
        t, g = split(it["title"])
        for h in recent:
            game = c in ("cat1", "cat2")
            if not R.same_item(t, g, h.get("title", ""), h.get("gp", ""), 0.9 if game else 0.8):
                continue
            where = f"{c}-{it['no']:02d} {t[:24]}"
            msg = f"與 {h['date']} 日報「{h.get('title', '')[:24]}」疑似重複（3 天去重）"
            if it["label"].startswith("🔁"):
                qa.warn(where, msg + "，已標 🔁")
            elif game:
                qa.err(where, msg)
            else:
                qa.warn(where, msg + "；若是新進展請在內文寫清楚")
            break


# ─────────────────────────── 5. 庫存使用檢查（v6.6.4） ───────────────────────────

def _mentioned(title, text):
    """原稿內部紀錄有沒有提到這一款（用來允許「查證後剔除」並寫明原因）。"""
    n = R.norm_title(title)
    return bool(n) and n in R.norm_title(text.replace("\n", " "))


def check_inventory_use(rep, day, qa):
    """補位要照 B 分；某區當天空著、庫存卻有料就要補。
    例外：在原稿最後的內部紀錄寫「剔除：<名稱>（原因）」，代表查證後確定不能用。"""
    if rep.get("edition"):
        return
    inv_path = os.path.join(ROOT, "state", "inventory.json")
    if not os.path.exists(inv_path):
        return
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import inventory as INV
    inv = INV.load()
    rk = INV.recent_keys(inv, day)
    horizon = day + timedelta(days=INV.PREVIEW_MAX_DAYS)
    internal = rep.get("internal", "")
    secs = {s["cat"]: s["items"] for s in rep["sections"]}

    def split(t):
        parts = re.split(r"\s+[–—-]\s+", t, maxsplit=1)
        return parts[0], (parts[1] if len(parts) > 1 else "")

    # ① Slot 補位要照 B 分
    slots = [x for x in inv["slots"] if not INV.expired(x, day, True) and not INV.matches(x, rk)
             and not INV.is_placeholder(x) and not (x.get("release_date") and INV.d(x["release_date"]) > horizon)]
    fills = [it for it in secs.get("cat1", []) if it["label"].startswith("📦")]
    used, used_b = [], []
    for it in fills:
        t, g = split(it["title"])
        hit = next((x for x in slots if R.same_item(t, g, x["title"], x.get("gp", ""))), None)
        if hit:
            used.append(hit)
            used_b.append(hit.get("b") or 0)
    if used_b:
        floor = min(used_b)
        for x in slots:
            if x in used or (x.get("b") or 0) <= floor:
                continue
            if any(R.same_item(split(it["title"])[0], split(it["title"])[1], x["title"], x.get("gp", ""))
                   for it in secs.get("cat1", [])):
                continue
            if _mentioned(x["title"], internal):
                continue
            qa.err("cat1", f"補位沒照 B 分：庫存有 {x['title']}（B{x.get('b')}）沒用，卻用了 B{floor} 的項目；"
                           f"不能用的話在原稿內部紀錄寫「剔除：{x['title']}（原因）」")
    # ①-b 該補沒補：平日當天新作 ≤5、週末 ≤2，Slot 沒滿上限、庫存還有沒用的 → 要補
    cap, thr = (3, 2) if day.weekday() >= 5 else (7, 5)
    cat1 = secs.get("cat1", [])
    new = [it for it in cat1 if not it["label"].startswith(("📦", "📋"))]
    if len(new) <= thr and len(cat1) < cap:
        left = [x for x in slots if x not in used and not _mentioned(x["title"], internal)
                and not any(R.same_item(split(it["title"])[0], split(it["title"])[1], x["title"], x.get("gp", "")) for it in cat1)]
        if left:
            best = max(left, key=lambda x: (x.get("b") or 0))
            qa.err("cat1", f"當天新作 {len(new)} 款（≤{thr}），Slot 只有 {len(cat1)} 款、未滿 {cap}，庫存還有 {len(left)} 款可補"
                           f"（最高 {best['title']} B{best.get('b')}）；不能用的話在原稿內部紀錄寫「剔除：名稱（原因）」")
    # ② 其他分類：當天空著、庫存有料就要補 1 則
    for cat in ("cat2", "cat3", "cat4", "cat5"):
        if secs.get(cat):
            continue
        stock = [x for x in inv["others"] if x.get("cat") == cat and not INV.expired(x, day, False)
                 and not INV.matches(x, rk) and not _mentioned(x["title"], internal)]
        if stock:
            qa.err(cat, f"今天 0 則，但庫存有 {len(stock)} 則可補（例：{stock[0]['title'][:30]}）；"
                        f"不能用的話在原稿內部紀錄寫「剔除：<名稱>（原因）」")


# ─────────────────────────── 主流程 ───────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--md")
    ap.add_argument("--out")
    ap.add_argument("--no-links", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    day = date.fromisoformat(a.date)
    md = a.md or os.path.join(ROOT, "state", f"{a.date}-igaming-report.md")
    out = a.out or os.path.join(ROOT, "reports", f"{a.date}.html")
    if not os.path.exists(md):
        print(f"✗ 找不到 {md}")
        sys.exit(2)
    rep = R.parse_md(open(md, encoding="utf-8").read())
    qa = QA()
    total = check_schema(rep, day, qa)
    links = {"checked": 0, "skipped": True} if a.no_links else check_links(rep, qa)
    check_dupes(rep, day, qa)
    check_inventory_use(rep, day, qa)
    # v6.5：「提取 N2 個資料來源」改由程式算 —— 全部則的來源連結去重後的數量（SKILL.md「📊 文末統計列」定義）
    n2 = len({u for sec in rep["sections"] for it in sec["items"] for _, u in it["sources"]})
    if rep.get("stats"):
        if rep["stats"]["n2"] != n2:
            qa.fix("文末", f"資料來源數 {rep['stats']['n2']} → {n2}（程式依來源連結去重計算）")
        rep["stats"]["n2"] = n2
        if rep["stats"]["n1"] < n2:
            qa.warn("文末", f"查詢網站數 N1（{rep['stats']['n1']}）小於實際來源數 {n2}，已調成 {n2}")
            rep["stats"]["n1"] = n2

    base = os.path.splitext(os.path.basename(md))[0].replace("-igaming-report", "")
    with open(os.path.join(ROOT, "state", f"{base}-report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    result = {"date": a.date, "md": os.path.relpath(md, ROOT), "html": None if a.check_only else os.path.relpath(out, ROOT),
              "items": total, "counts": {s["cat"]: len(s["items"]) for s in rep["sections"] if s["items"]},
              "links": links, "errors": qa.errors, "warnings": qa.warnings, "fixes": qa.fixes}
    with open(os.path.join(ROOT, "state", f"{base}-qa.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    if not a.check_only:
        with open(out, "w", encoding="utf-8") as f:
            f.write(R.render_html(rep))

    print(f"# 定稿檢查 {a.date}：{total} 則｜" + "、".join(f"{c} {n}" for c, n in result["counts"].items()))
    if not a.no_links:
        print(f"- 連結：檢查 {links['checked']}、正常 {links['ok']}、失效 {links['broken']}、"
              f"無法驗證 {links['blocked']}、配圖拿掉 {links['images_dropped']}")
    for title, rows in (("❌ 錯誤（必須修正 .md 後重跑）", qa.errors), ("⚠️ 警告", qa.warnings), ("🔧 自動修正", qa.fixes)):
        if rows:
            print(f"\n## {title} {len(rows)}")
            print("\n".join(f"- {r}" for r in rows))
    print(f"\n{'✗' if qa.errors else '✓'} HTML {'未寫（--check-only）' if a.check_only else '已寫入 ' + os.path.relpath(out, ROOT)}"
          f"；檢查結果 state/{base}-qa.json")
    sys.exit(1 if qa.errors else 0)


if __name__ == "__main__":
    main()
