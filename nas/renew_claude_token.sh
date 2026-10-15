#!/usr/bin/env bash
# 一鍵更新 NAS 上的 Claude token：產生新 token → 等你複製 → 自動寫進 NAS 的 secrets.env
#   bash ~/igaming-daily/nas/renew_claude_token.sh
set -uo pipefail
claude setup-token || { echo "✗ setup-token 沒有完成"; exit 1; }
echo
echo "════════════════════════════════════════════════════"
echo " 用滑鼠把上面 sk-ant-oat01- 開頭的那幾行全部選起來，按 ⌘C"
echo " （token 折成好幾行沒關係，前後多選幾行也沒關係，不用自己拼）"
echo " 複製好之後，回到這裡按 Enter"
echo "════════════════════════════════════════════════════"
read -r _
bash "$(dirname "$0")/fill_secrets.sh"
echo
echo "看到 Claude token「108 字元」就完成了。接著到 Container Manager：專案 igaming-daily → 停止 → 操作 → 建立"
