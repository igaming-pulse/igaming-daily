#!/usr/bin/env bash
# 發布當日 iGaming 日報到 GitHub Pages。
# 用法：./publish.sh [YYYY-MM-DD]   （不給日期就用今天，台北時間）
set -e
cd "$(dirname "$0")"

DATE="${1:-$(TZ=Asia/Taipei date +%Y-%m-%d)}"
SRC="$HOME/Desktop/All-in AI/04_Docs/NewsReport/${DATE}-igaming-report.html"

if [ ! -f "$SRC" ]; then
  echo "✗ 找不到當日報告：$SRC"
  echo "  請先用 daily-news-report + daily-report-html 產出該日 HTML。"
  exit 1
fi

cp "$SRC" "reports/${DATE}.html"

# /usr/local/bin/python3 目前架構損壞（Bad CPU type），改用系統內建的 /usr/bin/python3
PY3="/usr/bin/python3"
command -v "$PY3" >/dev/null 2>&1 || PY3="python3"
"$PY3" build_index.py

git add -A
if git diff --cached --quiet; then
  echo "（沒有變更，略過）"; exit 0
fi
git commit -m "日報：${DATE}"
git push
echo "✓ 已發布 ${DATE}。網址：https://igaming-pulse.github.io/igaming-daily/（約 30 秒後更新）"
