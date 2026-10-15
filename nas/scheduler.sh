#!/usr/bin/env bash
# 每天固定時刻（台北，DAILY_AT，預設 02:30）呼叫 scripts/run_daily.sh。
# 取代 Mac 上的 launchd。補跑：容器在 DAILY_AT 之後、CATCHUP_UNTIL 之前啟動（例如 NAS 半夜重開機），
# 立刻補跑一次 —— run_daily.sh 自己會判斷「今天已經有成功的日報 commit」而略過，不會重複產生。
set -uo pipefail
export TZ=Asia/Taipei
REPO="${IGAMING_REPO:-/data/igaming-daily}"
AT="${DAILY_AT:-02:30}"
UNTIL="${CATCHUP_UNTIL:-10:00}"
say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [scheduler] $*"; }

run() {
  say "開始執行 run_daily.sh"
  bash "$REPO/scripts/run_daily.sh"
  say "run_daily.sh 結束（exit $?）"
}

say "排程啟動：每天 ${AT}（台北）；${AT}–${UNTIL} 之間啟動會補跑"
now_hm=$(date +%H%M)
if [ "$now_hm" -ge "${AT/:/}" ] && [ "$now_hm" -lt "${UNTIL/:/}" ]; then
  say "目前 ${now_hm:0:2}:${now_hm:2:2}，在補跑區間內 → 補跑一次"
  run
fi

while true; do
  now=$(date +%s)
  next=$(date -d "today ${AT}" +%s)
  [ "$next" -le "$now" ] && next=$(date -d "tomorrow ${AT}" +%s)
  say "下次執行：$(date -d "@${next}" '+%Y-%m-%d %H:%M')"
  sleep $(( next - now ))
  run
done
