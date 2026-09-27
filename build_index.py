#!/usr/bin/env python3
"""掃 reports/*.html 產生 index.html（日報存檔首頁，最新在上）。"""
import os, re, glob, html
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(ROOT, "reports")

# 收集 YYYY-MM-DD.html
files = []
for f in glob.glob(os.path.join(REPORTS, "*.html")):
    b = os.path.basename(f)
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(-test|-v\d+|-special)?\.html$", b)
    if m:
        files.append((b[:10], b))
files.sort(reverse=True)  # 最新在上

def weekday_zh(datestr):
    wd = ["一", "二", "三", "四", "五", "六", "日"]
    try:
        return "週" + wd[datetime.strptime(datestr, "%Y-%m-%d").weekday()]
    except Exception:
        return ""

# 合併單位標籤覆寫：某些日報是「跨兩天合併回顧」，檔名沿用起始日（可被本掃描器收錄、
# 排序正確），但首頁卡片要顯示合併後的日期與星期。key=檔名日期，value=(顯示日期, 星期字串)。
LABEL_OVERRIDE = {
    "2026-09-08": ("2026-09-08＋09", "週二/三"),
}

cards = []
for date, fname in files:
    disp_date, disp_wd = LABEL_OVERRIDE.get(date, (date, weekday_zh(date)))
    if fname.endswith("-test.html"):
        disp_wd = disp_wd + " （測試）"
    vm = re.search(r"-v(\d+)\.html$", fname)
    if vm:
        v = vm.group(1)
        # -v2 ＝ 第二版重跑；-v64 ＝ 用 v6.4 規則重跑（兩位數以上視為規則版本號）
        disp_wd += f" （測試・第{v}版 v{v}）" if len(v) == 1 else f" （測試・v{v[0]}.{v[1:]} 規則）"
    label = f"{disp_wd} · iGaming 市場日報"
    # 卡片底色依「來源與內容」區分：
    #   <date>.html          ＝ 原本機器（Claude 帳號 natekao）→ 淡橘
    #   <date>-special.html  ＝ 特別版本內容 → 淡藍
    #   -test／-vN           ＝ 公司帳號機器（nathan.kao@bituslabs.com）→ 維持原樣
    kind = ""
    if fname.endswith("-special.html"):
        label = f"{disp_wd} 特別版本內容"
        kind = " src-special"
    elif re.match(r"^\d{4}-\d{2}-\d{2}\.html$", fname):
        kind = " src-old"
    cards.append(f'''    <a class="card{kind}" href="reports/{html.escape(fname)}">
      <div class="d">{html.escape(disp_date)}</div>
      <div class="w">{html.escape(label)}</div>
      <div class="go">查看日報 →</div>
    </a>''')

latest = files[0][0] if files else "—"
body_cards = "\n".join(cards) if cards else '<p style="color:#5B6675">目前沒有報告。</p>'

# 永遠置頂的「運作說明 OutputLogic」卡片：顯示運作說明最後一次更新的日期
import subprocess
def outputlogic_date():
    f = os.path.join(ROOT, "OutputLogic", "index.html")
    try:
        d = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%cs", "--", "OutputLogic/index.html"],
                           capture_output=True, text=True, timeout=10).stdout.strip()
        if d:
            return d.replace("-", "/")
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y/%m/%d") if os.path.exists(f) else "—"

pinned_card = f'''    <a class="card pin" href="OutputLogic/">
      <div class="picon">📘</div>
      <div class="d">運作說明</div>
      <div class="w">OutputLogic · 生成邏輯 {outputlogic_date()}<span class="pintag">📌 置頂</span></div>
      <div class="go">查看說明 →</div>
    </a>'''

out = f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>iGaming 市場日報</title>
<link rel="icon" type="image/png" sizes="32x32" href="icon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="icon-16.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>
  :root{{--bg:#F5F7FA;--card:#fff;--ink:#1A2230;--sub:#5B6675;--line:#E7EBF0;--accent:#1D9E75}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang TC","Noto Sans TC","Segoe UI",sans-serif;line-height:1.6;padding:40px 16px}}
  .wrap{{max-width:720px;margin:0 auto}}
  h1{{font-size:30px;font-weight:800;letter-spacing:-.5px}}
  .sub{{color:var(--sub);font-size:14px;margin:6px 0 26px}}
  .latest{{display:inline-block;background:#E1F5EE;color:#0F6E56;font-size:12px;font-weight:700;padding:4px 10px;border-radius:20px;margin-bottom:22px}}
  .list{{display:flex;flex-direction:column;gap:12px}}
  a.card{{display:flex;align-items:center;gap:14px;background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent);border-radius:12px;padding:16px 18px;text-decoration:none;color:inherit;transition:box-shadow .15s}}
  a.card:hover{{box-shadow:0 4px 14px rgba(0,0,0,.07)}}
  .card .d{{font-size:19px;font-weight:800;white-space:nowrap}}
  .card .w{{font-size:13px;color:var(--sub);flex:1}}
  .card .go{{font-size:13px;font-weight:700;color:var(--accent);white-space:nowrap}}
  .card.pin{{border-left-color:#0F6E56;background:#EEF7F3}}
  .card.pin .picon{{font-size:22px}}
  .card.pin .go{{color:#0F6E56}}
  .pintag{{display:inline-block;font-size:11px;font-weight:800;color:#0F6E56;background:#D9EFE6;padding:2px 8px;border-radius:20px;margin-left:8px}}
  .card.src-old{{background:#FFF3E6;border-left-color:#E8914A}}
  .card.src-old .go{{color:#B8612A}}
  .card.src-special{{background:#EAF2FF;border-left-color:#4F7FE0}}
  .card.src-special .go{{color:#2F5FC4}}
  .legend{{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;color:var(--sub);margin:-8px 0 18px}}
  .legend span{{display:inline-flex;align-items:center;gap:6px}}
  .legend i{{width:14px;height:14px;border-radius:4px;border:1px solid var(--line)}}
  .pager{{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:6px;margin-top:18px}}
  .pager button{{font:inherit;font-size:13px;min-width:36px;padding:6px 10px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;cursor:pointer}}
  .pager button[aria-current="page"]{{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}}
  .pager button:disabled{{opacity:.4;cursor:default}}
  .pager button:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
  .pageinfo{{font-size:12px;color:var(--sub);text-align:center;margin-top:8px}}
  .foot{{margin-top:30px;font-size:12px;color:var(--sub);text-align:center;line-height:1.7}}
  @media(max-width:520px){{.card .w{{display:none}}}}
</style>
</head>
<body>
<div class="wrap">
  <h1>🎰 iGaming 市場日報</h1>
  <div class="sub">每日 iGaming / 博弈產業新聞彙整 · Game Provider 新遊戲、非 Slot、主流動態、菲律賓、市場數據</div>
  <div class="latest">最新：{html.escape(latest)}</div>
  <div class="legend">
    <span><i style="background:#fff;border-left:4px solid #1D9E75"></i>15' v</span>
    <span><i style="background:#FFF3E6;border-left:4px solid #E8914A"></i>13' v</span>
    <span><i style="background:#EAF2FF;border-left:4px solid #4F7FE0"></i>特別版本內容</span>
  </div>
  <div class="list">
{pinned_card}
  </div>
  <div class="list" id="reports" style="margin-top:12px">
{body_cards}
  </div>
  <nav class="pager" id="pager" aria-label="日報分頁"></nav>
  <div class="pageinfo" id="pageinfo"></div>
  <div class="foot">
    自動由 daily-news-report 產出並發布 · 每則附原文連結供查證<br>
    © iGaming Daily
  </div>
</div>
<script>
(function(){{
  var PER = 20;
  var list = document.getElementById("reports");
  var cards = Array.prototype.slice.call(list.querySelectorAll("a.card"));
  var pager = document.getElementById("pager"), info = document.getElementById("pageinfo");
  var pages = Math.max(1, Math.ceil(cards.length / PER));
  if (pages <= 1) return;
  function btn(label, page, opts){{
    var b = document.createElement("button");
    b.type = "button"; b.textContent = label;
    if (opts && opts.current) b.setAttribute("aria-current", "page");
    if (opts && opts.disabled) b.disabled = true;
    b.addEventListener("click", function(){{ show(page, true); }});
    return b;
  }}
  function show(p, scroll){{
    cards.forEach(function(c, i){{ c.hidden = Math.floor(i / PER) !== p - 1; }});
    pager.innerHTML = "";
    pager.appendChild(btn("‹ 上一頁", p - 1, {{disabled: p === 1}}));
    for (var i = 1; i <= pages; i++) pager.appendChild(btn(String(i), i, {{current: i === p}}));
    pager.appendChild(btn("下一頁 ›", p + 1, {{disabled: p === pages}}));
    var a = (p - 1) * PER + 1, b = Math.min(p * PER, cards.length);
    info.textContent = "第 " + a + "–" + b + " 份，共 " + cards.length + " 份";
    if (scroll) list.scrollIntoView({{behavior: "smooth", block: "start"}});
  }}
  show(1, false);
}})();
</script>
</body>
</html>
'''

open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print(f"✓ index.html 已生成，共 {len(files)} 份報告，最新 {latest}")
