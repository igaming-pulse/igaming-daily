#!/usr/bin/env bash
# 晚到就立刻推播（2026-10-05，參考 15' v「流程拖過 06:30 就立刻補發」的做法）
#
# 為什麼：Telegram 由 GitHub Actions 的 06:40 排程發送，若那時日報還沒產出，它只會送「⚠️ 未產出」警報，
#         之後日報補出來也不會再送（10/1 發生過）。
# 做什麼：run_daily.sh 成功後呼叫。
#   - 現在（台北）早於 06:30 → 什麼都不做，交給 06:40 排程（避免半夜吵人）
#   - 已過 06:30 → 等網站上的 <DATE>-test.html 回 200（最多 5 分鐘），再 dispatch telegram-test-0640.yml
#   - workflow 那邊：今天已有成功的手動發送，排程那次就跳過，不會重複
# 憑證：用 macOS 鑰匙圈裡的 git 憑證（git credential fill），不寫進任何檔案。
set -uo pipefail

REPO="${IGAMING_REPO:-$HOME/igaming-daily}"
DATE="${1:-$(TZ=Asia/Taipei date +%F)}"
CUTOFF="${IGAMING_TELEGRAM_CUTOFF:-0630}"
OWNER_REPO="igaming-pulse/igaming-daily"
URL="https://igaming-pulse.github.io/igaming-daily/reports/${DATE}-test.html"

say() { echo "  [telegram] $*"; }

NOW=$(TZ=Asia/Taipei date +%H%M)
if [ "$DATE" != "$(TZ=Asia/Taipei date +%F)" ]; then
  say "日期 ${DATE} 不是今天，不自動推播（補發舊日期請手動 dispatch）"
  exit 0
fi
if [ "$NOW" -lt "$CUTOFF" ]; then
  say "現在 ${NOW:0:2}:${NOW:2:2}，早於 ${CUTOFF:0:2}:${CUTOFF:2:2}，交給 06:40 排程推播"
  exit 0
fi

ok=""
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "${URL}?t=$(date +%s)")
  [ "$code" = "200" ] && { ok=1; break; }
  sleep 10
done
[ -n "$ok" ] || { say "✗ 網站頁面 5 分鐘內沒有上線（${URL}），不推播，留給排程或手動補發"; exit 1; }

TOKEN=$(cd "$REPO" && printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | sed -n 's/^password=//p')
[ -n "$TOKEN" ] || { say "✗ 取不到 GitHub 憑證，無法觸發推播"; exit 1; }

code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${OWNER_REPO}/actions/workflows/telegram-test-0640.yml/dispatches" \
  -d "{\"ref\":\"main\",\"inputs\":{\"dry_run\":\"false\",\"url_suffix\":\"-test\",\"report_date\":\"${DATE}\"}}")
if [ "$code" = "204" ]; then
  say "✓ 已過 ${CUTOFF:0:2}:${CUTOFF:2:2}，立刻觸發推播（${DATE}）"
  exit 0
fi
say "✗ 觸發推播失敗（HTTP ${code}）"
exit 1
