#!/usr/bin/env bash
# 在 Mac 上執行：把新的 GitHub token 寫進 NAS 的 secrets.env（從剪貼簿讀，畫面不顯示、也不印出）
#   bash ~/igaming-daily/nas/set_github_token.sh
#
# 2026-11-21：NAS 原本用的是從 Mac 鑰匙圈複製來的 git 憑證，11/16 起失效（Invalid username or token），
# 日報在 NAS 產出卻推不上 GitHub 五天。改用專屬的 fine-grained token（只開 igaming-daily 這個 repo）。
# 寫入前會先用這組 token 實際連一次 GitHub 驗證：讀得到 repo、看得到 Actions，才寫進去。
set -uo pipefail
OUT="${1:-/Volumes/docker/igaming-daily/secrets.env}"
REPO_API="https://api.github.com/repos/igaming-pulse/igaming-daily"
[ -f "$OUT" ] || { echo "✗ 找不到 $OUT，先在 Finder 掛上 NAS 的 docker 資料夾"; exit 1; }

echo "════════════════════════════════════════════════════"
echo " 到 GitHub 剛產生 token 的頁面，按 token 旁邊的複製圖示（或選起來 ⌘C）"
echo " （不用貼到這裡，也不要打在終端機上）"
echo " 複製好之後，回到這裡按 Enter"
echo "════════════════════════════════════════════════════"
read -r _
TOKEN=$(pbpaste | python3 -c '
import re, sys
m = re.search(r"(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,})", sys.stdin.read())
print(m.group(1) if m else "")
')
[ -n "${TOKEN}" ] || { echo "  ✗ 剪貼簿裡找不到 GitHub token（github_pat_ 或 ghp_ 開頭）。請重新複製再跑一次，secrets.env 沒有改動。"; exit 1; }

code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" "${REPO_API}")
[ "$code" = "200" ] || { echo "  ✗ 這組 token 讀不到 igaming-pulse/igaming-daily（HTTP ${code}）。確認 Resource owner 選 igaming-pulse、Repository 有勾 igaming-daily。secrets.env 沒有改動。"; exit 1; }
code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" "${REPO_API}/actions/workflows")
[ "$code" = "200" ] || { echo "  ✗ 這組 token 沒有 Actions 權限（HTTP ${code}），06:30 推播會失敗。請把 Actions 設成 Read and write。secrets.env 沒有改動。"; exit 1; }
git ls-remote "https://x-access-token:${TOKEN}@github.com/igaming-pulse/igaming-daily.git" HEAD >/dev/null 2>&1 \
  || { echo "  ✗ git 用這組 token 連不上（Contents 權限不足？）。secrets.env 沒有改動。"; exit 1; }
printf '' | pbcopy   # 用完清空剪貼簿

TMP=$(mktemp); umask 077
grep -v '^GITHUB_TOKEN=' "$OUT" > "$TMP"
echo "GITHUB_TOKEN=${TOKEN}" >> "$TMP"
cat "$TMP" > "$OUT" && rm -f "$TMP"
echo "  ✓ GitHub token 驗證通過（讀 repo、Actions、git 連線都正常），已寫入（${#TOKEN} 字元）"
echo "接著到 Container Manager：專案 igaming-daily → 停止 → 操作 → 清除 → 操作 → 建立"
