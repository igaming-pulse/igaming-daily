#!/usr/bin/env bash
# 即時警報（2026-10-11）：日報一失敗、或開跑前檢查不過，就馬上發 Telegram，不等早上的推播排程。
#
#   bash scripts/alert_telegram.sh "<標題>" "<原因／建議動作（可多行）>"
#
# 做法：把警報文字寫成 state/pending_alert_<DATE>.txt → 只 commit 這個檔並推上 test-publish
#       → dispatch telegram-test-0640.yml（alert=true，不經守門員、不算「今天的日報推播」）。
# 憑證用 macOS 鑰匙圈裡的 git 憑證，不寫進任何檔案。失敗不影響呼叫端（一律 exit 0）。
set -uo pipefail

REPO="${IGAMING_REPO:-$HOME/igaming-daily}"
cd "$REPO" || exit 0
DATE=$(TZ=Asia/Taipei date +%F)
NOW=$(TZ=Asia/Taipei date '+%H:%M')
TITLE="${1:-日報異常}"
BODY="${2:-}"
F="state/pending_alert_${DATE}.txt"

printf '🚨 iGaming 日報即時警報 %s %s（13'"'"' v）\n%s\n\n%s\n\n詳細紀錄：~/igaming-daily/state/run.log\n' "$DATE" "$NOW" "$TITLE" "$BODY" > "$F"

git add "$F" >/dev/null 2>&1
git commit -q -m "alert: ${DATE} ${TITLE}" -- "$F" >/dev/null 2>&1
git push -q >/dev/null 2>&1 || { git pull -q --rebase >/dev/null 2>&1 && git push -q >/dev/null 2>&1; } \
  || { echo "  [alert] ✗ 警報內容推不上 GitHub，改由早上的守門員通知"; exit 0; }

TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | sed -n 's/^password=//p')
[ -n "$TOKEN" ] || { echo "  [alert] ✗ 取不到 GitHub 憑證"; exit 0; }
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/igaming-pulse/igaming-daily/actions/workflows/telegram-test-0640.yml/dispatches" \
  -d "{\"ref\":\"main\",\"inputs\":{\"dry_run\":\"false\",\"alert\":\"true\",\"report_date\":\"${DATE}\",\"pending_path\":\"${F}\",\"msg_prefix\":\" \"}}")
[ "$code" = "204" ] && echo "  [alert] ✓ 已發即時警報：${TITLE}" || echo "  [alert] ✗ 即時警報觸發失敗（HTTP ${code}）"
exit 0
