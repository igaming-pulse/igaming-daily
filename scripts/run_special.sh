#!/usr/bin/env bash
# ============================================================
#  v6.6 庫存釋放特別版（2026-10-11 使用者定案）
#
#  由 run_daily.sh 在「日報成功」後呼叫；只在週一、週四動作：
#    1. 當天日報已成功（有 daily: <DATE> report commit 且日報檔存在）
#    2. special_edition.py select：Slot 可用庫存 ≥5 才繼續（大廠在前、B1 最多 5、每期 ≤12）
#    3. claude -p docs/special-prompt.txt：查證寫稿 → finalize_report.py → reports/<DATE>-special.html
#    4. special_edition.py shown → inventory.py update --keep-day（實際寫進去的才算釋放）
#    5. 當天日報的 Telegram 訊息加一行特別版連結（合併推播）；若今天的推播已經送出，改單獨補發一則
#    6. commit＋push test-publish → publish_test_to_main.sh 以 -special 發佈到網站
#  週六、週日日報的 Slot 上限不受影響。
#
#  用法：bash scripts/run_special.sh [DATE] [--force] [--redo]
#        --force 略過「週一／週四」判斷（手動例外）；--redo 重做今天這期（帶回今天已發的，合成完整總覽、覆蓋同一個網址）
# ============================================================
set -uo pipefail

REPO="${IGAMING_REPO:-$HOME/igaming-daily}"
cd "$REPO" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

DATE="$(TZ=Asia/Taipei date +%F)"; FORCE=0; REDO=0
for a in "$@"; do case "$a" in --force) FORCE=1 ;; --redo) REDO=1; FORCE=1 ;; 20[0-9][0-9]-*) DATE="$a" ;; esac; done
LOG="$REPO/state/run.log"
CLAUDE_ARGS="${CLAUDE_ARGS:---permission-mode bypassPermissions}"
SITE="https://igaming-pulse.github.io/igaming-daily/reports"

say() { echo "[$(TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S')] [特別版] $*" | tee -a "$LOG"; }

WD=$(python3 -c "import datetime,sys;print(datetime.date.fromisoformat(sys.argv[1]).isoweekday())" "$DATE")
if [ "$FORCE" != "1" ] && [ "$WD" != "1" ] && [ "$WD" != "4" ]; then
  exit 0   # 只在週一、週四；其他天安靜略過
fi

SUBJECTS=$(git log --since="30 hours ago" --format=%s 2>/dev/null)
if ! printf '%s\n' "$SUBJECTS" | grep -qx "daily: ${DATE} report" || [ ! -f "reports/${DATE}.html" ]; then
  say "今天（${DATE}）的日報還沒成功，不發特別版"
  exit 0
fi
if [ "$REDO" != "1" ] && printf '%s\n' "$SUBJECTS" | grep -q "^special: ${DATE}"; then
  say "今天已經發過特別版，略過"
  exit 0
fi

say "檢查庫存…"
python3 scripts/special_edition.py select --date "$DATE" $([ "$REDO" = "1" ] && echo --redo) | tee -a "$LOG"
rc=${PIPESTATUS[0]}
if [ "$rc" = "3" ]; then say "可用庫存未達門檻，不發"; exit 0; fi
[ "$rc" = "0" ] || { say "✗ 選款失敗"; exit 1; }

# Firecrawl 上限：照今天的分級預算扣掉今天已用量（查不到就 8）
FC_LIMIT=$(python3 - "$DATE" <<'PY'
import json, os, subprocess, sys
date = sys.argv[1]
try:
    meta = json.load(open(f"state/harvest/{date}.json"))["meta"]["firecrawl"]
    budget = meta.get("budget")
    hist = json.load(open("state/health/credits.json")).get(date, {})
    key = os.environ.get("FIRECRAWL_API_KEY", "")
    now = None
    if key:
        r = subprocess.run(["curl", "-s", "--max-time", "15", "-H", f"Authorization: Bearer {key}",
                            "https://api.firecrawl.dev/v2/team/credit-usage"], capture_output=True, text=True)
        now = json.loads(r.stdout)["data"]["remainingCredits"]
    used = (hist.get("start", now) - now) if (now is not None and hist.get("start")) else 0
    n = len(json.load(open(f"state/special-{date}-items.json"))["chosen"])
    print(max(0, min(n, (budget or 20) - used)) if budget is not None else min(n, 20))
except Exception:
    print(20)
PY
)
say "Firecrawl 上限 ${FC_LIMIT} 次；啟動 Claude 寫稿"

PROMPT=$(sed -e "s/{{DATE}}/${DATE}/g" -e "s/{{FIRECRAWL_LIMIT}}/${FC_LIMIT}/g" docs/special-prompt.txt)
START=$(date +%s)
# shellcheck disable=SC2086
claude $CLAUDE_ARGS -p "$PROMPT" 2>&1 | tee -a "$LOG"
say "Claude 結束，耗時 $(( $(date +%s) - START )) 秒"

OUT="reports/${DATE}-special.html"
if [ ! -f "$OUT" ] || [ "$(date -r "$OUT" +%s)" -lt "$START" ]; then
  say "✗ 沒有產出 ${OUT}，本次特別版未完成（庫存不動）"
  exit 1
fi

python3 scripts/special_edition.py shown --date "$DATE" | tee -a "$LOG"
N=$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['shown']))" "state/inventory-picks-${DATE}-special.json")
python3 scripts/inventory.py update --date "$DATE" --file "state/inventory-picks-${DATE}-special.json" --keep-day | tee -a "$LOG"

# Telegram：合併進今天日報那則（插在前兩行與「❗收錄偏少」之後）
LINE="📦 今日另有特別版：釋放 ${N} 款近期新作（大廠在前）→ ${SITE}/${DATE}-special.html"
python3 - "$LINE" <<'PY'
import sys
p = "state/pending_telegram.txt"
line = sys.argv[1]
try:
    rows = open(p, encoding="utf-8").read().split("\n")
except FileNotFoundError:
    sys.exit(0)
rows = [r for r in rows if not r.startswith("📦 今日另有特別版")]
at = 3 if len(rows) > 2 and rows[2].startswith("❗") else 2
rows.insert(at, line)
open(p, "w", encoding="utf-8").write("\n".join(rows))
PY

git add "$OUT" "state/${DATE}-special-igaming-report.md" "state/${DATE}-special-report.json" "state/${DATE}-special-qa.json" \
        "state/special-${DATE}-items.json" "state/inventory-picks-${DATE}-special.json" state/inventory.json state/pending_telegram.txt 2>/dev/null
git commit -q -m "special: ${DATE} 特別版（庫存釋放 ${N} 款）$([ "$REDO" = "1" ] && echo "・重做全部釋放")" && git push -q || say "⚠️ push test-publish 失敗"

PUBLISH_SUFFIX=-special bash scripts/publish_test_to_main.sh "$DATE" 2>&1 | tee -a "$LOG"

# 今天的推播若已經送出（例如日報晚到、已立刻推播），單獨補發一則特別版通知
SENT=$(python3 - "$DATE" <<'PY'
import json, subprocess, sys, urllib.request
from datetime import datetime, timedelta, timezone
date = sys.argv[1]
tok = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                     capture_output=True, text=True).stdout
tok = next((l.split("=", 1)[1] for l in tok.splitlines() if l.startswith("password=")), "")
url = "https://api.github.com/repos/igaming-pulse/igaming-daily/actions/workflows/telegram-test-0640.yml/runs?status=success&per_page=10"
try:
    runs = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})))["workflow_runs"]
    tpe = timezone(timedelta(hours=8))
    print("1" if any(datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(tpe).date().isoformat() == date for r in runs) else "0")
except Exception:
    print("0")
PY
)
if [ "$SENT" = "1" ]; then
  printf '📦 iGaming 市場日報 %s 特別版\n🎰 釋放 %s 款近期新作（大廠優先）\n\n' "$DATE" "$N" > "state/pending_telegram_special_${DATE}.txt"
  python3 - "$DATE" >> "state/pending_telegram_special_${DATE}.txt" <<'PY'
import json, sys
sys.path.insert(0, "scripts")
import report_lib as R
rep = R.parse_md(open(f"state/{sys.argv[1]}-special-igaming-report.md", encoding="utf-8").read())
for s in rep["sections"]:
    for it in s["items"]:
        print(f"{it['no']:02d} {it['title']}")
PY
  git add "state/pending_telegram_special_${DATE}.txt" && git commit -q -m "special: ${DATE} 特別版推播內容" && git push -q
  TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | sed -n 's/^password=//p')
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/igaming-pulse/igaming-daily/actions/workflows/telegram-test-0640.yml/dispatches" \
    -d "{\"ref\":\"main\",\"inputs\":{\"dry_run\":\"false\",\"url_suffix\":\"-special\",\"report_date\":\"${DATE}\",\"pending_path\":\"state/pending_telegram_special_${DATE}.txt\",\"msg_prefix\":\"📦【特別版】公司帳號 13' v\"}}")
  say "今天的推播已送出 → 單獨補發特別版通知（HTTP ${code}）"
else
  say "特別版連結已加進今天日報的 Telegram 訊息，跟日報一起推播"
fi
say "✓ 完成：${OUT}（釋放 ${N} 款）"
