#!/usr/bin/env python3
"""每日輪掃批次產生器（daily rotating sweep）。

用途：解決「223 個來源平常沒被主動觸及」的問題。每天輸出一批（預設 8 個）
      應直接 firecrawl 查看的來源；批次由**日期**決定、無需任何狀態檔，
      半夜全新無記憶的 session 也能算出同一批。約 21 天把新聞型來源覆蓋一輪。

⚠️ 批次大小直接決定 Firecrawl 用量：每個來源 1 credit。
   size 8 → 8 credits/天、約 21 天一輪（現行，2026-09-20 定案為省額度）
   size 30 → 30 credits/天、約 6 天一輪（月額度會爆，不要用）

只輪掃「有每日新聞價值」的分類（見 INCLUDE_CATEGORIES）；
展會／論壇／Podcast／協會認證／已停用不進輪掃池（每日新聞產出低）。

與 Mac 舊版的差異：改讀 repo 內的 sources/sources.md，不再依賴 ~/.claude 路徑。

用法：
  python3 scripts/rotate_sources.py                    # 今天這一批
  python3 scripts/rotate_sources.py --size 12          # 改每批大小（同時改變覆蓋週期與 credit）
  python3 scripts/rotate_sources.py --date 2026-09-25  # 指定日期（驗證確定性用）
"""
import datetime
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_MD = os.path.join(ROOT, "sources", "sources.md")

# 只輪掃這幾個「有每日新聞價值」的分類（比對分類標題開頭）
INCLUDE_CATEGORIES = [
    "Provider 官網",
    "產品分析／評測",
    "產業媒體",
    "市場數據／分析公司",
    "監理機關／官方數據",
]
BATCH_SIZE = 8  # 每日輪掃批次大小（改這裡就改變覆蓋週期與 credit 用量）


def parse(md):
    """解析 sources.md 的分類表格 → [(category, name, url), ...]（檔案順序，穩定）。"""
    cur = None
    rows = []
    for line in md.splitlines():
        h = re.match(r'^##\s+(.+?)（\d+）\s*$', line)
        if h:
            cur = h.group(1).strip()
            continue
        if cur and line.lstrip().startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 2 and cells[0] not in ('名稱', '') and '---' not in cells[0]:
                m = re.search(r'https?://\S+', cells[1])
                if m:
                    rows.append((cur, cells[0], m.group(0)))
    return rows


def main():
    size = BATCH_SIZE
    day = datetime.date.today()
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == '--size' and i + 1 < len(args):
            size = int(args[i + 1])
        if a == '--date' and i + 1 < len(args):
            day = datetime.date.fromisoformat(args[i + 1])

    if not os.path.exists(SOURCES_MD):
        print(f"# 警告：找不到 {SOURCES_MD}，請先跑 scripts/sync_sources.py。本日略過輪掃。")
        return

    with open(SOURCES_MD, encoding='utf-8') as f:
        md = f.read()

    rows = [r for r in parse(md)
            if any(r[0].startswith(c) for c in INCLUDE_CATEGORIES)]
    n = len(rows)
    if n == 0:
        print("# 警告：輪掃池為 0（sources.md 解析失敗？），本日略過輪掃。")
        return

    nb = max(1, math.ceil(n / size))
    idx = day.toordinal() % nb
    batch = rows[idx * size:(idx + 1) * size]

    print(f"# 今日輪掃批次 {idx + 1}/{nb}（日期 {day.isoformat()}，"
          f"輪掃池 {n} 個新聞型來源，本批 {len(batch)} 個，約 {nb} 天覆蓋一輪）")
    print("# 用法：逐一 firecrawl summary（onlyMainContent:true），看『收集時間窗內』有無夠份量新聞；")
    print("#       有 → 納入候選、與搜尋結果去重、順手取 metadata['og:image']；沒有 → 跳過（多數會沒有，正常）。")
    for cat, name, url in batch:
        print(f"{name}\t{cat}\t{url}")


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        # 輸出被 head / more 之類截斷時不要噴 traceback
        try:
            sys.stdout.close()
        except Exception:
            pass
        os._exit(0)
