#!/usr/bin/env bash
# 在 Mac 上執行：把寄 Email 用的 SMTP 設定加進 NAS 的 secrets.env（密碼從剪貼簿讀，畫面不顯示、也不印出）
#   bash ~/igaming-daily/nas/add_smtp.sh
# Gmail 寄件：要先在 Google 帳戶開兩步驟驗證，再到 https://myaccount.google.com/apppasswords 產生「應用程式密碼」（16 個字母）
#
# 2026-10-19 改版：密碼改成「先 ⌘C、再按 Enter」從剪貼簿讀 —— 手動貼進隱藏輸入容易貼錯，
# 也避免使用者把密碼直接打在終端機的指令列上（會留在 shell 歷史紀錄）。
# 變數一律寫成 ${VAR}：$VAR 後面緊接全形字（例如「（」）時，bash 會把它當成變數名稱的一部分而報錯。
set -uo pipefail
OUT="${1:-/Volumes/docker/igaming-daily/secrets.env}"
[ -f "$OUT" ] || { echo "✗ 找不到 $OUT，先在 Finder 掛上 NAS 的 docker 資料夾"; exit 1; }

OLD_USER=$(sed -n 's/^SMTP_USER=//p' "$OUT" | head -1)
OLD_TO=$(sed -n 's/^MAIL_TO=//p' "$OUT" | head -1)

read -r -p "寄件 Gmail${OLD_USER:+（直接 Enter＝沿用 ${OLD_USER}）}：" SMTP_USER
SMTP_USER="${SMTP_USER:-${OLD_USER}}"
[ -n "${SMTP_USER}" ] || { echo "✗ 沒有寄件信箱"; exit 1; }
read -r -p "收件人（多位用逗號分隔；直接 Enter＝${OLD_TO:-寄給自己}）：" MAIL_TO
MAIL_TO="${MAIL_TO:-${OLD_TO:-${SMTP_USER}}}"

echo
echo "════════════════════════════════════════════════════"
echo " 到 Google 應用程式密碼的黃色框，把那 16 個字母選起來按 ⌘C"
echo " （不用貼到這裡，也不要打在終端機上）"
echo " 複製好之後，回到這裡按 Enter"
echo "════════════════════════════════════════════════════"
read -r _
SMTP_PASS=$(pbpaste | python3 -c '
import re, sys
t = sys.stdin.read()
m = re.search(r"\b([a-z]{4})\s?([a-z]{4})\s?([a-z]{4})\s?([a-z]{4})\b", t)
print("".join(m.groups()) if m else "")
')
if [ "${#SMTP_PASS}" -ne 16 ]; then
  echo "  ✗ 剪貼簿裡找不到 16 個小寫字母的應用程式密碼（4 組 × 4 個字母）。請重新複製再跑一次，secrets.env 沒有改動。"
  exit 1
fi
printf '' | pbcopy   # 用完清空剪貼簿

TMP=$(mktemp); umask 077
grep -vE '^(SMTP_HOST|SMTP_PORT|SMTP_USER|SMTP_PASS|MAIL_TO)=' "$OUT" > "$TMP"
{
  echo "SMTP_HOST=smtp.gmail.com"
  echo "SMTP_PORT=465"
  echo "SMTP_USER=${SMTP_USER}"
  echo "SMTP_PASS=${SMTP_PASS}"
  echo "MAIL_TO=${MAIL_TO}"
} >> "$TMP"
cat "$TMP" > "$OUT" && rm -f "$TMP"
echo "  ✓ 寄件：${SMTP_USER} → 收件：${MAIL_TO}（密碼 ${#SMTP_PASS} 字元）"
echo "已寫入 ${OUT}。接著到 Container Manager：專案 igaming-daily → 停止 → 操作 → 清除 → 操作 → 建立"
