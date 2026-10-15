# iGaming 日報 — 搬到 Synology NAS（DS1525+）

目標：02:30 日報和 Telegram bot（`/stock` 等）改由 NAS 24 小時執行，Mac 可以關機。

```
NAS（Container Manager）
├── igaming-bot     常駐，回應 Telegram 指令
└── igaming-daily   每天 02:30 跑 scripts/run_daily.sh（10:00 前重開機會自動補跑）
       兩者共用 data/igaming-daily（repo）與 data/home（Claude、git 設定）
```

06:30 的 Telegram 推播本來就在 GitHub Actions，不受影響。

---

## 事前準備（在 Mac 上做，公司或家裡都可以）

準備四個值，最後填進 `secrets.env`。**不要貼到聊天或任何文件裡。**
最省事：在 Mac 執行 `bash ~/igaming-daily/nas/fill_secrets.sh`，Telegram／GitHub／Firecrawl 會從 Mac 現有設定自動帶入，Claude token 從剪貼簿讀。

| 值 | 怎麼拿 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram → @BotFather → `/mybots` → 選 bot → API Token |
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → Fine-grained tokens → Generate。Resource owner 選 **igaming-pulse**，Repository 只勾 `igaming-daily`，權限：**Contents：Read and write**、**Actions：Read and write**。有效期限最長 1 年，到期前要換 |
| `CLAUDE_CODE_OAUTH_TOKEN` | Mac 終端機執行 `claude setup-token`，瀏覽器登入後會印出一串 `sk-ant-oat…`（108 字元，有效 1 年）。⚠️ **它會折成 2–3 行，直接 ⌘C 會連換行一起複製，貼上會斷掉、要手動拼回一行**。用 `fill_secrets.sh` 就不用拼：把那幾行 ⌘C 後執行腳本，它會從剪貼簿自動拼接 |
| `FIRECRAWL_API_KEY` | firecrawl.dev → API Keys（跟 Mac 上 `~/.zshrc` 裡的是同一把） |

---

## 第一階段：在 NAS 上架設（要在家裡同一個網路）

### 1. 安裝 Container Manager
DSM（瀏覽器開 `http://192.168.1.116:5000`）→ 套件中心 → 搜尋 **Container Manager** → 安裝。
安裝後會自動多出一個共用資料夾 `docker`。**不需要開 SSH。**

### 2. 放檔案
1. Finder → ⌘K → `smb://192.168.1.116/docker` → 連線
2. 在裡面建資料夾 `igaming-daily`
3. 把 repo 的 `nas/` 裡這幾個檔案複製進去：
   `Dockerfile`、`docker-compose.yml`、`entrypoint.sh`、`scheduler.sh`、`secrets.env.example`
4. 把 `secrets.env.example` 複製一份改名為 **`secrets.env`**，用文字編輯打開填入四個值
5. 在同一層建一個空資料夾 `data`

### 3. 權限
`docker-compose.yml` 裡的 `user: "1026:100"` 是 DSM **第一個自建帳號**的預設 uid（1026）和 users 群組（100）。
如果啟動後 log 出現「無法建立 /data/home」或 `Permission denied`：
File Station → `docker/igaming-daily/data` → 右鍵 內容 → 權限 → 新增 **Everyone：讀寫** → 套用到子資料夾。

### 4. 建立專案
Container Manager → **專案** → 新增：
- 專案名稱：`igaming-daily`
- 路徑：`/docker/igaming-daily`
- 來源：**使用現有的 docker-compose.yml**
- 下一步 → 完成（第一次會 build image，約 3–5 分鐘）

### 5. 先停 Mac 上的 bot（同一個 bot 只能有一處在跑）
Mac 終端機：
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.igaming.telegram-bot.plist
```

### 6. 驗證
- Container Manager → 容器 → `igaming-bot` → 日誌：看到 bot 啟動訊息、沒有錯誤
- Telegram 傳 `/stock` → 有回覆 ✅
- `igaming-daily` 日誌：看到「下次執行：…02:30」

---

## 第二階段：日報併行驗證（約 1 週）

Mac 和 NAS **不能同時 02:30 跑**（會重複花 Claude 額度、git 推送互相衝突）。
做法：**NAS 02:30 主跑，Mac 改到 05:30 當備援**。`run_daily.sh` 開頭會 `git pull`，看到今天已有成功的日報 commit 就自動略過，所以 NAS 成功時 Mac 什麼都不做；NAS 失敗時 Mac 補上。

Mac 改時間：把 `~/Library/LaunchAgents/com.igaming.daily-0230.plist` 的 Hour 改成 5、Minute 改成 30，然後重新載入。

每天早上看：
- Telegram 有沒有正常推播
- GitHub commit 作者時間在 02:30 之後一小時內 → NAS 跑的
- `data/igaming-daily/state/run.log`（用 SMB 打開）

## 第三階段：退役 Mac（連續一週都由 NAS 完成後）

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.igaming.daily-0230.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.igaming.keepawake.plist
```
plist 檔先不要刪，萬一 NAS 出問題可以 `launchctl bootstrap` 載回來。

---

## 日常操作

| 想做的事 | 怎麼做 |
|---|---|
| 立刻補跑日報 | Container Manager → 容器 → `igaming-daily` → 重新啟動（10:00 前才會補跑）；或任何時間在「動作 → 開啟終端機」執行 `bash /data/igaming-daily/scripts/run_daily.sh` |
| 強制重跑今天 | 終端機：`IGAMING_FORCE=1 bash /data/igaming-daily/scripts/run_daily.sh` |
| 看紀錄 | SMB 打開 `docker/igaming-daily/data/igaming-daily/state/run.log` |
| 更新 Claude 版本 | Container Manager → 專案 → 動作 → 建置（重 build image） |
| 換 token | 改 `secrets.env` → 專案 → **停止** → **操作 → 建立**（⚠️ 單純停止／啟動不會重讀 `secrets.env`，容器建立時就把值存起來了） |
| 程式碼更新 | 不用動：每次跑日報、bot 啟動都會 `git pull` |

## 會收到的警報

| Telegram 訊息 | 處理 |
|---|---|
| NAS 的 Claude token 失效 | Mac 執行 `claude setup-token` → 把 token 那幾行 ⌘C → `bash ~/igaming-daily/nas/fill_secrets.sh` → 專案 停止 → 操作 → 建立 |
| 日報沒有產出／沒有發布 | 看 `run.log` 最後一段，或跟 Claude 說「補跑日報」 |
| bot 沒回應 | Container Manager 看 `igaming-bot` 是否在跑、日誌有無錯誤 |

## 安全
- `secrets.env` 只放在 NAS，`.gitignore` 已排除，不會被推上 GitHub。
- 容器以一般使用者（非 root）執行，只看得到 `docker/igaming-daily/data`，**碰不到 `謎_T1` 等其他共用資料夾**。
- 不需要開 SSH、不需要路由器 port forwarding：bot 和日報都是 NAS 主動連出去。
