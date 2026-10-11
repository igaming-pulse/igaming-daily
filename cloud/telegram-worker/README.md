# Telegram 機器人搬到 Cloudflare Workers（雲端版）

目的：Telegram 查詢不再依賴公司 Mac。Telegram 收到訊息會主動通知 Cloudflare 上的程式（`worker.js`），
它從 GitHub 讀最新的庫存與日報資料回覆，24 小時都在、免費。

## 一次性設定（約 15 分鐘）

### 1. 註冊 Cloudflare 帳號
1. 打開 https://dash.cloudflare.com/sign-up
2. 用**你個人的 email** 註冊（換工作也帶得走），設定密碼 → 收驗證信點連結
3. 登入後如果問你要不要加網站（Add a site / domain），**跳過**，Workers 不需要網域

### 2. 建立 Worker
1. 左側選單點 **Workers & Pages**（有些版本叫 **Compute (Workers)**）
2. 點 **Create** →（選 **Workers**）→ **Create Worker**（或「Start with Hello World!」）
3. 名稱填 `igaming-tg-bot` → **Deploy**
4. 部署完會看到網址，例如 `https://igaming-tg-bot.<你的子網域>.workers.dev`，先記下來
   （第一次用 Workers 會請你取一個子網域名稱，隨便取，例如你的英文名）

### 3. 貼上程式
1. 在剛建好的 Worker 頁面點 **Edit code**
2. 左邊的 `worker.js`（或 `index.js`）**全部刪掉**
3. 貼上這個 repo 的 `cloud/telegram-worker/worker.js` 全部內容
   （GitHub 網址：https://github.com/igaming-pulse/igaming-daily/blob/test-publish/cloud/telegram-worker/worker.js → 點右上「Raw」→ 全選複製）
4. 右上角 **Deploy**

### 4. 設定三個變數
1. 回到 Worker 頁面 → **Settings** → **Variables and Secrets** → **Add**
2. 依序新增：

| 名稱 | 類型 | 值 |
|---|---|---|
| `BOT_TOKEN` | **Secret** | @BotFather 給的 bot token（跟每天推日報的是同一個 bot） |
| `WEBHOOK_SECRET` | **Secret** | 在終端機跑 `openssl rand -hex 16` 產生的一串亂碼 |
| `ALLOWED_CHAT_ID` | Text | `606981537` |

3. 每新增一個就按 **Save / Deploy**

### 5. 啟用（只要開一次網址）
瀏覽器打開：

```
https://igaming-tg-bot.<你的子網域>.workers.dev/setup?key=<你的 WEBHOOK_SECRET>
```

看到「✓ 完成」就好了。回 Telegram 打「狀態」或「/」試試。

### 6. 停掉本機機器人（如果有裝）
雲端版啟用後，本機版會收不到訊息（Telegram 一次只能交給一個地方），要把它停掉：

```bash
launchctl unload -w ~/Library/LaunchAgents/com.igaming.telegram-bot.plist
```

## 之後

- **更新程式**：Worker 頁面 → Edit code → 貼上新版 → Deploy
- **不開 Telegram 直接看某個指令的回覆**：`https://…workers.dev/test?key=<WEBHOOK_SECRET>&q=庫存`
- **改回本機機器人**：開 `https://…workers.dev/unset?key=<WEBHOOK_SECRET>`，再在 Mac 上 `launchctl load -w ~/Library/LaunchAgents/com.igaming.telegram-bot.plist`
- **資料多新**：讀 GitHub 上的檔案，每晚日報推上去後幾分鐘內就是最新
