#!/usr/bin/env python3
"""Firecrawl 每日用量（v6.6.11，2026-10-12）

日報文末「本日日報查詢約 N1 個網站…」下一行顯示：本日用量、剩餘點數、下次重置日。
- 用量 ＝ harvest.py 開跑時記下的剩餘點數（state/health/credits.json 的 start）− 定稿時的剩餘點數
- 每天的紀錄也寫回 credits.json：start / end / used / reset / reset_source
- 下次重置日：先用 Firecrawl API 回傳的 billingPeriodEnd；查不到就用
  state/firecrawl-reset.json 的 anchor（預設 2026-10-12）每次加一個月，取今天以後最近的一天。
  使用者可以手動改 anchor。
"""
import json
import os
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDITS = os.path.join(ROOT, "state", "health", "credits.json")
RESET_CFG = os.path.join(ROOT, "state", "firecrawl-reset.json")
DEFAULT_ANCHOR = "2026-10-12"


def _jload(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    last = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def estimated_reset(day):
    """anchor 每次加一個月，回傳 > day 的第一個日期（重置日當天顯示下一次）。"""
    cfg = _jload(RESET_CFG, {})
    try:
        anchor = date.fromisoformat(str(cfg.get("anchor") or DEFAULT_ANCHOR)[:10])
    except ValueError:
        anchor = date.fromisoformat(DEFAULT_ANCHOR)
    n = 0
    while add_months(anchor, n) <= day:   # 重置日當天 → 顯示下個月
        n += 1
    return add_months(anchor, n)


def live_credits():
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        return None
    req = urllib.request.Request("https://api.firecrawl.dev/v2/team/credit-usage",
                                 headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r).get("data", {})
        if d.get("remainingCredits") is None:
            return None
        return {"remaining": int(d["remainingCredits"]), "period_end": (d.get("billingPeriodEnd") or "")[:10]}
    except Exception:  # noqa: BLE001
        return None


def usage(day, save=True):
    """回傳 {used, remaining, reset, reset_source} 或 None（完全沒有資料）。save=True 時寫回 credits.json。"""
    hist = _jload(CREDITS, {})
    rec = hist.get(day.isoformat())
    rec = dict(rec) if isinstance(rec, dict) else ({"start": rec} if isinstance(rec, int) else {})
    cr = live_credits()
    if cr:
        rec["end"] = cr["remaining"]
    remaining = rec.get("end")
    if remaining is None and not rec.get("start"):
        return None
    if cr and cr["period_end"]:
        reset, src = cr["period_end"], "api"
    else:
        reset, src = estimated_reset(day).isoformat(), "estimate"
    used = rec["start"] - remaining if rec.get("start") is not None and remaining is not None else None
    if used is not None and used < 0:   # 中途重置過（剩餘變多），今天的用量算不出來
        used = None
    rec.update({"used": used, "reset": reset, "reset_source": src})
    if save:
        hist[day.isoformat()] = rec
        os.makedirs(os.path.dirname(CREDITS), exist_ok=True)
        with open(CREDITS, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(hist.items())[-40:]), f, ensure_ascii=False, indent=1)
    return {"used": used, "remaining": remaining, "reset": reset, "reset_source": src}


if __name__ == "__main__":
    import sys
    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(usage(d, save=False))
