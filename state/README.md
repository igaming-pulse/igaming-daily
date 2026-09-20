# state/ — 當日中繼檔

由 02:30 的排程任務寫入，由 GitHub Actions 讀取。

| 檔案 | 寫入者 | 讀取者 |
|---|---|---|
| `pending_telegram.txt` | SKILL 步驟 3 | 06:30 的 `send_telegram.py`；前兩行也被 `send_email.py` 用來組信 |
| `pending_telegram_url.txt` | SKILL 步驟 3 | `send_telegram.py`（inline 按鈕的連結） |
| `<DATE>-igaming-report.md` | SKILL 步驟 1 | 人工查閱／除錯用的中繼內容層 |

`pending_telegram.txt` 的**前兩行格式固定**（第 1 行標題含日期、第 2 行各區則數），
Email workflow 依賴這個格式，修改 SKILL 時要一起改。
