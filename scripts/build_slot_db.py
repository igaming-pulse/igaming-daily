#!/usr/bin/env python3
"""
Slot 新作資料庫頁（2026-10-11）：把所有日報與特別版收錄過的 Slot 整理成一個可搜尋、可篩選的網頁。

來源：state/*-igaming-report.md（日報、重跑版、特別版的原稿；只取 🎰 cat1 區）
輸出：slots/index.html（自帶資料、不連外部 API；發布時由 publish_test_to_main.sh 一起複製到網站 /slots/）
同一款出現多次（預告→上線、日報→特別版）只留一筆：取第一次出現的日期，連結到最後一次（資料最完整）的那份日報。

用法：python3 scripts/build_slot_db.py
"""
import glob
import html
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_lib as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "slots", "index.html")

# 品牌分級（同 SKILL.md「B 品牌權重」；只用來標示與篩選「大廠」）
BRAND = {6: ["acewin", "omiplay", "yellowbat", "atg", "yggdrasil", "jili", "tada"],
         4: ["pg soft", "pragmatic", "nolimit", "play'n go", "playn go", "red tiger", "aristocrat", "igt", "light & wonder", "light and wonder"],
         3: ["cp game", "peter & sons", "netent", "hacksaw", "fa chai", "evolution", "playtech", "betsoft", "spinomenal",
             "relax", "push gaming", "bgaming", "wazdan", "quickspin"]}


def brand_b(gp):
    g = (gp or "").lower()
    for b, names in BRAND.items():
        if any(n in g for n in names):
            return b
    return 1


def site_file(md_path):
    """原稿 → 網站上的日報頁：公司帳號日報在網站是 -test；重跑版、特別版沿用原名。"""
    base = os.path.basename(md_path).replace("-igaming-report.md", "")
    return f"{base}-test.html" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", base) else f"{base}.html"


def gp_lookup():
    """舊格式日報（標題沒寫廠商）用：從庫存的已出現紀錄、各日 picks 找廠商名稱。"""
    names = {}
    try:
        for h in json.load(open(os.path.join(ROOT, "state", "inventory.json"), encoding="utf-8")).get("history", []):
            if h.get("gp"):
                names.setdefault(R.norm_title(h.get("title", "")), h["gp"])
    except (OSError, ValueError):
        pass
    for f in glob.glob(os.path.join(ROOT, "state", "inventory-picks-*.json")):
        try:
            p = json.load(open(f, encoding="utf-8"))
        except ValueError:
            continue
        for x in p.get("shown", []) + p.get("stock", []):
            if x.get("gp"):
                names.setdefault(R.norm_title(x.get("title", "")), x["gp"])
    return names


def collect():
    rows = []
    known = gp_lookup()
    for md in sorted(glob.glob(os.path.join(ROOT, "state", "*-igaming-report.md"))):
        rep = R.parse_md(open(md, encoding="utf-8").read())
        for sec in rep["sections"]:
            if sec["cat"] != "cat1":
                continue
            for it in sec["items"]:
                parts = re.split(r"\s+[–—]\s+", it["title"], maxsplit=1)
                name = re.sub(r"^[⭐\s]+", "", parts[0]).strip()
                gp = parts[1].strip() if len(parts) > 1 else ""
                m = re.search(r"《([^》]+)》", it["title"])
                if not gp and m:                      # 舊寫法：「GP 推出…《遊戲名》…」
                    gp = it["title"].split("推出")[0].strip() if "推出" in it["title"] else ""
                    name = m.group(1)
                if not gp:
                    gp = known.get(R.norm_title(name), "")
                if not gp and it["body"]:
                    m2 = re.match(r"^([A-Z][\w'&.\- ]{1,40}?)\s*(?:推出|為|旗下|宣布|發表|攜手)", it["body"][0])
                    gp = m2.group(1).strip() if m2 else ""
                spec = {k: v for k, v in it["spec"]}
                rows.append({
                    "name": name, "gp": gp, "b": brand_b(gp), "report": rep["date"], "date": it["date"] or rep["date"],
                    "label": it["label"], "type": spec.get("遊戲類型", ""), "board": spec.get("盤面", ""),
                    "pays": spec.get("消除/賠付", ""), "maxwin": spec.get("最高倍率", ""), "rtp": spec.get("RTP", ""),
                    "vol": spec.get("波動", ""), "market": spec.get("目標市場", ""), "feat": spec.get("關鍵特色", ""),
                    "summary": (it["body"][0] if it["body"] else "")[:220],
                    "src": [[n, u] for n, u in it["sources"]][:4], "img": it["image"],
                    "page": site_file(md), "special": bool(rep.get("edition")),
                })
    merged = []
    for r in sorted(rows, key=lambda x: (x["report"], x["page"])):
        hit = next((m for m in merged if R.same_item(m["name"], m["gp"], r["name"], r["gp"])), None)
        if hit:
            hit["seen"] += 1
            first = hit["report"]
            hit.update({k: v for k, v in r.items() if v and k not in ("report",)})   # 新的資料較完整
            hit["report"] = first
            hit["last"] = r["report"]
        else:
            merged.append({**r, "seen": 1, "last": r["report"]})
    merged.sort(key=lambda x: (x["report"], x["b"]), reverse=True)
    return merged


PAGE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Slot 新作資料庫 · iGaming 市場日報</title>
<link rel="icon" type="image/png" sizes="32x32" href="../icon-32.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  :root{--paper:#EEE8DC;--sheet:#F7F3EA;--ink:#1B1A18;--sub:#5F584D;--rule:#D3C9B7;--dark:#2A2621;
        --s1:#C08A84;--s2:#C9976B;--s3:#CDB77A;--s4:#7D9C84;--s5:#7F97B5;--s6:#9B8AB5}
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Sans TC","PingFang TC",sans-serif;line-height:1.65}
  .wrap{max-width:1100px;margin:0 auto;padding:28px 16px 60px}
  a{color:inherit}
  .back{font-size:13px;color:var(--sub);text-decoration:none}
  .mast{display:grid;grid-template-columns:1fr 260px;border:1px solid var(--ink);background:var(--sheet);margin:12px 0 22px}
  .mast-main{padding:22px 24px}
  .eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.12em;color:var(--sub);text-transform:uppercase}
  h1{font-size:34px;font-weight:900;margin:6px 0 6px;text-wrap:balance}
  .lede{color:var(--sub);font-size:14px;margin:0}
  .spectrum{display:flex;height:6px;margin-top:16px}.spectrum i{flex:1}
  .mast-side{background:var(--dark);color:#F7F3EA;padding:18px 20px;display:grid;gap:10px;align-content:start}
  .mast-side div{display:flex;justify-content:space-between;border-bottom:1px solid #4a443c;padding-bottom:6px;font-size:13px}
  .mast-side b{font-family:"IBM Plex Mono",monospace;font-size:18px}
  .tools{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
  .tools input[type=search],.tools select{font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--rule);background:#fff;border-radius:6px}
  .tools input[type=search]{flex:1 1 260px;min-width:0}
  .tools label{font-size:13px;color:var(--sub);display:flex;gap:6px;align-items:center;white-space:nowrap}
  .tools input[type=checkbox]{width:16px;height:16px;margin:0;accent-color:var(--s2)}
  .count{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--sub);margin-left:auto}
  .list{display:grid;gap:12px}
  .row{display:grid;grid-template-columns:132px 1fr;gap:16px;background:var(--sheet);border:1px solid var(--rule);border-left:5px solid var(--s4);padding:14px 16px}
  .row.big{border-left-color:var(--s2)}
  .row img{width:132px;aspect-ratio:16/10;object-fit:cover;background:#ddd;display:block}
  .row .noimg{width:132px;aspect-ratio:16/10;background:repeating-linear-gradient(45deg,#e6dfd2,#e6dfd2 6px,#ece6db 6px,#ece6db 12px)}
  .top{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline}
  .top h2{font-size:18px;font-weight:700;margin:0}
  .gp{font-size:13px;color:var(--sub)}
  .tag{font-family:"IBM Plex Mono",monospace;font-size:11px;padding:1px 6px;border:1px solid var(--rule);color:var(--sub)}
  .tag.b{border-color:var(--s2);color:#8a5a2b}
  .specs{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;margin:6px 0 4px}
  .specs span b{font-weight:600;color:var(--sub);margin-right:4px}
  .sum{font-size:13px;color:#3a362f;margin:4px 0}
  .links{font-size:12px;color:var(--sub);display:flex;flex-wrap:wrap;gap:4px 10px}
  .links a{text-decoration:none;border-bottom:1px solid var(--rule)}
  .empty{padding:30px;text-align:center;color:var(--sub)}
  @media(max-width:720px){.mast{grid-template-columns:1fr}.row{grid-template-columns:1fr}.row img,.row .noimg{width:100%}h1{font-size:28px}}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../">← 回日報列表</a>
  <header class="mast">
    <div class="mast-main">
      <div class="eyebrow">Slot Database · 13' v</div>
      <h1>Slot 新作資料庫</h1>
      <p class="lede">日報與特別版收錄過的每一款老虎機新作，含盤面、倍率、RTP、機制與原文連結。每晚日報跑完自動更新。</p>
      <div class="spectrum"><i style="background:var(--s1)"></i><i style="background:var(--s2)"></i><i style="background:var(--s3)"></i><i style="background:var(--s4)"></i><i style="background:var(--s5)"></i><i style="background:var(--s6)"></i></div>
    </div>
    <aside class="mast-side">
      <div><span>收錄款數</span><b id="n-all"></b></div>
      <div><span>大廠款數</span><b id="n-big"></b></div>
      <div><span>遊戲商數</span><b id="n-gp"></b></div>
      <div><span>資料更新</span><b>__UPDATED__</b></div>
    </aside>
  </header>
  <div class="tools">
    <input id="q" type="search" placeholder="搜尋遊戲名、廠商、機制（例：Hold &amp; Win、Megaways、Pragmatic）" aria-label="搜尋">
    <select id="gp" aria-label="遊戲商"><option value="">全部遊戲商</option></select>
    <select id="sort" aria-label="排序"><option value="date">最新收錄在前</option><option value="b">大廠在前</option><option value="name">遊戲名 A→Z</option></select>
    <label><input id="big" type="checkbox"> 只看大廠</label>
    <span class="count" id="count"></span>
  </div>
  <div class="list" id="list"></div>
</div>
<script>
const DATA = __DATA__;
const $ = id => document.getElementById(id);
const esc = s => String(s || "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const gps = [...new Set(DATA.map(d => d.gp).filter(Boolean))].sort((a, b) => a.localeCompare(b));
$("n-all").textContent = DATA.length; $("n-big").textContent = DATA.filter(d => d.b >= 3).length; $("n-gp").textContent = gps.length;
gps.forEach(g => { const o = document.createElement("option"); o.value = o.textContent = g; $("gp").appendChild(o); });
const md = s => s ? `${+s.slice(5,7)}/${+s.slice(8,10)}` : "";
function spec(k, v) { return v && !/^(未公布|沒有|-|查無資料)$/.test(v) ? `<span><b>${k}</b>${esc(v)}</span>` : ""; }
function render() {
  const q = $("q").value.trim().toLowerCase(), g = $("gp").value, big = $("big").checked, s = $("sort").value;
  let rows = DATA.filter(d => (!g || d.gp === g) && (!big || d.b >= 3) &&
    (!q || [d.name, d.gp, d.pays, d.feat, d.type, d.market, d.summary].join(" ").toLowerCase().includes(q)));
  rows.sort(s === "b" ? (a, b) => b.b - a.b || b.report.localeCompare(a.report)
          : s === "name" ? (a, b) => a.name.localeCompare(b.name) : (a, b) => b.report.localeCompare(a.report) || b.b - a.b);
  $("count").textContent = `顯示 ${rows.length} / ${DATA.length} 款`;
  $("list").innerHTML = rows.length ? rows.map(d => `
    <article class="row ${d.b >= 3 ? "big" : ""}">
      ${d.img ? `<img src="${esc(d.img)}" alt="${esc(d.name)}" loading="lazy" onerror="this.outerHTML='<div class=noimg></div>'">` : `<div class="noimg"></div>`}
      <div>
        <div class="top"><h2>${esc(d.name)}</h2><span class="gp">${esc(d.gp)}</span>
          ${d.b >= 3 ? `<span class="tag b">大廠 B${d.b}</span>` : ""}
          <span class="tag">${md(d.report)} 收錄</span>${d.special ? `<span class="tag">特別版</span>` : ""}${d.seen > 1 ? `<span class="tag">出現 ${d.seen} 次</span>` : ""}</div>
        <div class="specs">${spec("類型", d.type)}${spec("盤面", d.board)}${spec("賠付", d.pays)}${spec("最高倍率", d.maxwin)}${spec("RTP", d.rtp)}${spec("波動", d.vol)}${spec("市場", d.market)}</div>
        ${d.feat ? `<div class="sum"><b>特色：</b>${esc(d.feat)}</div>` : ""}
        <div class="links"><a href="../reports/${esc(d.page)}">看日報卡片 ↗</a>${(d.src || []).map(([n, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(n)} ↗</a>`).join("")}</div>
      </div>
    </article>`).join("") : `<div class="empty">沒有符合條件的遊戲</div>`;
}
["q", "gp", "sort", "big"].forEach(id => $(id).addEventListener("input", render));
render();
</script>
</body>
</html>
"""


def main():
    rows = collect()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__DATA__", data).replace("__UPDATED__", date.today().strftime("%m/%d")))
    print(f"✓ Slot 資料庫：{len(rows)} 款（大廠 {sum(1 for r in rows if r['b'] >= 3)}、遊戲商 {len({r['gp'] for r in rows if r['gp']})}）"
          f" → {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
