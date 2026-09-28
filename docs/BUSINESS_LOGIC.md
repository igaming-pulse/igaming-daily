# iGaming Daily Report — Business Logic Handoff (machine-readable, for Claude)

```yaml
doc_version: 2
rules_version: SKILL v6.4.2
as_of: 2026-09-27 (Asia/Taipei)
audience: a future Claude session taking over on a new machine/account
scope: business logic, decision rules, rationale, failure modes, playbooks
not_in_scope: file inventory, secrets (only their locations)
precedence: repo skills/SKILL.md > this doc (this doc explains WHY)
repo: github.com/igaming-pulse/igaming-daily
site: https://igaming-pulse.github.io/igaming-daily/
docs_page: https://igaming-pulse.github.io/igaming-daily/OutputLogic/
```

---

## 0. Operating contract with the user

```yaml
language: Traditional Chinese (Taiwan); English only for code/terms/commands
acknowledgement: never reply with a bare "收到"; execute the task directly
style: plain, concrete, tables welcome; lead with the answer; admit mistakes with cause
discussion_first: when the user says "先討論" / "先列出來給我" / "確定再發", present and WAIT; do not implement
confirm_before: outward actions not already requested (sending Telegram, publishing new pages, deleting)
ambiguity: if two instructions from the user conflict (e.g. a mapping written two ways), stop and ask with evidence; do not guess
verification: verify the real observable outcome (rendered page, element visible, live URL 200), not a proxy (a flag/property). Past bugs were missed by checking proxies.
user_schedule: works Mon–Fri
user_role: PM at an iGaming company with Philippines-focused business
```

---

## 1. Product goal (what "good" means)

1. **New Slot games** (online + land-based cabinets) every day. Precision not required; inspiration is. 3–5 day delay OK. Pre-release/early reviews OK **only if release ≤ 7 days after the report date**.
2. **Market dynamics**: slot design trends first; big-brand actions (online GPs and land-based makers: Aristocrat, Light & Wonder, IGT, Konami, Everi, AGS, Zitro, Novomatic).
3. **Philippines**: platform strategy / operations / new products of DigiPlus family (BingoPlus, ArenaPlus, GameZone), PT Gaming, OKBet, Casino Plus, BET88, PlayTime → new brands making big moves in PH → GP listings on PH platforms → policy (last).
4. **Readability**: all 5 categories usually present. Empty 1–2 days acceptable; never persistently empty → inventory fills gaps.

---

## 2. Topology

```yaml
environments:
  old_machine:
    account: natekao (personal Claude; has "Routines")
    rules: SKILL v4.1 (search-first, lenient dates)
    publishes: main/reports/<DATE>.html (official), official Telegram + Email
    homepage_label: "YYYY-MM-DD 週X · iGaming 市場日報（15' v）", light-orange card
  company_machine (this one):
    account: nathan.kao@bituslabs.com, a Mac
    branch: test-publish
    publishes: main/reports/<DATE>-test.html via publish_test_to_main.sh
    homepage_label: "YYYY-MM-DD 週X · iGaming 市場日報（13' v）", white card + green edge
    telegram_prefix: "🧪【測試】公司帳號併行版"
    email: NOT wired
  cutover: undecided; parallel period ongoing
branches:
  test-publish: rules (skills/SKILL.md), scripts, sources xlsx, state (inventory, triggers, harvest md), docs, daily reports
  main: the website only (index.html, reports/*, OutputLogic/), root build_index.py, telegram workflow
  rule: homepage changes → main's root build_index.py; everything else → test-publish
scheduling:
  mechanism: macOS launchd (com.igaming.daily-0230) at 02:30 Taipei; missed runs catch up on wake
  why_not_cloud: Claude cloud sessions could not push to GitHub (proxy 403)
  risk: Mac must be awake for ~20–30 min; caffeinate only works on AC; lid closed on battery = frozen run (9/25 resumed 9 h later)
  pmset_wake: not configured (older docs claim 02:25; false)
credentials_locations:
  firecrawl: env FIRECRAWL_API_KEY in the launchd plist (~/.zshrc copy had stray quotes)
  github: macOS keychain git credential (used for pushes and workflow_dispatch via `git credential fill`); gh CLI not installed
  telegram/smtp: GitHub Actions secrets
commit_identity: "iGaming Pulse <igaming-pulse@users.noreply.github.com>"
firecrawl_plan: 1000 credits/month, resets on the 14th, 20 requests/min (sleep ≥3.5 s)
```

---

## 3. Daily pipeline (state machine)

```
02:30 launchd → scripts/run_daily.sh
  1 git pull --ff-only (test-publish)
  2 python3 scripts/harvest.py                → state/harvest/<DATE>.md (+ .json, <DATE>-lists/*.md)
  3 claude --permission-mode bypassPermissions -p "$(cat docs/scheduled-prompt.txt)"
      a read state/harvest/<DATE>.md and every <DATE>-lists/*.md
      b python3 scripts/inventory.py show --date <DATE>
      c layer-3 WebSearch (4 query families + 4 special GPs)
      d score → dedupe → caps → per-category selection (+ inventory fill)
      e verify selected only: primary-source date → corroboration → params → og:image
      f write state/<DATE>-igaming-report.md → render reports/<DATE>.html
      g write state/pending_telegram.txt + pending_telegram_url.txt
      h write state/inventory-picks-<DATE>.json → inventory.py update
      i build index, ONE commit "daily: <DATE> report", push test-publish
  4 acceptance: report mtime ≥ start AND HEAD changed (never trust exit code)
  5 scripts/publish_test_to_main.sh → main: reports/<DATE>-test.html + index.html
06:40 (often ~2 h late) GitHub Actions telegram-test-0640.yml on main
      → checkout test-publish → scripts/send_telegram.py → channel
      guard: no report or pending date ≠ today → "⚠️ 日報未產出"
```

---

## 4. Time rules

```yaml
window: 24h ending at ACTUAL execution time (normal: D-1 02:30 … D 02:30 Taipei)
never: fixed start anchor; widening; including items published after window end
late_run: window = run time − 24h; state it in the report
backfill: harvest.py --date D --anchor 02:30
```

### 4.1 Primary-source date gate (hard)
- Each item needs **1 primary source** with **publish date incl. year** inside the window (inventory-filled items: inside freshness).
- Date priority: `article:published_time` / `og:published_time` / JSON-LD `datePublished` → URL date `/YYYY/MM/DD/` → byline. `dateModified` ≠ publish date.
- Body event dates ("launches Sep 22") are not publish dates. Origin: DigiPlus Brazil "GamePlus" 2025 news accepted as 2026.
- Corroborating sources may be older; if ALL sources are out of window → old news → reject.
- Red flags: yearless dates; future tense about a past time; re-surfacing of an already-reported announcement.
- Report shows ONE date (primary). Per-source dates → internal section at end of the state md (not rendered).

---

## 5. Sources and collection

### 5.1 Source master
Excel `sources/igaming-daily-report-sources-v2.xlsx` (233 rows, 10 categories) → `scripts/sync_sources.py` → `sources/sources.md`.
Columns: 編號 · 分類 · 名稱 · 網址 · 備註 · **抓取方式** · **頻率** · **抓取端點** · **觸發關鍵字** (regex; `|` written as `¦` in sources.md) · **展期** (`YYYY-MM-DD~YYYY-MM-DD`, editions separated by `;`).

| 抓取方式／頻率 | Mechanism | ~Count |
|---|---|---|
| WP-API／RSS · 每日 | layer 1, curl, free | 93 unique endpoints |
| Firecrawl · 每日 | layer 2 fixed | 6: EEGaming Recent Slot Releases, BigWinBoard new-slots, SlotsLaunch, iGamingToday, SBC News, Inside Asian Gaming |
| Firecrawl · 輪掃 | layer 2 via rotate_sources.py | 3/day of ~71 (~24-day cycle) |
| Firecrawl · 每週／事件 | event trigger + Monday fixed | regulators (incl. PAGCOR) + feedless associations |
| Firecrawl · 行事曆 | calendar trigger | 21 exhibitions |
| forums, podcasts | not fetched | — |
| 不抓／停用 | never | 2 |

### 5.2 Layer 1 — harvest.py (free)
- WP REST `/wp-json/wp/v2/posts?after=<ISO>&per_page=100&_fields=date_gmt,link,title,excerpt` (exact UTC, time-filterable) — preferred.
- RSS/Atom `pubDate|published|updated|dc:date` (latest ~10–20 only). Yogonet: `https://www.yogonet.com/international/rss.xml` (-0300).
- BigWinBoard `/new-slots/` HTML → `title — provider — release date` (date-only; `(TBC)` = unconfirmed; release date ≠ article date).
- Filters: PH general media (GMA News, Rappler, SunStar, BusinessWorld) need gaming keywords; NOISE drops lottery draws (IT/DE), sports odds/predictions, press reviews.
- Retains: in-window items + "窗外近期" (Slot ≤7 d, others ≤3 d) as inventory candidates.
- Category guess (keywords; order cat4 → cat1 → cat2 → cat5 → default cat3). `releases` / `launches <Capital>` count as cat1 hints. Guess only — Claude reclassifies and must scan cat3/cat5 for launches.
- Output md: grouped by guess, ≤10 in-window lines per source, source health, layer-2 file list, Saturday checkpoint block.
- `--plan` prints today's layer-2 targets without calling Firecrawl.

### 5.3 Layer 2 — Firecrawl
- List pages: `formats:["markdown"], onlyMainContent:false` (v6.1: `summary` on lists returns a site blurb, no items).
- Articles: `formats:["summary"], onlyMainContent:true`; og:image + publish time in `data.metadata`. Never JSON extraction (5 credits).

### 5.4 Triggers for non-routine sources (v6.4.2)
Reason: "平常不抓、遇到題材才查" had no entry point = permanent exclusion.

| Trigger | Targets | Fires when | Limits |
|---|---|---|---|
| Event | rows with 觸發關鍵字 (regulators incl. PAGCOR, feedless associations) | an in-window **title** matches; priority PAGCOR → DICJ/Korea → rest | each keyword ≤1 per ISO week (Mon–Sun); ≤3/day; log `state/triggers.json` |
| Calendar | exhibitions with 展期 | report date ∈ [start − 14 d, end] (through closing day, user's choice) | ≤2/day, nearest start first |
| Fixed | regulators + feedless associations | every **Monday** (Monday report covers Sunday, thinnest weekday) | 3/week, rotated by ISO week |

Tuning lesson: matching titles+excerpts in list order let low-value ES/IT mentions consume slots before PAGCOR → title-only + PH/Asia priority.
Exhibition dates must be refreshed yearly (researched 2026-09-27; blank = unknown: AGE Asia next, G2E Asia @ Philippines, SiGMA World 2027).

### 5.5 Layer 3 — WebSearch (~30–40/day, cap 60)
1. PH platforms: DigiPlus, BingoPlus, ArenaPlus, GameZone, PT Gaming, OKBet, Casino Plus, BET88, PlayTime + new game/promo/launch/partnership.
2. New brands into PH: "Philippines launch", "enters Philippine market", "PAGCOR license", PH partnerships.
3. Land-based cabinets: Aristocrat, L&W, IGT, Konami, Everi, AGS, Zitro, Novomatic + new cabinet/debut.
4. Slot gap-fill & trends: "new slot release <date>"; weekly mechanic/trend round-ups.
Plus one search each: Acewin, Omiplay, YellowBat, ATG.
Anti-pattern: "brand group + RTP max win" → evergreen ranking pages only.

### 5.6 Tool choice
| | curl | Firecrawl | WebSearch | WebFetch |
|---|---|---|---|---|
| What | raw file from the Mac | cloud headless browser → cleaned md/summary + metadata | keyword search | Claude fetch + summary |
| Cost | free | 1 credit | free (≤60/day) | free |
| JS pages | empty | yes | n/a | often empty |
| Bot walls | often 403 | usually OK | n/a | often blocked |
| Publish time | exact (RSS/WP) | usually | vague | infer |
| Risk | blocked; parser breaks | quota, rate | old news, evergreen | summary omissions |
Order: RSS/WP API or fetchable HTML → curl; awkward parse → WebFetch; blocked/JS → Firecrawl; off-list topics → WebSearch. RSS/WP API are formats fetched with curl.

### 5.7 "Is today thin?"
Decided only by harvest in-window counts + source health. ≥3 major sources failing → "抓取異常", never "真實淡季". The phrase "真實淡季，非抓取方法錯誤" was wrong on 9/23 v1, 9/24, 9/26, 9/27 — treat it as a red flag.

---

## 6. Categories and format

| cat | Name | Content | Target (cap) | Format |
|---|---|---|---|---|
| cat1 | 🎰 Game Provider 新遊戲 | online slot launches; previews releasing ≤7 d; land-based cabinets | weekday ≤5 / weekend ≤2 | 3-part |
| cat2 | 🕹️ 非 Slot 新內容 | crash/mines/plinko → live → poker → local card → other; EEZE 1/day (skip if no news 3 d or same topic ≤3 d) | 2–3 (≤5) | 3-part, 5 or 3 params |
| cat3 | 🤝 主流 GP／平台動態 | concrete big-brand actions, online + land-based | 3–5 (≤7) | 動態 |
| cat4 | 🇵🇭 菲律賓 | platform strategy/ops/products > new brands > GP listings > policy; official separate | 2–4 (commercial ≤6) | 動態 |
| cat5 | 📊 市場數據 & 趨勢 | slot design trends > market data > trade-show impact | 1–3 (≤5) | market |

Total 15–18, cap 22. <10 items → Telegram line `❗今日收錄偏少（共 N 則）`. Sports low priority (casino/slot ops of betting brands or mega-event spillover only).
cat1 params: 遊戲類型 · 盤面 · 消除/賠付 · 最高倍率 · RTP · 波動 · 目標市場 · 關鍵特色. "未公布" only after SlotCatalog + provider + media page, noted in `查證：`. Never delete/downgrade data ("只增不減").
Title prefixes: `📦 近期新作（M/D 首見）` (inventory slot), `📦（M/D）` (inventory other), `🆕 新作預告（M/D 上線）`, `📋 本週補遺（M/D 發布）`, `🔁` (re-shown after >3 d with update).

---

## 7. Scoring and caps

`score = B + E + R + T`
- **B**: 6 = Acewin, Omiplay, YellowBat, ATG, EEZE, Yggdrasil, Jili, TaDa Gaming, DigiPlus, BingoPlus, ArenaPlus, GameZone, PeryaGame, Casino Plus, PlayTime, BET88, OKBet, PT Gaming, Stake, Betfury, PAGCOR · 4 = PG Soft, Pragmatic Play, Nolimit City, Play'n GO, Red Tiger, Aristocrat, IGT, Light & Wonder · 3 = second tier (CP Game, Peter & Sons, NetEnt, Hacksaw, FA CHAI, Evolution, Playtech, Betsoft, Spinomenal, Relax, Push, BGaming, Wazdan, Quickspin, …) · 1 = other named · 0 = unnamed.
- **E**: 6 launch / land-based debut / major integration · 5.5 preview · 5 market data, GGR, breakthroughs, trending mechanics · 2 trade show (±2 weeks) · 1 regulation, M&A, earnings · 0.5 awards, hires, marketing.
- **R** (market affected): 6 PH · 5 TW, SEA · 4 LatAm/Brazil/Mexico/South Africa/global · 3 India, US, Europe, Canada · 2 Macau, JP, KR, CN · 1 other.
- **T**: 0–12 h +2 · 12–24 h +1 · date-only 0.
- Caps (override score): same GP ≤2/day; PH commercial ≤6 (official separate); other single country ≤3; total ≤22. Same event, many outlets → one item.
- Ties: score → B → R → newer.

---

## 8. Selection

### 8.1 Dedupe
Items listed in `inventory.py show` "近 3 天已出現" are excluded (review/launch/promo of a game = same game). After >3 d, re-show only with material update, prefix 🔁. Known gap: a genuine new twist within 3 d is dropped (MGM/People Inc, 9/26).

### 8.2 cat1 algorithm (hard)
```
cap = 5 if weekday(report_date) in Mon..Fri else 2
cands = in-window slot items after dedupe
cands -= previews with release_date > report_date + 7     # → inventory as 待上線
picked = cands with B >= 3                                  # respect GP <= 2; overflow by B → inventory
picked += best remaining cands by score until cap
if count(in-window new items) <= 3:
    fill from inventory (B desc, first_seen asc, params complete) until cap; short → show what exists
else:
    no inventory fill
overflow → inventory
```
Supply evidence (EEGaming Weekend Reels, 12 weeks, 177 items): Mon 14% · Tue 21.5% · Wed 9% · **Thu 46%** (max in 12/12 weeks) · Fri 9% · Sat/Sun 0. Big brands (n=39): Mon 46%. Report D covers D−1 → Friday report richest; Sunday & Monday reports ≈ 0 fresh launches. EEGaming misses non-press-release GPs (Hacksaw/Nolimit/ELK) → BigWinBoard compensates.

### 8.3 Saturday checkpoint
Weekend Reels (EEGaming weekly column, Friday EU daytime) falls into the Saturday 02:30 window. harvest auto-fetches it + lists BigWinBoard's week. Compare with history/inventory: covered → skip; missed → `📋 本週補遺`, counts toward Saturday's 2 (big brands first), remainder → inventory for Mon–Wed. Report: WR total / covered / back-filled / stocked.

### 8.4 cat2–cat5
Score to targets. Empty 2 consecutive days (`連續空白天數 ≥ 2`) → day 3 fill 1–2 from inventory.

### 8.5 Verification (selected only)
1. Date gate (harvest times are trusted). Fail → drop, promote next.
2. ≥1 independent corroboration (≥2 for big/high-impact). Single source OK with cautious wording if it qualifies as primary.
3. Params: provider site / SlotCatalog / media page.
4. One Firecrawl per item (content + og:image, landscape ~16:9, no thumbnails).

### 8.6 Source trust
official (press/provider/regulator/exchange) > industry media > aggregators.
- **EEGaming**: HIPTHER OÜ (Estonia), B2B since 2015; best GP press-release aggregation; "Recent Slot Releases" + Friday "Weekend Reels" column (also syndicated on hipther.com).
- **BigWinBoard**: Stockholm, 2017, founder Daniel Hansson Sokcic (ex-streamer), ~6 staff; player-oriented reviews with specs; review date ≠ release date; `(TBC)` pages may be placeholders.
- **iGamingToday**: affiliate-marketing review site (domain 2017, anonymous team), often re-publishes BigWinBoard reviews days/weeks later → secondary only, never sole source.

---

## 9. Inventory

File `state/inventory.json` = `{slots[], others[], history[]}`; key = normalized `title|gp`.

| | Slot | cat2–cat5 |
|---|---|---|
| In | overflow beyond cap; Saturday back-fill overflow; previews >7 d out (待上線) | **exactly 1 per category per day**: best unused qualifying item (skip only if none; say so) |
| Out | day's new ≤3 → fill to cap | 2 empty days → day 3 fill 1–2 |
| Freshness | 7 d from first_seen; previews until release + 3 d | 3 d |

Commands: `inventory.py show --date D` (prunes; prints cap rule, stock, 待上線, recent history, empty streaks) · `inventory.py update --date D --file state/inventory-picks-D.json` with `{"shown":[{cat,title,gp}], "stock":[{cat,title,gp,b,first_seen,release_date?,sources:[{name,url,published}]}]}`.
Pitfalls: the model has stocked items it judged invalid (BigWinBoard placeholders) → clean. Weekly supply (~15–25) < capacity (29) → stock drains; large stock only from one-off seeding (9/27 seeded 36 from the 9/21–9/25 backtest).

---

## 10. Outputs

- `state/<DATE>-igaming-report.md` (internal sections not rendered) → `reports/<DATE>.html`: 5 colored sections, badges, stats grid (hide empty), cards with 🔎 `.verify`, sources + date, favicon `../icon-*.png`, footer `iGaming 日報自動化 v6.4（三層收集＋庫存）`, stats line `本日日報查詢約 N1 個網站，其中提取 N2 個資料來源並進行交叉比對`. Numbering per category from 01; PH official = `官方`.
- Quality notes only in Telegram.
- `state/pending_telegram.txt`: line 1 `🎰 iGaming 市場日報 <DATE>（週X）`, line 2 counts (both parsed by email workflow — keep format), then titles by category, then `📝 品質備註` 1–3 numbered; plain text ≤3500 chars. `pending_telegram_url.txt` = report URL.
- One commit: report, index, pending, inventory.json, inventory-picks, harvest md, triggers.json (harvest json/lists gitignored).

---

## 11. Website (main branch)

```yaml
file_naming:
  "<DATE>.html": old machine official
  "<DATE>-test.html": company machine daily
  "<DATE>-vN.html": company reruns (1 digit = 第N版; ≥2 digits = rules version, -v64 = v6.4 規則)
  "<DATE>-special.html": special edition (e.g. 2026-09-27 36-slot inventory showcase)
homepage_builder: main/build_index.py (both machines run it)
card_label_rule: label derived from background class via MACHINE_TAG (text and color cannot diverge)
  src-old (light orange)  → "YYYY-MM-DD 週X · iGaming 市場日報（15' v）"   # old machine natekao
  default (white, green)  → "… · iGaming 市場日報（13' v）"; -vN → "（13' v・第N版|vX.Y 規則）"  # company
  src-special (light blue)→ "週X 特別版本內容"
  applies_to: ALL cards (no date cutoff)
legend: "13' v" (white/green) · "15' v" (orange) · "特別版本內容" (blue)
pinned_card: "📘 運作說明 OutputLogic · 生成邏輯 YYYY/MM/DD 📌 置頂" (date = last git commit of OutputLogic/index.html)
pagination: 20 per page, client-side; pinned card outside pagination
css_gotcha: a.card{display:flex} overrides UA [hidden] → must have a.card[hidden]{display:none}
history_of_mistakes:
  - 13'/15' mapping was reversed once (user wrote it two ways; final answer: old=15', company=13')
  - a 9/28 date cutoff hid all labels; removed
  - pagination "worked" by property check but not visually; fixed with the CSS rule
```

Report page theme switch (main root `report_theme.py`, flag file `report_theme.txt`):
- `spectrum-c` = 色譜圖表風・方案 C (Morandi palette: sage #7D9C84 Slot, dusty rose #C08A84 非 Slot, mist blue #7F97B5 主流, clay #C9976B 菲律賓, grey-violet #9B8AB5 市場; date as main title; dark stats side panel; category-tinted spec/keyrow; no yellow/black blocks). `classic` = original look.
- Originals backed up to `reports/_classic/` before restyling; restyled files carry `<!-- theme:spectrum-c -->`.
- `build_index.py` calls `report_theme.auto()` on every rebuild → new compatible reports are restyled automatically while the flag is `spectrum-c`.
- Compatibility (v2, 9/28): needs `<header>`, `class="date"`, `class="card cN"`; stats container optional (`grid`／`stats`／`stats-grid`, matched as exact class `stat` to avoid hitting the `stats` container), section titles `sh`／`sec-title`, weekday `週X`／`星期X`. `THEME_FROM = 2026-09-27`: earlier reports are never restyled (user asked not to change past pages). **Old-machine files (`<DATE>.html`, 15' v) are never restyled** (risk of broken layout from unknown structures; user decided 9/28) — only `-test`／`-vN`／`-special` from ≥ 9/27. Card title h3 = 24px weight 600 SemiBold (user chose after comparing 400/500/600/700/900; mobile 21px; font link must load 600). Commands: `refresh` re-renders restyled files from `_classic` after CSS edits. Report HTML is still freshly written each day, so an unfamiliar structure is skipped; freezing the template remains an open decision.
- Hot IP rule (v6.4.3): Huff N' Puff, Bao Zhu Zhao Fu, SuperGems → H=+3, first in Slot area, preview window 30 days (Big Bass removed at user's request).
Homepage theme switch (main root `home_theme.py`, flag `home_theme.txt`): `v1` = 清單刊頭 (masthead with title + legend + spectrum strip, dark side panel with archive counts; ruled list rows with source colour square: 13' v sage #7D9C84, 15' v clay #C9976B, special mist blue #7F97B5; dark pinned OutputLogic bar); `classic` = previous homepage. `build_index.py` builds the classic HTML then calls `home_theme.transform()`; rollback = set flag + rebuild (no backups). **User keywords**: 「首頁樣式回滾」→ `python3 home_theme.py rollback` + push main; 「首頁樣式套用」→ `python3 home_theme.py apply` + push main.
- **User keywords**: 「日報樣式回滾」→ `python3 report_theme.py rollback` + rebuild + push main; 「日報樣式套用」→ `python3 report_theme.py apply` + rebuild + push main. Execute directly when heard.

OutputLogic page: generated by `scripts/build_outputlogic.py` on test-publish (architecture, 5 mermaid charts, tools table, triggers, categories, scoring, source table with 抓取方式/頻率/展期), then copy `OutputLogic/index.html` + `OutputLogic.md` to main. Every mermaid label must close with `"]`; check each `pre.mermaid` renders an SVG without "Syntax error".

---

## 12. Telegram

- Workflow `telegram-test-0640.yml` (main, cron 22:40 UTC) checks out test-publish. Env: `MSG_PREFIX`, `REPORT_URL_SUFFIX` (default `-test`). Manual dispatch inputs: `dry_run`, `url_suffix`, `msg_prefix`, `report_date`, `pending_path`.
- Manual send: wait until the target URL returns 200 on Pages, then dispatch with `dry_run=false`; confirm "✓ Telegram 已發送" in the job log.

---

## 13. Headless contract (docs/scheduled-prompt.txt)

Never ask; pick the most reasonable interpretation and document it. Pre-decided: overwrite today's report (never dedupe against today's file); stay on test-publish; push current branch; no notification actions; window overlap normal; dedupe only per written rules. Budgets: Firecrawl ≤35 (list pages ~9, +0–5 trigger days, +3 Mondays; articles shrink accordingly), WebSearch ≤60, no parallel sub-agents, ≤3 verification fetches/item. Done = report written AND committed+pushed.
Override block for special runs: fixed DATE/window, "harvest already done", distinct output names, forbid touching official files / inventory as required, no commit/push.

---

## 14. Playbooks

```yaml
rerun_past_date_as_separate_version:
  - python3 scripts/harvest.py --date D --anchor 02:30
  - claude -p "<scheduled prompt> + override: DATE=D, outputs reports/D-v64.html, state/D-v64-*.md, pending_telegram_v64_D.txt, no commit"
  - review Telegram text (remove phrases like "僅供內部")
  - copy reports/D-v64.html to main, run main build_index.py, push
  - after Pages 200: dispatch Telegram (url_suffix=-v64, report_date=D, pending_path=state/pending_telegram_v64_D.txt)
special_edition:
  - build item list JSON, run claude with explicit "do not run inventory.py / do not touch inventory.json"
  - publish as reports/<DATE>-special.html on main
add_or_change_source:
  - edit xlsx (fill 抓取方式/頻率/抓取端點; 觸發關鍵字 or 展期 if applicable) → sync_sources.py → build_outputlogic.py → commit test-publish → copy OutputLogic to main
refresh_exhibition_dates: yearly; research official dates; fill 展期; verify with harvest.py --date <date> --plan
change_homepage: edit main/build_index.py in a worktree of origin/main; rebuild; verify in a browser (visible elements, labels vs colors); push main
check_firecrawl: curl https://api.firecrawl.dev/v1/team/credit-usage -H "Authorization: Bearer $FIRECRAWL_API_KEY"
handoff_order_on_new_machine: docs/BUSINESS_LOGIC.md → skills/SKILL.md → docs/RUNBOOK.md
```

---

## 15. Version history (why the rules look like this)

| Version | Date | Change | Trigger |
|---|---|---|---|
| v5.x | ≤9/20 | repo-portable rules, launchd, Actions, Firecrawl cuts | account migration |
| v6.0 | 9/22 | discover → score → verify; B+E+R+T; caps; "core 8 list pages" | low overlap; unmeasurable judgment |
| v6.1 | 9/23 | list pages must use markdown | summary returned no items |
| v6.2 | 9/24 | primary-source date gate | DigiPlus 2025 news leaked |
| v6.4 | 9/27 | harvest.py, slot DB sites, inventory, PH redefinition, xlsx columns | 1 of 12 big-brand launches caught (9/23–9/26); iGB parsing failures |
| v6.4.1 | 9/27 | weekday 5 / weekend 2; fill only if ≤3; previews ≤7 d; Saturday checkpoint; iGamingToday secondary; cat2–5 stock 1/day | 9/27 slot area = 3 far-future previews from one affiliate site |
| v6.4.2 | 9/27 | three triggers; 觸發關鍵字 + 展期 columns; SBC Summit, iGB Live added; OutputLogic rewritten | "never fetched" sources |

Old machine v4.1: search-first ("brand + RTP max win reels" hits slot DBs), rotation 30/day, lenient dates, cat1 fixed 5 → more slots but included out-of-window items and far-future previews (9/27: 7 of 13 outside window). Neither machine is a gold standard.

---

## 16. Open issues

1. Exception for a new twist of a story shown ≤3 d ago — undecided.
2. Auto-reject BigWinBoard `(TBC)` placeholders from inventory.
3. Email for company line; cutover plan (drop `telegram-test-0640.yml`, use `telegram-0630.yml`, run on main).
4. Mac sleep risk (pmset wake or cloud scheduling; Routines not visible on company account).
5. Firecrawl ~25–30/day steady; backfills are expensive.
6. harvest md can reach ~100 KB on heavy news days.
7. PH platform promos often only on FB/IG/app.
8. Report page H1 still says "（測試）" for -test files (added by publish_test_to_main.sh); user has not decided whether to change it to 13' v.
