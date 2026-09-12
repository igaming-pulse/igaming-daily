#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生 OutputLogic 說明頁：Markdown（本機預覽）＋ 精美 HTML（發布用，流程圖以 mermaid 渲染）。
來源表格讀自主檔 xlsx；架構文字與流程圖為內建。來源異動後重跑即可更新。
用法：python3 build_outputlogic.py
輸出：OutputLogic.md、OutputLogic/index.html（本檔同目錄）
"""
import os, re, html, collections
import openpyxl

ROOT = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(os.path.expanduser("~"),
                    "Desktop/All-in AI/04_Docs/NewsReport/igaming-daily-report-sources-v2.xlsx")
OUT_MD = os.path.join(ROOT, "OutputLogic.md")
OUT_DIR = os.path.join(ROOT, "OutputLogic")
OUT_HTML = os.path.join(OUT_DIR, "index.html")
ORDER = ["Provider 官網", "產品分析／評測", "產業媒體", "產業協會／技術認證機構",
         "市場數據／分析公司", "監理機關／官方數據", "展會", "論壇／社群",
         "Podcast／影音", "已停用"]

wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
ws = wb.active
rows = [r for r in ws.iter_rows(values_only=True)][1:]
rows = [r for r in rows if r and r[3] and str(r[3]).startswith("http")]
total = len(rows)
groups = collections.OrderedDict((c, []) for c in ORDER)
for r in rows:
    groups.setdefault(str(r[1]).strip(), []).append(r)
active_cats = [c for c in ORDER if groups.get(c)]
catsum = "、".join(f"{c} {len(groups[c])}" for c in active_cats)

ARCH = ("本日報為**全自動**產物：每天**台北時間 02:30** 由排程觸發（半夜跑，讓運算用量在上班前就退出額度視窗；"
        "Email 於 02:30 即時寄出，Telegram 通知則延到 **06:30** 由系統排程零額外成本發送）。流程先**同步來源庫**"
        "——以 Excel 主檔 igaming-daily-report-sources-v2.xlsx（目前 **%d 個來源、10 大分類**）為唯一真相，重建成程式讀取的 sources.md；"
        "主檔若遺失會自動反向重建。接著**抓取新聞**：跨分類主動取材，被擋的站改用 Firecrawl（不觸發逐站授權），"
        "並依五大分類（🎰 Slot 新遊戲、🕹️ 非 Slot、🤝 主流動態、🇵🇭 菲律賓、📊 市場數據）歸位。"
        "**辨識與優先級**依序判斷：先分類，再看是否為「優先展示品牌」（Yggdrasil、Jili、DigiPlus 等）與市場衝擊性，高者排前、寧缺毋濫。"
        "每則都要**交叉查證**：至少再找一個獨立來源佐證、用官網／SlotCatalog 補全參數、遇數據衝突以最權威來源為準並標註"
        "——且**只增不減**，基本參數（盤面／倍率／RTP／波動）必須填滿。最後渲染成精美 HTML、發布 GitHub Pages，"
        "並附上「本日查詢約 N 個網站、提取 N 個來源交叉比對」的統計。") % total

DIAGRAMS = [
    ("2-1　每日總流程", """flowchart TD
  T["⏰ 每天 02:30 觸發"] --> S0["步驟0 同步來源庫<br/>xlsx → sources.md（%d 源）"]
  S0 --> S1["步驟1 抓新聞<br/>五大分類 · 交叉查證"]
  S1 --> S2["步驟2 渲染精美 HTML"]
  S2 --> S3["步驟3 發布 GitHub Pages"]
  S3 --> S4["步驟4 Email 即時寄出 ✉️"]
  S4 --> P["預存 Telegram 訊息（不即時發）"]
  P --> S6["步驟6 回報"]
  P -. "06:30 launchd · 零 token" .-> TG["📲 Telegram 推播"]""" % total),
    ("2-2　新聞分類辨識", """flowchart TD
  N["一則新聞"] --> Q1{"是新遊戲？"}
  Q1 -- "是 · Slot" --> C1["🎰 cat1 Slot 新遊戲"]
  Q1 -- "是 · 非 Slot（Crash/Live/Bingo）" --> C2["🕹️ cat2 非 Slot"]
  Q1 -- "否" --> Q2{"是趨勢/數據/報告？"}
  Q2 -- "是" --> C5["📊 cat5 市場數據"]
  Q2 -- "否" --> Q3{"涉及菲律賓廠商/平台/PAGCOR？"}
  Q3 -- "是" --> C4["🇵🇭 cat4 菲律賓"]
  Q3 -- "否" --> C3["🤝 cat3 主流動態"]"""),
    ("2-3　優先級判斷", """flowchart LR
  A["候選新聞"] --> B{"優先展示品牌？"}
  B -- "是（Yggdrasil/Jili/DigiPlus…）" --> P1["排該區前段"]
  B -- 否 --> C{"市場衝擊性高？"}
  C -- 高 --> P2["優先收錄"]
  C -- 低 --> P3["寧缺毋濫 · 可略過"]"""),
    ("2-4　交叉查證（只增不減）", """flowchart TD
  X["取得一則（單一來源）"] --> Y["找 ≥1 個獨立來源佐證"]
  Y --> Z["補全參數：SlotCatalog／Provider 官網"]
  Z --> W{"多來源數據衝突？"}
  W -- 是 --> W1["以最權威來源為準<br/>＋標註『各來源不一』"]
  W -- 否 --> W2["保留並增豐（只增不減）"]
  W1 --> O["列出所有查證來源 → 輸出"]
  W2 --> O"""),
    ("2-5　來源庫維護（雙向同步 · 自癒）", """flowchart LR
  XLSX["📗 主檔 xlsx<br/>%d 源 · 唯一真相"] -->|"每天 02:30 同步"| MD["📄 sources.md（skill 讀取）"]
  MD -.->|"xlsx 遺失 → 自癒重建"| XLSX""" % total),
]


def esc_cell(s):
    return str(s or "").replace("|", "／").replace("\n", " ").strip()


# ---------- Markdown ----------
def bold_md(t):
    return t
md = ["# 🎰 iGaming 市場日報 — OutputLogic（運作說明）", "",
      "> 本頁記錄「iGaming 市場日報」如何自動生成、涵蓋哪些來源、用什麼邏輯判斷與排序，作為日後維護與查證的說明書。", "",
      "## 一、生成的基本架構（約 300 字）", "", ARCH, "", "## 二、運作邏輯（流程圖）", ""]
for title, code in DIAGRAMS:
    md += [f"### {title}", "", "```mermaid", code, "```", ""]
md += [f"## 三、資料來源總表（共 {total} 個，依主檔 xlsx 五欄呈現）", "",
       f"> 欄位：編號｜分類｜網站名稱｜網站網址｜備註。分類數量：{catsum}。"]
for cat in active_cats:
    md += ["", f"### {cat}（{len(groups[cat])}）", "", "| 編號 | 網站名稱 | 網站網址 | 備註 |", "|---|---|---|---|"]
    for r in groups[cat]:
        md.append(f"| {r[0]} | {esc_cell(r[2])} | [{str(r[3]).strip()}]({str(r[3]).strip()}) | {esc_cell(r[4])} |")
md += ["", "---", "*本頁由 build_outputlogic.py 讀取主檔 xlsx 自動產生；來源異動後重跑即可更新。*", ""]
open(OUT_MD, "w", encoding="utf-8").write("\n".join(md))


# ---------- HTML ----------
def h(s):
    return html.escape(str(s or ""), quote=True)

def bold_html(t):
    out, b = [], False
    for i, seg in enumerate(t.split("**")):
        if i % 2 == 1:
            out.append("<strong>" + h(seg) + "</strong>")
        else:
            out.append(h(seg))
    return "".join(out)

diagram_html = "\n".join(
    f'  <div class="card"><h3>{h(t)}</h3><pre class="mermaid">\n{c}\n</pre></div>'
    for t, c in DIAGRAMS)

# 分類導覽
nav = " · ".join(f'<a href="#cat{i}">{h(c)}（{len(groups[c])}）</a>' for i, c in enumerate(active_cats))

# 分類表格
tables = []
for i, cat in enumerate(active_cats):
    body = "\n".join(
        f'      <tr><td class="no">{h(r[0])}</td><td>{h(esc_cell(r[2]))}</td>'
        f'<td><a href="{h(str(r[3]).strip())}" target="_blank" rel="noopener">{h(str(r[3]).strip())}</a></td>'
        f'<td class="note">{h(esc_cell(r[4]))}</td></tr>'
        for r in groups[cat])
    tables.append(
        f'  <h3 id="cat{i}" class="cat">{h(cat)}<span class="badge">{len(groups[cat])}</span>'
        f'<a class="top" href="#top">↑ 回頂部</a></h3>\n'
        f'  <div class="tablewrap"><table>\n'
        f'    <thead><tr><th>編號</th><th>網站名稱</th><th>網站網址</th><th>備註</th></tr></thead>\n'
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
  <div class="sub">iGaming 市場日報如何自動生成、涵蓋哪些來源、用什麼邏輯判斷與排序</div>

  <div class="h2">一、生成的基本架構</div>
  <div class="card"><p class="arch">__ARCH__</p></div>

  <div class="h2">二、運作邏輯（流程圖）</div>
__DIAGRAMS__

  <div class="h2">三、資料來源總表（共 __TOTAL__ 個 · 依主檔 xlsx 五欄）</div>
  <div class="nav">__NAV__</div>
__TABLES__

  <div class="foot">本頁由 build_outputlogic.py 讀取主檔 <code>igaming-daily-report-sources-v2.xlsx</code> 自動產生 · 來源異動後重跑即更新<br>© iGaming Daily</div>
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
            .replace("__NAV__", nav)
            .replace("__TABLES__", tables_html)
            .replace("__TOTAL__", str(total)))
os.makedirs(OUT_DIR, exist_ok=True)
open(OUT_HTML, "w", encoding="utf-8").write(HTML)

print("✓ 已產生：")
print("   MD  :", OUT_MD)
print("   HTML:", OUT_HTML)
print("   來源 %d 個、%d 分類" % (total, len(active_cats)))
