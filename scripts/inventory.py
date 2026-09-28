#!/usr/bin/env python3
"""
v6.4 庫存與重複控管（2026-09-27 定案）。

狀態檔：state/inventory.json（跟著 repo 走，每晚的執行都讀得到）
  slots    ：Slot／新遊戲庫存（含已上線、提前評測、預告）
  others   ：其他分類的庫存（cat2–cat5）
  history  ：已經在日報出現過的項目（去重用）

規則（SKILL.md「📦 庫存機制」為準）：
  - Slot：平日上限 5、週末上限 2；當天新作 ≤3 款才從庫存補到上限、≥4 款不補；首次看到後保鮮 7 天，
          未上線的預告保留到「上線日＋3 天」。
  - 其他分類：保鮮 3 天；某區連續空 2 天可以，第 3 天必須從庫存補。
  - 去重：3 天內出現過的不再出現；超過 3 天又出現且重要（例：預告→正式上線）可再展示。

用法：
  python3 scripts/inventory.py show --date 2026-09-27
      清掉過期項目，印出「可用庫存」與「近 3 天已出現」清單（給 Claude 讀）。
  python3 scripts/inventory.py update --date 2026-09-27 --file state/inventory-picks-2026-09-27.json
      picks 檔格式見 SKILL.md：{"shown":[...], "stock":[...]}，寫回 inventory.json。
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_lib import same_item  # noqa: E402  v6.5 模糊比對

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "state", "inventory.json")
SLOT_FRESH_DAYS = 7
SLOT_AFTER_RELEASE_DAYS = 3
OTHER_FRESH_DAYS = 3
DEDUP_DAYS = 3
PREVIEW_MAX_DAYS = 7   # 上線日在 7 天以後的預告不上日報（太遠，玩不到）


def key_of(item):
    base = item.get("key") or f"{item.get('title', '')}|{item.get('gp', '')}"
    return re.sub(r"[^0-9a-z一-鿿|]+", "", base.lower())


def load():
    if os.path.exists(INV):
        with open(INV, encoding="utf-8") as f:
            return json.load(f)
    return {"slots": [], "others": [], "history": []}


def save(inv):
    os.makedirs(os.path.dirname(INV), exist_ok=True)
    with open(INV, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=1)


def d(s):
    return date.fromisoformat(s[:10])


def expired(item, today, is_slot):
    first = d(item["first_seen"])
    if is_slot:
        rel = item.get("release_date")
        if rel and d(rel) > first:
            return today > max(first + timedelta(days=SLOT_FRESH_DAYS), d(rel) + timedelta(days=SLOT_AFTER_RELEASE_DAYS))
        return today > first + timedelta(days=SLOT_FRESH_DAYS)
    return today > first + timedelta(days=OTHER_FRESH_DAYS)


def recent_keys(inv, today):
    return {h["key"]: h for h in inv["history"] if 0 <= (today - d(h["date"])).days <= DEDUP_DAYS}


def matches(x, pool):
    """v6.5：同一款／同一則？先比正規化 key，再用模糊比對（Huff N´Puff＝Huff N' Puff、Pragmatic＝Pragmatic Play）。
    Slot／非 Slot 門檻 0.9；其他分類是中文新聞標題，只做精確 key 比對，避免誤殺不同新聞。"""
    k = key_of(x)
    if k in pool:
        return True
    if x.get("cat") not in ("cat1", "cat2"):
        return False
    return any(h.get("cat") in ("cat1", "cat2", "") and same_item(x.get("title", ""), x.get("gp", ""),
                                                                  h.get("title", ""), h.get("gp", ""))
               for h in pool.values())


def prune(inv, today):
    inv["slots"] = [x for x in inv["slots"] if not expired(x, today, True)]
    inv["others"] = [x for x in inv["others"] if not expired(x, today, False)]
    inv["history"] = [h for h in inv["history"] if (today - d(h["date"])).days <= 30]


def cmd_show(a):
    inv = load()
    today = date.fromisoformat(a.date)
    prune(inv, today)
    save(inv)
    rk = recent_keys(inv, today)
    print(f"# 庫存狀態 {a.date}（Slot 保鮮 {SLOT_FRESH_DAYS} 天、其他 {OTHER_FRESH_DAYS} 天、去重 {DEDUP_DAYS} 天）\n")
    cap = 2 if today.weekday() >= 5 else 5
    wd = "一二三四五六日"[today.weekday()]
    horizon = today + timedelta(days=PREVIEW_MAX_DAYS)
    pool = [x for x in inv["slots"] if not matches(x, rk)]
    later = [x for x in pool if x.get("release_date") and d(x["release_date"]) > horizon]
    slots = [x for x in pool if x not in later]
    slots.sort(key=lambda x: (-(x.get("b") or 0), x["first_seen"]))
    print(f"## 🎯 今天是週{wd}日報：Slot 上限 {cap} 款。當天新作 ≤3 款才從庫存補到 {cap} 款；≥4 款不補；"
          f"庫存不夠就有多少補多少，不足不硬湊")
    if today.weekday() == 5:
        print("## 📋 今天是週六檢查點：比對 Weekend Reels 與 BigWinBoard 本週新作，漏收的標「📋 本週補遺」，算在 2 款內，多的進庫存")
    print()
    print(f"## 🎰 Slot 可用庫存 {len(slots)} 款（B 分高→首見早排序）")
    for x in slots:
        rel = f"｜上線日 {x['release_date']}" if x.get("release_date") else ""
        src = x.get("sources", [{}])[0]
        print(f"- [{x.get('b', '?')}] {x['title']} — {x.get('gp', '?')}｜首見 {x['first_seen']}{rel}"
              f"｜{src.get('name', '')} {src.get('url', '')}".rstrip())
    if later:
        print()
        print(f"## ⏳ 待上線（上線日在 {horizon} 之後，今天不可上日報）{len(later)} 款")
        for x in later:
            print(f"- {x['title']} — {x.get('gp', '?')}｜上線日 {x['release_date']}")
    print()
    for cat in ["cat2", "cat3", "cat4", "cat5"]:
        items = [x for x in inv["others"] if x.get("cat") == cat and not matches(x, rk)]
        print(f"## {cat} 可用庫存 {len(items)} 則")
        for x in items:
            src = x.get("sources", [{}])[0]
            print(f"- {x['title']}｜首見 {x['first_seen']}｜{src.get('name', '')} {src.get('url', '')}".rstrip())
        print()
    print(f"## 🚫 近 {DEDUP_DAYS} 天已出現（不可重複；超過 {DEDUP_DAYS} 天且有重大更新才可再展示）")
    for k, h in sorted(rk.items(), key=lambda kv: kv[1]["date"], reverse=True):
        print(f"- {h['date']}｜{h.get('cat', '')}｜{h['title']}" + (f" — {h['gp']}" if h.get("gp") else ""))
    print()
    streak = {}
    for cat in ["cat1", "cat2", "cat3", "cat4", "cat5"]:
        n = 0
        for i in range(1, 4):
            day = (today - timedelta(days=i)).isoformat()
            if any(h["date"] == day and h.get("cat") == cat for h in inv["history"]):
                break
            if not any(h["date"] == day for h in inv["history"]):
                break  # 那天沒有紀錄（系統還沒上線），不算空
            n += 1
        streak[cat] = n
    print("## 📉 各區連續空白天數（≥2 表示今天必須從庫存補）")
    print("- " + "、".join(f"{c} {n} 天" for c, n in streak.items()))


def cmd_update(a):
    inv = load()
    today = date.fromisoformat(a.date)
    with open(a.file, encoding="utf-8") as f:
        picks = json.load(f)
    shown = {}
    # 重跑同一天：先清掉這一天舊的「已出現」紀錄，避免重複累加
    inv["history"] = [h for h in inv["history"] if h["date"] != a.date]
    for x in picks.get("shown", []):
        k = key_of(x)
        h = {"key": k, "date": a.date, "cat": x.get("cat", ""), "title": x.get("title", ""), "gp": x.get("gp", "")}
        shown[k] = h
        inv["history"].append(h)
    inv["slots"] = [x for x in inv["slots"] if not matches(x, shown)]
    inv["others"] = [x for x in inv["others"] if not matches(x, shown)]
    have = {key_of(x): x for x in inv["slots"] + inv["others"]}
    added = merged = 0
    for x in picks.get("stock", []):
        k = key_of(x)
        if matches(x, shown):
            continue
        if matches(x, have):
            merged += 1   # 同一款換個寫法又進來：保留舊的那筆（首見日較早）
            continue
        x.setdefault("first_seen", a.date)
        x["key"] = x.get("key") or k
        (inv["slots"] if x.get("cat") == "cat1" else inv["others"]).append(x)
        have[k] = x
        added += 1
    prune(inv, today)
    save(inv)
    print(f"✓ 庫存更新 {a.date}：已出現 {len(shown)} 則寫入紀錄、新增庫存 {added} 則"
          f"{f'（{merged} 則與既有庫存模糊比對為同一款，未重複加入）' if merged else ''}；"
          f"目前 Slot 庫存 {len(inv['slots'])}、其他 {len(inv['others'])}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("--date", required=True)
    u = sub.add_parser("update"); u.add_argument("--date", required=True); u.add_argument("--file", required=True)
    a = ap.parse_args()
    {"show": cmd_show, "update": cmd_update}[a.cmd](a)


if __name__ == "__main__":
    main()
