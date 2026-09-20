# RUNBOOK — iGaming 市場日報自動化

> **這份是換手時唯一需要讀的文件。**
> 設計原則：所有規則、來源、腳本都在這個 repo 裡；Claude 帳號只留「一個排程任務」。
> 換帳號、換機器時，只需要重建第 3 節那一個排程任務，其他都不用動。

最後更新：2026-09-20

---

## 1. 架構總覽

```
台北 02:25   pmset repeat wake ── 機器自己醒來（保險 ①）
台北 02:30   launchd → scripts/run_daily.sh → Claude Code CLI（吃訂閱額度）
             ├─ git pull
             ├─ 讀 skills/SKILL.md，依步驟 0–6 執行
             ├─ 收集 → 交叉查證 → 產 MD → 現寫 HTML
             ├─ 寫 reports/<DATE>.html
             ├─ 寫 state/pending_telegram.txt（+ _url.txt）
             └─ 重建 index → 單次 commit + push
                    │
                    ├──► push 觸發 GitHub Actions（零 token）
                    │      notify-email.yml → 寄 Email
                    │
台北 06:30   GitHub Actions cron（零 token）
             telegram-0630.yml → 發 Telegram
             └─ 守門員：repo 沒有今天的報告 → 發「未產出」警告（保險 ③）

漏跑時：launchd StartCalendarInterval 會在下次開機／喚醒自動補跑（保險 ②）
        補跑的 24h 收集窗照「實際執行時刻往前推 24h」平移，不回頭用 02:30
```

**三層不漏跑保險**

| # | 機制 | 擋什麼 |
|---|---|---|
| ① | `pmset repeat wake` 02:25 | 機器在睡覺，排程時刻醒不來 |
| ② | launchd `StartCalendarInterval` | 排定時刻機器是關的／睡死 → 下次醒來自動補跑一次 |
| ③ | 06:30 Actions 守門員 | 前兩層都失效 → 至少讓你知道今天沒產出 |

**為什麼是這個形狀**

| 環節 | 放哪 | 原因 |
|---|---|---|
| 收集／分析／寫稿 | 本機 Claude Code CLI | 只有這裡能吃訂閱額度。Claude 的雲端（Cowork / Code on the web）被公司工作區政策擋住 GitHub 存取，推不上來。 |
| 發布 | 本機 git | CLI 用本機憑證，沒有 proxy 問題 |
| Email／Telegram／守門員 | GitHub Actions | 零 token、零機器依賴，且換 Claude 帳號完全不受影響 |

> 詳細的診斷過程見 `docs/DECISIONS.md`。

---

## 2. 憑證清單

| 項目 | 放哪 | 誰在用 | 換帳號時 |
|---|---|---|---|
| GitHub 推送憑證 | 執行機器的 git（`gh auth login` 或 SSH key） | 02:30 排程 | **要重設** |
| `FIRECRAWL_API_KEY` | 執行機器的環境變數 | 02:30 排程 | **要重設** |
| `TELEGRAM_BOT_TOKEN` | GitHub Secrets | 06:30 Actions | 不用動 |
| `TELEGRAM_CHAT_ID` | GitHub Secrets | 06:30 Actions | 不用動 |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | GitHub Secrets | Email Actions | 不用動 |
| `MAIL_TO` | GitHub Secrets | Email Actions | 不用動 |

**設定 GitHub Secrets**：repo → Settings → Secrets and variables → Actions → New repository secret

**Gmail SMTP 建議值**

```
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 465
SMTP_USER = <寄件 Gmail 地址>
SMTP_PASS = <16 碼「應用程式密碼」，不是登入密碼>
MAIL_TO   = nathan.kao@bituslabs.com
```

應用程式密碼在 Google 帳戶 → 安全性 → 兩步驟驗證 → 應用程式密碼 產生。

**取得 Telegram chat_id**：先對 bot 傳一則訊息，然後
`curl "https://api.telegram.org/bot<TOKEN>/getUpdates"`，從回傳取 `chat.id`。

> ⚠️ Firecrawl key 與舊 PAT 都曾貼進對話紀錄，移轉完成後建議兩把都撤銷重發。

---

## 3. 排程設定（macOS · 三層保險）

> 排程的 prompt **已經是 repo 內的檔案**：`docs/scheduled-prompt.txt`。
> 換帳號／換機器時不需要複製貼上任何長文字，只要重建下面的排程即可。

### 3-1　保險①：讓機器自己醒來

```bash
sudo pmset repeat wake MTWRFSU 02:25:00
pmset -g sched            # 確認排定成功
```

每天 02:25 自動喚醒，確保 02:30 排程觸發時機器是清醒的。
（筆電闔蓋時此設定不生效，執行機器請維持開蓋或外接電源＋不闔蓋。）

### 3-2　保險②：launchd 排程（漏跑會自動補）

```bash
# 1. 從範本複製，把 __HOME__ 與 __FIRECRAWL_KEY__ 換成實際值
sed -e "s|__HOME__|$HOME|g" -e "s|__FIRECRAWL_KEY__|<你的 Firecrawl 金鑰>|" \
    docs/launchd/com.igaming.daily-0230.plist.example \
    > ~/Library/LaunchAgents/com.igaming.daily-0230.plist

# 2. 載入
launchctl load -w ~/Library/LaunchAgents/com.igaming.daily-0230.plist

# 3. 確認
launchctl list | grep igaming
```

**為什麼用 launchd 而不是 Claude 內建排程**：`StartCalendarInterval` 有「漏跑會補」的特性 ——
排定時刻若機器關機或睡死，**下次醒來會自動補跑一次**。Claude 內建排程沒有這個保證。

### 3-3　⚠️ 第一次設定必做：先手動跑一次

```bash
bash scripts/run_daily.sh
```

要確認的事：

1. **不會停下來問授權**。若停住了，用 `claude --help` 查目前版本正確的旗標名稱，
   改 `scripts/run_daily.sh` 裡的 `CLAUDE_ARGS` 那一行。
2. 跑完 `state/run.log` 有完整紀錄。
3. `git log -1` 看得到當天的 `daily: YYYY-MM-DD report` commit。

**沒手動驗過就直接排程 = 半夜靜悄悄失敗。** 這一步不要跳。

### 3-4　排程 prompt 內容

在 `docs/scheduled-prompt.txt`，由 `run_daily.sh` 自動讀取。
要改規則請改 `skills/SKILL.md`，這個 prompt 檔本身幾乎不需要動。

### 3-5　備案：用 Claude 內建排程

若不想用 launchd，也可以在 Claude 帳號建排程任務，cron `30 2 * * *`、時區 Asia/Taipei、
**權限設為自動核准**，prompt 貼 `docs/scheduled-prompt.txt` 的內容。
代價是**沒有漏跑自動補跑**，只剩保險 ① 和 ③。

---

## 4. 換帳號／換機器的完整步驟

1. 在新機器裝 Claude Code CLI，用**目標帳號**登入
   ```bash
   npm install -g @anthropic-ai/claude-code
   claude          # 進去後 /login，確認 /status 顯示的是目標帳號
   ```
2. clone repo，設定 git 憑證
   ```bash
   git clone https://github.com/igaming-pulse/igaming-daily.git ~/igaming-daily
   cd ~/igaming-daily
   gh auth login          # 或設 SSH key
   git config user.name  "iGaming Pulse"
   git config user.email "igaming-pulse@users.noreply.github.com"
   ```
3. 設 Firecrawl 金鑰（寫進 shell profile 讓排程也讀得到）
   ```bash
   echo 'export FIRECRAWL_API_KEY="<你的金鑰>"' >> ~/.zshrc
   ```
4. 驗證環境
   ```bash
   bash scripts/healthcheck.sh
   ```
5. **先手動跑一次** `bash scripts/run_daily.sh`，確認不會卡授權、log 正常、有 commit（見 §3-3）
6. 依 §3-1、§3-2 設好 `pmset repeat wake` 與 launchd 排程
7. 舊機器的排程**停用但先不刪**，保留兩週當備援
8. 觀察兩天：每天早上確認 Telegram 06:30 有到、網站有更新（Email 最後再接，見 §3 順序說明）

**GitHub Secrets 不用動** —— 它們綁在 repo，不綁帳號。

---

## 5. 日常維運

### 查今天輪掃哪一批

```bash
python3 scripts/rotate_sources.py                    # 今天
python3 scripts/rotate_sources.py --date 2026-10-01  # 指定日期（驗證用）
python3 scripts/rotate_sources.py --size 12          # 改批次大小
```

輪掃池固定 **168** 個新聞型來源，預設每批 **8** 個、**約 21 天**覆蓋一輪、批次由日期決定（無狀態檔）。
切換日可以用 `--date <切換日>` 跟舊環境對一下算出來的是不是同一批。

> ⚠️ **`--size` 直接等於 credit 用量**（每個來源 1 credit）。
> 現行 8 是 2026-09-20 為了控月額度定案的值，**覆蓋變慢是已知且接受的代價**。
> 只有在確定額度有餘裕、且真的需要更頻繁覆蓋來源時，才把 `--size` 往上調 ——
> 調上去要同步改 `skills/SKILL.md` 的整場上限，兩邊不能對不上。

### 改來源清單

```bash
# 1. 用 Excel 開 sources/igaming-daily-report-sources-v2.xlsx，改完存檔
# 2. 重建 sources.md（skill 實際讀的檔）
python3 scripts/sync_sources.py
# 3. 來源有增減時，順手更新運作說明頁
python3 scripts/build_outputlogic.py
# 4. commit
git add -A && git commit -m "sources: update" && git push
```

`sources.md` 是自動產物，**不要手改**。

### 手動補跑某一天

```bash
cd ~/igaming-daily && claude
# 進去後輸入：
#   讀 skills/SKILL.md，依執行步驟補跑 2026-09-18 這天的日報。
#   收集時間窗用 2026-09-17 02:30 ～ 2026-09-18 02:30。
```

### 手動測試通知

- Telegram：repo → Actions → 「Telegram 06:30 推播」→ Run workflow，`dry_run` 填 `true` 先看內容，確認後改 `false` 實際送
- Email：repo → Actions → 「日報 Email 通知」→ Run workflow

### 常見問題

| 症狀 | 多半是 | 怎麼查 |
|---|---|---|
| 早上沒收到 Telegram，也沒收到警告 | Actions 沒跑或 Secrets 沒設 | repo → Actions 看有沒有執行紀錄 |
| 收到「⚠️ 日報未產出」 | 02:30 排程沒跑或 push 失敗 | 看執行機器的排程紀錄、`git log` 有沒有當天的 commit |
| Telegram 有、Email 沒有 | SMTP Secrets 沒設或應用程式密碼失效 | Actions → notify-email 的執行日誌 |
| 網站沒更新 | push 成功但 Pages 還在建 | 等 1 分鐘；仍沒有就看 repo → Settings → Pages |
| 收錄則數偏少 | 來源被擋或當日新聞真的淡 | 看 Telegram 的「📝 品質備註」段 |
| Slot 參數大量「未公布」 | Firecrawl 金鑰失效或額度用完 | `bash scripts/healthcheck.sh` |

---

## 6. 已知限制

- **執行機器要開著。** 02:30 那段跑在本機 CLI。已用三層保險降低漏跑機率（見 §1），但機器長時間關機仍然會漏，06:30 的守門員會通知你。
- **Claude 的雲端跑不了這件事。** Bitus Labs 工作區未開放 GitHub 存取，Cowork 排程任務與 Claude Code on the web 都推不上 repo。若未來工作區開放，02:30 那段就能整段搬上雲端，repo 內容不用改。
- **HTML 模板不凍結**，每次由 LLM 現寫，版面會有輕微漂移（已定案接受）。
- **Firecrawl 額度** 1,125 credits／月，每月 14 日重置。現行設定一次日報 **≤ 14 credits**（輪掃 8 ＋ 其他 ≤ 6），一個月約 **420**，額度充裕 —— 併行期兩邊同時跑也不會爆。

---

## 7. 接通順序（2026-09-20 定案）

先求穩，再求全。不要一次接所有東西：

| 順序 | 做什麼 | 驗收標準 |
|---|---|---|
| 1 | repo 骨架推上 `test-publish` | GitHub 上看得到檔案 |
| 2 | 執行機器跑 `healthcheck.sh` 全綠 | push 權限、Firecrawl 都通 |
| 3 | 手動跑一次 `run_daily.sh` | 不卡授權、有 commit、網站更新 |
| 4 | 設 Telegram Secrets → Actions 手動 `dry_run` | 訊息內容正確 |
| 5 | 設好 pmset ＋ launchd，觀察兩晚 | 連兩天自動產出 |
| 6 | **最後**才設 `SMTP_*` / `MAIL_TO` | 收到 Email |

Email 刻意排最後 —— 前面沒穩之前接它只會增加變數。
兩支 workflow 在 Secrets 沒設時都會**安靜跳過**（exit 0），不會讓 Actions 變紅。

> ⚠️ **併行期規則**：在明確宣告「交接完整完成」之前，日報仍由**舊環境**每天照發。
> 新環境只在 `test-publish` 做平行測試，**不要接手 `main`**。切換日另行決定。

---

## 8. 相關文件

| 檔案 | 內容 |
|---|---|
| `skills/SKILL.md` | 收集、查證、渲染的完整規則（唯一真相） |
| `docs/DECISIONS.md` | 架構決策與診斷紀錄 |
| `sources/sources.md` | 來源清單（自動產物，勿手改） |
| `docs/scheduled-prompt.txt` | 排程任務實際餵給 Claude 的 prompt |
| `docs/launchd/*.plist.example` | macOS 排程範本 |
| `OutputLogic.md` / `OutputLogic/` | 對外的運作說明頁 |
