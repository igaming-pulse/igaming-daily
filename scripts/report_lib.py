#!/usr/bin/env python3
"""
v6.5 日報定稿共用模組（2026-09-28）：Markdown 解析、固定模板渲染、模糊比對。

- parse_md(text)       → dict（結構化日報；finalize_report.py 另存成 state/<DATE>-report.json）
- render_html(report)  → str（固定模板；結構與 report_theme.py 的 compatible() 相容，樣式開關／回滾照常運作）
- norm_title / same_item → 模糊比對（inventory.py 去重、finalize_report.py 查重都用這一套）

Markdown 格式以 SKILL.md「各區格式」為準；解析器也吃得下 v6.4 以前幾種寫法（「01」獨立一行、— 分隔 GP 等），
方便回測舊檔。
"""
import html
import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

CATS = {
    "cat1": {"emoji": "🎰", "h2": "Game Provider 新遊戲", "badge": "🎰 Slot", "stat": "🎰 Slot 新遊戲"},
    "cat2": {"emoji": "🕹️", "h2": "非 Slot 新內容", "badge": "🕹️ 非 Slot", "stat": "🕹️ 非 Slot 新內容"},
    "cat3": {"emoji": "🤝", "h2": "動態：主流 GP／平台", "badge": "🤝 主流", "stat": "🤝 主流動態"},
    "cat4": {"emoji": "🇵🇭", "h2": "動態：菲律賓 GP／平台", "badge": "🇵🇭 菲律賓", "stat": "🇵🇭 菲律賓"},
    "cat5": {"emoji": "📊", "h2": "市場數據 & 趨勢", "badge": "📊 市場數據", "stat": "📊 市場數據"},
}
EMOJI_CAT = [("🕹", "cat2"), ("🇵🇭", "cat4"), ("🤝", "cat3"), ("📊", "cat5"), ("🎰", "cat1")]
LABELS = ("📦", "🆕", "🔁", "📋")
SLOT_SPEC_KEYS = ["遊戲類型", "盤面", "消除/賠付", "最高倍率", "RTP", "波動", "目標市場", "關鍵特色"]
NONSLOT_SPEC_MIN = ["遊戲類型", "目標市場", "關鍵特色"]
WEEKDAY = "一二三四五六日"
VERSION = "v6.5（三層收集＋庫存＋定稿檢查）"

RX_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
RX_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
RX_NO_HEAD = re.compile(r"^###\s*(\d{1,2})\s*[.、．]?\s*(.*)$")
RX_NO_ALONE = re.compile(r"^(\d{1,2})\s*$")
RX_STATS = re.compile(r"查詢約\s*\**\s*(\d+)\s*\**\s*個網站.*?提取\s*\**\s*(\d+)\s*\**\s*個")
RX_FIELD = re.compile(r"^(衍生調整|參數|重點|查證|來源|圖片)\s*[:：]\s*(.*)$")


def section_cat(heading):
    if "內部" in heading or "不渲染" in heading:
        return "internal"
    for e, c in EMOJI_CAT:
        if e in heading:
            return c
    return None


def _new_item(no, title):
    return {"no": int(no), "label": "", "title": title.strip(), "body": [], "derive": "", "spec": [],
            "keyrow": [], "keyrow_raw": "", "verify": "", "sources": [], "date": "", "image": "", "image_raw": ""}


def _split_label(title):
    """標題開頭若帶 📦／🆕／🔁／📋 前綴，拆成 (label, title)。"""
    t = title.strip()
    if not t.startswith(LABELS):
        return "", t
    m = re.match(r"^((?:📦|🆕|🔁|📋)[^）)]*[）)])\s*(.*)$", t)
    if m and m.group(2):
        return m.group(1).strip(), m.group(2).strip()
    return "", t


def parse_md(text):
    rep = {"date": "", "sections": [], "stats": None, "internal": "", "header_counts": ""}
    lines = text.splitlines()
    m = RX_DATE.search(lines[0] if lines else "")
    rep["date"] = m.group(1) if m else ""
    sec = item = None
    field = None           # 目前在收的多行欄位（spec）
    pending_no = None      # 「01」獨立一行、下一行才是標題的舊寫法
    internal = []
    for raw in lines[1:]:
        line = raw.rstrip()
        s = line.strip()
        if sec == "internal":
            internal.append(line)
            continue
        if s.startswith("## "):
            c = section_cat(s)
            if c == "internal":
                sec = "internal"
                internal.append(line)
                continue
            sec = {"cat": c, "heading": s[3:].strip(), "items": []} if c else None
            if sec:
                rep["sections"].append(sec)
            item, field, pending_no = None, None, None
            continue
        st = RX_STATS.search(s)
        if st and "本日日報" in s:
            rep["stats"] = {"n1": int(st.group(1)), "n2": int(st.group(2))}
            item = None
            continue
        if s.startswith(("🎰 Slot", "Slot ")) and "・" in s and not sec:
            rep["header_counts"] = s
            continue
        if not sec or s == "---":
            if s == "---":
                field = None
            continue
        mh = RX_NO_HEAD.match(s)
        if mh:
            label, title = _split_label(mh.group(2))
            item = _new_item(mh.group(1), title)
            item["label"] = label
            sec["items"].append(item)
            field, pending_no = None, None
            continue
        if pending_no is not None and s:
            label, title = _split_label(s)
            item = _new_item(pending_no, title)
            item["label"] = label
            sec["items"].append(item)
            pending_no = None
            continue
        if RX_NO_ALONE.match(s) and (item is None or item["sources"] or item["body"]):
            pending_no = int(s)
            continue
        if item is None or not s:
            if not s and field == "spec" and item and item["spec"]:
                field = None
            continue
        if not item["body"] and not item["label"] and s.startswith(LABELS) and len(s) <= 40:
            item["label"] = s
            continue
        mf = RX_FIELD.match(s)
        if mf:
            k, v = mf.group(1), mf.group(2).strip()
            field = None
            if k == "衍生調整":
                item["derive"] = v
            elif k == "參數":
                field = "spec"
            elif k == "重點":
                item["keyrow_raw"] = v
                for part in re.split(r"\s*[｜|]\s*", v):
                    part = part.strip()
                    if not part:
                        continue
                    kv = re.match(r"^(類型|對象|影響)\s*[:：]?\s*(.*)$", part)
                    item["keyrow"].append([kv.group(1), kv.group(2).strip()] if kv else ["", part])
            elif k == "查證":
                item["verify"] = v
            elif k == "來源":
                item["sources"] = [[n.strip(), u.strip()] for n, u in RX_LINK.findall(v)]
                tail = RX_LINK.sub("", v)
                dm = RX_DATE.findall(tail)
                item["date"] = dm[-1] if dm else ""
            elif k == "圖片":
                item["image_raw"] = v
                um = re.search(r"https?://\S+", v)
                item["image"] = um.group(0).rstrip(")") if um else ""
            continue
        if field == "spec" and s.startswith(("-", "・", "•")):
            kv = re.match(r"^[-・•]\s*([^:：]+?)\s*[:：]\s*(.*)$", s)
            if kv:
                item["spec"].append([kv.group(1).strip(), kv.group(2).strip()])
            continue
        if s.startswith("（") and s.endswith("）") and not item["body"]:
            continue
        field = None
        item["body"].append(s)
    rep["internal"] = "\n".join(internal).strip()
    for sec in rep["sections"]:
        sec["count"] = len(sec["items"])
    return rep


# ─────────────────────────── 渲染（固定模板） ───────────────────────────

CSS = """  :root{
    --bg:#F5F7FA; --card:#ffffff; --line:#E7EBF0; --ink:#1A2230; --sub:#5B6675;
    --c1:#1D9E75; --c1bg:#E1F5EE; --c1txt:#0F6E56;
    --c2:#B31217; --c2bg:#FBE3E4; --c2txt:#8A1015;
    --c3:#378ADD; --c3bg:#E6F1FB; --c3txt:#185FA5;
    --c4:#D97706; --c4bg:#FBF0DD; --c4txt:#8A5206;
    --c5:#8B5CF6; --c5bg:#EEE9FC; --c5txt:#5B3FA6;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.7}
  .wrap{max-width:860px;margin:0 auto;padding:28px 16px 60px}
  header{text-align:center;margin-bottom:22px}
  header h1{font-size:26px;margin:6px 0 4px}
  header .date{color:var(--sub);font-size:14px}
  .badges{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:14px 0}
  .badge{font-size:12px;font-weight:700;padding:5px 12px;border-radius:999px}
  .b1{background:var(--c1bg);color:var(--c1txt)}
  .b2{background:var(--c2bg);color:var(--c2txt)}
  .b3{background:var(--c3bg);color:var(--c3txt)}
  .b4{background:var(--c4bg);color:var(--c4txt)}
  .b5{background:var(--c5bg);color:var(--c5txt)}
  .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:20px 0 32px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 10px;text-align:center}
  .stat .n{font-size:22px;font-weight:800}
  .stat .l{font-size:12px;color:var(--sub);margin-top:2px}
  .stat.s1 .n{color:var(--c1)} .stat.s2 .n{color:var(--c2)} .stat.s3 .n{color:var(--c3)} .stat.s4 .n{color:var(--c4)} .stat.s5 .n{color:var(--c5)}
  section{margin-bottom:36px}
  .sec-title{display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid var(--line)}
  .sec-title .emoji{font-size:1.5em}
  .sec-title h2{font-size:28px;margin:0}
  .sec-title .cnt{font-size:13px;color:var(--sub);font-weight:600}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:16px;position:relative;border-left:6px solid transparent}
  .card.c1{border-left-color:var(--c1)} .card.c2{border-left-color:var(--c2)} .card.c3{border-left-color:var(--c3)} .card.c4{border-left-color:var(--c4)} .card.c5{border-left-color:var(--c5)}
  .no{display:inline-block;font-size:12px;font-weight:800;color:#fff;background:var(--ink);border-radius:6px;padding:2px 8px;margin-bottom:8px}
  .c1 .no{background:var(--c1)} .c2 .no{background:var(--c2)} .c3 .no{background:var(--c3)} .c4 .no{background:var(--c4)} .c5 .no{background:var(--c5)}
  h3{font-size:17px;margin:4px 0 10px;line-height:1.5}
  p{font-size:14.5px;margin:0 0 10px;color:#2A3342}
  .derive{font-size:13px;color:#7a4d0b;background:#FBF3E4;border:1px solid #F0E2C6;border-radius:8px;padding:9px 12px;margin-bottom:10px}
  .derive b{color:#9a6209;margin-right:6px}
  .spec{background:#F2F6F4;border:1px solid #E1EAE6;border-radius:8px;padding:10px 12px;margin-bottom:10px;font-size:12.5px}
  .spec .row{display:flex;gap:10px;padding:3px 0;border-bottom:1px dashed #E1EAE6}
  .spec .row:last-child{border-bottom:none}
  .spec .k{flex:0 0 82px;font-weight:700;color:#0F6E56}
  .keyrow{display:flex;flex-wrap:wrap;gap:14px;background:#F4F8FC;border:1px solid #DCE8F4;border-radius:8px;padding:9px 12px;margin-bottom:10px;font-size:12.5px}
  .keyrow b{color:#185FA5;margin-right:5px}
  .c4 .keyrow b{color:#8A5206}
  .verify{font-size:12.5px;color:#334155;background:#F3F4F6;border:1px solid #E5E7EB;border-radius:8px;padding:8px 12px;margin-bottom:10px;line-height:1.6}
  .verify::before{content:"🔎 "}
  .tags{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:11px}
  a.src{font-weight:600;color:var(--sub);text-decoration:none}
  a.src:hover{text-decoration:underline}
  .hero{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px;margin-top:10px;display:block;background:#eee}
  .stats-line{max-width:860px;margin:26px auto 0;text-align:center;font-size:13.5px;color:#1A2230;line-height:1.8}
  .stats-line b{color:#B31217;font-weight:800}
  footer{text-align:center;margin-top:30px;color:var(--sub);font-size:12px}
  @media(max-width:600px){.sec-title h2{font-size:22px}}"""


def inline(s):
    """內文的最小 Markdown：[文字](網址) 與 **粗體**，其餘一律跳脫。"""
    out, last = [], 0
    for m in RX_LINK.finditer(s):
        out.append(html.escape(s[last:m.start()], quote=False))
        out.append(f'<a href="{html.escape(m.group(2))}" target="_blank" rel="noopener">{html.escape(m.group(1), quote=False)}</a>')
        last = m.end()
    out.append(html.escape(s[last:], quote=False))
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", "".join(out))


def _card(cat, it):
    e = lambda x: html.escape(x, quote=False)
    lab = it["label"]
    title = (lab + ("" if lab.endswith(("）", ")")) else " ") if lab else "") + it["title"]
    L = [f'  <div class="card {cat.replace("cat", "c")}">', f'    <div class="no">{it["no"]:02d}</div>',
         f"    <h3>{inline(title)}</h3>"]
    for para in it["body"]:
        L.append(f"    <p>{inline(para)}</p>")
    if cat in ("cat1", "cat2"):
        if it["derive"]:
            L.append(f'    <div class="derive"><b>衍生調整</b>{inline(it["derive"])}</div>')
        if it["spec"]:
            L.append('    <div class="spec">')
            for k, v in it["spec"]:
                L.append(f'      <div class="row"><span class="k">{e(k)}</span><span>{inline(v)}</span></div>')
            L.append("    </div>")
    elif it["keyrow"]:
        parts = [(f"<b>{e(k)}</b>" if k else "") + inline(v) for k, v in it["keyrow"]]
        L.append(f'    <div class="keyrow">{"　".join(parts)}</div>')
    if it["verify"]:
        L.append(f'    <div class="verify">{inline(it["verify"])}</div>')
    L.append('    <div class="tags">')
    L.append("      來源：")
    for n, u in it["sources"]:
        L.append(f'      <a class="src" href="{html.escape(u)}" target="_blank" rel="noopener">{e(n)} ↗</a>')
    if it["date"]:
        L.append(f"      · {it['date']}")
    L.append("    </div>")
    if cat in ("cat1", "cat2") and it["image"] and not it.get("image_dropped"):
        alt = html.escape(re.split(r"\s+[–—-]\s+", it["title"])[0])
        L.append(f'    <img class="hero" src="{html.escape(it["image"])}" alt="{alt}" loading="lazy" '
                 f"onerror=\"this.style.display='none'\">")
    L.append("  </div>")
    return "\n".join(L)


def render_html(rep):
    d = rep["date"]
    wd = WEEKDAY[date.fromisoformat(d).weekday()]
    secs = [s for s in rep["sections"] if s["items"]]
    order = {c: i for i, c in enumerate(CATS)}
    secs.sort(key=lambda s: order[s["cat"]])
    counts = {s["cat"]: len(s["items"]) for s in secs}
    badges = "\n".join(f'    <span class="badge b{c[-1]}">{CATS[c]["badge"]} {n}</span>' for c, n in counts.items())
    stats = "\n".join(f'  <div class="stat s{c[-1]}"><div class="n">{n}</div><div class="l">{CATS[c]["stat"]}</div></div>'
                      for c, n in counts.items())
    body = []
    for s in secs:
        c = s["cat"]
        body.append(f'<section>\n  <div class="sec-title"><span class="emoji">{CATS[c]["emoji"]}</span>'
                    f'<h2>{CATS[c]["h2"]}</h2><span class="cnt">共 {len(s["items"])} 則</span></div>\n')
        body.append("\n\n".join(_card(c, it) for it in s["items"]))
        body.append("\n</section>\n")
    st = rep.get("stats") or {"n1": 0, "n2": 0}
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="render_report.py {VERSION}">
<title>iGaming 市場日報 {d}</title>
<link rel="icon" type="image/png" sizes="32x32" href="../icon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="../icon-16.png">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<style>
{CSS}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="date">{d}（星期{wd}）・台北時間</div>
  <h1>🎰 iGaming 市場日報</h1>
  <div class="badges">
{badges}
  </div>
</header>

<div class="stats-grid">
{stats}
</div>

{"".join(body)}
<div class="stats-line">本日日報查詢約 <b>{st["n1"]}</b> 個網站，其中提取 <b>{st["n2"]}</b> 個資料來源並進行交叉比對</div>

<footer>
  iGaming 日報自動化 {VERSION}・每則皆附真實可點擊原文連結・多來源交叉查證<br>
  產出時間：{d}（台北時間）
</footer>
</div>
</body>
</html>
"""


# ─────────────────────────── 模糊比對 ───────────────────────────

_NOISE = re.compile(r"\b(slot|slots|the|game|new)\b")


def norm_title(s):
    """統一大小寫、全半形、各種撇號與商標符號，去掉「– 廠商」尾巴與 slot 等雜字。"""
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.split(r"\s+[–—]\s+|\s+-\s+", s)[0]
    s = re.sub(r"[™®©]", "", s)
    s = re.sub(r"[《》「」『』\"'`´’‘“”]", "", s)
    s = _NOISE.sub(" ", s)
    return re.sub(r"[^0-9a-z一-鿿]+", "", s)


def norm_gp(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"\b(gaming|games|studios?|entertainment|interactive|ltd|limited|group)\b", " ", s)
    return re.sub(r"[^0-9a-z一-鿿]+", "", s)


GP_ALIAS = {"lw": "lightwonder", "sg": "lightwonder", "scientific": "lightwonder", "pp": "pragmaticplay",
            "pg": "pgsoft", "pocketgames": "pgsoft", "btg": "bigtime", "nlc": "nolimitcity",
            "internationalgametechnology": "igt", "aristocratleisure": "aristocrat"}


def _acronym(s):
    words = re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", s or "").lower())
    return "".join(w[0] for w in words if w not in ("and", "of"))


def gp_same(a, b):
    ga, gb = norm_gp(a), norm_gp(b)
    if not ga or not gb:
        return True
    ga, gb = GP_ALIAS.get(ga, ga), GP_ALIAS.get(gb, gb)
    if ga in gb or gb in ga or ratio(ga, gb) >= 0.8:
        return True
    return _acronym(a) == gb or _acronym(b) == ga


def ratio(a, b):
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def same_item(a_title, a_gp, b_title, b_gp, threshold=0.9):
    """同一款遊戲／同一則新聞？標題正規化後相似度 ≥ threshold，且 GP 不衝突（任一方沒填 GP 視為不衝突）。"""
    ta, tb = norm_title(a_title), norm_title(b_title)
    if not ta or not tb:
        return False
    # 續作只差一個數字（Money Train 4／5、Thor's Rage／Thor's Rage 2、Big Bass Vegas／1000）→ 不同款
    if re.findall(r"\d+", ta) != re.findall(r"\d+", tb):
        return False
    return gp_same(a_gp, b_gp) and (ta == tb or ratio(ta, tb) >= threshold)
