#!/usr/bin/env bash
# 發布當日 iGaming 日報。
#
# 與 Mac 舊版的差異：
#   - 不再從 ~/Desktop 複製檔案（違反可攜性原則）
#   - 日報 HTML 由 skill 的步驟 2 直接寫進 reports/<DATE>.html
#   - 本腳本只負責：重建首頁 → commit → push
#   - commit message 改成已定案的英文格式 daily: YYYY-MM-DD report
#
# 用法：bash scripts/publish.sh [YYYY-MM-DD]   （不給日期就用今天，台北時間）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATE="${1:-$(TZ=Asia/Taipei date +%Y-%m-%d)}"
REPORT="reports/${DATE}.html"

if [ ! -f "$REPORT" ]; then
  echo "✗ 找不到當日報告：$REPORT"
  echo "  請先依 skills/SKILL.md 的步驟 1–2 產出該日 HTML。"
  exit 1
fi

# commit 作者用中性身分（不露個人帳號）
git config user.name  "iGaming Pulse"
git config user.email "igaming-pulse@users.noreply.github.com"

python3 scripts/build_index.py

git add -A
if git diff --cached --quiet; then
  echo "（沒有變更，略過）"
  exit 0
fi

git commit -m "daily: ${DATE} report"
git push

echo "✓ 已發布 ${DATE}"
echo "  首頁：https://igaming-pulse.github.io/igaming-daily/"
echo "  當日：https://igaming-pulse.github.io/igaming-daily/reports/${DATE}.html"
echo "  （GitHub Pages 約 30 秒後更新）"
