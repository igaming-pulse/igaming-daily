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


HELP = ("🤖 13' v 庫存查詢\n"
        "・庫存 或 /stock — 各分類數量與標題\n"
        "・slot 或 /slot — Slot 明細（含待上線）\n"
        "・說明 或 /help — 這份說明\n"
        "資料來自公司 Mac 上的 state/inventory.json，每晚日報跑完更新；Mac 睡眠時機器人不會回覆。")


def route(text):
    t = (text or "").strip().lower()
    t = t.split("@")[0] if t.startswith("/") else t      # /stock@MyBot → /stock
    t = t.lstrip("/").strip()
    if t in ("slot", "slots", "slot 庫存", "slot庫存", "老虎機", "老虎機庫存"):
        return reply_slot()
    if t in ("stock", "inventory", "庫存", "库存", "查庫存", "剩多少", "庫存多少", "剩多少庫存") or "庫存" in t or "库存" in t:
        return reply_stock()
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
            try:
                send(token, chat, route(text))
                log(f"回覆：{text[:20]!r}")
            except Exception as e:  # noqa: BLE001
                log(f"⚠️ 回覆失敗：{type(e).__name__}")


if __name__ == "__main__":
    main()
