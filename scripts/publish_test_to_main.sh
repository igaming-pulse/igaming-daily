#!/usr/bin/env bash
# 併行期專用：把 test-publish 上當天的日報，另外以「<DATE>-test.html」
# 發佈到 main，首頁會多一張（13' v）卡片，供與正式版並排比對。
# 切換日後 run_daily.sh 在分支為 main 時會自動跳過這一步。
#
# v2（2026-10-05）：
#   - 改在暫存 worktree 裡處理 main，每天排程用的工作目錄永遠不離開 test-publish
#     （10/5 舊版在原目錄切到 main、rebase 卡在 index.html 衝突，連帶切不回 test-publish）
#   - 只有 index.html 衝突時自動重建首頁、續 rebase（照 15' v 的 publish.sh 做法），最多重試 3 次；
#     其他檔案衝突 → abort，不留下合併到一半的狀態
#   - report_theme 產生的原始樣式備份 reports/_classic/ 一起提交（回滾才還原得到）
set -uo pipefail

REPO="${IGAMING_REPO:-$HOME/igaming-daily}"
cd "$REPO" || exit 1

DATE="${1:-$(TZ=Asia/Taipei date +%F)}"
SRC="$REPO/reports/${DATE}.html"
DST="reports/${DATE}-test.html"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")

say() { echo "  [test→main] $*"; }

[ "$BRANCH" = "main" ] && { say "已在 main，不需要併行條目，略過"; exit 0; }
[ -f "$SRC" ] || { say "✗ 找不到 reports/${DATE}.html，略過"; exit 1; }

git worktree prune >/dev/null 2>&1
git fetch -q origin main || { say "✗ 抓不到 origin/main"; exit 1; }
WT=$(mktemp -d /tmp/igaming-main-XXXXXX)
cleanup() { git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"; git -C "$REPO" worktree prune >/dev/null 2>&1; }
trap cleanup EXIT
git worktree add -q --detach "$WT" origin/main || { say "✗ 建不了 main 的暫存 worktree"; exit 1; }
cd "$WT" || exit 1

cp "$SRC" "$DST"
python3 - "$DST" <<'PY'
import sys, re, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
if '（測試）' not in s:
    s = re.sub(r'(<title>)(.*?)(</title>)', r'\1\2（測試）\3', s, count=1)
    s = re.sub(r'(<h1[^>]*>)(.*?)(</h1>)', r'\1\2（測試）\3', s, count=1, flags=re.S)
p.write_text(s, encoding='utf-8')
PY

python3 build_index.py >/dev/null || { say "✗ build_index.py 失敗"; exit 1; }
grep -q "${DATE}-test.html" index.html || { say "✗ 首頁沒收錄 $DST"; exit 1; }

# ⛔ 只加這幾個路徑。main 沒有 .gitignore，git add -A 會掃進不該進的東西。
git add "$DST" index.html
[ -d reports/_classic ] && git add reports/_classic
if git diff --cached --quiet; then
  say "內容沒變化，不用 commit"
  exit 0
fi
git commit -q -m "test: ${DATE} 公司帳號併行版（13' v 條目，不影響正式版）"

for try in 1 2 3; do
  git push -q origin HEAD:main 2>/dev/null && { say "✓ 已發佈 ${DST} 到 main"; exit 0; }
  say "push 被拒（第 ${try} 次），同步 origin/main 後重試…"
  git fetch -q origin main || continue
  if ! git rebase -q origin/main >/dev/null 2>&1; then
    conflicts=$(git diff --name-only --diff-filter=U)
    if [ "$conflicts" = "index.html" ]; then
      # 首頁是自動產物：取 main 最新版，再用網站程式重建（兩台機器的卡片都會在）
      git checkout --ours index.html >/dev/null 2>&1
      python3 build_index.py >/dev/null || { git rebase --abort; say "✗ 重建首頁失敗"; exit 1; }
      git add index.html
      [ -d reports/_classic ] && git add reports/_classic
      GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || { git rebase --abort; say "✗ rebase 續不下去"; exit 1; }
      say "首頁衝突已自動重建"
    else
      git rebase --abort >/dev/null 2>&1
      say "✗ 非首頁的檔案衝突（${conflicts//$'\n'/、}），放棄本次發布，請人工處理"
      exit 1
    fi
  fi
done
say "✗ push main 失敗（重試 3 次）"
exit 1
