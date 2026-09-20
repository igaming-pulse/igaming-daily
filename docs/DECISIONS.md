# 架構決策紀錄

> 記錄「為什麼是現在這個形狀」，讓未來接手的人（或未來的自己）不用重新踩一次坑。
> 依時間倒序。

---

## 2026-09-20（下午）— 原帳號裁示：砍 Firecrawl 用量、加不漏跑保險

v2 骨架送審後收到四點裁示，其中兩點改設定。

### ⚠️ Firecrawl 用量砍到 9–14 credits／天

| 參數 | 原值 | 改成 |
|---|---|---|
| `rotate_sources.py` 批次 | 30 | **8** |
| 整場 firecrawl 上限 | ≤ 45 | **≤ 14** |
| WebSearch 上限 | ≤ 20 | 維持 ≤ 20 |
| 薄弱日加碼 | 另外 +15 次 | **收進 14 的總額內，不另外開** |

**代價**：覆蓋 168 個新聞型來源從「6 天一輪」變成「**約 21 天一輪**」。
這是**已知並接受**的取捨 —— 優先保住月額度。

**驗證**：21 天覆蓋 168 個、零重複、每批固定 8 個。
月用量從約 1,050–1,350（會爆 1,125 額度）降到約 **420**，併行期兩邊同跑也安全。

> 這條**覆蓋掉** ROUND4 的「firecrawl ≤ 45」—— 當時沒把月額度算進去。

其他省 credit 原則升級為硬規則：**嚴禁開 5-credit 的 JSON 抽取**；
og:image 跟 summary 同一次免費帶回、不另抓。

### 🛡️ 不漏跑：從一層變三層

原本只靠「機器剛好醒著」，不夠。改成：

| # | 機制 | 擋什麼 |
|---|---|---|
| ① | `pmset repeat wake` 02:25 | 機器在睡覺、排程時刻醒不來 |
| ② | launchd `StartCalendarInterval` | 排定時刻機器是關的／睡死 → **下次醒來自動補跑一次** |
| ③ | 06:30 Actions 守門員 | 前兩層都失效 → 至少讓人知道今天沒產出 |

保險 ② 是選 launchd 而非 Claude 內建排程的**唯一理由** —— 內建排程沒有漏跑補跑的保證。

連帶新增三個檔：

- `docs/scheduled-prompt.txt` —— 排程 prompt 變成 repo 內的檔案，換機器時不用複製貼上長文字
- `scripts/run_daily.sh` —— launchd 呼叫的入口，負責 pull、跑 claude、寫 log
- `docs/launchd/com.igaming.daily-0230.plist.example` —— 排程範本

**補跑的時間窗**寫進 SKILL 硬規則：窗 ＝ **實際執行時刻**往前推 24 小時，
不是回頭用原定的 02:30 當起點。補跑時要在回報中註明實際窗。

### 其他兩點

- **Email 排最後接**。前面（骨架 → healthcheck → 手動跑 → Telegram → 自動排程）都穩了再設 `SMTP_*`。
  兩支 workflow 在 Secrets 沒設時會安靜跳過，不會讓 Actions 變紅。RUNBOOK §7 有完整順序表。
- **切換日不敲定**。在明確宣告「交接完整完成」前，日報仍由舊環境每天照發；
  新環境只在 `test-publish` 平行測試，不接手 `main`。

---

## 2026-09-20（上午）— 納入原帳號 ROUND4 更新

原帳號在 9/14 交接後又做了幾項變更，這裡一併吸收。

### 🔁 每日輪掃制（最重要）

**問題**：舊規則為了不撞額度，叫模型「別把 223 個來源全掃一遍，優先 ⭐ 重點來源＋精準搜尋」。
副作用是**絕大多數來源庫平常根本沒被主動觸及，等於白養**。

**解法**：在廣搜之外，每天固定輪流直接查一批來源，**由日期決定批次、無需狀態檔**
（半夜全新無記憶的 session 也算得出同一批），約 6 天把 168 個新聞型來源覆蓋一輪（**批次大小後來改為 8，變成約 21 天一輪**）。

新增 `scripts/rotate_sources.py`。輪掃池只含五個有每日新聞價值的分類
（Provider 官網 27＋產品分析／評測 11＋產業媒體 96＋市場數據 18＋監理機關 16 ＝ **168**）；
展會／論壇／Podcast／協會認證／已停用不進池。**已驗證：6 天覆蓋 168 個、零重複。**

**預算連帶調整**：ROUND4 原本把整場上限放寬為 `≤ 45`，但那沒把月額度（1,125）算進去。
**已被同日下午的裁示覆蓋成 `≤ 14`、批次 8** —— 見本檔最上面一節。

### 🔦 薄弱日再加碼

正常搜尋 ＋ 輪掃後五區合計仍 < 15 則，才針對不在今日批次內的 ⭐ 優先品牌官網＋產業媒體多挖，
上限再 +15 次，湊到 15 即停；仍不足就老實少收。有觸發要在 Telegram 品質備註加一則。

### 其他

| 變更 | 說明 |
|---|---|
| 日報 HTML 必附 favicon 三行 | 用 `../icon-*.png`（日報在 `reports/` 子目錄）。圖示檔已在 repo 根目錄，勿重產 |
| `build_index.py` 加 `LABEL_OVERRIDE` | 合併回顧日報：檔名沿用起始日（確保被掃描器收錄、排序正確），首頁卡片顯示合併標籤。目前一筆：`2026-09-08` → 「2026-09-08＋09／週二/三」 |
| `build_index.py` 首頁 favicon | 用不帶 `../` 的相對路徑 |
| 無人值守 Bash 規則 | 定位檔案直接用已知路徑 ＋ Read 工具，**禁用 `ls`／`find` 探測** —— 複合／探測型指令在半夜排程會觸發授權詢問、卡死流程 |

> ⚠️ **沒有照抄的一項**：原帳號的 `publish.sh` 硬指 `/usr/bin/python3`，因為**那台 Mac** 的
> `/usr/local/bin/python3` 架構損壞（Bad CPU type，Homebrew 問題）。
> 那是該機器的環境問題、不是流程需求，本 repo 維持 `python3`。
> 若未來某台執行機器也有這問題，在該機器上處理，不要改進 repo。

---

## 2026-09-19 — 定案：本機 CLI ＋ GitHub Actions 混合

### 背景

要把日報自動化從 natekao 帳號移轉到 nathan.kao@bituslabs.com，讓 token 算在後者的訂閱額度上。附帶硬約束：**未來還要能再搬回去**，所以規則與資料都要放在 repo。

### 卡住的地方

原本規劃「02:30 用 Cowork 排程任務在雲端產內容並 push」。實測後發現**做不到**：

| 嘗試 | 結果 |
|---|---|
| `git push`（靠 proxy 注入憑證） | 403 `not in this session's authorized repository set` |
| `git push`（URL 自帶 PAT） | **一模一樣的 403** —— proxy 在授權層攔截，不看憑證 |
| GitHub REST API 寫檔 | `Write access to this GitHub API path is not permitted through this proxy` |
| 容器直接連外轉送 | egress 白名單只放行 github／anthropic／npm／pypi |

根因在 Claude Code on the web 的提示裡說得最清楚：

> GitHub access is required for Claude Code on the web. Please contact an organization owner.

**這裡的 organization owner 指 Bitus Labs 的 Claude 工作區管理者**，不是 GitHub 組織的 Owner。同一個原因造成三個現象：git proxy 拒絕、Cowork 的 Connectors 沒有 GitHub、Code on the web 擋在門口。

`api.firecrawl.dev` 被同一份連外政策擋住（DNS 解析正常，CONNECT 回 403）。

### 為什麼不走「全雲端」

全雲端＝把收集與寫稿也搬進 GitHub Actions。Actions 裡呼叫 Claude 只能用 **Anthropic API（按量計費）**，吃不到訂閱額度 —— 那就違背了移轉的原始目的。

### 定案

**「需要 Claude 智能」的那一段留在本機 CLI（吃訂閱額度），其餘全部搬進 GitHub Actions（零 token、零機器依賴）。**

一個重要的認知修正：原始需求是「換登入帳號」，不是「換執行環境」。可攜性靠的是**東西放在 repo 裡**，不是跑在雲端。所以只要規則、來源、腳本、RUNBOOK 都在 repo，換帳號就只是換登入而已。

### 若未來工作區開放 GitHub 存取

02:30 那一段可以整段搬上 Claude 雲端排程任務，**repo 內容一個字都不用改** —— 只要把 RUNBOOK 第 3 節的 prompt 貼到雲端排程任務即可。這是刻意保留的升級路徑。

---

## 2026-09-19 — repo 結構重整

| 變更 | 原因 |
|---|---|
| 三支 skill 合併成 `skills/SKILL.md` | 規則放 repo 不放帳號，換帳號時不用重建 |
| 腳本移進 `scripts/`，全部改 repo 相對路徑 | 原本寫死 `~/Desktop/All-in AI/...`，違反可攜性 |
| xlsx 主檔 commit 進 `sources/` | 雲端與新機器都沒有 Desktop |
| 砍掉 sync 腳本的 AUTO-HEAL 反向重建 | 進 git 後版控就是備份 |
| 砍掉 `sources.json` | v2.3 舊設定，與 SKILL 規則互相矛盾（`max_items:10` vs 13–22、只收 3 地區、EKG 指向已停站網域、四大分類） |
| 來源總數改由 xlsx 動態帶入 | 四份文件曾有四個版本（218／221／222／223），實際 223 |
| commit message 改 `daily: YYYY-MM-DD report` | 機器可讀，已定案 |
| Telegram／Email 改由 Actions 發送 | 零 token；launchd 是 Mac 專屬，不可攜 |
| 06:30 job 加守門員 | 同時攔「沒跑」與「跑了但推播失敗」 |
| 日報改成**單次 push** | 分兩次會讓 Email workflow 觸發兩次 |

### 順手修掉的既有矛盾

- `daily-report-html` 的標題寫「四大分類版」、Phase 2 只解析四區，但色彩系統列五色 → 清成五分類
- 非 Slot 顏色自相矛盾：色彩系統寫 `#B31217`（血紅）、文末註解寫 `#0EA5A5`（青色）→ **成品是血紅，青色作廢**
- OutputLogic 頁寫死「218 個來源、10 大分類」→ 改成從 xlsx 動態算
- `sources.md` 只有 222 筆（已停用只帶 1 筆）→ 新的 sync 腳本保留全部 223 筆

---

## 2026-09-14 — 內容與成本規則定案

| 項目 | 定案 |
|---|---|
| 交叉查證次數 | 每則上限 **3 次**（原為 6 次） |
| HTML 模板 | **不凍結**，維持 LLM 每次現寫（接受版面輕微漂移） |
| Telegram 訊息 | **一則**（摘要＋文末品質備註＋一顆 inline 按鈕）。截圖看到的兩則是 09-14 手動補跑的一次性產物 |
| 品質備註 | **只能出現在 Telegram**，嚴禁進日報或 Email |
| Email 附件 | 砍掉（約 4.8 萬字元的 base64 常常附不上） |
| 時間 | 02:30 產出＋Email、06:30 Telegram（台北），照搬不改 |
| 收集時間窗 | 固定 24 小時滾動窗＝執行時刻往前推 24h |
| 最低 token 成本 | **加分項，不是硬約束**。品質與達成目的優先 |
| commit 作者 | 中性身分 `iGaming Pulse <igaming-pulse@users.noreply.github.com>` |

### 預算參考（原帳號實測）

產 17 則約 **29 次工具呼叫**（WebSearch ~18、firecrawl 5、WebFetch ~6）、Firecrawl 約 **9 credits**。

建議硬上限：WebSearch ≤ 20、firecrawl ≤ 12／整場。
省 credit 關鍵：少用 JSON 抽取（5 credits vs 1 credit）；og:image 跟摘要同一次拿。

---

## 併行期與切換

- 併行期間 natekao 端繼續推 `main`；新環境先推 `test-publish` 分支，**不碰 main、不碰 reports/**
- 切換日由 Nathan 拍板，建議挑平日、非重大展會／財報日
- 切換流程：前一天 natekao 照常跑 → 當天 natekao 先停排程 → 新環境同日接手，不留空窗
- 切換後舊機器排程**停用不刪**，保留兩週當備援
- Firecrawl 額度 1,125 credits／月、每月 14 日重置。併行期兩邊同時跑可能超支，必要時舊端暫時關掉 JSON 抽取降用量
