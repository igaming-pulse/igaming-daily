#!/usr/bin/env python3
"""
v6.6 庫存釋放特別版（2026-10-11 使用者定案）。

每週一、週四的日報成功後，run_special.sh 會呼叫這支挑選要釋放的 Slot 庫存：
  - 可用庫存＝沒過期、近 3 天沒出現、不是 TBC 佔位頁、上線日不在 7 天以後（同 inventory.py show 的判斷）
  - 可用 ≥ MIN_TRIGGER（5）款才發；週六、週日日報上限不受影響
  - v6.6.2：一次最多 10 款；大廠（B≥3）依 B 高→首見早排前面，B1 依首見早（快過期優先）排後面；沒放到的留在庫存給日報補位
  - 查證不過的（找不到真實原文、確認不了遊戲存在）直接移出庫存，記到 rejected，不再囤積
  - 重做同一天（--redo）：今天已發過的項目一併帶回，合成一份完整總覽

用法：
  python3 scripts/special_edition.py select --date 2026-10-12      # 印出並寫 state/special-<DATE>-items.json
  python3 scripts/special_edition.py shown  --date 2026-10-12      # 依寫好的特別版原稿產生 picks（給 inventory.py update）
結束碼：select 有達門檻＝0；沒達門檻＝3
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory as INV  # noqa: E402
import report_lib as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_TRIGGER = 5          # 使用者定案：可用庫存超過 4 款才發
MAX_TOTAL = 10           # v6.6.2 使用者定案：一次最多 10 款（太多看不完）；沒放到的留給之後的日報補位


def available(today):
    inv = INV.load()
    rk = INV.recent_keys(inv, today)
    horizon = today + timedelta(days=INV.PREVIEW_MAX_DAYS)
    out = []
    for x in inv["slots"]:
        if INV.expired(x, today, True) or INV.matches(x, rk) or INV.is_placeholder(x):
            continue
        if x.get("release_date") and INV.d(x["release_date"]) > horizon:
            continue
        out.append(x)
    return out


def pick(items):
    """全部釋放：大廠（B≥3）B 高→首見早在前，其餘依首見早在後。"""
    big = sorted([x for x in items if (x.get("b") or 0) >= 3], key=lambda x: (-(x.get("b") or 0), x["first_seen"]))
    small = sorted([x for x in items if (x.get("b") or 0) < 3], key=lambda x: (x["first_seen"], x["title"]))
    return (big + small)[:MAX_TOTAL]


def released_today(day):
    """--redo 用：今天特別版已經釋放的項目（完整資料從上一次的候選檔取回）。"""
    picks = os.path.join(ROOT, "state", f"inventory-picks-{day}-special.json")
    items = os.path.join(ROOT, "state", f"special-{day}-items.json")
    if not (os.path.exists(picks) and os.path.exists(items)):
        return []
    shown = json.load(open(picks, encoding="utf-8"))["shown"]
    prev = json.load(open(items, encoding="utf-8"))["chosen"]
    out = []
    for x in prev:
        if any(R.same_item(x["title"], x.get("gp", ""), s["title"], s.get("gp", "")) for s in shown):
            out.append({**x, "already_released": True})
    return out


def cmd_select(a):
    today = date.fromisoformat(a.date)
    av = available(today)
    back = released_today(a.date) if a.redo else []
    av_all = av + [x for x in back if not any(R.same_item(x["title"], x.get("gp", ""), y["title"], y.get("gp", "")) for y in av)]
    chosen = pick(av_all)
    path = os.path.join(ROOT, "state", f"special-{a.date}-items.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": a.date, "available": len(av), "chosen": chosen}, f, ensure_ascii=False, indent=1)
    print(f"# 特別版候選 {a.date}：可用庫存 {len(av)} 款（門檻 ≥{MIN_TRIGGER}），選出 {len(chosen)} 款"
          f"（大廠 {sum(1 for x in chosen if (x.get('b') or 0) >= 3)}、B1 {sum(1 for x in chosen if (x.get('b') or 0) < 3)}）"
          + (f"；含今天已發 {len(back)} 款" if back else ""))
    for i, x in enumerate(chosen, 1):
        rel = f"｜上線日 {x['release_date']}" if x.get("release_date") else ""
        print(f"{i:02d}. [B{x.get('b', '?')}] {x['title']} — {x.get('gp', '?')}｜首見 {x['first_seen']}{rel}")
    print(f"→ {os.path.relpath(path, ROOT)}")
    sys.exit(0 if (len(av) >= MIN_TRIGGER or a.redo) else 3)


def cmd_shown(a):
    """特別版原稿寫好後：實際寫進去的才算釋放（查證失敗被剔除的留在庫存）。"""
    md = os.path.join(ROOT, "state", f"{a.date}-special-igaming-report.md")
    rep = R.parse_md(open(md, encoding="utf-8").read())
    chosen = json.load(open(os.path.join(ROOT, "state", f"special-{a.date}-items.json"), encoding="utf-8"))["chosen"]
    shown = []
    for sec in rep["sections"]:
        for it in sec["items"]:
            parts = it["title"].split(" – ", 1) if " – " in it["title"] else it["title"].split(" — ", 1)
            t, g = parts[0], (parts[1] if len(parts) > 1 else "")
            hit = next((x for x in chosen if R.same_item(t, g, x["title"], x.get("gp", ""))), None)
            shown.append({"cat": "cat1", "title": hit["title"] if hit else t, "gp": hit.get("gp", g) if hit else g})
    out = os.path.join(ROOT, "state", f"inventory-picks-{a.date}-special.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"shown": shown, "stock": []}, f, ensure_ascii=False, indent=1)
    # 沒寫進去的＝查證不過 → 移出庫存、記到 rejected（不再囤積、下次也不會再被選到）
    dropped = [x for x in chosen if not any(R.same_item(x["title"], x.get("gp", ""), s["title"], s.get("gp", "")) for s in shown)]
    if dropped:
        inv = INV.load()
        keys = {INV.key_of(x) for x in dropped}
        inv["slots"] = [x for x in inv["slots"] if INV.key_of(x) not in keys and not any(
            R.same_item(x["title"], x.get("gp", ""), d["title"], d.get("gp", "")) for d in dropped)]
        inv.setdefault("rejected", []).extend({"date": a.date, "title": d["title"], "gp": d.get("gp", ""),
                                               "reason": "特別版查證未通過（找不到真實原文或確認不了遊戲存在）"} for d in dropped)
        inv["rejected"] = inv["rejected"][-50:]
        INV.save(inv)
    print(f"✓ 特別版實際釋放 {len(shown)} 款 → {os.path.relpath(out, ROOT)}"
          + (f"；查證未過、移出庫存 {len(dropped)} 款：" + "、".join(d["title"] for d in dropped) if dropped else ""))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("select", "shown"):
        p = sub.add_parser(n)
        p.add_argument("--date", required=True)
        p.add_argument("--redo", action="store_true", help="重做今天的特別版：帶回今天已發的項目")
    a = ap.parse_args()
    {"select": cmd_select, "shown": cmd_shown}[a.cmd](a)


if __name__ == "__main__":
    main()
