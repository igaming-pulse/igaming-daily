#!/usr/bin/env python3
"""
寄出當日 iGaming 日報 Email（由 GitHub Actions 在 push 後觸發，零 token）。

不使用任何第三方 Action —— 只用 Python 標準函式庫的 smtplib，
這樣換 GitHub 帳號、換 CI 平台時都能直接照搬。

資料來源：state/pending_telegram.txt 的前兩行
  第 1 行：🎰 iGaming 市場日報 YYYY-MM-DD（週X）
  第 2 行：🎰 Slot 5 ・ 🕹️ 非 Slot 3 ・ …
⚠️ 第 3 行起（含 📝 品質備註）一律不進 Email —— 這是硬規則。

需要的 Secrets：SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / MAIL_TO
缺任何一個就安靜跳過（exit 0），不讓 workflow 變紅。
"""
import os
import re
import smtplib
import sys
from email.message import EmailMessage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING = os.path.join(ROOT, "state", "pending_telegram.txt")
INDEX_URL = "https://igaming-pulse.github.io/igaming-daily/"
REPORT_URL = INDEX_URL + "reports/{date}.html"

REQUIRED = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_TO"]


def main():
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        print(f"✗ 缺少 Secrets：{', '.join(missing)} —— 略過寄信（不視為失敗）")
        return 0

    if not os.path.exists(PENDING):
        print(f"✗ 找不到 {PENDING} —— 略過寄信")
        return 0

    with open(PENDING, encoding="utf-8") as f:
        lines = [ln.rstrip() for ln in f.readlines()]
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        print("✗ pending 檔是空的 —— 略過寄信")
        return 0

    title = lines[0]
    counts = lines[1] if len(lines) > 1 else ""

    m = re.search(r"(\d{4}-\d{2}-\d{2})", title)
    if not m:
        print(f"✗ 第一行找不到日期：{title} —— 略過寄信")
        return 0
    date = m.group(1)
    wd = re.search(r"（(週.)）", title)
    subject = f"iGaming 市場日報 {date}" + (f"（{wd.group(1)}）" if wd else "")
    report_url = REPORT_URL.format(date=date)

    # ---- 純文字備援 ----
    text = "\n".join([
        f"iGaming 市場日報 {date}",
        "",
        counts,
        "",
        f"完整日報：{report_url}",
        f"存檔首頁：{INDEX_URL}",
    ])

    # ---- HTML（全 inline style，Gmail 會濾掉 <head>/<style>）----
    html = f"""<div style="margin:0;padding:24px 12px;background:#F5F7FA;font-family:-apple-system,'PingFang TC','Noto Sans TC','Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #E7EBF0;border-radius:14px;padding:28px 26px;">
    <div style="font-size:24px;font-weight:800;color:#1A2230;letter-spacing:-.4px;">🎰 iGaming 市場日報</div>
    <div style="font-size:14px;color:#5B6675;margin-top:6px;">{date}{'（' + wd.group(1) + '）' if wd else ''} · 台北時間</div>
    <div style="height:1px;background:#E7EBF0;margin:20px 0;"></div>
    <div style="font-size:14px;color:#1A2230;line-height:1.9;">{counts}</div>
    <div style="margin:26px 0 8px;">
      <a href="{report_url}" style="display:inline-block;background:#1D9E75;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;padding:13px 26px;border-radius:10px;">開啟今日完整日報 →</a>
    </div>
    <div style="font-size:12px;color:#5B6675;margin-top:18px;">
      日報存檔首頁：<a href="{INDEX_URL}" style="color:#185FA5;">{INDEX_URL}</a>
    </div>
  </div>
  <div style="max-width:600px;margin:14px auto 0;font-size:11.5px;color:#8A93A0;text-align:center;line-height:1.7;">
    每則皆附真實可點擊原文連結 · 多來源交叉查證
  </div>
</div>"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = os.environ["MAIL_TO"]
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as s:
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls()
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
                s.send_message(msg)
    except Exception as e:
        print(f"✗ 寄信失敗：{type(e).__name__}: {e}")
        return 1

    print(f"✓ Email 已寄出：{subject} → {os.environ['MAIL_TO']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
