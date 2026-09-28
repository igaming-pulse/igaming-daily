#!/usr/bin/env python3
"""
v6.5 額度與健康警報（2026-09-28 定案）。

檢查四件事，有狀況才出聲：
  1. Firecrawl 額度：剩餘點數、依近 7 天實際用量推估能不能撐到重置日
  2. 來源健康：同一個來源連續 ≥3 天抓取失敗（harvest 第一層＋第二層列表頁）
  3. 候選量異常：今天窗內候選數 < 近 7 天平均的一半（多半是抓取壞了，不是新聞少）
  4. 定稿檢查：finalize_report.py 還留著沒修掉的錯誤

用法：
  python3 scripts/health_alert.py --date <DATE>
      印出檢查結果；寫 state/health/<DATE>.json，更新 state/health/credits.json、source_streaks.json
  python3 scripts/health_alert.py --date <DATE> --append state/pending_telegram.txt
      另外把「⚙️ 系統警報」附在 Telegram 訊息最後（重跑會先移除舊的那段，不會重複）；沒有警報就不附

金鑰讀環境變數 FIRECRAWL_API_KEY（launchd plist 已設定）；讀不到就略過額度檢查並在結果註明。
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HDIR = os.path.join(ROOT, "state", "health")
CREDITS = os.path.join(HDIR, "credits.json")
STREAKS = os.path.join(HDIR, "source_streaks.json")
BLOCK = "⚙️ 系統警報"

CREDIT_FLOOR = 100          # 低於這個數字直接紅燈
DEFAULT_DAILY_USE = 35      # 還沒有用量紀錄時，用 SKILL.md 的單日上限估
FAIL_STREAK_DAYS = 3
LOW_CANDIDATE_RATIO = 0.5


def jload(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def jsave(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def firecrawl_credits():
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        return None, "沒有 FIRECRAWL_API_KEY，略過額度檢查"
    req = urllib.request.Request("https://api.firecrawl.dev/v2/team/credit-usage",
                                 headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r).get("data", {})
        return {"remaining": d.get("remainingCredits"), "plan": d.get("planCredits"),
                "period_end": (d.get("billingPeriodEnd") or "")[:10]}, ""
    except Exception as e:  # noqa: BLE001
        return None, f"額度查詢失敗（{type(e).__name__}）"


def check_credits(day, alerts, info):
    cr, note = firecrawl_credits()
    if not cr or cr["remaining"] is None:
        info["credits"] = note
        return
    hist = jload(CREDITS, {})
    hist[day.isoformat()] = cr["remaining"]
    hist = dict(sorted(hist.items())[-40:])
    jsave(CREDITS, hist)
    # 近 7 天實際用量：相鄰兩天剩餘點數的差（重置日會變多，跳過）
    days = sorted(hist)
    uses = [hist[a] - hist[b] for a, b in zip(days, days[1:])
            if (date.fromisoformat(b) - date.fromisoformat(a)).days == 1 and hist[a] >= hist[b]][-7:]
    daily = round(sum(uses) / len(uses)) if uses else DEFAULT_DAILY_USE
    end = date.fromisoformat(cr["period_end"]) if cr["period_end"] else None
    left_days = max((end - day).days, 0) if end else None
    need = daily * left_days if left_days is not None else None
    info["credits"] = {**cr, "daily_use": daily, "daily_basis": "近 7 天實際" if uses else "預設上限",
                       "days_to_reset": left_days, "need_until_reset": need}
    rem = cr["remaining"]
    if rem < CREDIT_FLOOR:
        alerts.append(f"🔴 Firecrawl 額度只剩 {rem} 點（{cr['period_end']} 重置），低於警戒線 {CREDIT_FLOOR}；"
                      f"建議暫停加碼抓取、只留第二層列表頁")
    elif need is not None and rem < need:
        run_out = day + timedelta(days=rem // max(daily, 1))
        alerts.append(f"🟠 Firecrawl 剩 {rem} 點，照每天約 {daily} 點會在 {run_out.month}/{run_out.day} 用完，"
                      f"撐不到 {end.month}/{end.day} 重置（還差約 {need - rem} 點）")


def check_sources(day, alerts, info):
    hp = os.path.join(ROOT, "state", "harvest", f"{day}.json")
    h = jload(hp, None)
    if not h:
        alerts.append(f"🟠 找不到 harvest 結果（state/harvest/{day}.json），今天的候選可能是 Claude 自己補抓的")
        info["harvest"] = "missing"
        return
    rows = [(x["source"], x["status"] == "OK") for x in h.get("health", [])]
    rows += [(x["source"], x["status"] == "OK") for x in h.get("lists", []) if not x["status"].startswith("略過")]
    streaks = jload(STREAKS, {})
    for src, ok in rows:
        s = streaks.setdefault(src, {"fail": 0, "last": ""})
        if s["last"] == day.isoformat():
            continue            # 同一天重跑不重複累加
        s["fail"] = 0 if ok else s["fail"] + 1
        s["last"] = day.isoformat()
    jsave(STREAKS, streaks)
    bad = sorted((k for k, v in streaks.items() if v["fail"] >= FAIL_STREAK_DAYS and v["last"] == day.isoformat()),
                 key=lambda k: -streaks[k]["fail"])
    failed_today = [s for s, ok in rows if not ok]
    info["sources"] = {"total": len(rows), "failed_today": failed_today, "streak_3d": bad}
    if bad:
        names = "、".join(f"{k}（{streaks[k]['fail']} 天）" for k in bad[:5])
        alerts.append(f"🟠 來源連續失敗 ≥{FAIL_STREAK_DAYS} 天：{names}" + (f" 等 {len(bad)} 個" if len(bad) > 5 else "")
                      + "；請檢查網址或改抓取方式")
    if rows and len(failed_today) / len(rows) >= 0.2:
        alerts.append(f"🟠 今天有 {len(failed_today)}/{len(rows)} 個來源抓取失敗（≥20%），可能是網路或被擋")
    # 候選量異常：只跟「同類型」的日子比 —— 週日、週一日報的窗落在週末，新聞本來就少
    weekend = lambda d: d.weekday() in (6, 0)
    n_today = sum(1 for x in h.get("items", []) if x.get("in_window"))
    past = []
    for i in range(1, 22):
        d = day - timedelta(days=i)
        if weekend(d) != weekend(day):
            continue
        p = jload(os.path.join(ROOT, "state", "harvest", f"{d}.json"), None)
        if p:
            past.append(sum(1 for x in p.get("items", []) if x.get("in_window")))
        if len(past) >= 5:
            break
    past.sort()
    med = past[len(past) // 2] if len(past) >= 3 else None
    info["candidates"] = {"today": n_today, "median_same_type": med, "basis_days": len(past),
                          "type": "週末窗" if weekend(day) else "平日窗"}
    if n_today < 5:
        alerts.append(f"🟠 今天窗內候選只有 {n_today} 則，幾乎沒抓到東西，先懷疑抓取壞了")
    elif med and n_today < med * LOW_CANDIDATE_RATIO:
        alerts.append(f"🟠 今天窗內候選 {n_today} 則，不到同類型日子中位數 {med} 則的一半，先懷疑抓取、再判斷新聞少")


def check_qa(day, alerts, info):
    qa = jload(os.path.join(ROOT, "state", f"{day}-qa.json"), None)
    if not qa:
        info["qa"] = "missing"
        return
    info["qa"] = {"errors": len(qa["errors"]), "warnings": len(qa["warnings"]), "fixes": len(qa["fixes"])}
    if qa["errors"]:
        alerts.append(f"🟠 定稿檢查還有 {len(qa['errors'])} 個錯誤沒修：{qa['errors'][0][:60]}"
                      + ("…" if len(qa["errors"]) > 1 else ""))
    broken = qa.get("links", {}).get("broken", 0)
    if broken:
        alerts.append(f"🟠 {broken} 個來源連結失效（404／網域不存在），詳見 state/{day}-qa.json")


def append_block(path, alerts):
    try:
        text = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return False
    i = text.find(BLOCK)
    if i != -1:
        text = text[:i]
    text = text.rstrip() + "\n"
    if alerts:
        text += f"\n{BLOCK}\n" + "\n".join(f"{n}. {a}" for n, a in enumerate(alerts, 1)) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--append")
    a = ap.parse_args()
    day = date.fromisoformat(a.date)
    alerts, info = [], {}
    check_credits(day, alerts, info)
    check_sources(day, alerts, info)
    check_qa(day, alerts, info)
    jsave(os.path.join(HDIR, f"{day}.json"), {"date": day.isoformat(), "alerts": alerts, "info": info})

    c = info.get("credits")
    print(f"# 健康檢查 {day}")
    if isinstance(c, dict):
        print(f"- Firecrawl：剩 {c['remaining']}/{c['plan']} 點，{c['period_end']} 重置（{c['days_to_reset']} 天），"
              f"每天約 {c['daily_use']} 點（{c['daily_basis']}），撐到重置需約 {c['need_until_reset']} 點")
    else:
        print(f"- Firecrawl：{c}")
    s = info.get("sources")
    if isinstance(s, dict):
        print(f"- 來源：{s['total']} 個，今天失敗 {len(s['failed_today'])}，連續失敗 ≥{FAIL_STREAK_DAYS} 天 {len(s['streak_3d'])}")
    cd = info.get("candidates")
    if cd:
        med = cd["median_same_type"]
        basis = med if med is not None else "資料不足（%d 天）" % cd["basis_days"]
        print(f"- 窗內候選：今天 {cd['today']}（{cd['type']}），同類型中位數 {basis}")
    q = info.get("qa")
    if isinstance(q, dict):
        print(f"- 定稿檢查：錯誤 {q['errors']}、警告 {q['warnings']}、自動修正 {q['fixes']}")
    print(f"\n## {BLOCK} {len(alerts)}" if alerts else "\n✓ 沒有警報")
    for n, x in enumerate(alerts, 1):
        print(f"{n}. {x}")
    if a.append:
        ok = append_block(a.append, alerts)
        print(f"\n{'✓ 已附到' if ok else '✗ 找不到'} {a.append}" + ("" if alerts or not ok else "（沒有警報，未附加）"))


if __name__ == "__main__":
    sys.exit(main())
