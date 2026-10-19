#!/usr/bin/env bash
# 在 Mac 上執行：把寄 Email 用的 SMTP 設定加進 NAS 的 secrets.env（密碼輸入時不顯示，也不會印出）
#   bash ~/igaming-daily/nas/add_smtp.sh
# Gmail 寄件：要先在 Google 帳戶開兩步驟驗證，再到 https://myaccount.google.com/apppasswords 產生「應用程式密碼」（16 碼）
set -uo pipefail
OUT="${1:-/Volumes/docker/igaming-daily/secrets.env}"
[ -f "$OUT" ] || { echo "✗ 找不到 $OUT，先在 Finder 掛上 NAS 的 docker 資料夾"; exit 1; }

read -r -p "寄件 Gmail（例如 xxx@gmail.com）：" SMTP_USER
read -r -p "收件人（多位用逗號分隔，直接 Enter＝寄給自己）：" MAIL_TO
[ -n "$MAIL_TO" ] || MAIL_TO="$SMTP_USER"
echo "貼上 Gmail 應用程式密碼（16 碼，空格會自動去掉，輸入時不會顯示），按 Enter："
IFS= read -rs SMTP_PASS; echo
SMTP_PASS=$(printf '%s' "$SMTP_PASS" | tr -d '[:space:]')
[ "${#SMTP_PASS}" -eq 16 ] || echo "  ⚠️ 密碼有 ${#SMTP_PASS} 字元，Gmail 應用程式密碼應該是 16 碼，請確認"

TMP=$(mktemp); umask 077
grep -vE '^(SMTP_HOST|SMTP_PORT|SMTP_USER|SMTP_PASS|MAIL_TO)=' "$OUT" > "$TMP"
cat >> "$TMP" <<EOT
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=$SMTP_USER
SMTP_PASS=$SMTP_PASS
MAIL_TO=$MAIL_TO
EOT
cat "$TMP" > "$OUT" && rm -f "$TMP"
echo "  ✓ 寄件：$SMTP_USER → 收件：$MAIL_TO（密碼 ${#SMTP_PASS} 字元）"
echo "已寫入 $OUT。接著到 Container Manager：專案 igaming-daily → 停止 → 操作 → 清除 → 操作 → 建立"
