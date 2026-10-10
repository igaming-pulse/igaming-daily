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
import re
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

ARCH_INTRO = ("本日報為**全自動**產物（規則版本 **v6.6.4**）：每天**台北時間 02:30** 由 Mac 排程啟動，"
              "從收集、選稿、查證、定稿到發布與推播，全程不需人工介入；每週一、週四另會視庫存發一期**特別版**。")
ARCH_SECTIONS = [
    ("① 收集：Claude 開工前，程式 harvest.py 先把當天的新聞收進來", [
        "**第一層｜免費抓取**：RSS／WordPress API／官網 sitemap 約 92 個來源，取得**精確發布時間**；"
        "程式另外解析 BigWinBoard 新作列表、**SlotsLaunch 上線日曆**、Play'n GO 官網上線日",
        "**第二層｜Firecrawl**：每天固定只剩 iGamingToday（擋程式抓取，由程式解析），加上輪掃與三種觸發",
        "**💳 用量分級**：開跑前查 Firecrawl 剩餘點數，今日預算＝（剩餘－保留 20）÷ 距離重置天數，"
        "分「充裕／標準／節約／保命」四級決定抓多少",
        f"**來源主檔**：Excel（目前 **{total} 個來源、{ncats} 大分類**），「抓取方式」「頻率」欄決定每個來源怎麼抓",
    ]),
    ("② 選稿：Claude 讀候選清單與庫存", [
        "**第三層｜WebSearch**：補程式抓不到的題目（菲律賓平台、新品牌進菲、實體機大廠、Slot 補漏）",
        "**打分**：品牌＋事件＋地區＋時效＋熱門 IP，套用 **3 天去重**與硬上限",
        "**Slot 區**：平日 7 款、週末 3 款；窗內大廠新作全收；平日當天新作 ≤5 款、週末 ≤2 款才從**庫存**依 B 分補",
        "**其他分類**：某區當天沒有合格新聞，就從庫存補 1 則",
    ]),
    ("③ 查證與定稿：只對入選的新聞", [
        "**主來源日期關**：發布日期含年份，且落在 24 小時收集窗內（庫存補位要在保鮮期內）",
        "**交叉查證**：至少一個獨立來源佐證，補齊盤面、倍率、RTP 等參數（只增不減）",
        "**定稿檢查（程式）**：格式、連結與配圖、模糊去重、**補位有沒有照 B 分**；"
        "通過後用**固定模板**產生 HTML（不再每天手寫）",
    ]),
    ("④ 發布與推播", [
        "日報、庫存、推播訊息以**單一 commit** 推上 repo，網站由 **GitHub Pages** 自動更新",
        "**Telegram** 早上定時推播；日報晚到（過 06:30）則跑完**立刻推播**；當天沒有日報改發「未產出」警告",
        "**系統警報**：Firecrawl 額度、來源連續失敗、候選量異常、定稿錯誤會附在推播最後",
        "**庫存查詢機器人**：在 Telegram 私訊打「庫存」即可查目前各分類庫存與標題",
    ]),
    ("⑤ 庫存釋放特別版（每週一、週四）", [
        "當天日報**成功後**接著檢查；Slot 可用庫存 **≥5 款**才發，不足就略過",
        "一次最多 **10 款**：大廠（B≥3）在前，其餘先放快過期的；查證不過的直接移出庫存",
        "連結**併進當天日報**的 Telegram 訊息，不另外多發一則",
    ]),
]

DIAGRAMS = [
    ("2-1　每日總流程", """flowchart TD
  A["⏰ 02:30 Mac 排程<br/>開啟防睡眠直到跑完"] --> B["run_daily.sh<br/>拉最新規則"]
  B --> C["harvest.py<br/>查額度分級 → 第一層＋第二層收集"]
  C --> D["候選清單<br/>含精確發布時間"]
  D --> F["讀庫存：今日上限／可用庫存／近 3 天已出現"]
  F --> G["第三層 WebSearch<br/>菲律賓平台・新品牌進菲・實體機・Slot 補漏"]
  G --> H["打分排序＋各區選稿＋庫存補位"]
  H --> I["只對入選者查證<br/>主來源日期→交叉佐證→補參數"]
  I --> J["寫 Markdown 原稿"]
  J --> QA{"定稿檢查通過？"}
  QA -- 否 --> FIX["修原稿重跑（最多 2 次）"]
  FIX --> QA
  QA -- 是 --> T["固定模板產生 HTML"]
  T --> K["Telegram 訊息＋系統警報"]
  K --> L["更新庫存 → 單一 commit"]
  L --> N{"驗收：有新日報＋新 commit？"}
  N -- 否 --> X["記錄失敗原因"]
  N -- 是 --> O["發布到網站"]
  O --> SP{"週一／週四且庫存 ≥5？"}
  SP -- 是 --> SE["發特別版，連結併進推播"]
  SP -- 否 --> PUSH["推播"]
  SE --> PUSH
  PUSH --> Q["Telegram：06:40 定時；過 06:30 才跑完則立刻推播"]
  X --> R["推播「日報未產出」警告"]"""),
    ("2-2　收集：網站內容怎麼抓、怎麼判斷", """flowchart TD
  S["Excel 來源主檔"] ==> W{"抓取方式／頻率？"}
  W == "免費：RSS／WP API／Sitemap（約 92）" ==> L1["第一層 curl：文章清單＋精確時間"]
  W == "免費：程式解析" ==> L0["BigWinBoard 新作・SlotsLaunch 上線日曆"]
  W == "Firecrawl：每日（iGamingToday）" ==> FC{"💳 今日分級？"}
  W == "Firecrawl：輪掃（約 70）" ==> FC
  W -. "Firecrawl：監理・協會・展會" .-> TR{"補充：三種觸發"}
  TR -.-> FC
  FC == "充裕／標準" ==> L2["第二層 Firecrawl：列表頁＋輪掃 2–3＋觸發"]
  FC -- "節約／保命" --> L2S["只抓 iGamingToday，停輪掃"]
  L0 ==> NZ
  L1 ==> NZ{"雜訊？樂透開獎・體育賠率<br/>綜合媒體無博彩關鍵字"}
  NZ -- 是 --> DROP["丟掉"]
  NZ == 否 ==> TW{"在 24 小時窗內？"}
  TW == 是 ==> IN["✅ 當日候選"]
  TW -- "否，Slot 7 天內／其他 3 天內" --> OLD["窗外近期＝庫存候選（另存 backlog）"]
  TW -- 更舊 --> DROP
  IN ==> OUT["候選清單＋來源健檢"]
  OLD --> OUT
  L2 ==> OUT
  L2S --> OUT
  classDef main fill:#FBF6EC,stroke:#1B1A18,stroke-width:2px,color:#1B1A18
  classDef minor fill:#EEE8DC,stroke:#A99F8E,stroke-dasharray:4 3,color:#8C8373
  class S,L0,L1,L2,IN main
  class TR minor"""),
    ("2-3　選稿：每則候選要過的關卡", """flowchart TD
  C["候選（程式＋WebSearch）"] --> D{"近 3 天出現過？"}
  D -- "是，無重大更新" --> OUT1["不收"]
  D -- "超過 3 天且有重大更新" --> RE["可再展示，標 🔁"]
  D -- 否 --> SC["打分：B 品牌＋E 事件＋R 地區＋T 時效＋H 熱門 IP"]
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
  DAY -- 週一～週五 --> C5["上限 7 款"]
  DAY -- 週六、週日 --> C2["上限 3 款"]
  C5 --> N{"平日當天新作 ≤5 款？"}
  C2 --> N2{"週末當天新作 ≤2 款？"}
  N -- 否 --> NOFILL["不補，超過上限的進庫存"]
  N2 -- 否 --> NOFILL
  N -- 是 --> FILL["③ 從庫存依 B 分補到上限<br/>（程式檢查順序）"]
  N2 -- 是 --> FILL
  FILL --> NAT["庫存不夠就自然呈現"]
  SAT["📋 週六檢查點：Weekend Reels＋BigWinBoard 本週新作"] --> MISS{"漏收？"}
  MISS -- 是 --> BU["標「📋 本週補遺」，算在 3 款內，多的進庫存"]"""),
    ("2-5　庫存機制", """flowchart LR
  I1["Slot：超過當日上限的新作"] --> GATE{"進庫存把關"}
  I2["cat2–cat5：每區每天沒用上的最高分 1 則"] --> GATE
  I3["週六補遺多出來的"] --> GATE
  I4["7 天後才上線的預告"] --> GATE
  GATE -- "沒網址／TBC 佔位頁" --> REJ["不收"]
  GATE -- "賓果／Crash 等" --> MV["改歸非 Slot"]
  GATE -- 通過 --> INV[("庫存 inventory.json")]
  MV --> INV
  INV --> O1["Slot：平日 ≤5 款、週末 ≤2 款時依 B 分補到上限"]
  INV --> O2["其他分類：當天空著就補 1 則"]
  INV --> O3["週一／週四特別版：≥5 款就釋放最多 10 款"]
  INV --> EX["過期：Slot 7 天・其他 3 天・預告到上線日＋3 天"]"""),
    ("2-6　庫存釋放特別版（每週一、週四）", """flowchart TD
  A["週一／週四日報"] --> OK{"日報成功？"}
  OK -- 否 --> SKIP["不發"]
  OK -- 是 --> CNT{"Slot 可用庫存 ≥5 款？<br/>不含 7 天外預告"}
  CNT -- 否 --> SKIP
  CNT -- 是 --> SEL["選款：最多 10 款<br/>大廠 B≥3 在前，其餘先放快過期的"]
  SEL --> VER{"每款查證：真實原文＋遊戲確實存在？"}
  VER -- 否 --> RM["剔除並移出庫存"]
  VER -- 是 --> CARD["寫卡片（可用資料庫上線日、保鮮 14 天、參數查不到寫未公布）"]
  CARD --> PUB["定稿檢查 → 特別版頁面上網站"]
  PUB --> TG["連結併進當天日報的 Telegram"]
  PUB --> UPD["發出的移出庫存、寫入 3 天去重"]"""),
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
    ["我們用在哪", "第一層：RSS／WP API／官網 sitemap 約 92 個；程式解析 BigWinBoard、SlotsLaunch 上線日曆", "iGamingToday、輪掃與觸發；入選新聞的內文與配圖（用量依每日分級）", "第三層：菲律賓平台、新品牌進菲、實體機、Slot 補漏", "備用：查證時抓一般網頁"],
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
    ["🎰 cat1 Slot 新遊戲", "線上老虎機新作、7 天內上線的預告、實體老虎機新機台", "平日 ≤7、週末 ≤3", "三段式：總述＋對 PM 的意義／衍生調整／參數"],
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
    ["H 熱門 IP", "+3", "Huff N' Puff、Bao Zhu Zhao Fu、SuperGems 的新作：排 Slot 區最前，預告放寬到 30 天"],
]
TOOL_STEPS = [
    ["工具", "出現在哪個步驟", "流程圖位置"],
    ["curl", "第一層：抓 RSS、WP API、官網 sitemap，以及 BigWinBoard／SlotsLaunch", "2-2「curl：RSS／WP API」分支（分支名稱寫的是資料格式，工具是 curl）"],
    ["Firecrawl", "第二層：iGamingToday、輪掃、三種觸發（強度依 💳 分級）；查證時抓入選新聞的內文與配圖", "2-2「Firecrawl：…」各分支；2-3 查證步驟"],
    ["WebSearch", "第三層：Claude 找來源清單以外的題目（菲律賓平台、新品牌進菲、實體機、Slot 補漏）", "2-1 總流程「第三層 WebSearch」（不在 2-2，因為不是照來源清單抓）"],
    ["WebFetch", "查證時的備用工具", "2-3「交叉佐證＋補參數」（不在 2-2）"],
]
EXTRA = [("三、四種找資料工具對比", TOOLS), ("三之一、工具 × 步驟對照", TOOL_STEPS), ("四、三種觸發（監理・協會・展會）", TRIGGERS),
         ("五、日報結構：五大分類", CATS), ("六、打分表", SCORE)]


# ---------- 流程圖配色：方案 C 修訂版（2026-09-27 定案） ----------
# 判斷節點＝中灰 #616161 白字；「否／剔除」＝淡橘虛線；「是／通過」＝綠線；最終輸出＝實心綠；直角折線
FLOW_OUTPUTS = {"2-1": ["Q"], "2-2": ["OUT"], "2-3": ["W"], "2-4": [], "2-5": [], "2-6": ["TG"]}
REJECT_RX = re.compile(r"丟掉|不收|剔除|失敗|未產出|不上日報|不發")
EDGE_RX = re.compile(r'^\s*(\w+)\s*(?:==>|-->|-\.->|--\s*"?([^">]*?)"?\s*-->|==\s*"?([^">]*?)"?\s*==>|-\.\s*"?([^">]*?)"?\s*\.->|-->\|"?([^|]*?)"?\|)\s*(\w+)')

def style_flow(key, code):
    lines = code.split("\n")
    labels = dict(re.findall(r'(\w+)[\[{(]+"([^"]*)"', code))
    gates = sorted(set(re.findall(r'(\w+)\{"', code)) - {"TR"})   # TR（補充：三種觸發）維持弱化樣式
    rejects = [n for n, t in labels.items() if REJECT_RX.search(t)]
    green, orange, idx = [], [], 0
    node_def = re.compile(r'(\w+)(?:\[\(|\(\[|\[\[|\(\(|\[|\{|\()"[^"]*"(?:\)\]|\]\)|\]\]|\)\)|\]|\}|\))')
    for ln in lines:
        ln = node_def.sub(r"\1", ln)   # 先把行內的節點定義（A["…"]）化簡成 A，邊才不會漏算
        m = EDGE_RX.match(ln)
        if not m:
            continue
        label = next((g for g in m.groups()[1:5] if g), "") or ""
        tgt, minor = m.group(6), "-.->" in ln or ".->" in ln
        if tgt in rejects or m.group(1) in rejects:   # 通往剔除、或從剔除折返的線都用淡橘
            orange.append(idx)
        elif not minor and (label.strip() in ("是", "通過", "否") or label.startswith("是")):
            green.append(idx)
        idx += 1
    extra = ["  classDef gate fill:#616161,stroke:#616161,color:#FFFFFF,font-weight:700",
             "  classDef out fill:#4E9E68,stroke:#3C7F52,color:#FFFFFF,font-weight:700",
             "  classDef muted fill:#EEE8DC,stroke:#A99F8E,color:#6F675A"]
    if gates:
        extra.append("  class " + ",".join(gates) + " gate")
    outs = [o for o in FLOW_OUTPUTS.get(key, []) if o in labels]
    if outs:
        extra.append("  class " + ",".join(outs) + " out")
    if rejects:
        extra.append("  class " + ",".join(rejects) + " muted")
    if green:
        extra.append("  linkStyle " + ",".join(map(str, green)) + " stroke:#4E9E68,stroke-width:2px")
    if orange:
        extra.append("  linkStyle " + ",".join(map(str, orange)) + " stroke:#F2A65A,stroke-width:2px,stroke-dasharray:5 4")
    return code + "\n" + "\n".join(extra)


DIAGRAMS = [(t, style_flow(t[:3], c)) for t, c in DIAGRAMS]


def esc_cell(s):
    return str(s or "").replace("|", "／").replace("\n", " ").strip()


# ---------- Markdown ----------
md = [
    "# 🎰 iGaming 市場日報 — OutputLogic（運作說明）", "",
    "> 本頁記錄「iGaming 市場日報」如何自動生成、涵蓋哪些來源、用什麼邏輯判斷與排序。", "",
    "## 一、生成的基本架構", "", ARCH_INTRO, "",
]
for head, items in ARCH_SECTIONS:
    md += [f"**{head}**", ""] + [f"- {x}" for x in items] + [""]
md += ["## 二、運作邏輯（流程圖）", ""]
for title, code in DIAGRAMS:
    md += [f"### {title}", "", "```mermaid", code, "```", ""]
for title, tbl in EXTRA:
    md += [f"## {title}", "", "| " + " | ".join(tbl[0]) + " |", "|" + "---|" * len(tbl[0])]
    md += ["| " + " | ".join(esc_cell(x) for x in row) + " |" for row in tbl[1:]] + [""]
md += [
    f"## 七、資料來源總表（共 {total} 個）", "",
    f"> 欄位：編號｜網站名稱｜網站網址｜抓取方式｜頻率｜備註｜展期。分類數量：{catsum}。",
]
for cat in active_cats:
    md += ["", f"### {cat}（{len(groups[cat])}）", "",
           "| 編號 | 網站名稱 | 網站網址 | 抓取方式 | 頻率 | 備註 | 展期 |", "|---|---|---|---|---|---|---|"]
    for r in groups[cat]:
        url = str(r[3] or "").strip()
        link = f"[{url}]({url})" if url.startswith("http") else esc_cell(url)
        g = lambda k: esc_cell(r[k]) if len(r) > k else ""
        md.append(f"| {r[0]} | {esc_cell(r[2])} | {link} | {g(5)} | {g(6)} | {esc_cell(r[4])} | {g(9)} |")
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
    return f'  <div class="tablewrap"><table class="kv">\n    <thead><tr>{head}</tr></thead>\n    <tbody>\n{body}\n    </tbody></table></div>'


extra_html = "\n".join(f'  <div class="h2">{h(t)}</div>\n{table_html(tb)}' for t, tb in EXTRA)

tables = []
for i, cat in enumerate(active_cats):
    body = "\n".join(
        f'      <tr><td class="no">{h(r[0])}</td><td>{h(esc_cell(r[2]))}</td>'
        + (f'<td><a href="{h(str(r[3]).strip())}" target="_blank" rel="noopener">{h(str(r[3]).strip())}</a></td>'
           if str(r[3] or "").strip().startswith("http")
           else f'<td class="note">{h(esc_cell(r[3]))}</td>')
        + "".join(f'<td class="note">{h(esc_cell(r[k]) if len(r) > k else "")}</td>' for k in (5, 6))
        + f'<td class="note">{h(esc_cell(r[4]))}</td>'
        + f'<td class="note">{h(esc_cell(r[9]) if len(r) > 9 else "")}</td></tr>'
        for r in groups[cat])
    tables.append(
        f'  <h3 id="cat{i}" class="cat" style="--mk:var(--s{i % 6 + 1})">{h(cat)}<span class="badge">{len(groups[cat])}</span>'
        f'<a class="top" href="#top">↑ 回頂部</a></h3>\n'
        f'  <div class="tablewrap"><table class="src">\n'
        f'    <thead><tr><th>編號</th><th>網站名稱</th><th>網站網址</th><th>抓取方式</th><th>頻率</th><th>備註</th><th>展期</th></tr></thead>\n'
        f'    <tbody>\n{body}\n    </tbody></table></div>')
tables_html = "\n".join(tables)

HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OutputLogic 運作說明</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  /* 風格參考：色譜圖表風（米白紙感底、粗黑標題、細線分隔、深色側欄、彩色色階帶）。CSS 為本站自寫，未複製任何第三方程式碼 */
  :root{--paper:#EEE8DC;--sheet:#F7F3EA;--ink:#1B1A18;--sub:#5F584D;--faint:#8C8373;--rule:#D3C9B7;--dark:#2A2621;--dark-ink:#EDE6D8;
        --s1:#D6493A;--s2:#EC8A2E;--s3:#E4C23A;--s4:#4E9E68;--s5:#3A78C4;--s6:#7654B4}
  *{box-sizing:border-box;margin:0;padding:0}
  html{background:var(--paper)}
  body{background:var(--paper);background-image:radial-gradient(rgba(60,48,30,.035) 1px,transparent 1px);background-size:3px 3px;
       color:var(--ink);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.75;padding-block:40px 60px;padding-inline:20px}
  .wrap{max-width:1000px;margin:0 auto}
  a{color:var(--s5)}
  code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.92em}
  .back{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.06em;color:var(--sub);text-decoration:none}
  .back:hover{color:var(--ink)}
  .masthead{display:grid;grid-template-columns:1fr 240px;gap:0;margin:18px 0 8px;border:1px solid var(--ink);background:var(--sheet)}
  .mh-main{padding:26px 28px 22px;display:flex;flex-direction:column;gap:10px}
  .eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--sub)}
  h1{font-size:40px;line-height:1.15;font-weight:900;letter-spacing:-.5px;text-wrap:balance}
  .sub{color:var(--sub);font-size:14px;max-width:62ch}
  .spectrum{display:flex;height:8px;margin-top:6px}
  .spectrum i{flex:1}
  .mh-side{background:var(--dark);color:var(--dark-ink);padding:22px 20px;display:flex;flex-direction:column;gap:12px;font-family:"IBM Plex Mono",monospace;font-size:12px}
  .mh-side div{display:flex;flex-direction:column;gap:2px;border-bottom:1px solid rgba(237,230,216,.18);padding-bottom:8px}
  .mh-side div:last-child{border-bottom:none}
  .mh-side b{font-size:18px;font-weight:600;color:#fff;font-variant-numeric:tabular-nums}
  .mh-side span{color:#B9AF9C;letter-spacing:.08em;text-transform:uppercase;font-size:10.5px}
  .h2{display:flex;align-items:center;gap:12px;font-size:23px;font-weight:900;margin:44px 0 14px;padding-bottom:10px;border-bottom:2px solid var(--ink);text-wrap:balance}
  .h2::before{content:"";flex:none;width:36px;height:10px;background:linear-gradient(90deg,var(--s1) 0 16.6%,var(--s2) 0 33.3%,var(--s3) 0 50%,var(--s4) 0 66.6%,var(--s5) 0 83.3%,var(--s6) 0)}
  .card{background:var(--sheet);border:1px solid var(--rule);padding:20px 22px;margin-bottom:16px}
  .card h3{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:600;letter-spacing:.04em;color:var(--sub);margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--rule)}
  .arch{font-size:15px;line-height:1.85}
  .arch strong{color:var(--ink);font-weight:900}
  .arch p{margin-bottom:16px;font-size:16px}
  .arch h4{font-size:15.5px;font-weight:900;margin:20px 0 8px;display:flex;align-items:center;gap:8px}
  .arch h4::before{content:"";width:10px;height:10px;background:var(--mk,var(--s4))}
  .arch h4:nth-of-type(1){--mk:var(--s1)} .arch h4:nth-of-type(2){--mk:var(--s2)} .arch h4:nth-of-type(3){--mk:var(--s4)} .arch h4:nth-of-type(4){--mk:var(--s5)}
  .arch ul{list-style:none;display:flex;flex-direction:column;gap:0;border-top:1px solid var(--rule)}
  .arch li{padding:9px 4px;border-bottom:1px solid var(--rule)}
  pre.mermaid{background:transparent;text-align:center;overflow-x:auto;margin:0;font-family:"Noto Sans TC","PingFang TC",sans-serif;white-space:normal}
  .nav{font-family:"IBM Plex Mono",monospace;font-size:12px;background:var(--dark);color:var(--dark-ink);padding:12px 16px;margin-bottom:18px;line-height:2.1}
  .nav a{color:var(--dark-ink);text-decoration:none;white-space:nowrap;border-bottom:1px solid rgba(237,230,216,.35)}
  .nav a:hover{color:#fff;border-bottom-color:#fff}
  h3.cat{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:900;margin:30px 0 10px}
  h3.cat::before{content:"";width:12px;height:12px;background:var(--mk,var(--s4))}
  h3.cat .badge{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;background:var(--ink);color:var(--sheet);padding:1px 8px}
  h3.cat .top{margin-left:auto;font-family:"IBM Plex Mono",monospace;font-size:11.5px;font-weight:500;color:var(--sub);text-decoration:none}
  .tablewrap{overflow-x:auto;border:1px solid var(--ink);background:var(--sheet)}
  table{border-collapse:collapse;width:100%;font-size:13px}
  thead th{position:sticky;top:0;background:var(--dark);color:var(--dark-ink);font-family:"IBM Plex Mono",monospace;font-weight:500;font-size:11.5px;letter-spacing:.06em;text-align:left;padding:10px 12px;white-space:nowrap}
  td{padding:9px 12px;border-bottom:1px solid var(--rule);vertical-align:top}
  tbody tr:nth-child(even) td{background:rgba(238,232,220,.55)}
  tr:last-child td{border-bottom:none}
  td.no{font-family:"IBM Plex Mono",monospace;color:var(--faint);width:48px;font-variant-numeric:tabular-nums}
  td a{word-break:break-all}
  table.src td:nth-child(2){min-width:130px;font-weight:700}
  table.src td:nth-child(3){min-width:240px}
  table.src td:nth-child(4),table.src td:nth-child(5){white-space:nowrap}
  table.src td:nth-child(7){white-space:nowrap;font-family:"IBM Plex Mono",monospace;font-size:12px}
  table.kv td:first-child{white-space:nowrap;font-weight:700}
  td.note{color:var(--sub);min-width:120px}
  .foot{margin-top:40px;padding-top:16px;border-top:2px solid var(--ink);font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--sub);line-height:1.9}
  a:focus-visible{outline:2px solid var(--s5);outline-offset:2px}
  @media(max-width:760px){.masthead{grid-template-columns:1fr}.mh-side{flex-direction:row;flex-wrap:wrap}.mh-side div{border-bottom:none;flex:1;min-width:120px}h1{font-size:30px}.h2{font-size:20px}}
</style>
</head>
<body>
<div class="wrap" id="top">
  <a class="back" href="../">← 回 iGaming 市場日報</a>
  <header class="masthead">
    <div class="mh-main">
      <div class="eyebrow">OutputLogic · 運作說明 · Rules v6.6.4</div>
      <h1>iGaming 市場日報如何產生</h1>
      <div class="sub">從排程、三層收集、選稿與庫存，到查證、發布與推播；以及涵蓋的全部資料來源。</div>
      <div class="spectrum" aria-hidden="true"><i style="background:var(--s1)"></i><i style="background:var(--s2)"></i><i style="background:var(--s3)"></i><i style="background:var(--s4)"></i><i style="background:var(--s5)"></i><i style="background:var(--s6)"></i></div>
    </div>
    <aside class="mh-side">
      <div><span>資料來源</span><b>__TOTAL__</b></div>
      <div><span>來源分類</span><b>__NCATS__</b></div>
      <div><span>每日排程</span><b>02:30</b></div>
      <div><span>Slot 上限</span><b>平日 7／週末 3</b></div>
    </aside>
  </header>

  <div class="h2">一、生成的基本架構</div>
  <div class="card arch">__ARCH__</div>

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
  if(window.mermaid){mermaid.initialize({startOnLoad:true,securityLevel:"loose",theme:"base",themeVariables:{fontFamily:'"Noto Sans TC","PingFang TC",sans-serif',fontSize:"14px",primaryColor:"#FBF6EC",primaryTextColor:"#1B1A18",primaryBorderColor:"#5F584D",lineColor:"#8C8373",secondaryColor:"#EEE8DC",tertiaryColor:"#F7F3EA",edgeLabelBackground:"#F7F3EA",clusterBkg:"#F7F3EA"},flowchart:{htmlLabels:true,useMaxWidth:true,curve:"stepAfter"}});}
</script>
</body>
</html>
"""
arch_html = f"<p>{bold_html(ARCH_INTRO)}</p>" + "".join(
    f"<h4>{h(head)}</h4><ul>" + "".join(f"<li>{bold_html(x)}</li>" for x in items) + "</ul>"
    for head, items in ARCH_SECTIONS)
HTML = (HTML.replace("__ARCH__", arch_html)
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
