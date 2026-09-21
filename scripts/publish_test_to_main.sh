#!/usr/bin/env bash
# 併行期專用：把 test-publish 上當天的日報，另外以「<DATE>-test.html」
# 發佈到 main，首頁會多一張標著（測試）的卡片，供與正式版並排比對。
# 切換日後 run_daily.sh 在分支為 main 時會自動跳過這一步。
set -uo pipefail

REPO="${IGAMING_REPO:-$HOME/igaming-daily}"
cd "$REPO" || exit 1

DATE="${1:-$(TZ=Asia/Taipei date +%F)}"
SRC="reports/${DATE}.html"
DST="reports/${DATE}-test.html"
ORIG_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "test-publish")

say() { echo "  [test→main] $*"; }
restore() { git checkout "$ORIG_BRANCH" >/dev/null 2>&1 || true; }
trap restore EXIT

[ "$ORIG_BRANCH" = "main" ] && { say "已在 main，不需要併行條目，略過"; exit 0; }
[ -f "$SRC" ] || { say "✗ 找不到 $SRC，略過"; exit 1; }

TMP=$(mktemp /tmp/igaming-test-XXXXXX.html)
cp "$SRC" "$TMP"
python3 - "$TMP" <<'PY'
import sys, re, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
if '（測試）' not in s:
    s = re.sub(r'(<title>)(.*?)(</title>)', r'\1\2（測試）\3', s, count=1)
    s = re.sub(r'(<h1[^>]*>)(.*?)(</h1>)', r'\1\2（測試）\3', s, count=1, flags=re.S)
p.write_text(s, encoding='utf-8')
PY

git checkout main >/dev/null 2>&1 || { say "✗ 切不到 main"; rm -f "$TMP"; exit 1; }
git pull --ff-only >/dev/null 2>&1 || say "⚠️ main pull 失敗，用本地版本繼續"
cp "$TMP" "$DST"; rm -f "$TMP"

python3 build_index.py >/dev/null || { say "✗ build_index.py 失敗"; exit 1; }
grep -q "${DATE}-test.html" index.html || { say "✗ 首頁沒收錄 $DST"; exit 1; }

# ⛔ 只加這兩個檔。main 沒有 .gitignore，git add -A 會把 state/*.log 掃進去。
git add "$DST" index.html
if git diff --cached --quiet; then
  say "內容沒變化，不用 commit"
  exit 0
fi
git commit -q -m "test: ${DATE} 公司帳號併行版（（測試）條目，不影響正式版）"
git push -q 2>/dev/null || { git pull --rebase -q >/dev/null 2>&1 && git push -q 2>/dev/null; } || { say "✗ push main 失敗"; exit 1; }
say "✓ 已發佈 ${DST} 到 main"
exit 0
