#!/usr/bin/env python3
"""
來源清單同步：xlsx（唯一真相）→ sources.md（skill 讀取）

與 Mac 舊版的差異：
  - 全部改成 repo 相對路徑，不再依賴 ~/Desktop
  - 砍掉 AUTO-HEAL 反向重建（進 git 後版控就是備份）
  - 印出實際筆數與分類數，供其他腳本與 skill 動態引用，不再寫死數字

用法：python3 scripts/sync_sources.py
"""
import os
import sys
import collections

try:
    import openpyxl
except ImportError:
    sys.exit("✗ 需要 openpyxl：pip3 install openpyxl --break-system-packages")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, "sources", "igaming-daily-report-sources-v2.xlsx")
OUT = os.path.join(ROOT, "sources", "sources.md")

ORDER = [
    "Provider 官網", "產品分析／評測", "產業媒體", "產業協會／技術認證機構",
    "市場數據／分析公司", "監理機關／官方數據", "展會", "論壇／社群",
    "Podcast／影音", "已停用",
]


def read_xlsx():
    if not os.path.exists(XLSX):
        sys.exit(f"✗ 找不到來源主檔：{XLSX}\n  主檔必須在 repo 內，請確認有 commit 進來。")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb.active
    rows = [r for r in ws.iter_rows(values_only=True)][1:]
    out = []
    for r in rows:
        if not r or not r[1]:
            continue
        cat = str(r[1]).strip()
        name = str(r[2] or "").strip()
        url = str(r[3] or "").strip()
        note = str(r[4] or "").strip()
        # 已停用的項目可能沒有有效 URL（例如「（網站已停止營運）」），仍要保留在清單裡
        if not url:
            url = "（無有效網址）"
        out.append((cat, name, url, note))
    return out


def write_md(records):
    groups = collections.OrderedDict((c, []) for c in ORDER)
    for cat, name, url, note in records:
        groups.setdefault(cat, []).append((name, url, note))

    lines = [
        f"# iGaming Daily Report — 資訊來源清單（共 {len(records)} 個來源）",
        "",
        "> 核心關注：Game Provider 產品動向、玩法設計、營運調整；盤口平台動態；市場數據與趨勢。",
        "> ⚠️ 本檔由 `sources/igaming-daily-report-sources-v2.xlsx` 自動產生。",
        "> **勿手動編輯本檔** —— 要改來源請改 xlsx，然後跑 `python3 scripts/sync_sources.py`。",
        "> 抓取時依當日題材跨分類取材；「已停用」分類不要抓。",
        "",
    ]
    for cat, items in groups.items():
        if not items:
            continue
        lines += [
            "---",
            "",
            f"## {cat}（{len(items)}）",
            "",
            "| 名稱 | URL | 備註 |",
            "|------|-----|------|",
        ]
        for name, url, note in items:
            safe = note.replace("\n", " ").replace("|", "／")
            lines.append(f"| {name} | {url} | {safe} |")
        lines.append("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    records = read_xlsx()
    write_md(records)
    counts = collections.Counter(c for c, _, _, _ in records)
    active = sum(v for k, v in counts.items() if k != "已停用")

    print(f"✓ sources.md 已同步：{len(records)} 個來源，{len(counts)} 個分類")
    for cat in ORDER:
        if counts.get(cat):
            print(f"   {counts[cat]:>4}  {cat}")
    for cat in counts:
        if cat not in ORDER:
            print(f"   {counts[cat]:>4}  {cat}  ⚠️ 未知分類，請確認 xlsx")
    print(f"   ---- 可抓取（扣除已停用）：{active}")


if __name__ == "__main__":
    main()
