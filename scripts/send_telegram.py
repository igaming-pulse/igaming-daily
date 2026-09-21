#!/usr/bin/env python3
"""
台北 06:30 由 GitHub Actions 觸發：發送當日 Telegram 推播，並兼任守門員。

守門員邏輯（同時攔「沒跑」與「跑了但沒推成功」）：
    repo 裡有今天的 reports/<DATE>.html 且 pending 檔指向今天
      → 正常推播
    否則
      → 推「⚠️ 今日日報未產出」警告

設計取捨：用「pending 檔裡的日期是不是今天」判斷，所以**不需要把已送的檔案寫回 repo**。
重跑同一天不會重複送嗎？會 —— 但排程一天只跑一次，手動重跑是刻意行為，這樣反而方便補送。

正式設計是**一則訊息**（摘要＋文末品質備註＋一顆 inline 按鈕）。
截圖看到的兩則是 2026-09-14 手動補跑的一次性產物，不是常態。

需要的 Secrets：TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
缺任何一個就安靜跳過（exit 0）。
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING = os.path.join(ROOT, "state", "pending_telegram.txt")
PENDING_URL = os.path.join(ROOT, "state", "pending_telegram_url.txt")
INDEX_URL = "https://igaming-pulse.github.io/igaming-daily/"
TAIPEI = timezone(timedelta(hours=8))
MAX_LEN = 4000          # Telegram 單則上限 4096，保守截斷

# 併行期用：在訊息最前面加一行標記，讓你分得出這則是哪一台機器發的。
# 由 workflow 的 MSG_PREFIX 環境變數帶入，沒設就是空字串（＝正式版行為不變）。
MSG_PREFIX = os.environ.get("MSG_PREFIX", "").strip()

# 併行期用：按鈕要指向網站上的哪一份。空＝正式版 <date>.html；"-test"＝併行版 <date>-test.html。
REPORT_URL_SUFFIX = os.environ.get("REPORT_URL_SUFFIX", "").strip()


def today_taipei():
    return datetime.now(TAIPEI).strftime("%Y-%m-%d")


def send(token, chat_id, text, button_url=None, dry=False):
    if MSG_PREFIX:
        text = f"{MSG_PREFIX}\n{text}"
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN - 20].rstrip() + "\n…（更多見完整日報）"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False,
    }
    if button_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": "📖 開啟完整日報 →", "url": button_url}]]
        }

    if dry:
        print("--- DRY RUN，實際會送出以下內容 ---")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return True

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"✗ Telegram HTTP {e.code}：{e.read().decode('utf-8', 'replace')[:400]}")
        return False
    except Exception as e:
        print(f"✗ Telegram 發送失敗：{type(e).__name__}: {e}")
        return False

    if not body.get("ok"):
        print(f"✗ Telegram 回傳 not ok：{body}")
        return False
    return True


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    dry = str(os.environ.get("DRY_RUN", "")).lower() == "true"

    if not token or not chat_id:
        print("✗ 缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID —— 略過（不視為失敗）")
        return 0

    date = today_taipei()
    report_path = os.path.join(ROOT, "reports", f"{date}.html")
    report_url = INDEX_URL + f"reports/{date}.html"

    has_report = os.path.exists(report_path)
    pending_text = ""
    pending_is_today = False

    if os.path.exists(PENDING):
        with open(PENDING, encoding="utf-8") as f:
            pending_text = f.read().strip()
        # 用 pending 檔第一行的日期判斷是不是今天的
        m = re.search(r"(\d{4}-\d{2}-\d{2})", pending_text.split("\n")[0] if pending_text else "")
        pending_is_today = bool(m and m.group(1) == date)

    # ---------- 守門員：沒有今天的報告 ----------
    if not has_report or not pending_is_today:
        reasons = []
        if not has_report:
            reasons.append(f"repo 裡沒有 reports/{date}.html")
        if not pending_is_today:
            reasons.append("待送訊息不是今天的（或不存在）")
        warn = (
            f"⚠️ iGaming 日報未產出 {date}\n\n"
            + "\n".join(f"・{r}" for r in reasons)
            + "\n\n02:30 的排程可能沒跑、跑失敗、或沒推上來。\n"
            f"存檔首頁：{INDEX_URL}"
        )
        print("守門員觸發：", "; ".join(reasons))
        ok = send(token, chat_id, warn, None, dry)
        return 0 if ok else 1

    # ---------- 正常推播 ----------
    text = pending_text
    if INDEX_URL not in text:
        text += f"\n\n📚 日報存檔首頁：{INDEX_URL}"

    url = report_url
    if REPORT_URL_SUFFIX:
        url = INDEX_URL + f"reports/{date}{REPORT_URL_SUFFIX}.html"
    elif os.path.exists(PENDING_URL):
        with open(PENDING_URL, encoding="utf-8") as f:
            u = f.read().strip()
            if u.startswith("http"):
                url = u

    ok = send(token, chat_id, text, url, dry)
    if ok:
        print(f"✓ Telegram 已發送 {date}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
