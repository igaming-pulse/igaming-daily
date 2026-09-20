# 🎰 iGaming 市場日報

每日 iGaming／博弈產業新聞彙整，分五大分類：Game Provider 新遊戲（Slot）、非 Slot 新內容、主流動態、菲律賓動態、市場數據 & 趨勢。每則附真實可點擊原文連結、經多來源交叉查證。

- **線上瀏覽**：https://igaming-pulse.github.io/igaming-daily/
- **運作說明**：https://igaming-pulse.github.io/igaming-daily/OutputLogic/

---

## 每天怎麼跑

```
02:25 台北  pmset 自動喚醒機器
02:30 台北  launchd → run_daily.sh → Claude CLI → 收集、查證、寫稿、渲染 → commit + push
            └─ push 觸發 Actions      → 寄 Email
06:30 台北  GitHub Actions cron       → 發 Telegram（含「未產出」守門員）

漏跑時 launchd 會在下次開機／喚醒自動補跑一次。
```

---

## repo 結構

```
skills/SKILL.md          收集／查證／渲染的完整規則 —— 唯一真相
sources/
  *.xlsx                 來源主檔（唯一真相，要改來源改這個）
  sources.md             由 xlsx 自動產生，skill 實際讀的檔（勿手改）
scripts/
  sync_sources.py        xlsx → sources.md
  rotate_sources.py      每日輪掃批次（168 源／每批 8、約 21 天一輪）
  run_daily.sh           launchd 呼叫的每日執行入口
  build_index.py         掃 reports/ 重建首頁
  build_outputlogic.py   產生運作說明頁（來源異動才需重跑）
  publish.sh             重建首頁 + commit + push
  send_email.py          Actions 用：寄日報 Email
  send_telegram.py       Actions 用：發 Telegram + 守門員
  healthcheck.sh         執行環境健檢
.github/workflows/
  notify-email.yml       push 觸發寄 Email
  telegram-0630.yml      06:30 cron 發 Telegram
docs/
  RUNBOOK.md             ★ 換手時唯一需要讀的文件
  DECISIONS.md           架構決策與診斷紀錄
  scheduled-prompt.txt   排程實際餵給 Claude 的 prompt
  launchd/               macOS 排程範本
state/                   當日中繼檔（pending Telegram 等）
reports/YYYY-MM-DD.html  每日報告
index.html               首頁（自動產生）
```

---

## 常用指令

```bash
bash scripts/healthcheck.sh        # 換機器或出問題時先跑這個
python3 scripts/rotate_sources.py  # 看今天要輪掃哪 8 個來源
bash scripts/run_daily.sh          # 手動跑一次完整流程（設排程前必做）
python3 scripts/sync_sources.py    # 改完 xlsx 後重建 sources.md
python3 scripts/build_outputlogic.py   # 來源有增減時更新說明頁
bash scripts/publish.sh            # 手動發布當日報告
```

---

## 換帳號／換機器

看 **[`docs/RUNBOOK.md`](docs/RUNBOOK.md)** 第 4 節，六個步驟。
排程任務的 prompt 逐字原文在同一份文件的第 3 節。
