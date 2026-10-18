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

# ── 從副本執行（2026-10-16）──────────────────────────────────────
# bash 是邊跑邊讀腳本檔的。下面的 git pull 若改到本檔，正在跑的程序會從新檔案的舊位置接著讀，
# 跳段或亂跑（10/16 NAS 第一次跑時「執行中標記」整段被跳過）。所以先複製一份到暫存檔、從副本執行；
# git pull 之後若本檔有更新，就用新版本從頭重新開始一次。
if [ -z "${IGAMING_RUN_COPY:-}" ]; then
  _copy=$(mktemp "${TMPDIR:-/tmp}/run_daily.XXXXXX") && cp "$0" "$_copy" \
    && IGAMING_RUN_COPY="$_copy" exec /bin/bash "$_copy" "$@"
fi
export IGAMING_RUN_COPY

# ── 防睡眠（2026-10-10）──────────────────────────────────────────
# 10/1、10/5、10/8、10/9、10/10 都是 02:30 準時開跑後 Mac 又睡回去，收集拖 1–2 小時、Claude 卡到早上。
# 這裡讓整支腳本在 caffeinate -i 底下重新執行：跑完才放開。用電池時也有效（-i＝防閒置睡眠）；闔上螢幕仍會睡（硬體限制）。
if [ -z "${IGAMING_CAFFEINATED:-}" ] && command -v caffeinate >/dev/null 2>&1; then
  export IGAMING_CAFFEINATED=1
  exec caffeinate -i /bin/bash "$0" "$@"
fi

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

# 保險（2026-10-05）：上一輪若卡在合併／rebase 中途，或停在別的分支，先恢復乾淨再開跑
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
  log "⚠️ 偵測到未完成的 rebase，先 abort"
  git rebase --abort >>"$LOG" 2>&1 || true
fi
if [ -f .git/MERGE_HEAD ]; then
  log "⚠️ 偵測到未完成的 merge，先 abort"
  git merge --abort >>"$LOG" 2>&1 || true
fi
EXPECT_BRANCH="${IGAMING_BRANCH:-test-publish}"
if [ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" != "$EXPECT_BRANCH" ] && git show-ref -q "refs/heads/$EXPECT_BRANCH"; then
  log "⚠️ 目前不在 ${EXPECT_BRANCH}，切回去"
  git checkout -q "$EXPECT_BRANCH" >>"$LOG" 2>&1 || log "✗ 切不回 ${EXPECT_BRANCH}"
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")

# Synology（2026-10-17）：從 Mac 用 SMB 寫過的資料夾，NAS 會產生隱藏的 @eaDir/*@SynoEAStream。
# 出現在 .git/refs 裡會讓 git pull 失敗（fatal: bad object refs/heads/@eaDir/...）→ 開跑前清掉（Mac 上不會有，無影響）
find .git -name '@eaDir' -type d -prune -exec rm -rf {} + 2>/dev/null

# NAS（2026-10-18）：bot 與 daily 兩個容器共用同一份 repo，同時 git pull 會互相干擾
# （fatal: Cannot fast-forward to multiple branches）→ 有 flock 就排隊（最多等 120 秒）。Mac 沒有 flock，直接跑。
PULL_LOCK=()
command -v flock >/dev/null 2>&1 && PULL_LOCK=(flock -w 120 .git/igaming-pull.lock)

log "git pull…"
${PULL_LOCK[@]+"${PULL_LOCK[@]}"} git pull --ff-only >>"$LOG" 2>&1 || log "⚠️ git pull 失敗，用本地版本繼續"
if [ -z "${IGAMING_REEXEC:-}" ] && ! cmp -s "$IGAMING_RUN_COPY" "$REPO/scripts/run_daily.sh"; then
  log "run_daily.sh 剛被 git pull 更新 → 用新版本重新開始"
  rm -f "$IGAMING_RUN_COPY"
  export IGAMING_REEXEC=1; unset IGAMING_RUN_COPY
  exec /bin/bash "$REPO/scripts/run_daily.sh" "$@"
fi
rm -f "$IGAMING_RUN_COPY"   # bash 已經開著它，刪掉檔名不影響繼續執行

# 提早手動執行後，02:30 的排程就不要再跑一次（2026-10-07）：今天已有成功的日報 commit → 略過
# 要強制重跑：IGAMING_FORCE=1 bash scripts/run_daily.sh
# ⚠️ 不可寫成 git log | grep -q：grep 提早結束讓 git log 收到 SIGPIPE，在 pipefail 下整條被當成失敗（10/7 因此重跑了一次）
RECENT_SUBJECTS=$(git log --since="18 hours ago" --format=%s 2>/dev/null)
if [ "${IGAMING_FORCE:-0}" != "1" ] && printf '%s\n' "$RECENT_SUBJECTS" | grep -x "daily: ${DATE} report" >/dev/null \
   && [ -f "reports/${DATE}.html" ]; then
  log "今天（${DATE}）已經有成功的日報 commit，略過本次（強制重跑請設 IGAMING_FORCE=1）"
  log "──────── 結束 ────────"
  exit 0
fi

# 開跑前檢查 Claude 登入（2026-10-11）：10/8 登入過期，白跑了收集才發現 → 先檢查，過期就立刻發警報、不浪費 Firecrawl 點數
# NAS（2026-10-15）：用 CLAUDE_CODE_OAUTH_TOKEN 長效 token、沒有互動登入 → 改成實際問一句，確認 token 有效
if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  PING=$(timeout 180 claude -p "只回覆 OK 兩個字母" 2>&1 | tail -5)
  case "$PING" in
    *OK*) AUTH_JSON='"loggedIn": true'; log "Claude token：正常" ;;
    *)
      log "✗ Claude token 無效或過期：${PING}"
      bash scripts/alert_telegram.sh "${IGAMING_MACHINE:-NAS} 的 Claude token 失效，日報沒有執行" \
        "請在 Mac 終端機執行 claude setup-token，把印出的 token 那幾行 ⌘C（會折行，不要手動貼），
再執行 bash ~/igaming-daily/nas/fill_secrets.sh 寫進 NAS；
最後到 Container Manager → 專案 igaming-daily → 停止 → 操作 → 建立（10:00 前完成會自動補跑）。" 2>&1 | tee -a "$LOG"
      log "──────── 結束 ────────"
      exit 1 ;;
  esac
else
  AUTH_JSON=$(claude auth status 2>&1)
fi
case "$AUTH_JSON" in
  *'"loggedIn": true'*) [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || log "Claude 登入：正常" ;;
  *)
    log "✗ Claude 終端機版沒有登入（或登入已過期），本次不執行"
    bash scripts/alert_telegram.sh "Claude 登入過期，日報沒有執行" \
      "請在終端機輸入 claude，進去後輸入 /login 重新登入（用 nathan.kao@bituslabs.com）。
登入後跟 Claude 說「補跑日報」，或在終端機執行：
launchctl kickstart gui/\$(id -u)/com.igaming.daily-0230" 2>&1 | tee -a "$LOG"
    log "──────── 結束 ────────"
    exit 1 ;;
esac

# ── 執行中標記（2026-10-15，NAS 主跑＋Mac 05:30 備援）──────────────────────────
# 開跑前把 state/running-<DATE>.txt 推上 GitHub，讓另一台知道「這台正在跑」。
# 另一台（備援）看到別台的標記、而且還在 running：每 5 分鐘 git pull 看一次，
#   日報出來 → 略過；標記變 failed 或等滿 IGAMING_LOCK_WAIT_MIN 分鐘（預設 90）→ 接手。
# 標記超過 IGAMING_LOCK_STALE_H 小時（預設 5）視為卡死，直接接手。IGAMING_FORCE=1 不看標記。
MACHINE="${IGAMING_MACHINE:-Mac}"
LOCK="state/running-${DATE}.txt"
lock_field() { sed -n "s/^$1=//p" "$LOCK" 2>/dev/null | head -1; }
lock_push() {   # $1 = running | failed
  printf 'machine=%s\nstarted=%s\nstatus=%s\nupdated=%s\n' "$MACHINE" "${LOCK_STARTED:-$(date +%s)}" "$1" "$(ts)" > "$LOCK"
  git add -f "$LOCK" >/dev/null 2>&1
  git commit -q -m "lock: ${DATE} ${MACHINE} $1" -- "$LOCK" >/dev/null 2>&1
  git push -q >/dev/null 2>&1 || { ${PULL_LOCK[@]+"${PULL_LOCK[@]}"} git pull -q --rebase >/dev/null 2>&1 && git push -q >/dev/null 2>&1; } \
    || log "  ⚠️ 執行中標記推不上 GitHub（不影響本次執行）"
}
if [ "${IGAMING_FORCE:-0}" != "1" ] && [ -f "$LOCK" ] && [ "$(lock_field machine)" != "$MACHINE" ] \
   && [ "$(lock_field status)" = "running" ]; then
  OTHER=$(lock_field machine); STARTED=$(lock_field started)
  case "$STARTED" in (*[!0-9]*|'') STARTED=0 ;; esac
  WAIT_MAX=$(( ${IGAMING_LOCK_WAIT_MIN:-90} * 60 )); STALE=$(( ${IGAMING_LOCK_STALE_H:-5} * 3600 ))
  WAITED=0
  log "${OTHER} 從 $(TZ=Asia/Taipei date -r "$STARTED" '+%H:%M' 2>/dev/null || TZ=Asia/Taipei date -d "@$STARTED" '+%H:%M') 開始在跑今天的日報，本機（${MACHINE}）先等它"
  while :; do
    if [ $(( $(date +%s) - STARTED )) -ge "$STALE" ]; then
      log "  ${OTHER} 的標記已超過 ${IGAMING_LOCK_STALE_H:-5} 小時，視為卡住 → 本機接手"; break
    fi
    if [ "$WAITED" -ge "$WAIT_MAX" ]; then
      log "  已等 $(( WAITED / 60 )) 分鐘仍未完成 → 本機接手"; break
    fi
    sleep 300; WAITED=$(( WAITED + 300 ))
    ${PULL_LOCK[@]+"${PULL_LOCK[@]}"} git pull --ff-only -q >>"$LOG" 2>&1 || true
    if git log --since="18 hours ago" --format=%s 2>/dev/null | grep -x "daily: ${DATE} report" >/dev/null \
       && [ -f "reports/${DATE}.html" ]; then
      log "  ✓ ${OTHER} 已完成今天的日報，本機略過"
      log "──────── 結束 ────────"
      exit 0
    fi
    if [ "$(lock_field status)" != "running" ]; then
      log "  ${OTHER} 回報失敗 → 本機接手"; break
    fi
  done
fi
LOCK_STARTED=$(date +%s)
lock_push running

HEAD_BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "none")
START_EPOCH=$(date +%s)

# v6.4：開跑前先用程式收集候選（第一層 WP-API／RSS ＋ 第二層 Firecrawl 列表頁）
log "harvest…"
python3 scripts/harvest.py >>"$LOG" 2>&1 && log "  ✓ harvest 完成：state/harvest/${DATE}.md" \
  || log "  ⚠️ harvest 失敗，Claude 會依 SKILL.md 自行補跑或退回舊流程"

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

# v6.5：日報應由 finalize_report.py 的固定模板產生（檔頭有 generator 標記）
if [ -f "$REPORT" ] && ! grep -q 'name="generator" content="render_report.py' "$REPORT"; then
  log "  ⚠️ ${REPORT} 不是固定模板產生的（Claude 可能手寫了 HTML），樣式開關可能套不上"
fi
if [ -f "state/${DATE}-qa.json" ]; then
  log "  定稿檢查：$(python3 -c "import json;q=json.load(open('state/${DATE}-qa.json'));print(f\"錯誤 {len(q['errors'])}、警告 {len(q['warnings'])}、自動修正 {len(q['fixes'])}\")" 2>/dev/null)"
else
  log "  ⚠️ 沒有 state/${DATE}-qa.json —— 定稿檢查沒跑"
fi

if [ "$HEAD_BEFORE" != "$HEAD_AFTER" ]; then
  log "  ✓ 有新 commit：$(git log -1 --format='%h %s')"
else
  log "  ✗ 沒有新 commit —— 沒有發布"
  fail=1
fi

# 2026-10-18：門檻 300→120 秒。NAS 上正常約 4–20 分鐘（10/18 只花 258 秒也是完整日報），只在真的提早結束時提醒
if [ "$ELAPSED" -lt 120 ]; then
  log "  ⚠️ 只跑了 ${ELAPSED} 秒，正常應該 4 分鐘以上 —— 很可能中途停下來反問或提早結束"
fi

if [ "$fail" -eq 0 ]; then
  log "✅ 本次執行成功"
  # 併行期：另外把當天日報以（測試）條目發到 main，讓網站上看得到新環境的產出。
  # 分支已是 main（＝切換完成）就自動跳過；設 IGAMING_PUBLISH_TEST_TO_MAIN=0 可關閉。
  if [ "${IGAMING_PUBLISH_TEST_TO_MAIN:-1}" = "1" ] && [ "$BRANCH" != "main" ]; then
    bash scripts/publish_test_to_main.sh "$DATE" 2>&1 | tee -a "$LOG"
    # v6.6 庫存釋放特別版：週一、週四且 Slot 可用庫存 ≥5 才發（其他天自動略過）；放在推播前，連結才會併進今天的訊息
    bash scripts/run_special.sh "$DATE"   # 它自己會寫 run.log，這裡不再 tee（避免紀錄重複）
    # 晚到就立刻推播：已過 06:30 才跑完時，等網站頁面上線後直接觸發 Telegram（早於 06:30 交給排程）
    bash scripts/notify_telegram.sh "$DATE" 2>&1 | tee -a "$LOG"
  fi
  log "──────── 結束 ────────"
  exit 0
fi

lock_push failed
log ""
log "❌❌❌ 本次執行失敗 —— 日報沒產出或沒發布 ❌❌❌"
# 即時警報（2026-10-11）：判斷最可能的原因，馬上發 Telegram，不等早上的守門員
TAIL=$(tail -60 "$LOG")
case "$TAIL" in
  *"OAuth"*|*"authenticate"*|*"Login expired"*)
    WHY="Claude 登入過期"; HOWTO="請在終端機輸入 claude → /login 重新登入，再跟 Claude 說「補跑日報」。" ;;
  *"usage limit"*|*"session limit"*|*"rate limit"*)
    WHY="Claude 用量額度用完"; HOWTO="等額度重置後再補跑；若 reports/ 已產出只差發布，可手動 commit／push。" ;;
  *)
    if [ "$fail" -eq 1 ] && [ ! -f "$REPORT" ]; then WHY="日報沒有產出"; else WHY="日報沒有發布（沒有新 commit）"; fi
    HOWTO="耗時 ${ELAPSED} 秒。可跟 Claude 說「補跑日報」，或看 state/run.log 最後一段。" ;;
esac
bash scripts/alert_telegram.sh "$WHY" "$HOWTO" 2>&1 | tee -a "$LOG"
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
