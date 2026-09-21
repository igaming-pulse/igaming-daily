---
name: igaming-daily
description: iGaming 市場日報自動化 — 收集、交叉查證、產 Markdown、渲染 HTML、發布 GitHub Pages、預存 Telegram。五大分類版 v5.2。
---

# iGaming 市場日報 — 完整規則（v5.2 · 雲端可攜版）

> 本檔是三支舊 skill（`daily-news-report` / `daily-report-html` / `scheduled-task`）合併後的唯一真相。
> **規則放在 repo，不放帳號 Skill** —— 換 Claude 帳號時這份不用動。
> 排程任務的 prompt 只負責：clone/pull repo → 讀這份 → 依序執行。

全程用**繁體中文**、**台北時間（Asia/Taipei）**。

---

## ⛔ 最高優先的三條硬規則

1. **嚴禁平行 sub-agent**。全程在主線程循序、分批處理。（原帳號撞每週用量上限的元凶就是這個。）
2. **交叉查證只增不減**。查證的目的是補足與更正，**嚴禁把已有資訊刪掉或降級成「未公布」**。
3. **每則必附真實可點擊原文 URL**。嚴禁編造或猜測，抓不到真實 URL 的不得收錄。

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

依本檔「內容規格」章節收集。收集由三塊組成，缺一不可：

1. **精準搜尋廣撒**（WebSearch ＋ ⭐ 重點來源）
2. **每日輪掃**（見「🔁 每日輪掃制」）—— 先跑 `python3 <REPO>/scripts/rotate_sources.py` 取今日批次
3. **薄弱日再加碼**（總則數 < 15 才觸發）

存成：

```
<REPO>/state/<DATE>-igaming-report.md
```

> ⚙️ **無人值守 Bash 規則**：需要讀特定檔案時，**直接用已知路徑搭配 Read 工具**，
> **不要用 `ls` / `ls | tail` / `find` 撈目錄** —— 複合或探測型指令在半夜排程會觸發授權詢問、卡死流程。
> 日期由步驟給定，路徑可以直接組出來。

### 步驟 2 — 渲染 HTML

依本檔「渲染規格」章節，把上面的 .md 現寫成 HTML，存成：

```
<REPO>/reports/<DATE>.html
```

**不使用固定模板，每次現寫**（已定案）。但注意兩個已知的渲染地雷：

- 不要把 Markdown 的 `---` 分隔線當內容輸出（會變成 `<p>---</p>`）
- 文末統計句**只放 footer 一次**，不要誤植進分類卡片裡

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

**📝 品質備註規則**
- 放在訊息**最後**，用 **1–3 條數字編號**（`1.` `2.` `3.`，不要用「・」）
- 寫本次爬找／涵蓋品質的誠實判斷：本窗新聞多寡（週末偏淡）、某類用了「近幾天最新可查證料」、某些則日期只查到「近期」、來源異常等
- **沒有值得提的就整段省略**
- ⛔ **只能出現在 Telegram**，嚴禁寫進日報本身或 Email

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

> ⚠️ **報告、index、pending 檔必須在同一個 commit 一起推上去。**
> 分成兩次 push 會讓 Email workflow 觸發兩次（第一次還讀不到 pending 檔）。

### 步驟 5 — Email

Email 由 GitHub Actions 在收到 push 後自動寄出（`.github/workflows/notify-email.yml`），**本步驟不需要動作**。

若該 workflow 尚未設定 Secrets，在步驟 6 註明「Email 尚未接通」。

### 步驟 6 — 回報

說明：各區收錄幾則、公開網址、當日報告頁網址、push 是否成功、pending 檔是否已寫入、來源庫同步狀態。

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
- 邊界以新聞的**發布／更新時間（台北時區）**為準；抓不到精確時間時，用「明顯屬於這 24 小時內的當日消息」從寬認定，但不可把超過 48 小時的舊聞當新聞收。
- **補跑（漏跑後自動補、或手動補檔）沿用同一公式**：窗 ＝ **實際執行時刻**往前推 24 小時，
  **不是**回頭用原定的 02:30 當起點。例：機器關機、隔天 09:10 開機才補跑 → 窗為 D-1 09:10 ～ D 09:10。
  補跑時要在回報中註明「本次為補跑，實際窗為 XX:XX ～ XX:XX」。

---

## 內容規格

### 五大分類與則數

| # | 分類 | 則數 | 內容 | 格式 |
|---|------|------|------|------|
| 1 | 🎰 Game Provider 新遊戲（Slot） | **5** | 權重高的新 slot（強勢＋新興品牌）。**只收電子老虎機**，非 slot 放 cat2 | 三段式 |
| 2 | 🕹️ 非 Slot 新內容 | **3–5** | 非 slot 的新遊戲／新內容。**優先序**：① 小遊戲（Crash／Mines／Plinko）② Live Game ③ Poker／德州 ④ 地方棋牌 ⑤ 其他 | 三段式 |
| 3 | 🤝 動態：主流 GP／平台 | **5** | 大品牌或關鍵大事：合作、併購、互相提告、運營活動與成效 | 動態格式 |
| 4 | 🇵🇭 動態：菲律賓 GP／平台 | provider 0–3 ＋ 平台 0–3 ＋ 政府／在地，**整區上限約 6–8** | 菲律賓廠商／平台大事 ＋ 政府／在地新聞 | 動態格式 |
| 5 | 📊 市場數據 & 趨勢 | **3** | 市場趨勢優先（風靡玩法、影響產業的賽事／展會之實際影響） | 市場格式 |

總量約 **13–22 則**（資訊完整優先）。比例不必硬湊，**寧缺毋濫**：某類沒有夠份量的新聞就少收或省略，嚴禁灌水。

### ⚖️ 體育低優先（非全面排除）

體育不是高優先題材，但以下兩種**可納入**（以對遊戲／賭場的影響書寫，不寫賽事本身）：

1. **體育導向的平台／現金網**（bet365、DraftKings 等）有與 Slot／賭場相關的營運操作或產品
2. **極大型全球賽事**（World Cup、Olympics）外溢影響各類遊戲的整體投注量

純體育賽果、單純運彩盤口／賠率、體育贊助本身，不收。

### 📌 EEZE 每日固定收錄（🕹️ 非 Slot）

- **EEZE**（Malta 的 Live Casino B2B 聚合／內容商）每天在「🕹️ 非 Slot 新內容」固定收錄 **1 則**（歸 Live 品類）。遊戲類型欄位標「Live Game（EEZE 平台／聚合）」，非遊戲型的參數欄位填「不適用」。
- 例外跳過：① 連續 3 天完全沒有 EEZE 消息；② 該則與「近 3 天」已收的 EEZE 議題**相同**（來源不同但議題相同也算重複）。

### ⭐ 優先展示品牌

Yggdrasil、Jili、Tada、DigiPlus、Casino Plus、Bingo Plus、Arena Plus、GameZone、Bet88、betfury、Stake、PlayTime、**Acewin（IGS鈊象）、Omiplay（尊博）、YellowBat**。

這些品牌當日若有夠份量的新聞，一律**優先鎖定並排在該區前段**。仍守「寧缺毋濫」。

#### ⭐⭐ Acewin／Omiplay／YellowBat 特別追蹤

這三家 GP 的下列動態一律當新聞處理，與其他消息比權重後決定是否露出，**同等條件下優先級提高**：

1. **上新遊戲** —— 尤其上線到 DigiPlus 旗下平台（BingoPlus／ArenaPlus／GameZone）、Casino Plus 等菲律賓現金網、或 YellowBat→PlayTime。新 slot 放 cat1、非 slot 放 cat2。
2. **特別活動** —— 線上或線下的行銷／賽事／合作活動
3. **平台功能更新** —— GP 自身或其在菲律賓平台上的功能改版

背景（判權重用）：Acewin＝IGS鈊象旗下、Jili 低配版、多款與 Jili 互通、B 端價格優勢；Omiplay＝尊博集團、Super Gem 對標 Fortune Gem 成功、獲 BingoPlus／CasinoPlus 認可；YellowBat＝PlayTime 深度策略夥伴。

### 🔎 交叉查證、補全與衝突辨識

每則在輸出前，**不可「單一來源拿到就直接輸出」**，依序做三件事：

**1. 交叉查證**
- 至少再找 **1 個獨立來源**佐證。高衝擊事件與優先品牌盡量湊到 **2 個以上**。
- 真的只有單一來源時可收，但敘述保守處理、不誇大。
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
- **整場硬上限**：`firecrawl ≤ 30 次`、`WebSearch ≤ 60 次`。
  > WebSearch 上限比 firecrawl 寬鬆是刻意的：**WebSearch 不消耗 Firecrawl credit**，
  > 成本只是執行時間。2026-09-22 由 30 上調為 60 —— 當天為了確認「真的是淡季」
  > 而非抓取不足，用了約 55 次才敢下結論，這種查證是該鼓勵的，不該卡在上限。
  拆法：**輪掃 8 次 ＋ 其他（新聞頁內文／補參數／og:image／薄弱日加碼）合計 ≤ 22 次**。
  > 2026-09-21 上調（原 ≤14／≤20）：連續兩天實測，≤14 只收到 5 則與 2 則，
  > 同日同來源的舊環境用 ≤45 都收到 10 則 —— 證明是**抓取量不足**，不是當日新聞真的少。
  > 月額度 1,125（每月 14 日重置），30×30 天 = 900，仍在額度內。
  > ⚠️ 額度不夠時**優先砍「其他」、不要砍輪掃**，輪掃是來源覆蓋率的保證。
  超過就停止擴大、用現有素材成稿。
  **⛔ 嚴禁開 5-credit 的 JSON 抽取** —— 能用 WebSearch snippet ＋ firecrawl summary 拿到的就不要開；
  og:image 跟 summary **同一次免費帶回，不另抓**。

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

### 🔁 每日輪掃制（硬規則，2026-09-19 定案）

**為什麼有這條**：舊規則為了省額度叫模型「別把來源全掃一遍、優先 ⭐ 重點來源＋精準搜尋」，
副作用是**絕大多數來源庫平常根本沒被主動觸及，等於白養**。輪掃是那條規則的明確例外。

做法：除了搜尋廣撒，每天固定「輪流」直接查一批來源，**由日期決定是哪一批、無需狀態檔**
（半夜全新無記憶的 session 也算得出同一批），約 **21 天**把 **168 個新聞型來源**覆蓋一輪。

1. **取今日批次**
   ```bash
   python3 <REPO>/scripts/rotate_sources.py
   ```
   輸出今天輪值的 **8 個**來源，每行 `名稱<TAB>分類<TAB>URL`。
   輪掃池只含五個有每日新聞價值的分類：Provider 官網、產品分析／評測、產業媒體、市場數據／分析公司、監理機關／官方數據。
   **展會／論壇／Podcast／協會認證／已停用不進池。**

2. **逐一查**：對批次內每個 URL 用 Firecrawl（`formats:["summary"]` ＋ `onlyMainContent:true`，1 credit／次），
   看有無「**收集時間窗內、夠份量**」的新聞。
   - **有** → 納入候選、與搜尋結果**去重**、順手取 `metadata['og:image']`
   - **沒有** → 跳過（多數會沒有，這是正常的）
   - Firecrawl 抓不到的站直接跳過，不停下來等授權

3. **底線（最高優先）**：輪掃**只收窗內、真實**新聞。它的作用是「補搜尋沒索引到的冷門來源」，
   **嚴禁**把舊聞／跨窗料當新聞，**嚴禁**灌水。

4. **預算**：**8 次 firecrawl／天**（＝8 credits）。
   這是 2026-09-20 為了控月額度定案的值 —— 覆蓋變慢（21 天一輪）是**已知且接受的代價**。
   要更頻繁覆蓋才把 `--size` 往上調，但那會等比例提高 credit 用量。

### 🔦 薄弱日再加碼（總則數 < 15 才觸發）

做完正常搜尋 ＋ 每日輪掃後，若五區合計**仍 < 15 則**，才針對**不在今日批次內的 ⭐ 優先品牌官網
＋「產業媒體」分類**多挖，同樣用 Firecrawl summary。
**加碼不另外開額度，一律在整場 30 次的總額內進行**（輪掃 8 用掉後，最多再 22 次）。
湊到 15 則即停；額度用完仍 < 15 就**老實少收**（寧缺毋濫），不可灌水。

有觸發加碼 → 在步驟 3 的 **Telegram 品質備註**加一則，例如
「本窗新聞偏少，已額外回退掃描重點來源補齊；窗內確實較淡」。
**只進 Telegram，不進日報／Email。**

#### Firecrawl（HTTP API，非 MCP）

金鑰從環境變數 `FIRECRAWL_API_KEY` 讀取。

```bash
curl -s -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"<文章頁URL>","formats":["summary"],"onlyMainContent":true}'
```

取 `data.summary`（摘要）與 `data.metadata["og:image"]`（卡片橫向圖）。

- JS 重的頁（SlotCatalog 列表）才加 `"waitFor": 5000`；`proxy` 用預設 `basic`。
- JSON 抽取的 schema **要扁平物件、不要包陣列**（包成 `{slots:[...]}` 會觸發「schema 需有 type」錯誤）。
- **計價**：一般 scrape（summary/markdown）**1 credit**；帶 `jsonOptions` 的 JSON 抽取 **5 credits**。
- **省 credit 關鍵**：少用 JSON 抽取；og:image 跟摘要**同一次**拿，不要另抓。

#### 🪶 抓取節約原則

- **Firecrawl**：一律 `onlyMainContent: true` ＋ `formats: ["summary"]`。**不要用 `formats:["markdown"]` 抓整頁** —— 整頁約 80% 是導覽選單／Cookie 表／頁尾，會撐爆 context。
- **WebFetch**：prompt 要**窄**，只問「標題＋關鍵參數（RTP／倍率／盤面／機制／日期）＋3 句內摘要＋原文 URL」。
- **WebSearch**：先用結果 snippet 判斷夠不夠，真的需要細節才去抓那一頁。
- **鐵則**：進到 context 的只能是「精煉後的標題／參數／摘要」，不能是整頁原文。此原則**不減少來源數量、不影響交叉查證深度**。

#### 🖼️ 配圖規則（cat1 Slot ＋ cat2 非 Slot）

- **og:image 是免費的**：`firecrawl_scrape` 就算用 `formats:["summary"]`，回傳的 `metadata` 仍含 `og:image`。**只要為了拿參數去 firecrawl 抓了該則文章頁，就順手把 `metadata['og:image']` 取出當卡片圖**，零額外成本。
- **只缺圖時最省的作法**：用 firecrawl 抓該文章頁一次，從 `metadata['og:image']` 取圖。
- ⚠️ **不要用 WebFetch 抓 og:image** —— WebFetch 會把頁面轉 markdown、丟掉 `<head>` 的 og 標籤，拿不到。
- **退而求其次**：用文章內文出現的橫向圖完整網址（2:1 或 16:9），不要用 `-768x512`／`-218x150` 這種列表縮圖。
- 只放**橫向**；只有正方形或直立就寫 `圖片：無`。cat3／cat4／cat5 不配圖。

#### 📌 菲律賓重點品牌每日固定排查（硬規則）

抓 cat4 時**每天一定要固定打開**：

1. **DigiPlus News & Updates** — https://digiplus.com.ph/news-updates/ → BingoPlus／ArenaPlus／GameZone／PeryaGame 的官方新聞稿都發在這
2. **DigiPlus Investor Relations** — https://digiplus.com.ph/investor-relations/ → 財報、季度營收
3. **PSE EDGE (DigiPlus, PLUS)** — https://edge.pse.com.ph/companyInformation/form.do?cmpy_id=96 → 交易所官方揭露；JS 渲染，抓不到就退回上面兩個或當地財經媒體
4. **DigiPlus 官方 FB** — https://www.facebook.com/DigiPlusInteractive/ → 補充用；登入牆常抓不到，**失敗就略過**

**Casino Plus**（非 DigiPlus 旗下、官網無新聞稿頁）：用**品牌名 web search ＋ 當地媒體（GMA、Philstar、Manila Times）＋ PAGCOR 公告**每日撿罰款／認證／營運事件，不抓它的遊戲站。

守「寧缺毋濫」：固定來源當天沒夠份量新聞就不收，但**「有沒有去查」是硬規則，「收不收」才看份量**。

### 各區格式

#### cat1 — 🎰 Game Provider 新遊戲（5 則，三段式）

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
來源：[名稱A](URL) · [名稱B](URL) · 日期
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
來源：[名稱](URL) · 日期
```

**cat3 只收「品牌具體動作」，不收趨勢／展望（趨勢一律歸 cat5）。** 內容優先序：

1. 品牌在自身產品的革新（新機制、新玩法、產品線大改）
2. 實體老虎機三大廠（IGT、Light & Wonder、Aristocrat）的布局操作、新機台、特定市場的卓越表現
3. 其他品牌具體動作（合作、併購、互相提告、運營活動與成效、獲獎）
4. **最低優先（大多可忽略）**：國家法規更新、品牌進入特定市場

**國家／市場收斂（重要）**：涉及國家／特定市場地區的新聞，**整區最多保留 1 則** —— 優先保留涉及優先品牌的那則；若剛好有 2 則都涉及優先品牌，最多留 2 則。非國家型的（產品革新、獲獎、機制發表）不受此上限。

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
- **N2** ＝ 實際**提取並用於交叉比對的資料來源數**（所有則來源連結去重後的總數）
- **N2 < N1 是正常的。** 兩數字由 LLM 估算，非程式精確計數。
- 渲染時兩個數字用紅色。

### ⛔ 日報本身不放「爬找品質判斷」

像「本窗週末偏淡」「某類用近期料」「某則日期只到近期」這類**對抓取品質的說明／免責**，**不要**寫進 .md／HTML，也不要放進 Email。那類話只放 Telegram 的「📝 品質備註」。

---

## 渲染規格（Markdown → HTML）

輸出到 `<REPO>/reports/<DATE>.html`，完整獨立 HTML（內嵌 CSS、無外部依賴）。

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
5. **Footer**：`iGaming 日報自動化 v5.2（五大分類版）・每則皆附真實可點擊原文連結・多來源交叉查證` ＋ `產出時間：<DATE>（台北時間）`

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

- **v5.2**（2026-09-20）依原帳號裁示砍 Firecrawl 用量：輪掃批次 30→**8**（覆蓋週期 6 天→**約 21 天**，已知並接受）、整場 firecrawl 上限 45→**14**、薄弱日加碼收進總額內不另外開、明令嚴禁 5-credit JSON 抽取；補上補跑時的時間窗規則
- **v5.1**（2026-09-20）納入原帳號 ROUND4 更新：每日輪掃制 ＋ `rotate_sources.py`（168 源／6 天一輪）、薄弱日再加碼（<15 則觸發）、整場預算上限改為 firecrawl ≤ 45／WebSearch ≤ 20、日報 HTML 必附 favicon 三行、無人值守 Bash 規則（禁 ls／find 探測）、`build_index.py` 加入合併回顧標籤 `LABEL_OVERRIDE` 與首頁 favicon
- **v5.0**（2026-09-19）三支 skill 合併成一支放進 repo；砍 sources.json 舊設定、砍 AUTO-HEAL、砍 visualize 預覽、砍 Mac 專屬路徑；交叉查證上限 6→3；清除四分類殘留；非 Slot 顏色統一為血紅；來源總數改由 xlsx 動態帶入；Firecrawl 改走 HTTP API；Telegram 改由 GitHub Actions 發送
- v4.1　五大分類（🎰 Slot／🕹️ 非 Slot／🤝 主流動態／🇵🇭 菲律賓／📊 市場數據）
