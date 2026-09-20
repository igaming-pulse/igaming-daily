#!/usr/bin/env bash
# ============================================================
#  每日日報執行入口 —— 由 launchd（或任何排程器）呼叫。
#
#  為什麼要有這一支（而不是直接用 Claude 內建排程）：
#    macOS launchd 的 StartCalendarInterval 有「**漏跑會補**」的特性 ——
#    若排定時刻機器是關機／睡死的，下次醒來會自動補跑一次。
#    這是 2026-09-20 定案的「不漏跑」保險之一。
#
#  用法：
#    bash scripts/run_daily.sh              # 手動跑一次（第一次設定時先這樣測）
#    由 launchd 呼叫時不帶參數
#
#  環境變數：
#    IGAMING_REPO   repo 路徑（預設 ~/igaming-daily）
#    CLAUDE_ARGS    傳給 claude 的額外旗標（見下方說明）
# ============================================================
set -uo pipefail

REPO="${IGAMING_REPO:-$HOME/igaming-daily}"
PROMPT_FILE="$REPO/docs/scheduled-prompt.txt"
LOG_DIR="$REPO/state"
LOG="$LOG_DIR/run.log"

# ---- 無人值守的授權旗標 ----
# ⚠️ 第一次設定時請先手動跑一次本腳本，確認**不會停下來問授權**。
#    若停住了，用 `claude --help` 查目前版本正確的旗標名稱，改下面這一行。
CLAUDE_ARGS="${CLAUDE_ARGS:---permission-mode bypassPermissions}"

ts() { TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }

mkdir -p "$LOG_DIR"

log "──────── 開始 ────────"
log "repo: $REPO"

if [ ! -d "$REPO/.git" ]; then
  log "✗ $REPO 不是 git repo，中止。"
  exit 1
fi

cd "$REPO" || exit 1

# PATH：launchd 啟動的環境很精簡，補上常見的安裝位置
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

if ! command -v claude >/dev/null 2>&1; then
  log "✗ 找不到 claude CLI。請確認已安裝，或在本腳本的 PATH 補上它的位置。"
  exit 1
fi

if [ ! -f "$PROMPT_FILE" ]; then
  log "✗ 找不到 $PROMPT_FILE"
  exit 1
fi

log "git pull…"
git pull --ff-only >>"$LOG" 2>&1 || log "⚠️ git pull 失敗，用本地版本繼續"

log "claude $CLAUDE_ARGS -p <docs/scheduled-prompt.txt>"
# shellcheck disable=SC2086
claude $CLAUDE_ARGS -p "$(cat "$PROMPT_FILE")" >>"$LOG" 2>&1
rc=$?

if [ $rc -eq 0 ]; then
  log "✓ 完成（exit 0）"
else
  log "✗ 結束但有錯（exit ${rc}）—— 06:30 的守門員會發警報"
fi
log "──────── 結束 ────────"
exit $rc
