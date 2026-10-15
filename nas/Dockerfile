# iGaming 日報 — Synology NAS（Container Manager）用的執行環境
# 同一個 image 跑兩個服務：bot（Telegram 查詢）與 daily（每天 02:30 產日報）。
# 程式碼不放在 image 裡：容器啟動時把 repo clone 到 /data/igaming-daily（NAS 上的資料夾），
# 之後靠 git pull 更新，改程式不用重建 image。
FROM python:3.12-slim

ENV TZ=Asia/Taipei \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    DISABLE_AUTOUPDATER=1 \
    HOME=/data/home \
    IGAMING_REPO=/data/igaming-daily

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates tzdata procps \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir openpyxl

# Claude Code 原生安裝版（不需要 Node）。裝完把執行檔複製到系統路徑，任何 uid 都能用。
RUN HOME=/root curl -fsSL https://claude.ai/install.sh | HOME=/root bash \
 && cp -L /root/.local/bin/claude /usr/local/bin/claude \
 && rm -rf /root/.local /root/.claude* \
 && claude --version

COPY entrypoint.sh scheduler.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/entrypoint.sh /usr/local/bin/scheduler.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bot"]
