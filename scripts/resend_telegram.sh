#!/usr/bin/env bash
# 補發某一天的 Telegram 日報推播（2026-10-18）
#   bash scripts/resend_telegram.sh 2026-10-17
#
# state/pending_telegram.txt 每天會被新的日報覆蓋，所以補發舊日期時：
#   1. 從那天的「daily: <DATE> report」commit 取出當時的預存訊息
#   2. 存成 state/pending_telegram_resend_<DATE>.txt，commit 並推上 test-publish
#   3. 手動觸發 telegram-test-0640.yml（report_date＋pending_path，訊息第一行加【補發】）
# 憑證：鑰匙圈裡的 git 憑證（git credential fill），不寫進任何檔案。
set -uo pipefail
REPO="${IGAMING_REPO:-$HOME/igaming-daily}"
DATE="${1:?用法：bash scripts/resend_telegram.sh YYYY-MM-DD}"
cd "$REPO" || exit 1
say() { echo "  [補發] $*"; }

git pull -q --ff-only || say "⚠️ git pull 失敗，用本地版本繼續"
C=$(git log --format=%h -1 --grep="^daily: ${DATE} report$")
[ -n "$C" ] || { say "✗ 找不到 daily: ${DATE} report 的 commit"; exit 1; }
F="state/pending_telegram_resend_${DATE}.txt"
git show "${C}:state/pending_telegram.txt" > "$F" 2>/dev/null || { say "✗ ${C} 裡沒有 state/pending_telegram.txt"; exit 1; }
head -1 "$F" | grep -q "$DATE" || { say "✗ ${C} 的預存訊息不是 ${DATE} 的：$(head -1 "$F")"; exit 1; }
say "預存訊息取自 ${C}：$(head -1 "$F")"

git add "$F" && git commit -q -m "resend: ${DATE} Telegram 補發" -- "$F" >/dev/null 2>&1
git push -q || { git pull -q --rebase && git push -q; } || { say "✗ 推不上 GitHub"; exit 1; }

TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | sed -n 's/^password=//p')
[ -n "$TOKEN" ] || { say "✗ 取不到 GitHub 憑證"; exit 1; }
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/igaming-pulse/igaming-daily/actions/workflows/telegram-test-0640.yml/dispatches" \
  -d "{\"ref\":\"main\",\"inputs\":{\"dry_run\":\"false\",\"url_suffix\":\"-test\",\"report_date\":\"${DATE}\",\"pending_path\":\"${F}\",\"msg_prefix\":\"🔁【補發】${DATE}\"}}")
[ "$code" = "204" ] && say "✓ 已觸發補發（${DATE}），約 1 分鐘內會收到" || { say "✗ 觸發失敗（HTTP ${code}）"; exit 1; }
