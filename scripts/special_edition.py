#!/usr/bin/env python3
"""
v6.6 庫存釋放特別版（2026-10-11 使用者定案）。

每週一、週四的日報成功後，run_special.sh 會呼叫這支挑選要釋放的 Slot 庫存：
  - 可用庫存＝沒過期、近 3 天沒出現、不是 TBC 佔位頁、上線日不在 7 天以後（同 inventory.py show 的判斷）
  - 可用 ≥ MIN_TRIGGER（5）款才發；週六、週日日報上限不受影響
  - 大廠（B≥3）全收，依 B 高→首見早，一律排在前面
  - B1 小廠最多 MAX_B1 款，優先挑快過期的（首見早），排在大廠後面
  - 每期最多 MAX_TOTAL 款；沒選上的留在庫存

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
MIN_TRIGGER = 5
MAX_TOTAL = 12
MAX_B1 = 5


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
    big = sorted([x for x in items if (x.get("b") or 0) >= 3], key=lambda x: (-(x.get("b") or 0), x["first_seen"]))
    small = sorted([x for x in items if (x.get("b") or 0) < 3], key=lambda x: (x["first_seen"], x["title"]))
    big = big[:MAX_TOTAL]
    small = small[:max(0, min(MAX_B1, MAX_TOTAL - len(big)))]
    return big + small


def cmd_select(a):
    today = date.fromisoformat(a.date)
    av = available(today)
    chosen = pick(av)
    path = os.path.join(ROOT, "state", f"special-{a.date}-items.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": a.date, "available": len(av), "chosen": chosen}, f, ensure_ascii=False, indent=1)
    print(f"# 特別版候選 {a.date}：可用庫存 {len(av)} 款（門檻 ≥{MIN_TRIGGER}），選出 {len(chosen)} 款"
          f"（大廠 {sum(1 for x in chosen if (x.get('b') or 0) >= 3)}、B1 {sum(1 for x in chosen if (x.get('b') or 0) < 3)}）")
    for i, x in enumerate(chosen, 1):
        rel = f"｜上線日 {x['release_date']}" if x.get("release_date") else ""
        print(f"{i:02d}. [B{x.get('b', '?')}] {x['title']} — {x.get('gp', '?')}｜首見 {x['first_seen']}{rel}")
    print(f"→ {os.path.relpath(path, ROOT)}")
    sys.exit(0 if len(av) >= MIN_TRIGGER else 3)


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
    print(f"✓ 特別版實際釋放 {len(shown)} 款 → {os.path.relpath(out, ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("select", "shown"):
        p = sub.add_parser(n)
        p.add_argument("--date", required=True)
    a = ap.parse_args()
    {"select": cmd_select, "shown": cmd_shown}[a.cmd](a)


if __name__ == "__main__":
    main()
