#!/usr/bin/env python3
"""
Telegram 庫存查詢機器人（2026-10-04）—— 在接收日報的同一個 bot 裡打字問庫存。

架構：本機常駐長輪詢（getUpdates, timeout=30），由 launchd 保持執行（KeepAlive）。
      不用 GitHub Actions：它的 cron 實測會遲到 2–3 小時，不適合即時問答。
資料：只讀本機 state/inventory.json（每晚 02:30 的日報執行會更新它）；不呼叫其他 API、不花 Firecrawl 點數。
      「可用／待上線／過期」的判斷直接沿用 scripts/inventory.py，跟日報用的是同一套規則。

指令（有沒有斜線都可以，中英文都認）：
  庫存 ／ /stock     各分類數量＋標題
  slot ／ /slot      只看 Slot 明細（含待上線）
  說明 ／ /help      指令列表；認不出來的訊息也回這個

安全：
  - 只回應 TELEGRAM_ALLOWED_CHAT_ID（預設 606981537），其他人的訊息直接丟棄、不回覆
  - token 讀環境變數 TELEGRAM_BOT_TOKEN，不寫進 repo

用法：
  前景測試：TELEGRAM_BOT_TOKEN=… python3 scripts/telegram_bot.py
  只印回覆內容、不連 Telegram：python3 scripts/telegram_bot.py --print 庫存
常駐：docs/launchd/com.igaming.telegram-bot.plist.example
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inventory as INV  # noqa: E402  沿用保鮮期、去重、待上線的判斷

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFSET_FILE = os.path.join(ROOT, "state", "telegram-bot.offset")
ALLOWED = os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "606981537").strip()
CATS = {"cat2": "🕹️ 非 Slot", "cat3": "🤝 主流動態", "cat4": "🇵🇭 菲律賓", "cat5": "📊 市場數據"}
WEEK = "一二三四五六日"
WARN_DAYS = 2


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


# ─────────────────────────── 庫存整理 ───────────────────────────

def deadline(x, is_slot):
    """最後可用日（含當天）。與 inventory.expired() 同一套規則。"""
    first = INV.d(x["first_seen"])
    if is_slot:
        rel = x.get("release_date")
        if rel and INV.d(rel) > first:
            return max(first + timedelta(days=INV.SLOT_FRESH_DAYS), INV.d(rel) + timedelta(days=INV.SLOT_AFTER_RELEASE_DAYS))
        return first + timedelta(days=INV.SLOT_FRESH_DAYS)
    return first + timedelta(days=INV.OTHER_FRESH_DAYS)


_LAST_PULL = [0.0]


def sync_repo():
    """IGAMING_BOT_PULL=1（裝在沒有跑日報的電腦上）：回答前先 git pull，最多每 5 分鐘一次，讀到 GitHub 上最新的庫存與日報。"""
    if os.environ.get("IGAMING_BOT_PULL") != "1" or time.time() - _LAST_PULL[0] < 300:
        return
    import subprocess
    _LAST_PULL[0] = time.time()
    r = subprocess.run(["git", "-C", ROOT, "pull", "-q", "--ff-only"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log(f"⚠️ git pull 失敗：{(r.stderr or '').strip()[:120]}")


def snapshot(today=None):
    today = today or date.today()
    inv = INV.load()
    rk = INV.recent_keys(inv, today)
    horizon = today + timedelta(days=INV.PREVIEW_MAX_DAYS)
    slots = [x for x in inv["slots"] if not INV.expired(x, today, True) and not INV.matches(x, rk)
             and not INV.is_placeholder(x)]
    later = [x for x in slots if x.get("release_date") and INV.d(x["release_date"]) > horizon]
    ready = [x for x in slots if x not in later]
    key = lambda x: (-(x.get("b") or 0), x["first_seen"])
    ready.sort(key=key)
    later.sort(key=lambda x: x["release_date"])
    others = {c: sorted((x for x in inv["others"] if x.get("cat") == c and not INV.expired(x, today, False)
                         and not INV.matches(x, rk)), key=lambda x: x["first_seen"]) for c in CATS}
    mtime = datetime.fromtimestamp(os.path.getmtime(INV.INV))
    return today, mtime, ready, later, others


def left(x, today, is_slot):
    n = (deadline(x, is_slot) - today).days
    tag = "今天最後一天" if n == 0 else f"剩 {n} 天"
    return ("⚠️ " if n <= WARN_DAYS else "") + tag


def md(s):
    return f"{int(s[5:7])}/{int(s[8:10])}"


def header(today, mtime):
    return (f"📦 13' v 庫存（公司帳號・v6.x 規則）\n"
            f"資料時間：{mtime:%Y-%m-%d %H:%M}（每晚日報跑完更新）\n"
            f"查詢日：{today:%Y-%m-%d}（週{WEEK[today.weekday()]}）")


def slot_lines(today, ready, later):
    L = [f"🎰 Slot 可用 {len(ready)} 款（B 分高→首見早）"]
    for i, x in enumerate(ready, 1):
        L.append(f"{i}. [B{x.get('b', '?')}] {x['title']} — {x.get('gp', '?')}｜{md(x['first_seen'])} 首見｜{left(x, today, True)}")
    if not ready:
        L.append("（無）")
    if later:
        L.append("")
        L.append(f"⏳ 待上線 {len(later)} 款（上線日在 7 天以後，還不能上日報）")
        for x in later:
            L.append(f"・[B{x.get('b', '?')}] {x['title']} — {x.get('gp', '?')}｜{md(x['release_date'])} 上線")
    return L


def reply_stock():
    today, mtime, ready, later, others = snapshot()
    total = len(ready) + sum(len(v) for v in others.values())
    L = [header(today, mtime), "",
         f"合計可用 {total} 則：Slot {len(ready)}" + (f"（另有待上線 {len(later)}）" if later else "") + "・"
         + "・".join(f"{n.split(' ', 1)[1]} {len(others[c])}" for c, n in CATS.items()), ""]
    L += slot_lines(today, ready, later)
    for c, name in CATS.items():
        L.append("")
        L.append(f"{name} {len(others[c])} 則")
        for x in others[c]:
            L.append(f"・{x['title']}｜{md(x['first_seen'])} 首見｜{left(x, today, False)}")
        if not others[c]:
            L.append("（無）")
    return "\n".join(L)


def reply_slot():
    today, mtime, ready, later, _ = snapshot()
    return "\n".join([header(today, mtime), ""] + slot_lines(today, ready, later))


SITE = "https://igaming-pulse.github.io/igaming-daily"


def _read(path, default=None):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            return json.load(f) if path.endswith(".json") else f.read()
    except (OSError, ValueError):
        return default


def _runs(n=40):
    """state/run.log 裡最近幾次執行：[(開始時間, 結果, 細節)]。
    沒有 run.log（機器人裝在別台電腦）時，改用 git 紀錄裡的「daily: <DATE> report」判斷哪幾天成功。"""
    log_text = _read("state/run.log", "") or ""
    if not log_text:
        import subprocess
        out = subprocess.run(["git", "-C", ROOT, "log", "-40", "--format=%cd|%s", "--date=format:%Y-%m-%d %H:%M"],
                             capture_output=True, text=True).stdout
        rows = [[ln.split("|", 1)[0], "✅ 成功（日報已推上 GitHub）", ""] for ln in out.splitlines()
                if "|daily: " in ln]
        return list(reversed(rows))[-n:]
    out, cur = [], None
    for ln in log_text.splitlines():
        if "──────── 開始 ────────" in ln:
            cur = [ln[1:20], "執行中", ""]
            out.append(cur)
        elif cur and "✅ 本次執行成功" in ln:
            cur[1] = "✅ 成功"
        elif cur and "❌❌❌" in ln:
            cur[1] = "❌ 失敗"
        elif cur and "略過本次" in ln:
            cur[1] = "⏭ 略過（今天已跑過）"
        elif cur and "Claude 終端機版沒有登入" in ln:
            cur[1] = "❌ Claude 登入過期"
        elif cur and "claude 結束" in ln:
            cur[2] = ln.split("，")[-1] if "，" in ln else ""
    return out[-n:]


def reply_today():
    today = date.today().isoformat()
    md_text = _read(f"state/{today}-igaming-report.md")
    if not md_text:
        last = _runs(1)
        st = f"（最近一次執行：{last[0][0]} {last[0][1]}）" if last else ""
        return f"📰 今天（{today}）的 13' v 日報還沒產出 {st}\n要補跑請跟 Claude 說「補跑日報」。"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import report_lib as R
    rep = R.parse_md(md_text)
    names = {"cat1": "🎰 Slot", "cat2": "🕹️ 非 Slot", "cat3": "🤝 主流", "cat4": "🇵🇭 菲律賓", "cat5": "📊 市場數據"}
    secs = [s for s in rep["sections"] if s["items"]]
    L = [f"📰 今日日報 {today}（週{WEEK[date.today().weekday()]}）・13' v",
         "・".join(f"{names[s['cat']]} {len(s['items'])}" for s in secs), ""]
    for s in secs:
        L.append(names[s["cat"]])
        L += [f"{it['no']:02d} {it['title'][:60]}" for it in s["items"]]
        L.append("")
    L.append(f"🔗 {SITE}/reports/{today}-test.html")
    if os.path.exists(os.path.join(ROOT, "reports", f"{today}-special.html")):
        L.append(f"📦 今日特別版：{SITE}/reports/{today}-special.html")
    return "\n".join(L)


def reply_status():
    import subprocess
    L = ["🩺 系統狀態（13' v）", ""]
    runs = _runs(5)
    if runs:
        L.append("🕑 最近執行")
        L += [f"・{r[0]}　{r[1]}" + (f"（{r[2]}）" if r[2] else "") for r in runs[-4:]]
        L.append("")
    try:
        auth = subprocess.run([os.path.expanduser("~/.local/bin/claude"), "auth", "status"], capture_output=True,
                              text=True, timeout=20).stdout
        L.append("🔑 Claude 登入：" + ("✅ 正常" if '"loggedIn": true' in auth else "❌ 已過期（終端機輸入 claude → /login）"))
    except Exception:  # noqa: BLE001
        L.append("🔑 Claude 登入：無法確認")
    cr = _read("state/health/credits.json", {}) or {}
    if cr:
        d = sorted(cr)[-1]
        v = cr[d]
        rem = v.get("end", v.get("start")) if isinstance(v, dict) else v
        used = (v["start"] - v["end"]) if isinstance(v, dict) and "start" in v and "end" in v else None
        L.append(f"💳 Firecrawl：剩 {rem} 點（{d}）" + (f"，當天用 {used} 點" if used is not None else "") + "；每月 14 日重置")
    hl = _read(f"state/health/{date.today().isoformat()}.json") or _read(
        f"state/health/{(date.today() - timedelta(days=1)).isoformat()}.json")
    if hl and hl.get("alerts"):
        L.append("⚙️ 系統警報：")
        L += [f"・{a[:80]}" for a in hl["alerts"]]
    else:
        L.append("⚙️ 系統警報：無")
    L.append("")
    L.append("⏰ 下次排程：每天 02:30（週一、週四日報成功後會檢查特別版）")
    return "\n".join(L)


def reply_special():
    import glob
    files = sorted(glob.glob(os.path.join(ROOT, "state", "*-special-igaming-report.md")))
    today, _, ready, later, _ = snapshot()
    nxt = next(today + timedelta(days=i) for i in range(1, 8) if (today + timedelta(days=i)).weekday() in (0, 3))
    L = ["📦 庫存釋放特別版", ""]
    if files:
        d = os.path.basename(files[-1])[:10]
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import report_lib as R
        rep = R.parse_md(open(files[-1], encoding="utf-8").read())
        n = sum(len(s["items"]) for s in rep["sections"])
        L += [f"最近一期：{d}，釋放 {n} 款", f"🔗 {SITE}/reports/{d}-special.html", ""]
    L.append(f"下一次檢查：{nxt.month}/{nxt.day}（週{WEEK[nxt.weekday()]}）日報成功後")
    L.append(f"目前 Slot 可用庫存 {len(ready)} 款（門檻 ≥5）→ " + ("會發" if len(ready) >= 5 else "不到門檻，不會發"))
    return "\n".join(L)


def reply_week():
    """本週（週日起算）每天的收錄概況。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import report_lib as R
    today = date.today()
    start = today - timedelta(days=(today.weekday() + 1) % 7)
    L = [f"📅 本週概況（{start.month}/{start.day} 週日起）", ""]
    for i in range((today - start).days + 1):
        d = start + timedelta(days=i)
        md_text = _read(f"state/{d.isoformat()}-igaming-report.md")
        if not md_text:
            L.append(f"{d.month}/{d.day} 週{WEEK[d.weekday()]}　—")
            continue
        rep = R.parse_md(md_text)
        c = {s["cat"]: len(s["items"]) for s in rep["sections"]}
        sp = "　📦特別版" if os.path.exists(os.path.join(ROOT, "reports", f"{d.isoformat()}-special.html")) else ""
        L.append(f"{d.month}/{d.day} 週{WEEK[d.weekday()]}　共 {sum(c.values())} 則（Slot {c.get('cat1', 0)}）{sp}")
    return "\n".join(L)


COMMANDS = [("today", "今天的日報：各區標題與連結"), ("stock", "庫存：各分類數量與標題"),
            ("slot", "Slot 庫存明細（含待上線）"), ("special", "特別版：最近一期與下次檢查"),
            ("week", "本週每天收錄概況"), ("status", "系統狀態：最近執行、登入、額度、警報"),
            ("help", "指令說明")]

HELP = ("🤖 13' v 日報機器人（有沒有斜線都可以）\n"
        "・今天 或 /today — 今天的日報：各區標題與連結\n"
        "・庫存 或 /stock — 各分類庫存數量與標題\n"
        "・slot 或 /slot — Slot 庫存明細（含待上線）\n"
        "・特別版 或 /special — 最近一期與下次檢查\n"
        "・本週 或 /week — 本週每天收錄概況\n"
        "・狀態 或 /status — 最近執行、Claude 登入、Firecrawl 額度、系統警報\n"
        "・說明 或 /help — 這份說明\n"
        "資料來自公司 Mac，每晚日報跑完更新；Mac 睡眠時機器人不會回覆，醒來後會補回。")


def route(text):
    t = (text or "").strip().lower()
    t = t.split("@")[0] if t.startswith("/") else t      # /stock@MyBot → /stock
    t = t.lstrip("/").strip()
    try:
        if t in ("slot", "slots", "slot 庫存", "slot庫存", "老虎機", "老虎機庫存"):
            return reply_slot()
        if t in ("today", "今天", "今日", "日報", "今天日報", "今日日報"):
            return reply_today()
        if t in ("special", "特別版", "釋放"):
            return reply_special()
        if t in ("week", "本週", "這週", "週報"):
            return reply_week()
        if t in ("status", "狀態", "系統", "健康", "health"):
            return reply_status()
        if t in ("stock", "inventory", "庫存", "库存", "查庫存", "剩多少", "庫存多少", "剩多少庫存") or "庫存" in t or "库存" in t:
            return reply_stock()
    except Exception as e:  # noqa: BLE001  資料檔讀到一半等狀況，回一句而不是讓機器人掛掉
        return f"⚠️ 查詢時出錯（{type(e).__name__}），請稍後再試"
    return HELP


# ─────────────────────────── Telegram ───────────────────────────

def api(token, method, params, timeout=40):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=timeout) as r:
        return json.load(r)


def send(token, chat_id, text):
    for i in range(0, len(text), 4000):           # Telegram 單則上限 4096 字
        api(token, "sendMessage", {"chat_id": chat_id, "text": text[i:i + 4000], "disable_web_page_preview": "true"})


def load_offset():
    try:
        return int(open(OFFSET_FILE).read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_offset(n):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(n))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--print":
        print(route(" ".join(sys.argv[2:]) or "庫存"))
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("✗ 沒有 TELEGRAM_BOT_TOKEN 環境變數")
    offset = load_offset()
    log(f"啟動：只回應 chat_id {ALLOWED}，offset {offset}")
    try:   # 註冊指令選單：在 Telegram 打「/」就會列出可用指令
        api(token, "setMyCommands", {"commands": json.dumps([{"command": c, "description": d} for c, d in COMMANDS],
                                                            ensure_ascii=False)})
        log("已註冊指令選單")
    except Exception as e:  # noqa: BLE001
        log(f"⚠️ 註冊指令選單失敗：{type(e).__name__}")
    backoff = 5
    while True:
        try:
            res = api(token, "getUpdates", {"timeout": 30, "offset": offset, "allowed_updates": '["message"]'})
            backoff = 5
        except urllib.error.HTTPError as e:
            # 409：這個 bot 設了 webhook，或另有程式也在 getUpdates —— 記下來、等一下再試，不要自己刪 webhook
            log(f"⚠️ getUpdates HTTP {e.code}{'（webhook 或另一個輪詢程式衝突）' if e.code == 409 else ''}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)
            continue
        except Exception as e:  # noqa: BLE001  斷網、Mac 剛醒來等
            log(f"⚠️ 連線失敗：{type(e).__name__}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)
            continue
        for u in res.get("result", []):
            offset = u["update_id"] + 1
            save_offset(offset)                    # 先記 offset：就算回覆失敗也不會一直重複處理同一則
            m = u.get("message") or {}
            chat = str((m.get("chat") or {}).get("id", ""))
            if chat != ALLOWED:
                continue                           # 非白名單：直接丟棄，不回覆、不記內容
            text = m.get("text", "")
            sync_repo()
            try:
                send(token, chat, route(text))
                log(f"回覆：{text[:20]!r}")
            except Exception as e:  # noqa: BLE001
                log(f"⚠️ 回覆失敗：{type(e).__name__}")


if __name__ == "__main__":
    main()
