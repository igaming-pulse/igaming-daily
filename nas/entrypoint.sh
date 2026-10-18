#!/usr/bin/env bash
# 容器入口：準備 git 憑證與 repo，然後依參數進入 bot / daily / run-once / shell。
# 憑證全部來自環境變數（NAS 上的 .env），不寫進任何檔案。
set -uo pipefail

REPO="${IGAMING_REPO:-/data/igaming-daily}"
BRANCH="${IGAMING_BRANCH:-test-publish}"
REPO_URL="${IGAMING_REPO_URL:-https://github.com/igaming-pulse/igaming-daily.git}"
say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [entrypoint] $*"; }

mkdir -p "$HOME" || { say "✗ 無法建立 $HOME —— NAS 資料夾權限不足（見 nas/README.md「權限」）"; exit 1; }

# git：身分、憑證（credential helper 直接讀環境變數，硬碟上不存 token）
git config --global user.name  "${GIT_USER_NAME:-iGaming Pulse}"
git config --global user.email "${GIT_USER_EMAIL:-igaming-pulse@users.noreply.github.com}"
git config --global safe.directory '*'
git config --global pull.ff only
if [ -n "${GITHUB_TOKEN:-}" ]; then
  git config --global credential.helper \
    '!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f'
else
  say "⚠️ 沒有 GITHUB_TOKEN：可以讀 repo，但日報無法 push、警報無法觸發"
fi

if [ ! -d "$REPO/.git" ]; then
  say "第一次啟動：clone ${REPO_URL}（${BRANCH}）→ ${REPO}"
  git clone -q -b "$BRANCH" "$REPO_URL" "$REPO" || { say "✗ clone 失敗"; exit 1; }
fi

case "${1:-bot}" in
  bot)
    [ -n "${TELEGRAM_BOT_TOKEN:-}" ] || { say "✗ 沒有 TELEGRAM_BOT_TOKEN"; exit 1; }
    cd "$REPO" && git pull -q || say "⚠️ git pull 失敗，用現有版本"
    exec python3 "$REPO/scripts/telegram_bot.py" ;;
  daily)
    # 優先用 repo 裡的排程（改排程不必重建映像檔），沒有才用映像檔內建的
    cd "$REPO" && git pull -q || say "⚠️ git pull 失敗，用現有版本"
    if [ -f "$REPO/nas/scheduler.sh" ]; then exec bash "$REPO/nas/scheduler.sh"; fi
    exec /usr/local/bin/scheduler.sh ;;
  run-once)            # 手動立刻跑一次：docker compose run --rm daily run-once
    exec bash "$REPO/scripts/run_daily.sh" ;;
  shell)
    exec bash ;;
  *)
    exec "$@" ;;
esac
