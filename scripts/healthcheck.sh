#!/usr/bin/env bash
# 執行環境健檢。換機器、換帳號、或日報出問題時先跑這支。
# 用法：bash scripts/healthcheck.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass=0; fail=0
ok()   { echo "  ✅ $1"; pass=$((pass+1)); }
bad()  { echo "  ❌ $1"; fail=$((fail+1)); }
warn() { echo "  ⚠️  $1"; }

echo "iGaming 日報 — 環境健檢"
echo "repo: $ROOT"
echo "現在（台北）: $(TZ=Asia/Taipei date '+%Y-%m-%d %H:%M')"
echo

echo "[1] 基本工具"
command -v python3 >/dev/null && ok "python3 $(python3 -V 2>&1 | cut -d' ' -f2)" || bad "python3 沒裝"
command -v git     >/dev/null && ok "git $(git --version | cut -d' ' -f3)"      || bad "git 沒裝"
command -v claude  >/dev/null && ok "claude CLI $(claude --version 2>/dev/null | head -1)" || warn "claude CLI 沒裝（排程需要）"
python3 -c "import openpyxl" 2>/dev/null && ok "openpyxl" || bad "openpyxl 沒裝：pip3 install openpyxl --break-system-packages"
echo

echo "[2] repo 檔案"
for f in skills/SKILL.md sources/igaming-daily-report-sources-v2.xlsx \
         scripts/sync_sources.py scripts/build_index.py \
         .github/workflows/telegram-0630.yml .github/workflows/notify-email.yml; do
  [ -f "$f" ] && ok "$f" || bad "缺少 $f"
done
echo

echo "[3] 來源庫"
if python3 scripts/sync_sources.py >/tmp/_sync.log 2>&1; then
  ok "$(head -1 /tmp/_sync.log | sed 's/^✓ //')"
else
  bad "sync_sources.py 失敗：$(tail -1 /tmp/_sync.log)"
fi
echo

echo "[4] GitHub 寫入權"
git config user.name  >/dev/null 2>&1 && ok "git user.name  = $(git config user.name)"  || warn "git user.name 未設"
git config user.email >/dev/null 2>&1 && ok "git user.email = $(git config user.email)" || warn "git user.email 未設"
if git push --dry-run origin HEAD >/tmp/_push.log 2>&1; then
  ok "git push 權限正常"
else
  bad "git push 失敗：$(grep -m1 -E 'remote:|fatal:' /tmp/_push.log || tail -1 /tmp/_push.log)"
fi
echo

echo "[5] 對外連線"
code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 https://api.firecrawl.dev/ 2>/dev/null)
[ "$code" != "000" ] && ok "api.firecrawl.dev 可連（HTTP ${code}）" || bad "api.firecrawl.dev 連不到"
if [ -n "${FIRECRAWL_API_KEY:-}" ]; then
  fc=$(curl -s -o /dev/null -w '%{http_code}' -m 25 -X POST https://api.firecrawl.dev/v1/scrape \
       -H "Authorization: Bearer $FIRECRAWL_API_KEY" -H "Content-Type: application/json" \
       -d '{"url":"https://example.com","formats":["summary"],"onlyMainContent":true}' 2>/dev/null)
  [ "$fc" = "200" ] && ok "Firecrawl 金鑰有效" || bad "Firecrawl 金鑰測試回 HTTP $fc"
else
  warn "FIRECRAWL_API_KEY 未設（日報的配圖與被擋站會抓不到）"
fi
echo

echo "[6] 排程設定（macOS）"
if command -v pmset >/dev/null 2>&1; then
  if pmset -g sched 2>/dev/null | grep -qi wake; then
    ok "pmset 自動喚醒已設定：$(pmset -g sched | grep -i wake | head -1 | xargs)"
  else
    warn "pmset 自動喚醒未設定（見 RUNBOOK §3-1）"
  fi
  if launchctl list 2>/dev/null | grep -q igaming; then
    ok "launchd 排程已載入：$(launchctl list | grep igaming | awk '{print $3}')"
  else
    warn "launchd 排程未載入（見 RUNBOOK §3-2）"
  fi
else
  warn "非 macOS，跳過排程檢查"
fi
echo

echo "─────────────────────────────"
echo "通過 $pass 項，失敗 $fail 項"
[ "$fail" -eq 0 ] && echo "✅ 環境正常，可以跑日報。" || echo "❌ 請先修掉上面的 ❌ 項目。"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
