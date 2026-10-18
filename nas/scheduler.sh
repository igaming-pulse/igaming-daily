#!/usr/bin/env bash
# NAS 容器的排程（台北時間），取代 Mac 的 launchd 與 GitHub 的 cron：
#   DAILY_AT（預設 02:30）→ scripts/run_daily.sh 產日報
#   PUSH_AT （預設 06:30）→ scripts/notify_telegram.sh 觸發 Telegram 推播
#     （2026-10-18：GitHub cron 常延遲 2 小時以上，10/17 拖到 08:45 才送，改由 NAS 準時觸發；
#       GitHub 那邊的排程保留當備援，它看到今天已手動發送過就會自己跳過）
#
# 補跑：容器在 DAILY_AT 之後、CATCHUP_UNTIL 之前啟動（例如 NAS 半夜重開機）→ 立刻補跑日報一次，
#       run_daily.sh 自己會判斷「今天已經有成功的日報 commit」而略過。
#
# 容器入口會優先執行 repo 裡的這支（data/igaming-daily/nas/scheduler.sh），
# 所以改排程只要推上 GitHub、再重啟 igaming-daily 容器，不必重建映像檔。
set -uo pipefail
export TZ=Asia/Taipei
REPO="${IGAMING_REPO:-/data/igaming-daily}"
AT="${DAILY_AT:-02:30}"
PUSH_AT="${PUSH_AT:-06:30}"
UNTIL="${CATCHUP_UNTIL:-10:00}"
LOCK=/tmp/igaming-daily.lock
say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [scheduler] $*"; }

# ── 啟動時自己更新（2026-10-18）────────────────────────────────
# bot 和 daily 兩個容器同時啟動、同時 git pull 會互相干擾（fatal: Cannot fast-forward to multiple branches），
# 入口那次 pull 失敗就會跑到舊版排程。所以這裡再清一次 .git 裡的 Synology @eaDir、重試 pull，
# 本檔有更新就用新版重新開始（只做一次）。
if [ -z "${IGAMING_SCHED_UPDATED:-}" ] && [ -d "$REPO/.git" ]; then
  self="$REPO/nas/scheduler.sh"; before=$(cksum < "$self" 2>/dev/null)
  find "$REPO/.git" -name '@eaDir' -type d -prune -exec rm -rf {} + 2>/dev/null
  for i in 1 2 3; do
    (cd "$REPO" && flock -w 120 .git/igaming-pull.lock git pull -q --ff-only 2>&1) && break
    say "git pull 失敗（第 ${i} 次），10 秒後重試"; sleep 10
  done
  if [ -f "$self" ] && [ "$(cksum < "$self")" != "$before" ]; then
    say "排程程式已更新 → 用新版本重新開始"
    export IGAMING_SCHED_UPDATED=1; exec bash "$self"
  fi
fi

run_daily() {
  say "開始執行 run_daily.sh"
  flock -n "$LOCK" bash "$REPO/scripts/run_daily.sh"
  say "run_daily.sh 結束（exit $?）"
}

push() {
  # 日報還在跑 → 不推：run_daily.sh 跑完時若已過 06:30 會自己觸發推播（成功）或發即時警報（失敗），避免重複
  if ! flock -n "$LOCK" true; then
    say "日報還在跑，06:30 推播交給 run_daily.sh 跑完時觸發"
    return
  fi
  say "觸發 Telegram 推播"
  # 沒有今天的日報也照樣觸發：workflow 的守門員會改發「日報未產出」警報
  IGAMING_PUSH_ANYWAY=1 bash "$REPO/scripts/notify_telegram.sh"
  say "推播觸發結束（exit $?）"
}

next_at() {   # $1 = HH:MM → 下一次的 epoch 秒
  local t; t=$(date -d "today $1" +%s)
  [ "$t" -le "$(date +%s)" ] && t=$(date -d "tomorrow $1" +%s)
  echo "$t"
}

say "排程啟動：日報 ${AT}、推播 ${PUSH_AT}（台北）；${AT}–${UNTIL} 之間啟動會補跑日報"
now_hm=$(date +%H%M)
if [ "$now_hm" -ge "${AT/:/}" ] && [ "$now_hm" -lt "${UNTIL/:/}" ]; then
  say "目前 ${now_hm:0:2}:${now_hm:2:2}，在補跑區間內 → 補跑一次"
  run_daily &
fi

while true; do
  nd=$(next_at "$AT"); np=$(next_at "$PUSH_AT")
  if [ "$nd" -le "$np" ]; then next=$nd; job=run_daily; else next=$np; job=push; fi
  say "下一個工作：$( [ "$job" = run_daily ] && echo 日報 || echo 推播 ) $(date -d "@${next}" '+%m-%d %H:%M')"
  wait_s=$(( next - $(date +%s) )); [ "$wait_s" -gt 0 ] && sleep "$wait_s"
  $job &     # 背景執行：日報跑很久也不會擋住 06:30 的推播判斷
  sleep 1
done
