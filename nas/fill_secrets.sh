#!/usr/bin/env bash
# 在 Mac 上執行：把 Mac 現有的憑證填進 NAS 的 secrets.env，畫面上不會顯示任何值。
#   bash ~/igaming-daily/nas/fill_secrets.sh
# 來源：Telegram ← bot 的 launchd plist；Firecrawl ← ~/.zshrc；GitHub ← 鑰匙圈裡的 git 憑證；
#       Claude ← 剪貼簿（先執行 claude setup-token，把印出的 token 那幾行 ⌘C，再跑本腳本）。
set -uo pipefail
OUT="${1:-/Volumes/docker/igaming-daily/secrets.env}"
[ -d "$(dirname "$OUT")" ] || { echo "✗ 找不到 $(dirname "$OUT")，先在 Finder 掛上 NAS 的 docker 資料夾"; exit 1; }

TG=$(/usr/libexec/PlistBuddy -c "Print :EnvironmentVariables:TELEGRAM_BOT_TOKEN" \
     ~/Library/LaunchAgents/com.igaming.telegram-bot.plist 2>/dev/null)
FC=$(zsh -ic 'printf %s "$FIRECRAWL_API_KEY"' 2>/dev/null | tr -d '\r\n"'"'")
GH=$(cd ~/igaming-daily && printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | sed -n 's/^password=//p')

# Claude token：從剪貼簿讀，不用貼進終端機（2026-10-15）
# setup-token 印出的 token 會折成好幾行，⌘C 會連換行一起複製，直接貼上會斷掉。
# 所以改成：把 token 那幾行（多選前後幾行也沒關係）⌘C → 這裡從剪貼簿找出 sk-ant-oat 開頭的那段，自動把折行拼回去。
CL=$(pbpaste | python3 -c '
import re, sys
t = sys.stdin.read().replace("\r", "")
m = re.search(r"sk-ant-oat[A-Za-z0-9_-]+(?:\n[ \t]*[A-Za-z0-9_-]+(?=[ \t]*(?:\n|$)))*", t)
print(re.sub(r"\s+", "", m.group(0)) if m else "")
')
[ -n "$CL" ] && printf '' | pbcopy   # 用完清空剪貼簿

ok() { [ -n "$2" ] && echo "  ✓ $1（${#2} 字元）" || echo "  ✗ $1 沒有取得，請手動填"; }
ok "TELEGRAM_BOT_TOKEN" "$TG"; ok "FIRECRAWL_API_KEY" "$FC"; ok "GITHUB_TOKEN" "$GH"; ok "CLAUDE_CODE_OAUTH_TOKEN" "$CL"
case "$CL" in sk-ant-oat*|'') ;; *) echo "  ⚠️ Claude token 開頭不是 sk-ant-oat，請確認貼的是 setup-token 的輸出" ;; esac
[ -n "$CL" ] && [ "${#CL}" -ne 108 ] && echo "  ⚠️ Claude token 有 ${#CL} 字元，正常是 108 —— 請重新複製 token 那幾行再跑一次"
[ -n "$CL" ] || { echo "  ✗ 剪貼簿裡找不到 sk-ant-oat 開頭的 token：請先把 claude setup-token 印出的 token 那幾行 ⌘C，再跑一次"; exit 1; }

umask 077
cat > "$OUT" <<EOF
TELEGRAM_BOT_TOKEN=$TG
TELEGRAM_ALLOWED_CHAT_ID=606981537
GITHUB_TOKEN=$GH
CLAUDE_CODE_OAUTH_TOKEN=$CL
FIRECRAWL_API_KEY=$FC
EOF
echo "已寫入 $OUT"
