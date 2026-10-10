---
name: igaming-daily
description: iGaming 市場日報自動化 — 收集、交叉查證、產 Markdown、渲染 HTML、發布 GitHub Pages、預存 Telegram。五大分類版 v6.5（三層收集＋庫存＋定稿檢查）。
---

# iGaming 市場日報 — 完整規則（v6.5 · 三層收集＋庫存＋定稿檢查版）

> 本檔是三支舊 skill（`daily-news-report` / `daily-report-html` / `scheduled-task`）合併後的唯一真相。
> **規則放在 repo，不放帳號 Skill** —— 換 Claude 帳號時這份不用動。
> 排程任務的 prompt 只負責：clone/pull repo → 讀這份 → 依序執行。

全程用**繁體中文**、**台北時間（Asia/Taipei）**。

---

## ⛔ 最高優先的三條硬規則

1. **嚴禁平行 sub-agent**。全程在主線程循序、分批處理。（原帳號撞每週用量上限的元凶就是這個。）
2. **交叉查證只增不減**。查證的目的是補足與更正，**嚴禁把已有資訊刪掉或降級成「未公布」**。
3. **每則必附真實可點擊原文 URL**。嚴禁編造或猜測，抓不到真實 URL 的不得收錄。
4. **每則必須有 1 個「主來源」，其發布日期含年份、且落在收集時間窗內**（v6.2）。
   內文提到的活動日期（「9 月 22 日上線」）**不算發布日期**。細則見「📅 主來源日期規則」。

---

## 執行步驟

先執行 `TZ=Asia/Taipei date` 取得今天的台北日期 `YYYY-MM-DD`，以下以 `<DATE>` 表示。
所有路徑皆相對於 **repo 根目錄**（以下以 `<REPO>` 表示）。

### 步驟 0 — 同步來源庫

```bash
python3 <REPO>/scripts/sync_sources.py
```

把 `sources/igaming-daily-report-sources-v2.xlsx`（唯一真相）重建成 `sources/sources.md`（本 skill 實際讀取的檔）。

- 需要 `openpyxl`。缺了就 `pip3 install openpyxl --break-system-packages`。
- **此步失敗不致命**：照常往下跑，並在步驟 6 回報「來源庫同步失敗」。
- 腳本會印出實際來源筆數與分類數，**後續任何需要引用來源總數的地方一律用這個數字**，嚴禁寫死。

### 步驟 1 — 收集並產出日報 Markdown

依本檔「內容規格」章節收集。**v6.4 起改為「三層收集 → 打分 → 查證 → 庫存」，順序不可對調**：

**第零段｜讀程式備好的候選與庫存（v6.4 新增，一定先做）**
1. 讀 `<REPO>/state/harvest/<DATE>.md`。這是 `scripts/harvest.py` 在你開跑前產生的候選清單：
   約 90 個 WP-API／RSS 來源＋BigWinBoard 新作列表，**每則都有精確到分鐘的台北發布時間**，
   並已依關鍵字預判分類；開頭有「💳 Firecrawl 今日分級」與**今天文章抓取上限**；最後附「第二層 Firecrawl 列表頁」存檔路徑。
   v6.5 起 BigWinBoard、SlotsLaunch 上線日曆、EEGaming、SBC News、IAG 都由程式免費抓並併入候選，iGamingToday 列表頁也由程式解析；
   窗外近期的候選另存 `state/harvest/<DATE>-backlog.md`（需要庫存補位時再讀）。
   - 檔案不存在、或標頭的「收集時間窗」不是這次的窗 → 自己跑 `python3 <REPO>/scripts/harvest.py`
     （補跑舊日期加 `--date <DATE> --anchor 02:30`），跑完再讀。
2. 讀第二層列表頁存檔中**標「請讀檔」的那幾個**（輪掃、觸發、週六 Weekend Reels），從 markdown 解析出**窗內**條目併入候選；
   標「✅ 已解析」的（iGamingToday）不用再讀原檔。
3. 跑 `python3 <REPO>/scripts/inventory.py show --date <DATE>`，讀「可用庫存」「近 3 天已出現」「各區連續空白天數」。

**第一段｜第三層 WebSearch 補「程式抓不到」的題目（不查證）**
依「📡 三層收集」章節的四類查詢執行（菲律賓平台、新品牌進菲、實體機大廠、Slot 設計趨勢），
新找到的條目也只記「標題＋原文 URL＋含年份的發布時間＋所屬分類」，**不做交叉查證、不抓內文**。

⚠️ **判斷「今天新聞少」的唯一依據是 harvest 的「窗內候選數」與「來源健檢」**，不是你自己的感覺。
harvest 顯示窗內候選多、你卻收得少 → 是你篩錯了，回頭檢查；
來源健檢有 ≥3 個主要來源「失敗」→ 在回報與 Telegram 品質備註寫「抓取異常」，**不准寫「真實淡季」**。

**第二段｜打分排序（不花 credit）**
依「🧮 排序與取捨」章節對每則候選打分，套用硬上限、平手規則、**各區目標數與庫存保底**（見「📦 庫存機制」）。

**第三段｜只對入選的做查證**
對入選的每則做交叉查證並抓 og:image。
**Firecrawl 每則原則上只用 1 次**（內文＋og:image 同一次帶回）；
額外佐證優先用 **WebSearch（不吃 Firecrawl 額度）**，每則查證抓取仍以 3 次為上限。

**第三段的第一件事是驗主來源日期**（v6.2 硬規則，見「📅 主來源日期規則」）：
當日新聞要有 1 個主來源、發布日期含年份且在窗內；**庫存補位的項目**則要求主來源在保鮮期內（Slot 7 天、其他 3 天）。
過不了就直接剔除、換下一名遞補。harvest 已經給了精確時間的，直接採用，不必重查。
剔除與遞補的數量要記下來，步驟 6 回報。

**第四段｜更新庫存（v6.4 新增，寫完 Markdown 後一定要做）**
把「今天出現在日報的項目」與「合格但今天沒用上的項目」寫成 `<REPO>/state/inventory-picks-<DATE>.json`：

```json
{"shown": [{"cat":"cat1","title":"遊戲名","gp":"廠商"}, {"cat":"cat3","title":"新聞標題"}],
 "stock": [{"cat":"cat1","title":"遊戲名","gp":"廠商","b":4,"first_seen":"YYYY-MM-DD",
            "release_date":"YYYY-MM-DD（未上線才填）","sources":[{"name":"來源","url":"https://…","published":"YYYY-MM-DD HH:MM"}]}]}
```

然後跑 `python3 <REPO>/scripts/inventory.py update --date <DATE> --file <REPO>/state/inventory-picks-<DATE>.json`。
`shown` 用來做 3 天去重，`stock` 是明天以後的補位來源 —— **Slot 超過當天上限（平日 7、週末 2）的部分一定要進 stock**。
**⛔ 其他分類也一定要進 stock（硬規則）**：cat2、cat3、cat4、cat5 **每一區各挑 1 則**「分數最高、但今天沒用上」的合格項目寫進 `stock`（該區當天沒有合格的剩餘候選才可從缺，並在回報註明）。
這是「連續空 2 天、第 3 天從庫存補」能運作的前提。

存成：

```
<REPO>/state/<DATE>-igaming-report.md
```

**📐 Markdown 固定格式（v6.5 硬規則）** —— 這份 .md 是日報的**唯一原稿**，HTML 由程式照它渲染、不再手寫，
所以格式一定要照下面寫，程式才讀得懂（各欄位的內容要求見「各區格式」）：

```
# 🎰 iGaming 市場日報 <DATE>（週X）

🎰 Slot N ・ 🕹️ 非 Slot N ・ 🤝 主流 N ・ 🇵🇭 菲律賓 N ・ 📊 市場數據 N

---

## 🎰 Game Provider 新遊戲

### 01 <遊戲名> – <廠商>
📦 近期新作（M/D 首見）          ← 只有補位／預告／補遺／再展示才加這一行（📦／🆕／📋／🔁）

<內文一段，結尾「對 PM 的意義：…」>

衍生調整：<…>

參數：
- 遊戲類型：<…>
- 盤面：<…>
- 消除/賠付：<…>
- 最高倍率：<…>
- RTP：<…>
- 波動：<…>
- 目標市場：<…>
- 關鍵特色：<…>

查證：<可省略>
來源：[名稱A](URL) · [名稱B](URL) · 日期：YYYY-MM-DD
圖片：<URL 或 無>

## 🕹️ 非 Slot 新內容          ← 參數依品類 5 欄或 3 欄
## 🤝 動態：主流 GP／平台        ← 用「重點：類型 … ｜ 對象 … ｜ 影響 …」，不放參數與圖片
## 🇵🇭 動態：菲律賓 GP／平台
## 📊 市場數據 & 趨勢

---

本日日報查詢約 N1 個網站，其中提取 N2 個資料來源並進行交叉比對

---

## 🗓️ 來源日期紀錄（內部，不渲染）
```

- 區塊標題靠 emoji 辨識（🎰🕹️🤝🇵🇭📊），**0 則的區整段省略**；編號每區從 01 起，一律寫成 `### 01 標題`
- cat1、cat2 標題一律 `遊戲名 – 廠商`（en dash 前後各一空白）
- 「來源：」行的最後一定是 `日期：YYYY-MM-DD`（＝主來源發布日期）
- 標題含「內部」或「不渲染」的 `##` 區塊之後，全部不會進 HTML —— 內部紀錄一律放在最後

> ⚙️ **無人值守 Bash 規則**：需要讀特定檔案時，**直接用已知路徑搭配 Read 工具**，
> **不要用 `ls` / `ls | tail` / `find` 撈目錄** —— 複合或探測型指令在半夜排程會觸發授權詢問、卡死流程。
> 日期由步驟給定，路徑可以直接組出來。

### 步驟 2 — 定稿檢查＋渲染 HTML（v6.5：程式渲染，不再手寫）

```bash
python3 <REPO>/scripts/finalize_report.py --date <DATE>
```

這一行做完四件事：
1. 把 .md 解析成 `state/<DATE>-report.json`
2. **資料格式檢查**：每則必備欄位、主來源日期（當日新聞要在窗內、📦 要在保鮮期內）、cat1 參數 8 項、統計列、內文不可出現品質備註用語
3. **連結與圖片檢查**：來源連結 404／網域不存在＝錯誤；被網站擋（403 等）＝只警告；**配圖打不開會自動拿掉**
4. **模糊比對去重**：同份日報內互比、跟近 3 天日報比（Huff N´Puff＝Huff N' Puff、L&W＝Light & Wonder）

然後用**固定模板**寫出 `reports/<DATE>.html`，檢查結果寫進 `state/<DATE>-qa.json`。

**依結束碼處理（硬規則）**：
- `0` → 完成，往下做步驟 3
- `1` → 印出的「❌ 錯誤」逐條修 **.md**（不是修 HTML），修完重跑同一行；**最多重跑 2 次**
  - 來源連結失效 → 換成另一個查證過的來源；該則只剩失效連結 → 整則拿掉、依分數遞補
  - 同份或近 3 天重複 → 拿掉重複的那則（真的是新進展就標 🔁 並在內文寫清楚）
  - 主來源日期不合格 → 依「📅 主來源日期規則」換主來源或剔除
- 重跑 2 次還有錯誤 → **照樣發布**（HTML 已經寫好），把剩下的錯誤寫進步驟 6 回報；Telegram 的系統警報會自動帶出
- 「⚠️ 警告」不擋發布，看過、合理就好

⛔ **嚴禁手寫或手改 `reports/<DATE>.html`**。版面要改就改 `scripts/report_lib.py`（模板）或 main 分支的
`report_theme.py`（網站樣式開關），不在每天的執行裡改。

### 步驟 3 — 預存 Telegram 訊息

把訊息寫進 `<REPO>/state/pending_telegram.txt`（**覆蓋整個檔**），把當日報告 URL
`https://igaming-pulse.github.io/igaming-daily/reports/<DATE>.html`
寫進 `<REPO>/state/pending_telegram_url.txt`（**覆蓋**）。

06:30 的 GitHub Actions 會讀這兩個檔發送，**不需要本機排程、零 token**。

> ⚠️ **檔案的前兩行有固定格式，不可更動** —— Email workflow 會讀這兩行組信：
> 第 1 行是標題含日期，第 2 行是各區則數。第 3 行起才是內容。

訊息格式（純文字，**不要 HTML 標籤**，全文 3500 字內）：

```
🎰 iGaming 市場日報 <DATE>（週X）
🎰 Slot X ・ 🕹️ 非 Slot X ・ 🤝 主流 X ・ 🇵🇭 菲律賓 X ・ 📊 市場數據 X

🎰 Slot 新遊戲
01 <標題>
02 <標題>
…

🕹️ 非 Slot 新內容
…

（各區之間空一行）

📝 品質備註（本次爬找判斷）
1. …
2. …
```

**Telegram 標題行照樣加 📦／🆕／🔁 前綴**，讓讀者分得出當日與補位。

**📝 品質備註規則**
- 放在訊息**最後**，用 **1–3 條數字編號**（`1.` `2.` `3.`，不要用「・」）
- 寫本次爬找／涵蓋品質的誠實判斷：本窗新聞多寡（週末偏淡）、因主來源日期不合格剔除了幾則、來源異常等
  （v6.2 起不再有「用近幾天料」「日期只查到近期」這種收錄 —— 那種料一律不收）
- **沒有值得提的就整段省略**
- ⛔ **只能出現在 Telegram**，嚴禁寫進日報本身或 Email

**寫完 pending 檔後一定要跑（v6.5）**：

```bash
python3 <REPO>/scripts/health_alert.py --date <DATE> --append <REPO>/state/pending_telegram.txt
```

檢查 Firecrawl 額度夠不夠撐到重置日、來源是否連續 3 天失敗、窗內候選量是否異常、定稿檢查是否還有沒修的錯誤；
有狀況才在訊息最後附「⚙️ 系統警報」（重跑會自動替換、不會重複）。**這段由程式產生，不要自己改寫或刪掉。**

### 步驟 4 — 重建首頁並發布（**只 push 一次**）

```bash
cd <REPO>
python3 scripts/build_index.py
git add -A
git commit -m "daily: <DATE> report"
git push
```

或直接用封裝好的：`bash <REPO>/scripts/publish.sh`

commit 作者用中性身分（首次設定一次即可）：

```bash
git config user.name  "iGaming Pulse"
git config user.email "igaming-pulse@users.noreply.github.com"
```

> v6.4：`state/inventory.json`、`state/inventory-picks-<DATE>.json`、`state/harvest/<DATE>.md` 也要在同一個 commit。
> v6.5：`state/<DATE>-report.json`、`state/<DATE>-qa.json`、`state/health/` 也一起（`git add -A` 已涵蓋）。
>
> ⚠️ **報告、index、pending 檔必須在同一個 commit 一起推上去。**
> 分成兩次 push 會讓 Email workflow 觸發兩次（第一次還讀不到 pending 檔）。

### 步驟 5 — Email

Email 由 GitHub Actions 在收到 push 後自動寄出（`.github/workflows/notify-email.yml`），**本步驟不需要動作**。

若該 workflow 尚未設定 Secrets，在步驟 6 註明「Email 尚未接通」。

### 步驟 6 — 回報

說明：各區收錄幾則、公開網址、當日報告頁網址、push 是否成功、pending 檔是否已寫入、來源庫同步狀態。

**v6.2 起必報**：第三段因「主來源日期不合格」剔除幾則、各是哪則（標題＋查到的實際發布日期），以及遞補了幾則。

**v6.4 起必報**：harvest 窗內候選數與失敗來源、第二層列表頁成功幾個、各區當日幾則／庫存補幾則、
Slot 進庫存幾款、目前庫存量（Slot／其他）、各區連續空白天數。

**v6.5 起必報**：定稿檢查跑了幾次、最後剩幾個錯誤／警告、連結檢查結果（失效幾個、配圖拿掉幾張）、
健康檢查結果（Firecrawl 剩餘點數與預估、系統警報內容）。

---

## ⚠️ 失敗警報

任一步驟失敗、被略過、或結果明顯不完整時，把警報文字寫進 `state/pending_telegram.txt`（覆蓋），06:30 會自動發出。內容要寫清楚：**哪一步、原因、完成到哪**。

**收錄量過少保護**：算五區總則數，正常約 15–22 則。若**總和 < 10**：
1. Telegram 訊息最上方加一行 `❗今日收錄偏少（共 N 則），可能來源異常，請留意`
2. 步驟 6 回報點出
3. 仍照常完成發布與預存

---

## ⏱️ 收集時間窗（硬規則）

- **固定 24 小時滾動窗** ＝ 執行時刻往前推 24 小時，錨定在排程執行時刻 T。目前 **T ＝ 台北 02:30**。
- 產「D 日日報」只收 **D-1 日 T ～ D 日 T** 這 24 小時內發布的新聞。
- **執行時刻改變時，起訖一起平移，永遠維持 24 小時、絕不膨脹**。例：T 改 06:00 → 窗變 D-1 06:00 ～ D 06:00。
- ⛔ **嚴禁固定起點**（如永遠 D-1 00:00）—— 那會在執行時間變晚時把窗撐到 30、42 小時。
- **執行時刻若變更，必須在回報中主動提醒 Nate**「收集起始時刻已連動改為 XX:XX、窗仍為 24 小時」。
- 邊界以**主來源的發布時間（台北時區）**為準。只精確到「日」時，日期落在窗的起訖兩天內即算在窗內。
- ⛔ **v6.2 刪除舊版「抓不到精確時間就從寬認定」條款。** 2026-09-24 就是被這條放行：
  DigiPlus 官方稿內文寫「GamePlus 將於 9 月 22 日上線」，沒寫年份，被從寬認定為 2026/9/22；
  實際是 **2025-09** 的預告，暫停公告發布於 **2025-10-10**。三個來源全是 2025 年，卻被當成當日新聞收進 cat4。
  **主來源發布日期不明＝不收**，詳見下節。
- **補跑（漏跑後自動補、或手動補檔）沿用同一公式**：窗 ＝ **實際執行時刻**往前推 24 小時，
  **不是**回頭用原定的 02:30 當起點。例：機器關機、隔天 09:10 開機才補跑 → 窗為 D-1 09:10 ～ D 09:10。
  補跑時要在回報中註明「本次為補跑，實際窗為 XX:XX ～ XX:XX」。

---

## 📅 主來源日期規則（v6.2 硬規則）

每則入選新聞都要指定 **1 個「主來源」**——撐起「今天發生了什麼」這個主張的那篇報導／官方稿。

### 1. 主來源的門檻（缺一不收）
- 發布日期**含年份**（`YYYY-MM-DD`）
- 發布日期**落在收集時間窗內**（見「⏱️ 收集時間窗」）
- 日期是**這篇文章本身的發布日期**，不是內文提到的活動日期、上線日期、展會日期

### 2. 發布日期從哪裡取（依序，取到第一個就停）
1. 網頁 metadata：`article:published_time`、`og:published_time`、JSON-LD `datePublished`
   —— Firecrawl 回傳的 `data.metadata` 通常就帶著，**跟抓內文同一次拿，不多花 credit**
2. 網址內的日期（`/2026/09/23/`）
3. 頁面上印出的發布日期／署名日期（byline）

`dateModified`／「最後更新」**不能**當發布日期 —— 舊文改個錯字就會被刷新。

### 3. 主來源讀不到日期時
用 **WebSearch**（不吃 Firecrawl 額度）找**有日期的轉載或同題報導**改當主來源。
找不到 → **不收**，換下一名遞補。不可自行推斷年份、不可用「看起來是最近的」代替。

### 3.5 庫存補位項目（v6.4）
庫存補位的項目，主來源發布日期要在保鮮期內（Slot 7 天、其他 3 天），並在日報標 📦；
新作預告的日期以**文章發布日**為準，遊戲上線日另外寫在內文。

### 4. 佐證來源可以比窗舊
其他佐證來源**不要求在窗內**，可用來補背景、補參數
（例：PokerStars PSN 那則引用 9/8 的 Pokerfuse 補 Betfair 轉入時程，正常）。
但**如果所有來源都在窗外，就算彼此說法一致也不收** —— 一致只代表它們講的是同一件舊事。

### 5. 必須回頭核對年份的破綻訊號
出現下列任一，先查清楚主來源的年份再決定：
- 內文日期**沒寫年份**（「9 月 22 日」「Sep 22」）
- 內文用**未來式描述已過去的時間**（2026 年 9 月的新聞寫「將於 2026 年初重新上線」）
- 事件在近幾天的日報**已經報導過**，今天又以「宣布／啟動」的口吻出現
- 搜尋結果頁顯示的日期與文章內容對不上

### 6. 要記在哪
- **日報頁面**：每則「來源：… · 日期」的日期 **＝ 主來源發布日期**，單一日期、不寫區間
  （❌ `2026-09-22/23`）。不列每個來源的日期，版面不變。
- **內部紀錄**：`state/<DATE>-igaming-report.md` 最末加一段
  `## 🗓️ 來源日期紀錄（內部，不渲染）`，逐則列：主來源名稱＋發布日期＋日期取自哪裡（metadata／網址／byline），
  以及各佐證來源的日期。**渲染 HTML 時跳過這一段**，也不進 Email。

---

## 內容規格

### 五大分類與則數

| # | 分類 | 目標（上限） | 內容 | 格式 |
|---|------|------|------|------|
| 1 | 🎰 Game Provider 新遊戲（Slot＋實體機） | **平日 7 款、週末 2 款**（超過進庫存） | 線上電子老虎機新作，**也收已公布但未上線的新作預告／提前評測**、**實體老虎機新機台**。非 slot 放 cat2 | 三段式 |
| 2 | 🕹️ 非 Slot 新內容 | **2–3**（≤5） | 非 slot 的新遊戲／新內容。**優先序**：① 小遊戲（Crash／Mines／Plinko）② Live Game ③ Poker／德州 ④ 地方棋牌 ⑤ 其他 | 三段式 |
| 3 | 🤝 動態：主流 GP／平台 | **3–5**（≤7） | 大品牌具體動作：合作、併購、提告、運營活動與成效；**線上與實體機大廠（Aristocrat、L&W、IGT、Konami 等）都算** | 動態格式 |
| 4 | 🇵🇭 動態：菲律賓 GP／平台 | **2–4**（商業 ≤6，官方另計） | 見「🇵🇭 菲律賓區優先序」：平台策略與運營＞新品牌大動作＞GP 上架＞政策 | 動態格式 |
| 5 | 📊 市場數據 & 趨勢 | **1–3**（≤5） | 老虎機設計趨勢優先（風靡玩法、新機制），其次市場數據、展會實際影響 | 市場格式 |

> ### 🎯 總量：目標 15–18 則、**硬上限 22 則**
>
> 為什麼有硬上限：每則入選都要花 1 次 Firecrawl（抓內文＋og:image）。
> 第二層列表頁約 9 次 ＋ 入選 ≤22 次 ≤ 35 次／天。**超過 22 則就會吃掉補跑的緩衝**。

**可讀性優先**：每一區都要有內容可看。某區當天沒料 → 依「📦 庫存機制」從庫存補；
**連續空 2 天可以，第 3 天一定要補**。仍嚴禁灌水：庫存也沒有合格的，才讓它空著，並在 Telegram 品質備註說明。
總量低於 10 則時在 Telegram 發出偏少警示。

### 🧮 排序與取捨（v6.0 硬規則）

候選池建好後，**每一則都要打分**，依分數排序後取用。這取代舊版「看市場衝擊性」那種需要臨場判斷的描述。

**公式：`總分 ＝ B（品牌）＋ E（事件）＋ R（地區）＋ T（時效）＋ H（熱門 IP，見「🔥 熱門 IP／系列作」）`，再套 D（重複）與硬上限。**

#### B 品牌權重

| 分 | 對象 |
|---|---|
| **6** | 下列 21 個（⭐⭐ 特別追蹤 4：**Acewin**（IGS 鈊象）、**Omiplay**（尊博）、**YellowBat**、**ATG**（atg-games.com）｜每日固定收錄 1：**EEZE**｜⭐ 優先展示 GP 3：**Yggdrasil、Jili、TaDa Gaming**｜菲律賓核心集團／平台 10：**DigiPlus、BingoPlus、ArenaPlus、GameZone、PeryaGame、Casino Plus、PlayTime、BET88、OKBet、PT Gaming**｜國際現金網 2：**Stake、Betfury**｜菲律賓官方 1：**PAGCOR**） |
| **4** | 一線大廠：PG Soft、Pragmatic Play、Nolimit City、Play'n GO、Red Tiger Gaming、Aristocrat、IGT、Light & Wonder |
| **3** | 二線知名（包含但不限於）：CP Game、Peter & Sons、NetEnt、Hacksaw Gaming、FA CHAI (FC)、Evolution、Playtech、Betsoft、Spinomenal、Relax Gaming、Push Gaming、BGaming、Wazdan、Quickspin |
| **1** | 其他有名有姓的 GP／平台 |
| **0** | 不具名或查不到主體 |

#### E 事件類型權重

| 分 | 對象 |
|---|---|
| **6** | 新遊戲上線（日報主軸）、**實體老虎機新機台首發**、重大平台整合／內容分銷合約 |
| **5.5** | **新作預告／提前評測**（遊戲已公布、尚未上線；標題標「新作預告（M/D 上線）」） |
| **5** | 市場數據報告、GGR／營收數字、**新的突破**、**特定玩法流行**（既有玩法如 Hold & Spin、Collect to Win，新玩法，以及 Free Spin 等運營手段） |
| **2** | 展會消息（本次展會重點／亮點）—— **限該展會開始與結束前後各 2 週內** |
| **1** | 監理法規重大變動（禁令、牌照、稅制）、大型 M&A、上市公司財報 |
| **0.5** | 獲獎提名、人事任命、純行銷稿、贊助、活動花絮 |

#### R 地區權重

**判定依據是「這則新聞影響的市場」，不是公司總部所在地。**

| 分 | 地區 |
|---|---|
| **6** | 菲律賓 |
| **5** | 台灣、東南亞 |
| **4** | 拉丁美洲、南美、中美洲、巴西、墨西哥、南非、**全球（無特定單一市場）** |
| **3** | 印度、美國、歐洲、加拿大 |
| **2** | 澳門、日本、韓國、中國 |
| **1** | 其他國家／與本業無關的單一小市場 |

#### T 時效加分　／　D 重複扣分

- **T**：窗內 0–12 小時 `+2`／12–24 小時 `+1`／主來源只精確到「日」`0`
  —— v6.2 起**沒有「時間不明」這一檔**：主來源沒有含年份的發布日期，根本進不了評分（見「📅 主來源日期規則」）
- **D**：`inventory.py show` 列在「近 3 天已出現」的項目**直接不收**（同一款遊戲的評測、上線、推廣算同一款）。
  超過 3 天又出現、且有重大更新（預告→正式上線、大廠、新數據）→ **可以再展示**，標題前加「🔁 正式上線」或「🔁 更新」

#### ⛔ 三個硬上限（優先級高於分數）

1. **同一 GP 當日最多 2 則** —— 第 3 則即使滿分 20 也不收
2. **同一國家**：菲律賓**商業新聞 ≤6 則**（PAGCOR／官方監理來源**另計不佔名額**）；其他國家 **≤3 則**
3. **總量硬上限 22 則**

> 舊版 cat3 的「涉及國家／特定市場地區的新聞整區最多保留 1 則」**由本條取代**（改為其他國家 ≤3）。

#### 平手規則

`總分 → B 高者優先 → R 高者優先 → 發布時間新者優先`

#### 分類保底（v6.4 改為庫存保底）

依「📦 庫存機制」：Slot 平日當天新作不到 7 款就從庫存補到 7 款、週末 ≤1 款才補到 2 款；其他分類連續空 2 天、第 3 天從庫存補。
若某區在前 18 名內一則都沒有、但當日候選池裡有該區的合格項目，照舊從全池補 1–2 則。

### ⚖️ 體育低優先（非全面排除）

體育不是高優先題材，但以下兩種**可納入**（以對遊戲／賭場的影響書寫，不寫賽事本身）：

1. **體育導向的平台／現金網**（bet365、DraftKings 等）有與 Slot／賭場相關的營運操作或產品
2. **極大型全球賽事**（World Cup、Olympics）外溢影響各類遊戲的整體投注量

純體育賽果、單純運彩盤口／賠率、體育贊助本身，不收。

### 📌 EEZE 每日固定收錄（🕹️ 非 Slot）

- **EEZE**（Malta 的 Live Casino B2B 聚合／內容商）每天在「🕹️ 非 Slot 新內容」固定收錄 **1 則**（歸 Live 品類）。遊戲類型欄位標「Live Game（EEZE 平台／聚合）」，非遊戲型的參數欄位填「不適用」。
- 例外跳過：① 連續 3 天完全沒有 EEZE 消息；② 該則與「近 3 天」已收的 EEZE 議題**相同**（來源不同但議題相同也算重複）。

### ⭐ 優先展示品牌

完整名單見「🧮 排序與取捨」章節的 **B＝6**（21 個）。這些品牌當日若有夠份量的新聞，
一律**優先鎖定並排在該區前段**。仍守「寧缺毋濫」。

#### 🔥 熱門 IP／系列作（v6.4.3，H 加分）

下列系列的**任何新作**——續作、換皮、節慶版、實體機或線上版——一律視為高度關注：

| 系列 | 廠商 | 備註 |
|---|---|---|
| **Huff N' Puff** | Light & Wonder | 三隻小豬系列；例：Huff N' Puff Haunted Mansion（萬聖節換皮） |
| **Bao Zhu Zhao Fu（爆竹招福）** | Light & Wonder | 亞洲市場熱門實體機 IP |
| **SuperGems（Super Gem）** | Omiplay（尊博） | 對標 Fortune Gem、在菲律賓平台有成績 |

規則：
- 打分加 **H = +3**（`score = B + E + R + T + H`），在 Slot 區排到最前面（同分時熱門 IP 優先）。
- **不受「7 天內才上線」的預告限制**：上線日在 30 天內的預告也可以上日報，標題標「🆕 新作預告（M/D 上線）」。
- 名單要增減直接改這張表；判斷時比對遊戲名稱是否含系列名（不分大小寫、忽略標點）。
- 起因：2026-09-28 Huff N' Puff Haunted Mansion 在 iGamingToday 列表頁上、窗內發布，卻因 7 天預告限制與列表頁未解析而漏收，舊機器反而有收。

#### ⭐⭐ Acewin／Omiplay／YellowBat／ATG 特別追蹤

這四家 GP 的下列動態一律當新聞處理，與其他消息比權重後決定是否露出，**同等條件下優先級提高**：

1. **上新遊戲** —— 尤其上線到 DigiPlus 旗下平台（BingoPlus／ArenaPlus／GameZone）、Casino Plus 等菲律賓現金網、或 YellowBat→PlayTime。新 slot 放 cat1、非 slot 放 cat2。
2. **特別活動** —— 線上或線下的行銷／賽事／合作活動
3. **平台功能更新** —— GP 自身或其在菲律賓平台上的功能改版

ATG（`https://atg-games.com/zh-tw`）同列特別追蹤，判準與下述三家相同。

背景（判權重用）：Acewin＝IGS鈊象旗下、Jili 低配版、多款與 Jili 互通、B 端價格優勢；Omiplay＝尊博集團、Super Gem 對標 Fortune Gem 成功、獲 BingoPlus／CasinoPlus 認可；YellowBat＝PlayTime 深度策略夥伴。

### 🔎 交叉查證、補全與衝突辨識

每則在輸出前，**不可「單一來源拿到就直接輸出」**，依序做三件事：

**1. 交叉查證**
- 至少再找 **1 個獨立來源**佐證。高衝擊事件與優先品牌盡量湊到 **2 個以上**。
- 真的只有單一來源時可收，但敘述保守處理、不誇大；那個單一來源本身就必須是合格的主來源。
- 佐證來源負責「證明內容正確」，**主來源負責「證明是今天的事」**，兩件事分開驗（見「📅 主來源日期規則」）。
- **列出所有查證過的來源**（可點擊、去重、**不設 3 個上限**）。

**2. 補全豐富度**
- **Slot／遊戲類（每支必做）** → 去該 **Provider 官網 + SlotCatalog** 補齊並填滿：盤面、最高倍率、RTP、波動、消除／賠付機制、發行日、目標市場。
- **財務／營運類** → investor relations / PSE EDGE / 監理機關官方數據補正確數字。
- **市場數據（cat5）** → 對照調研機構（EKG 等）與監理機關官方數字。

**3. 衝突辨識與更正**
- 以**最權威來源為準**：官方新聞稿／Provider 官網／監理機關／交易所揭露 ＞ 產業媒體 ＞ 聚合／評測站。
- 差異重大且無法判斷孰對 → **明確註記「各來源數據不一（A 稱 X、B 稱 Y）」**，嚴禁偷偷挑一個當定論。
- 明顯誤植 → 以原始出處更正後輸出，並用原始出處當來源。
- **查證說明**：只要該則有衝突或補了重要資訊，加一行 `查證：<說明>`，**不超過 50 字**。

**4. 成本上限（已定案）**
- 每則的額外交叉查證抓取 **上限 3 次**。查證預算花在高衝擊／優先品牌的則；低優先的則有 1 個佐證即可。
- **整場硬上限**：Firecrawl 依「💳 用量分級」（v6.5，下方）—— **以 harvest 檔頭寫的「今天文章最多 N 次」為準**；`WebSearch ≤ 60 次`。
  > WebSearch 上限比 firecrawl 寬鬆是刻意的：**WebSearch 不消耗 Firecrawl credit**，
  > 成本只是執行時間。2026-09-22 由 30 上調為 60 —— 當天為了確認「真的是淡季」
  > 而非抓取不足，用了約 55 次才敢下結論，這種查證是該鼓勵的，不該卡在上限。
  （以下 v6.4.2 的舊拆法僅供參考，v6.5 起由分級取代）拆法：**第二層列表頁約 9（固定 6 ＋ 輪掃 3），觸發日另加 0–5（事件 ≤3、展會 ≤2），週一另加 3 ＋ 入選文章 ≤22**；觸發日列表頁較多時，入選文章相應減少，整場仍 ≤35。第一層 WP-API／RSS 不花 Firecrawl。
  `35 × 30 天 = 1,050`，月額度 1,125，餘裕 6.7%（約 2 次補跑的緩衝）。
  ⚠️ 交叉查證**優先用 WebSearch**（不吃 Firecrawl 額度）；firecrawl 只花在「入選且需要 og:image／內文」的那一次。
  > 2026-09-21 上調（原 ≤14／≤20）：連續兩天實測，≤14 只收到 5 則與 2 則，
  > 同日同來源的舊環境用 ≤45 都收到 10 則 —— 證明是**抓取量不足**，不是當日新聞真的少。
  > 月額度 1,125（每月 14 日重置），30×30 天 = 900，仍在額度內。
  > ⚠️ 額度不夠時**優先砍「其他」、不要砍輪掃**，輪掃是來源覆蓋率的保證。
  超過就停止擴大、用現有素材成稿。
  **⛔ 嚴禁開 5-credit 的 JSON 抽取** —— 能用 WebSearch snippet ＋ firecrawl summary 拿到的就不要開；
  og:image 跟 summary **同一次免費帶回，不另抓**。

**💳 Firecrawl 用量分級（v6.5 硬規則，2026-09-28 定案）**

`harvest.py` 開跑前先查 Firecrawl 剩餘點數，算出今天的預算，決定抓取強度：

```
今日預算 ＝（剩餘點數 − 保留 20）÷ 距離重置日的天數
```

| 等級 | 今日預算 | 輪掃 | 事件觸發 | 展會 | 週一固定 | 文章（入選查證）上限 |
|---|---|---|---|---|---|---|
| 🟢 充裕 | ≥30 | 3 | 3 | 2 | 3 | 22 |
| 🟡 標準 | 20–29 | 2 | 2 | 1 | 2 | 16 |
| 🟠 節約 | 15–19 | 0 | 1 | 1 | 0 | 10，只給 Slot／非 Slot；其他分類用 WebSearch |
| 🔴 保命 | <15，或剩餘 <100 | 0 | 0 | 0 | 0 | 0；配圖改用 WebFetch 抓 og:image，抓不到寫「圖片：無」 |

- 每天固定只剩 iGamingToday 1 個列表頁要花點數（其他來源 v6.5 起都改免費抓）
- 實際文章上限 ＝ min(等級上限, 今日預算 − 程式已花在列表頁的點數)，**寫在 harvest 檔頭，照那個數字做**
- 查不到剩餘點數時預設「標準」
- 保留 20 點給重跑與特別版。**重跑或特別版要先估點數**，並說明會不會讓之後幾天降級，經使用者同意才跑
- 省下的點數會自動讓隔天預算變多，不用另外處理
- 開跑前、收尾各記一次剩餘點數（`state/health/credits.json`），`health_alert.py` 算出當天實際用量，超過預算或降到節約／保命級會發系統警報

**📋 Slot 基本欄位必須填滿**

盤面、最高倍率、RTP、波動是最基本資訊，**原則上一定查得到**。每支 slot 至少要抓到能填滿這四欄的來源。

「未公布」是**最後手段**：只有確實查過 **SlotCatalog ＋ Provider 官網 ＋ 該遊戲媒體內頁**三處都沒有時才可寫，且要在「查證：」註明「已查 SlotCatalog／官網／媒體內頁仍無」。單支 slot 出現多個「未公布」而查證沒說明查過哪些來源＝抓取不足，須補抓。

### 抓取來源與方式

1. 讀 `sources/sources.md`（10 大分類：Provider 官網、產品分析／評測、產業媒體、產業協會／技術認證機構、市場數據／分析公司、監理機關／官方數據、展會、論壇／社群、Podcast／影音、已停用）。**依當日題材主動跨分類取材**，避免只用少數幾個來源。
   - 來源清單的**唯一真相是 `sources/igaming-daily-report-sources-v2.xlsx`**。要加／刪來源：① 改 xlsx → ② 跑 `scripts/sync_sources.py`。`sources.md` 為自動產物、勿手改。
   - **「已停用」分類的來源不要抓。**
   - **cat5** 優先參考「市場數據／分析公司」與「監理機關／官方數據」。
   - **cat3／cat4 法規與監理** 查「監理機關／官方數據」與「產業協會／技術認證機構」。
2. WebFetch 被擋（403/404）的站改用 **Firecrawl HTTP API**（見下）。**嚴禁用瀏覽器模式**——會觸發逐站授權，破壞無人值守自動化。Firecrawl 仍抓不到就**跳過該站**、用其他來源補，不要停下來等授權。

**實測 WebFetch 必擋站**：SlotCatalog、SBC、Gambling Insider、eegaming、PAGCOR、GGRAsia。
通用策略：**WebFetch 失敗或要 og:image 就切 Firecrawl**，比維護黑名單實在。

### 📡 三層收集（v6.4 硬規則，取代 v6.0 的「核心必掃 8 站」與舊輪掃制）

`sources/sources.md` 的「抓取方式」「頻率」兩欄（來自 xlsx）決定每個來源怎麼抓：

| 層 | 誰做 | 範圍 | 成本 |
|---|---|---|---|
| **第一層** | `scripts/harvest.py`（run_daily.sh 開跑前自動執行） | 抓取方式＝**WP-API／RSS** 的來源全部每天掃（約 90 個，含菲律賓在地媒體、DigiPlus 官網；v6.5 起 EEGaming、SBC News、IAG 改 RSS），加上**程式解析**的 BigWinBoard 新作列表與 **SlotsLaunch 上線日曆**（每款有上線日） | 免費 |
| **第二層** | 同上（`harvest.py` 內建） | 抓取方式＝Firecrawl、頻率＝**每日**：只剩 iGamingToday（擋程式抓取，程式解析成候選）；加上輪掃與三種觸發，數量依「💳 用量分級」 | 1–10 次 Firecrawl |
| **第三層** | 你（Claude），WebSearch | 程式抓不到的四類題目（下表） | WebSearch 約 30–40 次 |

**第三層固定查詢（每天都要跑，查詢字串加上當週日期）**：

| # | 題目 | 查詢方向 |
|---|---|---|
| 1 | **菲律賓平台動態** | DigiPlus、BingoPlus、ArenaPlus、GameZone、PT Gaming、OKBet、Casino Plus、BET88、PlayTime 各自＋「new game／promo／launch／partnership」 |
| 2 | **新品牌進入菲律賓** | 「Philippines launch」「enters Philippine market」「PAGCOR license」「Philippines partnership casino」 |
| 3 | **實體機大廠新機台** | Aristocrat、Light & Wonder、IGT、Konami、Everi、AGS、Zitro、Novomatic ＋「new cabinet／slot machine／debut」 |
| 4 | **Slot 新作補漏與設計趨勢** | 「new slot release ＋日期」；每週 1–2 次查新機制／爆紅玩法整理文章 |

特別追蹤 4 家（Acewin、Omiplay、YellowBat、ATG）維持每天單獨搜尋一次。
**品牌名＋RTP／max win 的分組查詢實測效果很差（只會回長青排行頁），不要用。**

輪掃池只剩 xlsx「頻率＝輪掃」的來源（約 70 個沒有 API 的新聞型站），每天 3 個、約 24 天一輪，由 harvest.py 一起抓。
「頻率＝每週／事件」與「行事曆」的來源，由 harvest.py 依下列三種觸發自動抓（v6.4.2）：

| 觸發 | 對象 | 條件 | 上限 |
|---|---|---|---|
| **事件觸發** | 監理機關（含 PAGCOR）、沒有 API 的協會（xlsx「觸發關鍵字」欄） | 當天**窗內新聞標題**命中該機構的觸發關鍵字 → 抓該機構官方頁當主來源／佐證。菲律賓、亞洲機構優先 | **每個關鍵字每週（週一～週日）最多一次**，每天最多 3 個；紀錄在 `state/triggers.json` |
| **行事曆觸發** | 展會（xlsx「展期」欄，格式 `YYYY-MM-DD~YYYY-MM-DD`，多屆用 `;` 分隔） | 報告日期落在**開展前 14 天～閉展日** → 每天抓該展會新聞頁 | 每天最多 2 個，開展日近者優先 |
| **固定週期** | 監理機關＋沒有 API 的協會 | **每週一**（平日裡新聞最少的一天：週一日報涵蓋週日）依 ISO 週數輪 3 個 | 每週 3 個 |

觸發抓回的頁面一樣存進 `state/harvest/<DATE>-lists/`，候選清單的第二層區塊會標出是哪一種觸發、命中哪一則新聞。
論壇、Podcast 仍不主動抓。展會展期要每年更新 xlsx（過期的展期不會觸發）。

### 📦 庫存機制（v6.4 硬規則）

狀態檔 `state/inventory.json`，由 `scripts/inventory.py` 維護（`show` 讀、`update` 寫）。

| 項目 | Slot（cat1） | 其他分類（cat2–cat5） |
|---|---|---|
| 收什麼 | 已上線、提前評測、新作預告、實體機新機台都收；**上線日在日報日期 7 天以後的預告不上日報**，只進庫存標「待上線」，進入 7 天內才可用 | 合格但當天沒用上的新聞 |
| 每天出幾則 | **週一到週五日報：上限 7 款（v6.6.2）；週六、週日日報：上限 2 款（不可更改）**。大廠（B≥3）優先；湊不滿就自然呈現，不硬補 | 依各區目標數 |
| 什麼時候進庫存 | 當天合格新作超過上限（平日 7、週末 2）的部分 | **每區每天必存 1 則**：分數最高、但今天沒用上的合格項目 |
| 什麼時候取庫存 | **平日**：當天新作不到 7 款就從庫存依 B 分補到 7 款（v6.6.2，讓庫存每天消耗、不囤積）；**週末**：當天新作 ≤1 款才補到 2 款。庫存不足時有多少補多少，自然呈現 | 該區**連續空 2 天**，第 3 天從庫存補 1–2 則 |
| 保鮮期 | 首次看到後 **7 天**；未上線的預告保留到「上線日＋3 天」 | **3 天** |
| 取用順序 | B 分高 → 首見早 → 參數齊全 | 分數高 → 首見早 |
| **Slot 選取順序（硬規則）** | ① **窗內的大廠新作（B≥3）全部收**（受同一 GP ≤2 限制；超過上限取 B 分最高的，其餘進庫存）→ ② 其他窗內新作依分數補到 5 款 → ③ 平日不到 7 款就從庫存補到 7；週末 ≤1 款才補到 2 | — |
| 日報標示 | 標題前加「📦 近期新作（M/D 首見）」；週六檢查點補遺加「📋 本週補遺（M/D 發布）」 | 標題前加「📦（M/D）」 |

**📋 週六檢查點（v6.4 硬規則）**：EEGaming 每週五（歐洲白天、台北週五晚上）發布「Weekend Reels」整理當週 Slot 新作，
它落在**週六 02:30 日報**的時間窗。harvest 在週六會自動把最新一篇 Weekend Reels 抓進 `state/harvest/<DATE>-lists/`，
並列出 BigWinBoard 本週上線的新作（補 Hacksaw、Nolimit City、ELK 這類不發新聞稿的大廠）。週六日報要逐款比對：
- 已在「近 3 天已出現」或庫存裡 → 跳過
- 漏掉的 → 標「📋 本週補遺（M/D 發布）」，**算在週六的 2 款上限內**（大廠優先），多的進庫存給下週一到週三用
- 週六回報要寫：Weekend Reels 共幾款、我們本週已收幾款、補遺幾款、進庫存幾款

**iGamingToday 是次要來源**：聯盟行銷型評測站，常晚 BigWinBoard 數天到數週轉寫。它的評測只在找不到其他來源時才用，
且不可當唯一來源（至少再配 1 個 BigWinBoard／GP 官網／新聞通稿）。

⚠️ harvest 的預判分類只是關鍵字猜的：**cat3、cat5 區也要掃一遍有沒有「releases／launches＋遊戲名」的 Slot 新作**，找到就移到 cat1。

harvest 清單裡每區的「窗外近期」也是庫存候選（Slot 近 7 天、其他近 3 天），可以直接取用，但一樣要標 📦。
**從庫存補的項目不佔「當日新聞」的時間窗規則**，但主來源必須在保鮮期內。

**去重（3 天規則）**：`inventory.py show` 的「近 3 天已出現」清單裡的項目不可再出現。
超過 3 天又出現且重要（預告→正式上線、大廠新數據）可以再展示，標題前加「🔁」。
**（TBC）佔位頁自動剔除（v6.5）**：BigWinBoard 標 TBC、沒有明確上線日、頁面日期比首見日還舊的項目，`inventory.py` 會自動移出庫存，`show` 會列出當天剔除了哪些。
v6.5 起 Slot／非 Slot 用**模糊比對**判斷是不是同一款（撇號、大小寫、™、「Slot」字尾、廠商縮寫都不影響；
續作數字不同視為不同款），`inventory.py` 與 `finalize_report.py` 共用 `scripts/report_lib.py` 的同一套規則。

### 🔦 加碼規則（v6.4）

**觸發點是 harvest 的窗內候選數**，不是你自己數的候選池：

- harvest 窗內候選 **< 30 則**（扣掉雜訊後）→ 第三層 WebSearch 加跑一輪，每類多 2–3 次查詢
- 仍不足 → **先用庫存補，再考慮少收**，不可灌水

有觸發加碼或用了庫存 → 在步驟 3 的 **Telegram 品質備註**寫一則。**只進 Telegram，不進日報／Email。**

#### Firecrawl（HTTP API，非 MCP）

金鑰從環境變數 `FIRECRAWL_API_KEY` 讀取。

```bash
curl -s -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"<文章頁URL>","formats":["summary"],"onlyMainContent":true}'
```

取 `data.summary`（摘要）、`data.metadata["og:image"]`（卡片橫向圖），
以及發布日期 `data.metadata` 內的 `article:published_time`／`publishedTime`／`og:published_time`（主來源日期，見「📅 主來源日期規則」）。

- JS 重的頁（SlotCatalog 列表）才加 `"waitFor": 5000`；`proxy` 用預設 `basic`。
- JSON 抽取的 schema **要扁平物件、不要包陣列**（包成 `{slots:[...]}` 會觸發「schema 需有 type」錯誤）。
- **計價**：一般 scrape（summary/markdown）**1 credit**；帶 `jsonOptions` 的 JSON 抽取 **5 credits**。
- **省 credit 關鍵**：少用 JSON 抽取；og:image 跟摘要**同一次**拿，不要另抓。

#### 🪶 抓取節約原則

- **Firecrawl**：**分兩種用法，不可混用（v6.1）**
  - **文章內頁** → `onlyMainContent: true` ＋ `formats: ["summary"]`。不要對內頁用 `markdown` 抓整頁 —— 整頁約 80% 是導覽選單／Cookie 表／頁尾，會撐爆 context。
  - **列表頁／首頁／分類頁**（第二層固定站、每日輪掃、Provider 官網新聞列表；v6.4 起由 harvest.py 代抓）→ **必須** `formats: ["markdown"]` ＋ `onlyMainContent: false`。用 summary 抓列表頁等於沒抓，理由見「每日核心必掃清單」。
- **WebFetch**：prompt 要**窄**，只問「標題＋關鍵參數（RTP／倍率／盤面／機制／日期）＋3 句內摘要＋原文 URL」。
- **WebSearch**：先用結果 snippet 判斷夠不夠，真的需要細節才去抓那一頁。
- **鐵則**：進到 context 的只能是「精煉後的標題／參數／摘要」，不能是整頁原文。此原則**不減少來源數量、不影響交叉查證深度**。

#### 🖼️ 配圖規則（cat1 Slot ＋ cat2 非 Slot）

- **og:image 是免費的**：`firecrawl_scrape` 就算用 `formats:["summary"]`，回傳的 `metadata` 仍含 `og:image`。**只要為了拿參數去 firecrawl 抓了該則文章頁，就順手把 `metadata['og:image']` 取出當卡片圖**，零額外成本。
- **只缺圖時最省的作法**：用 firecrawl 抓該文章頁一次，從 `metadata['og:image']` 取圖。
- ⚠️ **不要用 WebFetch 抓 og:image** —— WebFetch 會把頁面轉 markdown、丟掉 `<head>` 的 og 標籤，拿不到。
- **退而求其次**：用文章內文出現的橫向圖完整網址（2:1 或 16:9），不要用 `-768x512`／`-218x150` 這種列表縮圖。
- 只放**橫向**；只有正方形或直立就寫 `圖片：無`。cat3／cat4／cat5 不配圖。

#### 🇵🇭 菲律賓區優先序（v6.4 硬規則）

| 優先序 | 內容 | 例子 |
|---|---|---|
| **1** | **DigiPlus 旗下與主要現金網的策略、運營操作、上架新產品** | BingoPlus／ArenaPlus／GameZone 新遊戲或新功能、PT Gaming、OKBet、Casino Plus、BET88、PlayTime 的行銷活動、合作、改版 |
| **2** | **新品牌在菲律賓的大型操作** | 國際品牌取得牌照或進入市場、大型贊助、代言人、實體賭場開幕 |
| **3** | GP 在菲律賓平台的上架與合作 | Acewin、YellowBat、Omiplay 上架 PlayTime／GameZone 等 |
| **4（最後）** | 政策、監理 | PAGCOR 公告、稅制、禁令 —— 有重大變動才收，官方另計不佔名額 |

**每天固定查（有沒有查是硬規則，收不收看份量）**：
1. harvest 已自動收進 DigiPlus 官網 RSS、GMA News、Rappler、SunStar、BusinessWorld、AGB Philippines 的博弈相關新聞 —— 先看 harvest 的 cat4 區
2. 第三層 WebSearch 第 1、2 類查詢（平台動態、新品牌進菲）
3. DigiPlus Investor Relations／PSE EDGE 有財報或揭露時才收

限制說明：現金網的促銷與新品很多只發在 Facebook／IG／App 內，不會有新聞稿，抓不到就算了，靠庫存維持可讀性。

### 各區格式

#### cat1 — 🎰 Game Provider 新遊戲（平日 7 款、週末 2 款，三段式）

標題前綴：未上線的加「🆕 新作預告（M/D 上線）」、從庫存補的加「📦 近期新作（M/D 首見）」、超過 3 天再展示的加「🔁」。

每則約 300 字繁中，三段清楚換行：

```
[第一段：總述 + 產業意義，約 150~200 字，結尾帶一句「對 PM 的意義：…」]

衍生調整：<相對原作新增或調整了什麼；全新款寫「全新 IP，無衍生」>

參數：
- 遊戲類型：<四選一> 實體老虎機 / 線上電子老虎機 / 實體+電子老虎機 / 其他類型遊戲（括號註明）
- 盤面：<例 3×5 直式 / 6×5>
- 消除/賠付：<例 Cluster Pays、243 ways、Cascading 連消、Hold & Win>
- 最高倍率：<例 25,000x / 未公布>
- RTP：<例 97.05% / 未公布>
- 波動：<高 / 中 / 未公布>
- 目標市場：<例 北美；無資訊寫「沒有」>
- 關鍵特色：<核心機制賣點>

查證：<若有衝突或補充，50 字內>
來源：[名稱A](URL) · [名稱B](URL) · 日期（＝主來源發布日期 YYYY-MM-DD）
圖片：<橫向圖片URL 或 無>
```

「衍生調整」「參數的每個子項目」都必須各自換行，**不可用 ｜ 擠成一行**。

#### cat2 — 🕹️ 非 Slot 新內容（3–5 則，三段式）

同 cat1 的三段式，但**參數欄位依品類分兩套**（沒資料的欄位寫「未公布 / 沒有 / 查無資料 / -」擇一）：

- **小遊戲（Plinko/Crash/Mines）、Bingo、Live game show（有倍率/RTP 者）→ 5 欄位**：遊戲類型、最高倍率、RTP、目標市場、關鍵特色
- **撲克/德州、體育、棋牌、平台聚合動態（無倍率/RTP 者，如 EEZE）→ 3 欄位**：遊戲類型、目標市場、關鍵特色
- 非 Slot **不放** Slot 的「盤面 / 消除·賠付 / 波動」欄位

#### cat3 & cat4 — 🤝/🇵🇭 動態格式

```
[標題]

[內文段落，約 150~250 字：講清楚發生什麼、對象、影響／意義（PM 視角），結尾帶「對 PM 的意義：…」]

重點：類型 <合作 / 併購 / 提告 / 認證 / 運營活動 / 財務 / 政府法規 / 獲獎 / 人事 / 市場進入 / 負責任博彩> ｜ 對象 <涉及的品牌/機構> ｜ 影響 <一句話產業影響>

查證：<可選>
來源：[名稱](URL) · 日期（＝主來源發布日期 YYYY-MM-DD）
```

**cat3 只收「品牌具體動作」，不收趨勢／展望（趨勢一律歸 cat5）。** 內容優先序：

1. 品牌在自身產品的革新（新機制、新玩法、產品線大改）
2. 實體老虎機三大廠（IGT、Light & Wonder、Aristocrat）的布局操作、新機台、特定市場的卓越表現
3. 其他品牌具體動作（合作、併購、互相提告、運營活動與成效、獲獎）
4. **最低優先（大多可忽略）**：國家法規更新、品牌進入特定市場

**國家／市場收斂**：依「三個硬上限」第 2 條（其他國家 ≤3 則）；同一事件被大量報導時合併成 1 則，其餘當佐證來源。

亞洲／菲律賓系大牌（Jili、CQ9、JDB、Fachai、Spadegaming、AdvantPlay）依該則新聞內容動態判斷放 cat3 或 cat4。

#### cat5 — 📊 市場數據 & 趨勢（3 則）

- 本區**吸收所有趨勢／展望／預測**：媒體／專家／報告／大廠明確發表的當年、當季、下季、明年主流趨勢（玩法、變種玩法、類型），以及市場數據報告、展會／活動的實際影響（需有新聞來源／報告，不能只列時間與性質）。
- 主題優先序：① **老虎機趨勢（最優先）** → ② 小遊戲（Crash、Plinko、Mines）→ ③ 其他電子品類 → ④ 撲克
- **不要寫體育**；各國政府法規／博彩政策優先級**最後**。

### 🔢 編號與多來源

- **編號**：每個分類**各自從 01 開始**（cat1 的 01–05、cat2 的 01–04、cat3 的 01…）。
- **多來源**：每則把**所有實際查證過的來源連結全部列上**（可點擊、去重、不設上限）。來源數量**不影響優先級** —— 優先級一律看市場衝擊性 ＋ 既定規則。

### 📊 文末統計列

在整份報告的**最末端**輸出一行（整數、必為本次執行真實數字）：

```
本日日報查詢約 <N1> 個網站，其中提取 <N2> 個資料來源並進行交叉比對
```

- **N1** ＝ 本次實際查詢／開啟過的**不重複網站數**（WebFetch＋Firecrawl＋WebSearch 實際點開的頁面，去重估算）
- **N2** ＝ 實際**提取並用於交叉比對的資料來源數**（所有則來源連結去重後的總數）—— **v6.5 起由 `finalize_report.py` 自動計算並覆蓋**，.md 裡寫多少都會被改成實際數字
- **N2 < N1 是正常的。** 兩數字由 LLM 估算，非程式精確計數。
- 渲染時兩個數字用紅色。

### ⛔ 日報本身不放「爬找品質判斷」

像「本窗週末偏淡」「某類用近期料」「某則日期只到近期」這類**對抓取品質的說明／免責**，**不要**寫進 .md／HTML，也不要放進 Email。那類話只放 Telegram 的「📝 品質備註」。

---

## 渲染規格（Markdown → HTML）

輸出到 `<REPO>/reports/<DATE>.html`，完整獨立 HTML（內嵌 CSS、無外部依賴）。

> **v6.5：以下規格已凍結成程式模板 `scripts/report_lib.py`（`render_html`），由 `finalize_report.py` 產生，這一章只是說明。**
> 模板輸出的結構與 main 分支 `report_theme.py` 相容，網站樣式開關與「日報樣式回滾／套用」口令照常運作。

### 🔖 網站圖示（favicon，必附）

`<head>` 內 `<title>` 之後**必須**加這三行。日報位於 repo 的 `reports/`，所以用 `../` 指向 repo 根目錄：

```html
<link rel="icon" type="image/png" sizes="32x32" href="../icon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="../icon-16.png">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
```

圖示檔（`icon-16.png`／`icon-32.png`／`icon-512.png`／`apple-touch-icon.png`）**已存在 repo 根目錄，勿重新產生**。
首頁 `index.html` 的 favicon 由 `scripts/build_index.py` 自動帶入（用不帶 `../` 的相對路徑）。

### 色彩系統（五區各一色）

```
🎰 Slot 新遊戲      主色 #1D9E75   badge 底 #E1F5EE / 字 #0F6E56
🕹️ 非 Slot 新內容   主色 #B31217   badge 底 #FBE3E4 / 字 #8A1015
🤝 主流動態         主色 #378ADD   badge 底 #E6F1FB / 字 #185FA5
🇵🇭 菲律賓          主色 #D97706   badge 底 #FBF0DD / 字 #8A5206
📊 市場數據         主色 #8B5CF6   badge 底 #EEE9FC / 字 #5B3FA6

共用：底 #F5F7FA、卡片 #FFFFFF、線 #E7EBF0、主字 #1A2230、次字 #5B6675
```

> ⚠️ 非 Slot 就是**血紅 `#B31217`**。舊文件曾出現 `#0EA5A5`（青色），那是改版殘留，**已作廢**。

### 版面元素（依序）

1. **Header**：日期（週X）· 台北時間 → H1「🎰 iGaming 市場日報」→ 五顆膠囊 badge
2. **統計卡片 grid**（最多 5 格，0 則的區不顯示）：各區則數，數字用各區主色
3. **五區依序**，每區一個 section 標題（含該區顏色左邊條 + 則數）。**某區 0 則則整段省略**（含標題）
4. **文末統計列**（Footer 上方）：`本日日報查詢約 <b>N1</b> 個網站，其中提取 <b>N2</b> 個資料來源並進行交叉比對`，兩數字紅色粗體
5. **Footer**：`iGaming 日報自動化 v6.5（三層收集＋庫存＋定稿檢查）・每則皆附真實可點擊原文連結・多來源交叉查證` ＋ `產出時間：<DATE>（台北時間）`

### 卡片規格

- **分類標題放大**：section 標題字級約 **28px**，Emoji 隨之放大（約 1.4–1.5em），讓五區區隔明顯
- **編號每區從 01 起**
- **多來源**：每則卡片底部渲染該則**所有**來源連結，每個可點擊（`來源 A ↗ B ↗ C ↗`）
- **查證說明**：若該則有 `查證：…`，在內文下方渲染一條 `.verify`（🔎 前綴、淺灰底）
- **配圖**：cat1 與 cat2 卡片**最下方**放橫向圖 `.hero`，`onerror` 隱藏。cat3/4/5 不配圖
- **cat1/cat2 的參數逐項換行**，嚴禁擠成一行
- 內文完整呈現不截斷；卡片 RWD，手機單欄

```css
.derive{font-size:13px;color:#7a4d0b;background:#FBF3E4;border:1px solid #F0E2C6;border-radius:8px;padding:9px 12px;margin-bottom:10px}
.spec{background:#F2F6F4;border:1px solid #E1EAE6;border-radius:8px;padding:10px 12px;margin-bottom:10px;font-size:12.5px}
.spec .row{display:flex;gap:10px;padding:3px 0;border-bottom:1px dashed #E1EAE6}
.spec .k{flex:0 0 82px;font-weight:700;color:#0F6E56}
.keyrow{display:flex;flex-wrap:wrap;gap:14px;background:#F4F8FC;border:1px solid #DCE8F4;border-radius:8px;padding:9px 12px;margin-bottom:10px;font-size:12.5px}
.verify{font-size:12.5px;color:#334155;background:#F3F4F6;border:1px solid #E5E7EB;border-radius:8px;padding:8px 12px;margin-bottom:10px;line-height:1.6}
.verify::before{content:"🔎 "}
.hero{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px;margin-top:10px;display:block;background:#eee}
.stats-line{max-width:860px;margin:26px auto 0;text-align:center;font-size:13.5px;color:#1A2230;line-height:1.8}
.stats-line b{color:#B31217;font-weight:800}
```

---

## 名單庫（watchlists）

> 抓取時優先鎖定以下品牌。非 slot 品牌：新遊戲／新內容放 cat2、商業動態放 cat3。

**主流 Game Provider**
ELK Studios、Push Gaming、AvatarUX、Hacksaw Gaming、Pragmatic Play、PG Soft、4ThePlayer、Peter & Sons、Relax Gaming、Betsoft、Yggdrasil、Play'n GO、Wazdan、Amusnet、Quickspin、Stakelogic、Endorphina、Playson、Evoplay、3 Oaks Gaming、Octoplay、Swintt、RubyPlay、IGT PlayDigital、ELA Games、Thunderkick、Light & Wonder iGaming、ICONIC21、Nolimit City、Red Tiger、Kalamba Games、NetEnt、Big Time Gaming、Fantasma Games、Print Studios、Jili、TADA Gaming、Fachai、CQ9、JDB、Spadegaming、AdvantPlay、PlayStar、iSLOT（實體）、Choice Gaming、SmartSoft Gaming (Crash)、Galaxsys (Crash)、Turbo Games (Crash)、SPRIBE (Crash)、AllBet (Live)、Sexy Gaming (Live)、Evolution (Live)

**主流平台（含現金網）**
bet365、betway、1xbet、888casino、DraftKings、BetMGM、Caesars、Stake、Roobet、Betfury、sportsbet.io、Blaze、Betano、Betclic、Betsson、bwin、Betfair、LeoVegas、William Hill、Coral、Sisal、Sky Bet、BetVictor、M88、BetOnline、Cwinz、ECLbet、SlotPesa、2up.io、Betika、J9、K8

**撲克平台（cat2）**
PokerStars、WPT、Natural8、PPPoker、KKPoker、GGPoker

**菲律賓 Game Provider（cat4）**
Darwin Gaming、Gaming Panda、5G Games

**菲律賓平台（cat4）**
789 Bingo、Hann Online、NWRPlay、FBMPLAY、OKADA PLAY、BigBunny、NUSTAR、BET88、ArionPlay、NinoGaming、PlayTime、Lucky Taya、OKBet、BingoPlus、FASTWIN、inPlay、LuckPOT、CasinoPlus、CrazyWin、BLucky、MegaPerya、GameZone、S5 Casino、Juan365、LakiWin、ArenaPlus、Legend Link、Buenas、Solaire Online、Midori Online、D'Heights Online、Thunderbird Rizal Online、Winford Online、Casino Maxx、SportsPlus、IGO、747、M Game、Jackpot Combo、FilGame、Winzir、SG8、Pin77

**菲律賓政府／在地事件源**
PAGCOR 官方公告與規範；實體賭場（Okada Manila、Solaire、NUSTAR、Winford、Thunderbird）重大事件；現金網／線上營運商的管理或罰款事件

---

## 版本沿革

- **v6.6.2**（2026-10-11，使用者定案）平日 Slot 上限 5 → **7 款**（週末 2 款不變）；平日補位改為「當天新作不到 7 款就從庫存依 B 分補到 7」（原本 ≤3 款才補，平日幾乎不補導致積壓）；特別版一次最多 **10 款**（太多看不完），沒放到的留給之後的日報補位

- **v6.6.1**（2026-10-11，使用者更正）特別版改為**全部釋放、不設上限**（大廠在前）；特別版放寬：可用資料庫上線日當主來源日期、保鮮 14 天、參數查不到寫未公布、非 Slot 另開一區；唯一不放寬：真實原文網址＋遊戲確實存在。查證不過的直接移出庫存（記 rejected），釋放後庫存只剩 7 天外的待上線。理由：每天新作穩定 ≥3 款，庫存不需囤積，釋放的目的是讓使用者一次掌握漏掉的市場資訊

- **v6.6**（2026-10-11）庫存釋放特別版：每週一、週四日報成功後，Slot 可用庫存（不含 7 天外預告、TBC 佔位）≥5 款就另發 `reports/<DATE>-special.html`；大廠（B≥3）全收在前、B1 最多 5 款（快過期優先）、每期 ≤12 款；連結併進當天日報的 Telegram（今天推播已送出才單獨補發）。週六、週日日報上限不變。程式：`scripts/special_edition.py`、`scripts/run_special.sh`、`docs/special-prompt.txt`。起因：14 天 Slot 庫存進 39、用 11，約 10 款大廠款白白過期

- **v6.5.2**（2026-10-11）來源修復：Play'n GO 官網改用 Wix、RSS 消失 → 新增抓取方式「Sitemap」（`harvest.py` 的 `fetch_sitemap`；`/games/` 的日期＝上線日，當 Slot 上線日曆用）；Kalamba Games、Casino Inside Romania 加了機器人驗證 → 改 Firecrawl 輪掃。另：排程自帶防睡眠（caffeinate）、晚到立刻推播、發布到 main 改暫存 worktree

- **v6.5.1**（2026-09-28）① Firecrawl 用量分級（充裕≥30／標準 20–29／節約 15–19／保命<15，保留 20 點），開跑前查剩餘點數決定強度；
  ② BigWinBoard、SlotsLaunch（改抓上線日曆）、EEGaming、SBC News、IAG 改為免費抓取，每天固定列表頁從 6 個降到 1 個（iGamingToday，由程式解析）；
  ③ 窗外候選另存 backlog 檔；④ 庫存自動剔除（TBC）佔位頁；⑤ 文末資料來源數改由程式計算；⑥ `tests/` 回歸測試（過去 11 份日報＋列表頁存檔）。
  起因：剩 599 點撐 16 天、Huff N´Puff 埋在未解析的列表頁、TBC 佔位頁進庫存、N2 估算與實際差 6

- **v6.5**（2026-09-28）定稿檢查：① 凍結日報模板 —— .md 改為固定格式的唯一原稿，HTML 由 `scripts/finalize_report.py` 用固定模板渲染，不再每次手寫；
  ② 資料格式檢查（必備欄位、主來源日期、cat1 參數 8 項）；③ 連結與圖片檢查（失效連結擋下、破圖自動拿掉）；
  ④ 模糊比對去重（`report_lib.same_item`，inventory 與定稿共用）；⑤ `scripts/health_alert.py` 額度與健康警報附在 Telegram 最後。
  起因：每天 HTML 結構不同導致新樣式套不上、寫法差異造成重複判斷不到、Firecrawl 額度與來源失效沒有人盯
- **v6.4.3**（2026-09-28）新增「🔥 熱門 IP／系列作」：Huff N' Puff、Bao Zhu Zhao Fu、SuperGems 的新作加 H=+3、排 Slot 區最前，預告放寬到 30 天內
- **v6.4.2**（2026-09-27）「每週／事件」「行事曆」來源改為三種觸發：事件觸發（標題命中關鍵字，每個關鍵字每週一次）、行事曆觸發（展會開展前 14 天～閉展日）、每週一固定輪 3 個；xlsx 新增「觸發關鍵字」「展期」兩欄。起因：原寫法「平常不抓、遇到題材才查」沒有切入點，實際等於永久排除
- **v6.4.1**（2026-09-27）Slot 節奏規則：平日上限 5、週末上限 2；當天 ≤3 款才從庫存補、≥4 款不補、不足 5 款自然呈現；
  上線日在 7 天以後的預告不上日報（只進庫存）；新增「📋 週六檢查點」（Weekend Reels＋BigWinBoard 本週新作）；iGamingToday 降為次要來源。
  依據：EEGaming Weekend Reels 12 週 177 則統計，週四佔 46%、週末 0%
- **v6.4**（2026-09-27）收集架構改造：① 新增 `scripts/harvest.py`，第一層用 WP-API／RSS 每天免費掃約 90 個來源、取得精確發布時間，
  第二層 Firecrawl 只抓 EEGaming Slot 分類、BigWinBoard、SlotsLaunch、iGamingToday、SBC News、IAG 與輪掃 3 站；
  ② 取消「核心必掃 8 站」（CasinoBeats 停更、Gambling Insider 轉向體育，連日掛零）；
  ③ 新增 Slot 庫存（每天 5 款、< 3 款才補、保鮮 7 天）與其他分類庫存（保鮮 3 天、連續空 2 天第 3 天補），`scripts/inventory.py`；
  ④ cat1 收新作預告／提前評測（E=5.5）與實體機新機台（E=6）；⑤ 3 天去重、超過 3 天且重要可再展示；
  ⑥ 菲律賓區改為平台策略與運營優先、政策最後；⑦ xlsx 新增 9 個來源（菲律賓 5、Slot 資料庫 3、EEGaming Slot 分類）與「抓取方式／頻率／抓取端點」三欄。
  起因：9/23–9/26 四天大廠新作 12 款只收 1 款、9/27 只收 1 則（實際窗內合格 4–7 則），iGB 等核心站列表頁反覆解析失敗
- **v6.2**（2026-09-24）新增「📅 主來源日期規則」：每則必須有 1 個發布日期含年份且在窗內的主來源，
  佐證來源可比窗舊但不可全部在窗外；刪除時間窗的「從寬認定」條款；T 分取消「時間不明＝0 分仍可入選」；
  日報日期欄固定為主來源發布日期（不寫區間）；各來源日期只記在 state md 內部紀錄。
  起因：2026-09-24 cat4 收錄 DigiPlus 巴西 GamePlus「軟啟動三週後暫停」，三個來源全是 2025 年
  （暫停公告 2025-10-10），因內文「9 月 22 日」無年份被從寬認定為當日新聞；9/23 首跑亦收過同一則舊聞
- **v6.1**（2026-09-23）修正 v6.0 的致命抓法錯誤：列表頁原本沿用 `formats:["summary"]`，
  而 summary 不回傳條目清單，導致核心必掃 8 個「掃了等於沒掃」——
  首跑只撈到 7 則、cat2 整區空白，且漏掉 SlotBeats 首頁上兩則窗內新 slot（其中一則是 B=6 的 Yggdrasil）。
  改為列表頁一律 `formats:["markdown"]` ＋ `onlyMainContent:false`；
  並要求回報必須逐站列出「各撈到幾則」，禁止只報「已掃 8 個」
- **v6.0**（2026-09-22）收集流程與排序規則全面改版：① 新增「每日核心必掃 8 個」列表頁；② 收集改**三段式**（廣蒐候選不查證 → 打分排序 → 只查證入選者）；③ 新增可計算的排序公式 `B+E+R+T+D`（滿分 20）取代「看市場衝擊性」；④ 新增三個硬上限（同一 GP ≤2、菲律賓商業 ≤6＋官方另計、其他國家 ≤3、總量 ≤22）；⑤ 平手規則 `總分→B→R→時間`；⑥ 則數調整 cat1 5→≤8、cat3 5→≤7、cat5 3→2–5、總量目標 18／硬上限 22；⑦ 輪掃批次 8→5（約 34 天一輪），額度挪給核心必掃；⑧ firecrawl 上限 30→35；⑨ 加碼觸發點由「成稿 < 15 則」改為「候選池 < 25 則」；⑩ B=6 名單納入 ATG、OKBet、PT Gaming、EEZE
- **v5.2**（2026-09-20）依原帳號裁示砍 Firecrawl 用量：輪掃批次 30→**8**（覆蓋週期 6 天→**約 21 天**，已知並接受）、整場 firecrawl 上限 45→**14**、薄弱日加碼收進總額內不另外開、明令嚴禁 5-credit JSON 抽取；補上補跑時的時間窗規則
- **v5.1**（2026-09-20）納入原帳號 ROUND4 更新：每日輪掃制 ＋ `rotate_sources.py`（168 源／6 天一輪）、薄弱日再加碼（<15 則觸發）、整場預算上限改為 firecrawl ≤ 45／WebSearch ≤ 20、日報 HTML 必附 favicon 三行、無人值守 Bash 規則（禁 ls／find 探測）、`build_index.py` 加入合併回顧標籤 `LABEL_OVERRIDE` 與首頁 favicon
- **v5.0**（2026-09-19）三支 skill 合併成一支放進 repo；砍 sources.json 舊設定、砍 AUTO-HEAL、砍 visualize 預覽、砍 Mac 專屬路徑；交叉查證上限 6→3；清除四分類殘留；非 Slot 顏色統一為血紅；來源總數改由 xlsx 動態帶入；Firecrawl 改走 HTTP API；Telegram 改由 GitHub Actions 發送
- v4.1　五大分類（🎰 Slot／🕹️ 非 Slot／🤝 主流動態／🇵🇭 菲律賓／📊 市場數據）
