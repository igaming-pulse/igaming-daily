#!/usr/bin/env python3
"""
首頁樣式開關（2026-09-27）：V1 清單刊頭（色譜圖表風・莫蘭迪色）⇄ 原樣式（classic）。

  python3 home_theme.py status     看目前開關
  python3 home_theme.py apply      開關設為 v1，重建首頁
  python3 home_theme.py rollback   開關設為 classic，重建首頁（回到原本的首頁樣式）

口令（對 Claude Code 說）：
  「首頁樣式回滾」→ rollback 並推上 main
  「首頁樣式套用」→ apply 並推上 main

設計：build_index.py 先照原樣產生首頁 HTML，最後呼叫 transform()；開關是 v1 才轉成 V1 樣式。
首頁每次都重新產生，所以回滾不需要備份檔。
"""
import os, re, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
FLAG = os.path.join(ROOT, "home_theme.txt")

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap">'
CSS = r'''
:root{--paper:#EEE8DC;--sheet:#F7F3EA;--ink:#1B1A18;--sub:#5F584D;--faint:#8C8373;--rule:#D3C9B7;--dark:#2A2621;--dark-ink:#EDE6D8;
      --s1:#C08A84;--s2:#C9976B;--s3:#CDB77A;--s4:#7D9C84;--s5:#7F97B5;--s6:#9B8AB5;
      --v13:#7D9C84;--v15:#C9976B;--vsp:#7F97B5;--src:var(--v13)}
*{box-sizing:border-box;margin:0;padding:0}
html{background:var(--paper)}
body{background:var(--paper);background-image:radial-gradient(rgba(60,48,30,.035) 1px,transparent 1px);background-size:3px 3px;color:var(--ink);font-family:"Noto Sans TC","PingFang TC",sans-serif;line-height:1.6;padding:32px 20px 56px}
.wrap{max-width:760px;margin:0 auto}
a{color:inherit}
a:focus-visible,button:focus-visible{outline:2px solid var(--s5);outline-offset:2px}
header.mast{display:grid;grid-template-columns:1fr 260px;border:1px solid var(--ink);background:var(--sheet);margin-bottom:26px}
.mast-main{padding:24px 26px 20px;display:flex;flex-direction:column;gap:10px}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--sub)}
h1{font-size:40px;line-height:1.1;font-weight:900;letter-spacing:-.4px}
.sub{color:var(--sub);font-size:13.5px;max-width:60ch}
.spectrum{display:flex;height:8px;margin-top:4px}.spectrum i{flex:1}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12.5px;color:var(--sub)}
.legend span{display:inline-flex;align-items:center;gap:7px}
.legend i{width:12px;height:12px;display:inline-block}
.mast-side{background:var(--dark);color:var(--dark-ink);padding:18px;font-family:"IBM Plex Mono",monospace;font-size:12px;display:flex;flex-direction:column}
.mast-side .cap{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#B9AF9C;padding-bottom:8px}
.mast-side .row{display:flex;justify-content:space-between;align-items:baseline;border-top:1px solid rgba(237,230,216,.18);padding:8px 0}
.mast-side .row b{font-size:18px;font-weight:600;color:#fff;font-variant-numeric:tabular-nums}
.mast-side .row span{display:flex;align-items:center;gap:8px;font-family:"Noto Sans TC",sans-serif;font-size:13px}
.mast-side .row span i{width:9px;height:9px;display:inline-block}
a.card{text-decoration:none;color:inherit}
a.card[hidden]{display:none}
a.card.src-old{--src:var(--v15)} a.card.src-special{--src:var(--vsp)}
.pintag{font-family:"IBM Plex Mono",monospace;font-size:10.5px;font-weight:600;letter-spacing:.06em;margin-left:8px;padding:1px 7px;border:1px solid currentColor}
.pager{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin-top:22px}
.pager button{font-family:"IBM Plex Mono",monospace;font-size:12.5px;min-width:38px;padding:6px 10px;border:1px solid var(--ink);background:var(--sheet);color:var(--ink);cursor:pointer;border-radius:0}
.pager button[aria-current="page"]{background:var(--ink);color:var(--sheet);font-weight:600}
.pager button:disabled{opacity:.35;cursor:default}
.pageinfo{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--sub);text-align:center;margin-top:8px}
.foot{margin-top:34px;padding-top:14px;border-top:2px solid var(--ink);font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--faint);line-height:1.8}
@media(max-width:720px){header.mast{grid-template-columns:1fr}h1{font-size:30px}}

.list{display:flex;flex-direction:column;border-top:2px solid var(--ink)}
#reports{margin-top:0!important}
a.card{display:grid;grid-template-columns:12px 150px 1fr auto;align-items:center;gap:16px;padding:14px 6px;border-bottom:1px solid var(--rule);background:transparent}
a.card::before{content:"";width:12px;height:12px;background:var(--src)}
a.card:hover{background:var(--sheet)}
.card .d{font-family:"IBM Plex Mono",monospace;font-size:17px;font-weight:600;font-variant-numeric:tabular-nums}
.card .w{font-size:13.5px;color:var(--sub)}
.card .go{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;color:color-mix(in srgb,var(--src) 70%,#000)}
a.card.pin{grid-template-columns:auto auto 1fr auto;background:var(--dark);color:var(--dark-ink);border:none;padding:16px 18px;margin-bottom:14px}
a.card.pin::before{display:none}
.card.pin .picon{font-size:20px}
.card.pin .d{font-family:"Noto Sans TC",sans-serif;font-size:17px;font-weight:900;color:#fff;display:inline}
.card.pin .w{color:#CFC6B4;display:inline;margin-left:10px}
.card.pin .go{color:#fff}
.card.pin .pintag{color:#E8DFC9}
.list:first-of-type{border-top:none}
@media(max-width:560px){a.card{grid-template-columns:12px 1fr auto}.card .w{grid-column:2/4;grid-row:2}}
'''


def flag():
    try:
        return open(FLAG, encoding="utf-8").read().strip() or "classic"
    except FileNotFoundError:
        return "classic"


def to_v1(s):
    cards = re.findall(r'<a class="card([^"]*)" href="reports/', s)
    n13 = sum(1 for c in cards if c.strip() == "")
    n15 = sum(1 for c in cards if "src-old" in c)
    nsp = sum(1 for c in cards if "src-special" in c)
    m = re.search(r"最新：([\d-]+)", s)
    latest = m.group(1) if m else "—"
    s = re.sub(r"<style>.*?</style>", "<style>" + CSS + "</style>", s, count=1, flags=re.S)
    s = s.replace("</head>", FONTS + "</head>", 1)
    legend = ('<div class="legend"><span><i style="background:var(--v13)"></i>13\' v</span>'
              '<span><i style="background:var(--v15)"></i>15\' v</span><span><i style="background:var(--vsp)"></i>特別版本內容</span></div>')
    spectrum = '<div class="spectrum" aria-hidden="true">' + "".join(f'<i style="background:var(--s{i})"></i>' for i in range(1, 7)) + "</div>"
    mast = f'''  <header class="mast">
    <div class="mast-main">
      <div class="eyebrow">iGaming Pulse · Daily Market Report</div>
      <h1>iGaming 市場日報</h1>
      <div class="sub">每日 iGaming／博弈產業新聞彙整：Game Provider 新遊戲、非 Slot、主流動態、菲律賓、市場數據。</div>
      {legend}
      {spectrum}
    </div>
    <aside class="mast-side">
      <div class="cap">日報存檔</div>
      <div class="row"><span>最新一期</span><b>{latest[5:]}</b></div>
      <div class="row"><span>全部</span><b>{len(cards)}</b></div>
      <div class="row"><span><i style="background:var(--v13)"></i>13\' v</span><b>{n13}</b></div>
      <div class="row"><span><i style="background:var(--v15)"></i>15\' v</span><b>{n15}</b></div>
      <div class="row"><span><i style="background:var(--vsp)"></i>特別版</span><b>{nsp}</b></div>
    </aside>
  </header>
'''
    hm = re.search(r'  <h1>.*?(?=  <div class="list">)', s, re.S)
    if hm:
        s = s.replace(hm.group(0), mast, 1)
    return s.replace("<head>", "<head><!-- home-theme:v1 -->", 1)


def transform(s):
    """build_index.py 呼叫：開關是 v1 才轉換。"""
    return to_v1(s) if flag() == "v1" else s


def rebuild():
    subprocess.run([sys.executable, os.path.join(ROOT, "build_index.py")], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "apply":
        open(FLAG, "w", encoding="utf-8").write("v1\n"); rebuild(); print("✓ 首頁樣式＝V1 清單刊頭")
    elif cmd == "rollback":
        open(FLAG, "w", encoding="utf-8").write("classic\n"); rebuild(); print("✓ 首頁樣式已回滾為原樣式（classic）")
    else:
        print(f"首頁樣式開關：{flag()}")
