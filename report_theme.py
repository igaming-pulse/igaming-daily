#!/usr/bin/env python3
"""
日報樣式開關（2026-09-27）：色譜圖表風・方案 C（莫蘭迪色）⇄ 原樣式（classic）。

  python3 report_theme.py status              看目前開關與各日報狀態
  python3 report_theme.py apply               開關設為 spectrum-c，套用到所有「結構符合」的日報
  python3 report_theme.py rollback            開關設為 classic，從 reports/_classic/ 還原所有已套用的日報

口令（對 Claude Code 說）：
  「日報樣式回滾」→ 執行 rollback 並推上 main
  「日報樣式套用」→ 執行 apply 並推上 main

設計：
  - 套用前把原始檔備份到 reports/_classic/<檔名>（已存在就不覆蓋），套用後的檔案帶標記 <!-- theme:spectrum-c -->
  - build_index.py 每次重建首頁都會呼叫 auto()：開關是 spectrum-c 時，自動套用還沒套用的新日報
  - 只套用結構符合的日報（有 <header>、class="date"、class="grid"、class="card cN"）；
    日報 HTML 每天由 Claude 現寫、結構不固定，不符合的一律跳過、不動
"""
import os, re, sys, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(ROOT, "reports")
BACKUP = os.path.join(REPORTS, "_classic")
FLAG = os.path.join(ROOT, "report_theme.txt")
MARK = "<!-- theme:spectrum-c -->"
THEME_FROM = "2026-09-27"
# 舊機器（15' v）的 <date>.html 結構每天不同，硬套有破版風險 → 不套用，維持它原本的樣式（2026-09-28 使用者決定）
OURS_RX = re.compile(r"^\d{4}-\d{2}-\d{2}-(test|v\d+|special)\.html$")  # 只套用這天以後的日報；更早的保留原樣（使用者要求過去的頁面不改）
NAME_RX = re.compile(r"^\d{4}-\d{2}-\d{2}(-test|-v\d+|-special)?\.html$")

CSS = r'''
:root{--paper:#EEE8DC;--sheet:#F7F3EA;--ink:#1B1A18;--sub:#5F584D;--faint:#8C8373;--rule:#D3C9B7;--dark:#2A2621;--dark-ink:#EDE6D8;
      --s1:#C08A84;--s2:#C9976B;--s3:#CDB77A;--s4:#7D9C84;--s5:#7F97B5;--s6:#9B8AB5;--cat:var(--ink)}
*{box-sizing:border-box}
html{background:var(--paper)}
body{margin:0;background:var(--paper);background-image:radial-gradient(rgba(60,48,30,.035) 1px,transparent 1px);background-size:3px 3px;
     color:var(--ink);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.75}
.wrap{max-width:920px;margin:0 auto;padding:32px 20px 48px}
/* ---- 刊頭：左標題＋色階帶，右深色側欄（各區則數） ---- */
header.mast{display:grid;grid-template-columns:1fr 250px;border:1px solid var(--ink);background:var(--sheet);margin-bottom:26px}
.mast-main{padding:24px 26px 20px;display:flex;flex-direction:column;gap:10px}
.date{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;letter-spacing:.12em;color:var(--sub);font-weight:500}
h1{font-size:46px;line-height:1.05;font-weight:900;margin:0;letter-spacing:-.5px;font-variant-numeric:tabular-nums;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
h1 .wd{font-size:22px;font-weight:700;color:var(--sub);letter-spacing:0}
.brand{font-size:15px;font-weight:700;color:var(--ink);display:flex;align-items:center;gap:6px}
.badges{display:flex;flex-wrap:wrap;gap:6px}
.badge{font-size:12px;font-weight:700;padding:2px 9px;border:1px solid var(--ink);background:transparent!important;color:var(--ink)!important;border-radius:0}
.srcline{font-size:13px;color:var(--sub)}
.spectrum{display:flex;height:8px;margin-top:4px}.spectrum i{flex:1}
.mast-side{background:var(--dark);color:var(--dark-ink);padding:18px 18px;display:flex;flex-direction:column;gap:0}
.mast-side .cap{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#B9AF9C;padding-bottom:8px}
.grid,.stats,.stats-grid{display:flex;flex-direction:column;gap:0;margin:0}
.stat{display:flex;align-items:baseline;justify-content:space-between;gap:10px;background:transparent;border:none!important;border-top:1px solid rgba(237,230,216,.18)!important;border-radius:0;padding:9px 0}
.stat .n{font-family:"IBM Plex Mono",monospace;font-size:22px;font-weight:600;color:#fff!important;font-variant-numeric:tabular-nums;order:2}
.stat .l{font-size:13px;color:var(--dark-ink);order:1;display:flex;align-items:center;gap:8px}
.stat .l::before{content:"";width:9px;height:9px;background:var(--mk,#999)}
/* ---- 分類區塊 ---- */
section{margin-top:40px}
.sh{font-size:24px;font-weight:900;color:var(--ink)!important;border:none!important;border-bottom:2px solid var(--ink)!important;padding:0 0 10px!important;margin:0 0 16px;display:flex;align-items:center;gap:10px}
.sh::before{content:"";width:14px;height:14px;background:var(--cat);flex:none;order:-2}
.sh .em{font-size:1.1em}
.sec-title{font-size:24px;font-weight:900;color:var(--ink)!important;border:none!important;border-bottom:2px solid var(--ink)!important;padding:0 0 10px!important;margin:0 0 16px;display:flex;align-items:center;gap:10px;background:none!important}
.sec-title::before{content:"";width:14px;height:14px;background:var(--cat);flex:none;order:-2}
.sec-title h2{font-size:inherit;font-weight:900;margin:0;color:var(--ink)}
.sec-title .emo,.sec-title .emoji{font-size:1.1em}
.sec-title .cnt{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;color:var(--sheet)!important;background:var(--ink);padding:2px 9px;margin-left:auto}
.sh .cnt{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;color:var(--sheet)!important;background:var(--ink);padding:2px 9px;margin-left:auto}
section:has(.c1){--cat:var(--s4)} section:has(.c5){--cat:var(--s1)} section:has(.c2){--cat:var(--s5)}
section:has(.c3){--cat:var(--s2)} section:has(.c4){--cat:var(--s6)}
/* ---- 卡片 ---- */
.card{background:var(--sheet);border:1px solid var(--rule)!important;border-top:3px solid var(--cat)!important;border-radius:0;padding:20px 22px;margin-bottom:16px}
.card.c1{--cat:var(--s4)}.card.c5{--cat:var(--s1)}.card.c2{--cat:var(--s5)}.card.c3{--cat:var(--s2)}.card.c4{--cat:var(--s6)}
.no{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;color:var(--cat);letter-spacing:.1em}
h3{font-size:24px;font-weight:400;margin:4px 0 12px;line-height:1.4}
p{margin:0 0 12px;font-size:14.5px}
p b{font-weight:900}
.derive{font-size:13px;color:var(--ink);background:transparent;border:none;border-left:3px solid var(--cat);border-radius:0;padding:4px 0 4px 12px;margin-bottom:12px}
.derive b{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.08em;color:color-mix(in srgb,var(--cat) 70%,#000);margin-right:8px;font-weight:600}
.spec{background:color-mix(in srgb,var(--cat) 13%,var(--sheet))!important;border:none!important;border-left:4px solid var(--cat)!important;border-radius:0;padding:6px 14px;margin-bottom:12px;font-size:13px}
.spec .row{display:flex;gap:12px;padding:7px 0;border-bottom:1px solid color-mix(in srgb,var(--cat) 22%,transparent)!important}
.spec .row:last-child{border-bottom:none!important}
.spec .k{flex:0 0 86px;font-family:"IBM Plex Mono",monospace;font-size:11.5px;font-weight:600;letter-spacing:.04em;color:color-mix(in srgb,var(--cat) 70%,#000)!important;padding-top:1px}
.spec .v{color:var(--ink)}
.keyrow{display:flex;flex-wrap:wrap;gap:6px 18px;background:color-mix(in srgb,var(--cat) 13%,var(--sheet));color:var(--ink);border:none;border-radius:0;padding:10px 14px;margin-bottom:12px;font-size:12.5px}
.keyrow b{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.08em;color:color-mix(in srgb,var(--cat) 70%,#000)!important;margin-right:6px;font-weight:600}
.verify{font-size:12.5px;color:var(--sub);background:transparent;border:1px dashed var(--rule);border-radius:0;padding:8px 12px;margin-bottom:12px;line-height:1.65}
.tags{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--sub)}
.tags .lbl{font-weight:600;letter-spacing:.08em;color:var(--ink)}
a.src{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:500;color:var(--ink);text-decoration:none;background:transparent;border:1px solid var(--ink);border-radius:0;padding:1px 7px}
a.src:hover{background:var(--ink);color:var(--sheet)}
a:focus-visible{outline:2px solid var(--s5);outline-offset:2px}
.hero{width:100%;aspect-ratio:16/9;object-fit:cover;border:1px solid var(--ink);border-radius:0;margin-top:14px;display:block;background:var(--paper)}
.stats-line{max-width:920px;margin:36px auto 0;padding:14px 20px 0;border-top:2px solid var(--ink);text-align:left;font-size:13px;color:var(--sub);line-height:1.8}
.stats-line b{font-family:"IBM Plex Mono",monospace;color:var(--ink);font-weight:600;font-size:15px}
footer{text-align:left;max-width:920px;margin:10px auto 0;padding:0 20px;font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--faint);line-height:1.8}
@media(max-width:720px){header.mast{grid-template-columns:1fr}h1{font-size:28px}h3{font-size:21px}.sh{font-size:20px}.card{padding:16px}.spec .k{flex-basis:72px}}
'''

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap">')


def compatible(s):
    # v2（2026-09-28）：統計格改為選用；區塊標題 sh／sec-title 都可
    return all(k in s for k in ("<header>", 'class="date"')) and re.search(r'class="card c[1-5]"', s)


def restyle(s):
    s = re.sub(r"<style>.*?</style>", "<style>" + CSS + "</style>", s, count=1, flags=re.S)
    s = s.replace("</head>", FONTS + "</head>", 1)
    dm = re.search(r'<div class="date">\s*(\d{4}-\d{2}-\d{2})（(週.|星期.)）[^<]*</div>\s*<h1>(.*?)</h1>', s, re.S)
    if dm:
        wd = dm.group(2).replace("星期", "週")
        s = s.replace(dm.group(0), f'<div class="brand">{dm.group(3)}</div><h1>{dm.group(1)} <span class="wd">{wd}</span></h1>', 1)
    hm = re.search(r"<header>(.*?)</header>", s, re.S)
    gm = re.search(r'<div class="(?:grid|stats|stats-grid)">\s*(?:<div class="stat(?:\s[^"]*)?"[^>]*>.*?</div>\s*</div>\s*)+</div>', s, re.S)
    grid = gm.group(0) if gm else ""
    if gm:
        s = s.replace(grid, "", 1)
    MK = {"🎰": "var(--s4)", "🕹️": "var(--s1)", "🤝": "var(--s5)", "🇵🇭": "var(--s2)", "📊": "var(--s6)"}
    def mk(m):
        lab = m.group(0)
        col = next((v for k, v in MK.items() if k in lab), "#999")
        return re.sub(r'class="stat(?:\s[^"]*)?"', f'class="stat" style="--mk:{col}"', lab, count=1)
    grid = re.sub(r'<div class="stat(?:\s[^"]*)?"[^>]*>.*?</div>\s*</div>', mk, grid, flags=re.S)
    grid = re.sub(r'style="border-top-color:[^"]*"', "", grid)
    spectrum = ('<div class="spectrum" aria-hidden="true">' +
                "".join(f'<i style="background:var(--s{i})"></i>' for i in range(1, 7)) + "</div>")
    s = s.replace(hm.group(0), '<header class="mast"><div class="mast-main">' + hm.group(1) + spectrum + '</div>'
                  '<aside class="mast-side"><div class="cap">本日收錄</div>' + grid + '</aside></header>', 1)
    return s.replace("<head>", "<head>" + MARK, 1) if "<head>" in s else MARK + s


def flag():
    try:
        return open(FLAG, encoding="utf-8").read().strip() or "classic"
    except FileNotFoundError:
        return "classic"


def files():
    return sorted(f for f in os.listdir(REPORTS) if NAME_RX.match(f))


def apply_all(verbose=True):
    done, skipped = [], []
    os.makedirs(BACKUP, exist_ok=True)
    for f in files():
        if f[:10] < THEME_FROM or not OURS_RX.match(f):
            continue
        p = os.path.join(REPORTS, f)
        s = open(p, encoding="utf-8").read()
        if MARK in s:
            continue
        if not compatible(s):
            skipped.append(f)
            continue
        b = os.path.join(BACKUP, f)
        if not os.path.exists(b):
            shutil.copy2(p, b)
        open(p, "w", encoding="utf-8").write(restyle(s))
        done.append(f)
    if verbose:
        print(f"✓ 套用 {len(done)} 份：{', '.join(done) or '（無新的）'}")
        print(f"  結構不符合、跳過 {len(skipped)} 份")
    return done, skipped


def rollback():
    restored = []
    if os.path.isdir(BACKUP):
        for f in sorted(os.listdir(BACKUP)):
            if NAME_RX.match(f):
                shutil.copy2(os.path.join(BACKUP, f), os.path.join(REPORTS, f))
                restored.append(f)
    open(FLAG, "w", encoding="utf-8").write("classic\n")
    print(f"✓ 已回滾到原樣式，還原 {len(restored)} 份：{', '.join(restored) or '（無）'}；開關＝classic")


def refresh():
    """CSS 調整後重跑：已套用的檔案從 reports/_classic/ 原檔重新產生。"""
    done = []
    for f in files():
        b = os.path.join(BACKUP, f)
        p = os.path.join(REPORTS, f)
        if OURS_RX.match(f) and os.path.exists(b) and MARK in open(p, encoding="utf-8").read():
            open(p, "w", encoding="utf-8").write(restyle(open(b, encoding="utf-8").read()))
            done.append(f)
    print(f"✓ 重新產生 {len(done)} 份：{', '.join(done) or '（無）'}")


def unapply_old():
    """把已套用的舊機器日報還原成原樣（只在規則改為不套舊機器時用一次）。"""
    back = []
    for f in files():
        b = os.path.join(BACKUP, f)
        if not OURS_RX.match(f) and os.path.exists(b):
            shutil.copy2(b, os.path.join(REPORTS, f))
            os.remove(b)
            back.append(f)
    print(f"✓ 舊機器日報還原 {len(back)} 份：{', '.join(back) or '（無）'}")


def auto():
    """build_index.py 呼叫：開關是 spectrum-c 才套用新日報。"""
    if flag() == "spectrum-c":
        apply_all(verbose=False)


def status():
    print(f"開關：{flag()}")
    for f in files():
        s = open(os.path.join(REPORTS, f), encoding="utf-8").read()
        st = ("spectrum-c" if MARK in s else "早於套用起始日（不動）" if f[:10] < THEME_FROM
              else "舊機器日報（不套用）" if not OURS_RX.match(f)
              else ("可套用" if compatible(s) else "結構不符（跳過）"))
        print(f"  {f}：{st}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "apply":
        open(FLAG, "w", encoding="utf-8").write("spectrum-c\n")
        apply_all()
    elif cmd == "rollback":
        rollback()
    elif cmd == "refresh":
        refresh()
    elif cmd == "unapply-old":
        unapply_old()
    else:
        status()
