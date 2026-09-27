#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
產生 OutputLogic 運作說明頁：Markdown（repo 內閱讀）＋ HTML（發布用，mermaid 流程圖）。

與 Mac 舊版的差異：
  - xlsx 改 repo 相對路徑
  - 來源總數與分類數**全部動態帶入**，不再有寫死的 218／10
  - 流程圖更新為現行架構（02:30 本機 CLI → push；06:30 GitHub Actions）
  - 只在「來源異動」時需要重跑，不再每天執行

用法：python3 scripts/build_outputlogic.py
輸出：OutputLogic.md、OutputLogic/index.html
"""
import os
import html
import collections
import sys

try:
    import openpyxl
except ImportError:
    sys.exit("✗ 需要 openpyxl：pip3 install openpyxl --break-system-packages")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, "sources", "igaming-daily-report-sources-v2.xlsx")
OUT_MD = os.path.join(ROOT, "OutputLogic.md")
OUT_DIR = os.path.join(ROOT, "OutputLogic")
OUT_HTML = os.path.join(OUT_DIR, "index.html")

ORDER = [
    "Provider 官網", "產品分析／評測", "產業媒體", "產業協會／技術認證機構",
    "市場數據／分析公司", "監理機關／官方數據", "展會", "論壇／社群",
    "Podcast／影音", "已停用",
]

wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
ws = wb.active
rows = [r for r in ws.iter_rows(values_only=True)][1:]
rows = [r for r in rows if r and r[1]]
total = len(rows)

groups = collections.OrderedDict((c, []) for c in ORDER)
for r in rows:
    groups.setdefault(str(r[1]).strip(), []).append(r)
active_cats = [c for c in ORDER if groups.get(c)]
for c in groups:
    if c not in active_cats and groups[c]:
        active_cats.append(c)
ncats = len(active_cats)
catsum = "、".join(f"{c} {len(groups[c])}" for c in active_cats)

ARCH = (
    "本日報為**全自動**產物（規則版本 **v6.4.2**）：每天**台北時間 02:30** 由 Mac 排程啟動。"
    "Claude 開工前，程式 **harvest.py** 先把當天的新聞收進來：**第一層**用 RSS／WordPress API 免費掃約 90 個來源，"
    "拿到每篇文章**精確到分鐘的發布時間**；**第二層**用 Firecrawl 抓沒有 API 的高價值站（Slot 資料庫站、SBC News、IAG）與每日輪掃 3 站，"
    "並依**三種觸發**（事件、行事曆、每週一固定週期）抓監理機關、協會與展會。"
    f"來源主檔是 Excel（目前 **{total} 個來源、{ncats} 大分類**），「抓取方式」「頻率」欄決定每個來源怎麼抓。"
    "接著 Claude 讀候選清單與**庫存**狀態，用 **WebSearch** 補程式抓不到的題目（菲律賓平台、新品牌進菲、實體機大廠、Slot 補漏），"
    "以「品牌＋事件＋地區＋時效」打分，套用 **3 天去重**與硬上限選稿：**Slot 平日 5 款、週末 2 款，窗內大廠新作全收，當天 ≤3 款才從庫存補**。"
    "入選者先過**主來源日期關**（發布日期含年份且在 24 小時窗內），再做**交叉查證**並補齊參數（只增不減）。"
    "寫稿、渲染 HTML、寫 Telegram 預存訊息、更新庫存後，以單一 commit 推上 repo，網站由 GitHub Pages 自動更新；"
    "**Telegram 由 GitHub Actions 在早上定時推播**（當天沒有日報則改發「未產出」警告）。"
)

DIAGRAMS = [
    ("2-1　每日總流程", """flowchart TD
  A["⏰ 02:30 Mac 排程"] --> B["run_daily.sh<br/>拉最新規則"]
  B --> C["harvest.py<br/>第一層＋第二層收集"]
  C --> D["候選清單<br/>含精確發布時間"]
  D --> E["Claude 讀候選＋列表頁存檔"]
  E --> F["讀庫存：今日上限／可用庫存／近 3 天已出現"]
  F --> G["第三層 WebSearch<br/>菲律賓平台・新品牌進菲・實體機・Slot 補漏"]
  G --> H["打分排序＋各區選稿"]
  H --> I["只對入選者查證<br/>主來源日期→交叉佐證→補參數"]
  I --> J["寫 Markdown → 渲染 HTML"]
  J --> K["寫 Telegram 預存訊息"]
  K --> L["更新庫存"]
  L --> M["單一 commit 推上 repo"]
  M --> N{"驗收：有新日報＋新 commit？"}
  N -- 是 --> O["發布到網站（GitHub Pages）"]
  N -- 否 --> X["記錄失敗原因"]
  O --> Q["早上 GitHub Actions 推播 Telegram"]
  X --> R["推播「日報未產出」警告\""""),
    ("2-2　收集：網站內容怎麼抓、怎麼判斷", """flowchart TD
  S["Excel 來源主檔"] --> W{"抓取方式／頻率？"}
  W -- "RSS／WP API（約 90）" --> L1["第一層 curl：文章清單＋精確時間"]
  W -- "Firecrawl・每日（6）" --> L2["第二層 Firecrawl：Slot 資料庫站・SBC News・IAG"]
  W -- "Firecrawl・輪掃（約 70）" --> RT["每天輪 3 個"]
  W -- "每週／事件（監理・協會）" --> TR{"三種觸發"}
  W -- "行事曆（展會）" --> TR
  TR --> E1["事件：標題命中關鍵字<br/>每個關鍵字每週一次"]
  TR --> E2["行事曆：開展前 14 天～閉展日"]
  TR --> E3["固定：每週一輪 3 個"]
  RT --> L2
  E1 --> L2
  E2 --> L2
  E3 --> L2
  L1 --> NZ{"雜訊？樂透開獎・體育賠率<br/>綜合媒體無博彩關鍵字"}
  NZ -- 是 --> DROP["丟掉"]
  NZ -- 否 --> TW{"在 24 小時窗內？"}
  TW -- 是 --> IN["✅ 當日候選"]
  TW -- "否，Slot 7 天內／其他 3 天內" --> OLD["窗外近期＝庫存候選"]
  TW -- 更舊 --> DROP
  IN --> OUT["候選清單＋來源健檢"]
  OLD --> OUT
  L2 --> OUT"""),
    ("2-3　選稿：每則候選要過的關卡", """flowchart TD
  C["候選（程式＋WebSearch）"] --> D{"近 3 天出現過？"}
  D -- "是，無重大更新" --> OUT1["不收"]
  D -- "超過 3 天且有重大更新" --> RE["可再展示，標 🔁"]
  D -- 否 --> SC["打分：B 品牌＋E 事件＋R 地區＋T 時效"]
  RE --> SC
  SC --> CAP{"硬上限：同 GP ≤2・其他國家 ≤3・總量 ≤22"}
  CAP -- 超過 --> STOCK["進庫存"]
  CAP -- 通過 --> PICK["依各區目標選入"]
  PICK --> V{"主來源日期含年份、在窗內？"}
  V -- 否 --> SWAP["剔除，換下一名"]
  SWAP --> PICK
  V -- 是 --> X["交叉佐證＋補參數"]
  X --> W["寫入日報"]"""),
    ("2-4　Slot 區選法與庫存調用", """flowchart TD
  A["當日 Slot 候選"] --> PV{"預告：上線日在 7 天以後？"}
  PV -- 是 --> LATER["不上日報，存入庫存「待上線」"]
  PV -- 否 --> BIG["① 窗內大廠 B≥3 全收（同 GP ≤2）"]
  BIG --> OTHER["② 其他窗內新作依分數補"]
  OTHER --> DAY{"日報是？"}
  DAY -- 週一～週五 --> C5["上限 5 款"]
  DAY -- 週六、週日 --> C2["上限 2 款"]
  C5 --> N{"當天新作幾款？"}
  C2 --> N
  N -- "≥4 款" --> NOFILL["不補，超過上限的進庫存"]
  N -- "≤3 款" --> FILL["③ 從庫存補到上限"]
  FILL --> NAT["庫存不夠就自然呈現"]
  SAT["📋 週六檢查點：Weekend Reels＋BigWinBoard 本週新作"] --> MISS{"漏收？"}
  MISS -- 是 --> BU["標「📋 本週補遺」，算在 2 款內，多的進庫存\""""),
    ("2-5　庫存機制", """flowchart LR
  I1["Slot：超過當日上限的新作"] --> INV[("庫存 inventory.json")]
  I2["cat2–cat5：每區每天分數最高、沒用上的 1 則"] --> INV
  I3["週六補遺多出來的"] --> INV
  I4["7 天後才上線的預告"] --> INV
  INV --> O1["Slot：當天 ≤3 款時補到上限"]
  INV --> O2["其他分類：連續空 2 天，第 3 天補 1–2 則"]
  INV --> EX["過期：Slot 7 天・其他 3 天・預告到上線日＋3 天\""""),
]

TOOLS = [
    ["", "curl", "Firecrawl", "WebSearch", "WebFetch"],
    ["是什麼", "從 Mac 直接向網站要原始檔案", "雲端服務，用真瀏覽器打開網頁再整理回傳", "搜尋引擎，下關鍵字找全網", "Claude 內建的抓頁工具，抓完順便摘要"],
    ["成本", "免費", "每次 1 點（月額度 1,000）", "免費（每天上限 60 次）", "免費"],
    ["速度", "快，90 個來源約 10 秒", "慢，每分鐘最多 20 次", "中等，每次數秒", "中等，每次數秒"],
    ["要知道網址嗎", "要", "要", "不用，給關鍵字即可", "要"],
    ["需要 JavaScript 的網頁", "拿到空殼", "可以", "不適用", "常拿到空殼"],
    ["防機器人的站", "常被擋（403）", "多數能通過", "不受影響", "常被擋"],
    ["發布時間", "RSS／WP API 精確到秒；一般網頁要自己找", "附在標籤資料裡，常有", "只有大概日期，常不準", "要自己從內文判斷"],
    ["回傳內容", "原始碼、RSS、JSON，要自己解析", "整理好的 markdown 或摘要，附配圖、發布時間", "標題、網址、摘要片段", "依提問整理過的摘要，看不到全文"],
    ["主要風險", "被擋、網頁改版就解析失敗", "額度用完、速率限制", "容易撈到舊聞、長青排行頁", "摘要可能遺漏或誤讀細節"],
    ["我們用在哪", "第一層：RSS 約 30、WP API 約 60、BigWinBoard 新作列表", "第二層列表頁、觸發來源、入選新聞的內文與配圖", "第三層：菲律賓平台、新品牌進菲、實體機、Slot 補漏", "備用：查證時抓一般網頁"],
    ["判斷順序", "① 有 RSS／WP API 或網頁抓得到就用它", "③ curl 或 WebFetch 被擋才用", "④ 來源清單以外的題目", "② curl 不方便解析時的替代"],
]
TRIGGERS = [
    ["觸發", "對象", "條件", "上限"],
    ["事件觸發", "監理機關（含 PAGCOR）、沒有 API 的協會", "當天窗內新聞的標題命中該機構的關鍵字 → 抓官方頁當主來源／佐證；菲律賓、亞洲機構優先", "每個關鍵字每週一次、每天最多 3 個"],
    ["行事曆觸發", "展會（依 Excel 展期）", "開展前 14 天～閉展日，每天抓該展會新聞頁", "每天最多 2 個，開展日近者優先"],
    ["固定週期", "監理機關＋沒有 API 的協會", "每週一（平日裡新聞最少的一天）輪 3 個", "每週 3 個"],
]
CATS = [
    ["分類", "收什麼", "每天數量", "格式"],
    ["🎰 cat1 Slot 新遊戲", "線上老虎機新作、7 天內上線的預告、實體老虎機新機台", "平日 ≤5、週末 ≤2", "三段式：總述＋對 PM 的意義／衍生調整／參數"],
    ["🕹️ cat2 非 Slot 新內容", "小遊戲 → Live Game → 撲克 → 棋牌 → 其他；EEZE 每日固定 1 則", "目標 2–3、上限 5", "三段式，參數 3 或 5 欄"],
    ["🤝 cat3 主流 GP／平台動態", "大品牌具體動作：合作、併購、提告、運營；線上與實體機大廠", "目標 3–5、上限 7", "動態格式"],
    ["🇵🇭 cat4 菲律賓", "平台策略與新產品 ＞ 新品牌進菲 ＞ GP 上架 ＞ 政策", "目標 2–4，商業 ≤6，官方另計", "動態格式"],
    ["📊 cat5 市場數據 & 趨勢", "老虎機設計趨勢優先，其次市場數據、展會影響", "目標 1–3、上限 5", "市場格式"],
]
SCORE = [
    ["項目", "分數", "內容"],
    ["B 品牌", "6／4／3／1／0", "6：優先品牌 21 家（Acewin、Omiplay、YellowBat、ATG、EEZE、Yggdrasil、Jili、TaDa、DigiPlus 系、Stake、PAGCOR 等）；4：PG Soft、Pragmatic、Nolimit、Play'n GO、Red Tiger、Aristocrat、IGT、L&W；3：二線知名；1：其他"],
    ["E 事件", "6／5.5／5／2／1／0.5", "6：新遊戲上線、實體機首發、重大整合；5.5：新作預告；5：市場數據、玩法流行；2：展會；1：法規、M&A、財報；0.5：人事、獲獎、行銷"],
    ["R 地區", "6／5／4／3／2／1", "6：菲律賓；5：台灣、東南亞；4：拉美、巴西、全球；3：美國、歐洲；2：澳門、日韓、中國；1：其他"],
    ["T 時效", "+2／+1／0", "窗內 0–12 小時 +2；12–24 小時 +1；只精確到日 0"],
]
EXTRA = [("三、四種找資料工具對比", TOOLS), ("四、三種觸發（監理・協會・展會）", TRIGGERS),
         ("五、日報結構：五大分類", CATS), ("六、打分表", SCORE)]


def esc_cell(s):
    return str(s or "").replace("|", "／").replace("\n", " ").strip()


# ---------- Markdown ----------
md = [
    "# 🎰 iGaming 市場日報 — OutputLogic（運作說明）", "",
    "> 本頁記錄「iGaming 市場日報」如何自動生成、涵蓋哪些來源、用什麼邏輯判斷與排序。", "",
    "## 一、生成的基本架構", "", ARCH, "", "## 二、運作邏輯（流程圖）", "",
]
for title, code in DIAGRAMS:
    md += [f"### {title}", "", "```mermaid", code, "```", ""]
for title, tbl in EXTRA:
    md += [f"## {title}", "", "| " + " | ".join(tbl[0]) + " |", "|" + "---|" * len(tbl[0])]
    md += ["| " + " | ".join(esc_cell(x) for x in row) + " |" for row in tbl[1:]] + [""]
md += [
    f"## 七、資料來源總表（共 {total} 個）", "",
    f"> 欄位：編號｜網站名稱｜網站網址｜抓取方式｜頻率｜展期｜備註。分類數量：{catsum}。",
]
for cat in active_cats:
    md += ["", f"### {cat}（{len(groups[cat])}）", "",
           "| 編號 | 網站名稱 | 網站網址 | 抓取方式 | 頻率 | 展期 | 備註 |", "|---|---|---|---|---|---|---|"]
    for r in groups[cat]:
        url = str(r[3] or "").strip()
        link = f"[{url}]({url})" if url.startswith("http") else esc_cell(url)
        g = lambda k: esc_cell(r[k]) if len(r) > k else ""
        md.append(f"| {r[0]} | {esc_cell(r[2])} | {link} | {g(5)} | {g(6)} | {g(9)} | {esc_cell(r[4])} |")
md += ["", "---",
       "*本頁由 scripts/build_outputlogic.py 讀取主檔 xlsx 自動產生；來源異動後重跑即可更新。*", ""]
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(md))


# ---------- HTML ----------
def h(s):
    return html.escape(str(s or ""), quote=True)


def bold_html(t):
    out = []
    for i, seg in enumerate(t.split("**")):
        out.append("<strong>" + h(seg) + "</strong>" if i % 2 else h(seg))
    return "".join(out)


diagram_html = "\n".join(
    f'  <div class="card"><h3>{h(t)}</h3><pre class="mermaid">\n{c}\n</pre></div>'
    for t, c in DIAGRAMS)

nav = " · ".join(f'<a href="#cat{i}">{h(c)}（{len(groups[c])}）</a>'
                 for i, c in enumerate(active_cats))

def table_html(tbl):
    head = "".join(f"<th>{h(x)}</th>" for x in tbl[0])
    body = "\n".join("      <tr>" + "".join(f"<td>{h(x)}</td>" for x in row) + "</tr>" for row in tbl[1:])
    return f'  <div class="tablewrap"><table>\n    <thead><tr>{head}</tr></thead>\n    <tbody>\n{body}\n    </tbody></table></div>'


extra_html = "\n".join(f'  <div class="h2">{h(t)}</div>\n{table_html(tb)}' for t, tb in EXTRA)

tables = []
for i, cat in enumerate(active_cats):
    body = "\n".join(
        f'      <tr><td class="no">{h(r[0])}</td><td>{h(esc_cell(r[2]))}</td>'
        + (f'<td><a href="{h(str(r[3]).strip())}" target="_blank" rel="noopener">{h(str(r[3]).strip())}</a></td>'
           if str(r[3] or "").strip().startswith("http")
           else f'<td class="note">{h(esc_cell(r[3]))}</td>')
        + "".join(f'<td class="note">{h(esc_cell(r[k]) if len(r) > k else "")}</td>' for k in (5, 6, 9))
        + f'<td class="note">{h(esc_cell(r[4]))}</td></tr>'
        for r in groups[cat])
    tables.append(
        f'  <h3 id="cat{i}" class="cat">{h(cat)}<span class="badge">{len(groups[cat])}</span>'
        f'<a class="top" href="#top">↑ 回頂部</a></h3>\n'
        f'  <div class="tablewrap"><table>\n'
        f'    <thead><tr><th>編號</th><th>網站名稱</th><th>網站網址</th><th>抓取方式</th><th>頻率</th><th>展期</th><th>備註</th></tr></thead>\n'
        f'    <tbody>\n{body}\n    </tbody></table></div>')
tables_html = "\n".join(tables)

HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OutputLogic — iGaming 市場日報 運作說明</title>
<style>
  :root{--bg:#F5F7FA;--card:#fff;--ink:#1A2230;--sub:#5B6675;--line:#E7EBF0;--accent:#1D9E75;--accent2:#0F6E56}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang TC","Noto Sans TC","Segoe UI",sans-serif;line-height:1.75;padding:36px 16px}
  .wrap{max-width:960px;margin:0 auto}
  a{color:#185FA5}
  .back{font-size:13px;color:var(--sub);text-decoration:none}
  h1{font-size:30px;font-weight:800;letter-spacing:-.5px;margin:10px 0 4px}
  .sub{color:var(--sub);font-size:14px;margin-bottom:6px}
  .h2{font-size:22px;font-weight:800;margin:34px 0 14px;padding-left:12px;border-left:6px solid var(--accent)}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:16px}
  .card h3{font-size:15px;font-weight:800;color:var(--accent2);margin-bottom:10px}
  .arch{font-size:15px;line-height:1.95;text-align:justify}
  .arch strong{color:var(--accent2)}
  pre.mermaid{background:#fff;text-align:center;overflow-x:auto;margin:0}
  .nav{font-size:12.5px;color:var(--sub);background:#EEF6F2;border:1px solid #D6EAE0;border-radius:10px;padding:10px 14px;margin-bottom:16px;line-height:2}
  .nav a{color:var(--accent2);text-decoration:none;white-space:nowrap}
  h3.cat{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:800;margin:26px 0 10px;padding-left:10px;border-left:5px solid var(--accent)}
  h3.cat .badge{font-size:12px;font-weight:700;background:#E1F5EE;color:var(--accent2);padding:2px 9px;border-radius:20px}
  h3.cat .top{margin-left:auto;font-size:12px;font-weight:600;color:var(--sub);text-decoration:none}
  .tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:#fff}
  table{border-collapse:collapse;width:100%;font-size:13px}
  thead th{position:sticky;top:0;background:#F2F6F4;color:var(--accent2);text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
  td{padding:9px 12px;border-bottom:1px solid #F0F2F5;vertical-align:top}
  tr:last-child td{border-bottom:none}
  td.no{color:var(--sub);width:48px}
  td a{word-break:break-all}
  td.note{color:#4a5563;min-width:200px}
  .foot{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--sub);text-align:center;line-height:1.8}
  @media(max-width:640px){h1{font-size:24px}.h2{font-size:19px}}
</style>
</head>
<body>
<div class="wrap" id="top">
  <a class="back" href="../">← 回 iGaming 市場日報</a>
  <h1>🎰 OutputLogic — 運作說明</h1>
  <div class="sub">iGaming 市場日報如何自動生成、涵蓋哪些來源、用什麼邏輯判斷與排序 · 規則版本 v6.4.2</div>

  <div class="h2">一、生成的基本架構</div>
  <div class="card"><p class="arch">__ARCH__</p></div>

  <div class="h2">二、運作邏輯（流程圖）</div>
__DIAGRAMS__

__EXTRA__

  <div class="h2">七、資料來源總表（共 __TOTAL__ 個 · __NCATS__ 大分類）</div>
  <div class="nav">__NAV__</div>
__TABLES__

  <div class="foot">本頁由 scripts/build_outputlogic.py 讀取 repo 內主檔 <code>sources/igaming-daily-report-sources-v2.xlsx</code> 自動產生 · 來源異動後重跑即更新<br>© iGaming Daily</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
  if(window.mermaid){mermaid.initialize({startOnLoad:true,securityLevel:"loose",theme:"neutral",flowchart:{htmlLabels:true,useMaxWidth:true}});}
</script>
</body>
</html>
"""
HTML = (HTML.replace("__ARCH__", bold_html(ARCH))
            .replace("__DIAGRAMS__", diagram_html)
            .replace("__EXTRA__", extra_html)
            .replace("__NAV__", nav)
            .replace("__TABLES__", tables_html)
            .replace("__TOTAL__", str(total))
            .replace("__NCATS__", str(ncats)))
os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(HTML)

print("✓ 已產生：")
print("   MD  :", OUT_MD)
print("   HTML:", OUT_HTML)
print(f"   來源 {total} 個、{ncats} 分類")
