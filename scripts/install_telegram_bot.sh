#!/bin/bash
# Telegram 機器人本機常駐安裝程式（2026-10-11）
#   bash ~/igaming-daily/scripts/install_telegram_bot.sh
# 會：詢問 bot token（不顯示、不留在指令紀錄）→ 向 Telegram 驗證 token → 產生 launchd 設定（權限 600）→ 啟動 → 確認在跑
# token 只寫進 ~/Library/LaunchAgents/com.igaming.telegram-bot.plist，不進 repo。
set -u
REPO="$HOME/igaming-daily"
TPL="$REPO/docs/launchd/com.igaming.telegram-bot.plist.example"
DST="$HOME/Library/LaunchAgents/com.igaming.telegram-bot.plist"

echo "== iGaming 日報 Telegram 機器人：本機常駐安裝 =="
[ -f "$TPL" ] || { echo "✗ 找不到範本 $TPL（repo 不在 ~/igaming-daily？）"; exit 1; }
mkdir -p "$HOME/Library/LaunchAgents"

printf "請貼上 Bot token（畫面不會顯示），貼完按 Enter： "
IFS= read -rs TOKEN; echo
TOKEN=$(printf '%s' "$TOKEN" | tr -d '[:space:]')
[ -n "$TOKEN" ] || { echo "✗ 沒有收到 token"; exit 1; }
case "$TOKEN" in *:*) ;; *) echo "✗ 格式不對：token 應該長得像「數字:一串英數字」（例如 1234567890:AAH...），請到 @BotFather → /mybots → 選 bot → API Token 複製完整一串"; exit 1 ;; esac

echo "→ 向 Telegram 驗證 token…"
ME=$(curl -s -m 20 "https://api.telegram.org/bot${TOKEN}/getMe")
case "$ME" in
  *'"ok":true'*) echo "  ✓ token 正確：$(printf '%s' "$ME" | sed -n 's/.*"username":"\([^"]*\)".*/@\1/p')" ;;
  *) echo "  ✗ Telegram 說這個 token 無效（回覆：${ME:0:120}）。請重新到 @BotFather 複製完整 token 再試一次"; exit 1 ;;
esac

WH=$(curl -s -m 20 "https://api.telegram.org/bot${TOKEN}/getWebhookInfo")
case "$WH" in *'"url":"http'*) echo "  ⚠️ 這個 bot 已經設定了雲端 webhook（Cloudflare 版在接手）。本機版會收不到訊息，建議直接用雲端版，安裝中止"; exit 1 ;; esac

launchctl unload "$DST" >/dev/null 2>&1
sed -e "s|__HOME__|$HOME|g" -e "s|__TELEGRAM_BOT_TOKEN__|${TOKEN}|" "$TPL" > "$DST" || { echo "✗ 寫不進 $DST"; exit 1; }
chmod 600 "$DST"
unset TOKEN
launchctl load -w "$DST" || { echo "✗ launchctl load 失敗"; exit 1; }

sleep 4
if launchctl list | grep -q "com.igaming.telegram-bot"; then
  echo "✓ 安裝完成，機器人在背景執行中"
  tail -3 "$REPO/state/telegram-bot.log" 2>/dev/null | sed 's/^/  /'
  echo "→ 回 Telegram 打 /stock 或「狀態」試試；打「/」會出現指令選單"
else
  echo "✗ 看起來沒有啟動成功，紀錄檔最後幾行："
  tail -10 "$REPO/state/telegram-bot.log" 2>/dev/null
fi
