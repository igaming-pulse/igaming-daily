#!/usr/bin/env bash
# ============================================================
#  每日日報執行入口 —— 由 launchd（或任何排程器）呼叫。
#
#  為什麼要有這一支（而不是直接用 Claude 內建排程）：
#    macOS launchd 的 StartCalendarInterval 有「**漏跑會補**」的特性 ——
#    若排定時刻機器是關機／睡死的，下次醒來會自動補跑一次。
#    這是 2026-09-20 定案的「不漏跑」保險之一。
#
#  ⚠️ 為什麼要驗收（2026-09-20 加）：
#    headless 模式下 Claude 若停下來反問，會直接 exit 0 結束 ——
#    log 看起來「✓ 完成」，實際上什麼都沒產出。所以本腳本不信任 exit code，
#    一律用「有沒有當天的 report」＋「有沒有新 commit」來判定成敗。
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

DATE=$(TZ=Asia/Taipei date +%F)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
log "日期: ${DATE}　分支: ${BRANCH}"
[ "$BRANCH" = "main" ] && log "※ 目前在 main —— 併行期應該在 test-publish，切換後才會是 main"

log "git pull…"
git pull --ff-only >>"$LOG" 2>&1 || log "⚠️ git pull 失敗，用本地版本繼續"

HEAD_BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "none")
START_EPOCH=$(date +%s)

log "claude $CLAUDE_ARGS -p <docs/scheduled-prompt.txt>"
# 同時印到畫面與 log —— 手動跑時才看得到失敗原因（pipefail 讓 $? 仍是 claude 的退出碼）
# shellcheck disable=SC2086
claude $CLAUDE_ARGS -p "$(cat "$PROMPT_FILE")" 2>&1 | tee -a "$LOG"
CLAUDE_RC=$?

ELAPSED=$(( $(date +%s) - START_EPOCH ))
log "claude 結束（exit ${CLAUDE_RC}），耗時 ${ELAPSED} 秒"

# ══════════════════════════════════════════════════
#  驗收 —— 不信任 exit code，實際看有沒有產出
# ══════════════════════════════════════════════════
HEAD_AFTER=$(git rev-parse HEAD 2>/dev/null || echo "none")
REPORT="reports/${DATE}.html"
fail=0

if [ ! -f "$REPORT" ]; then
  log "  ✗ 找不到 ${REPORT} —— 日報沒產出"
  fail=1
else
  # 只有「存在」不夠 —— 昨天或上一輪的舊檔也會存在。要比本次開跑時間新才算數。
  # date -r <file> 在 macOS(BSD) 與 Linux(GNU) 都是讀檔案 mtime，比 stat 好移植
  MTIME=$(date -r "$REPORT" +%s 2>/dev/null || echo 0)
  case "$MTIME" in (*[!0-9]*|'') MTIME=0 ;; esac
  if [ "$MTIME" -ge "$START_EPOCH" ]; then
    log "  ✓ ${REPORT} 是本次產生的"
  else
    log "  ✗ ${REPORT} 是舊檔，本次並未重新產生"
    fail=1
  fi
fi

if [ "$HEAD_BEFORE" != "$HEAD_AFTER" ]; then
  log "  ✓ 有新 commit：$(git log -1 --format='%h %s')"
else
  log "  ✗ 沒有新 commit —— 沒有發布"
  fail=1
fi

if [ "$ELAPSED" -lt 300 ]; then
  log "  ⚠️ 只跑了 ${ELAPSED} 秒，正常應該 30 分鐘以上 —— 很可能中途停下來反問或提早結束"
fi

if [ "$fail" -eq 0 ]; then
  log "✅ 本次執行成功"
  log "──────── 結束 ────────"
  exit 0
fi

log ""
log "❌❌❌ 本次執行失敗 —— 日報沒產出或沒發布 ❌❌❌"
if tail -40 "$LOG" | grep -qiE 'session limit|usage limit|rate limit'; then
  log "   ⚠️ 偵測到「用量上限」訊息 —— 這不是流程壞掉，是 Claude 訂閱額度用完。"
  log "      等額度重置後重跑；若 reports/ 與 state/ 的產物已經寫好，只差發布，"
  log "      可以直接手動 git add / commit / push 補完，不需要再花額度。"
fi
log "   常見原因："
log "   1. Claude 在 headless 模式下停下來反問（往上翻 log 會看到它在問問題）"
log "      → 把該情境的裁示補進 docs/scheduled-prompt.txt 的「已經預先裁示的狀況」"
log "   2. 抓取或查證階段失敗"
log "   3. git push 被拒（憑證過期？）"
log "   06:30 的守門員會發出「日報未產出」警報。"
log "──────── 結束 ────────"
exit 1
