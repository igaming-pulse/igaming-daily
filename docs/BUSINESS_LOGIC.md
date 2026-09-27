# iGaming Daily Report — Business Logic Handoff (for Claude)

> Audience: a future Claude session taking over this workflow on a new machine.
> Scope: business logic, rules, rationale, known failure modes. Not a file inventory.
> Rule version described: **SKILL v6.4.2** (2026-09-27). If the repo's `skills/SKILL.md` disagrees with this doc, the repo wins; this doc explains *why*.
> Language contract with the user: reply in **Traditional Chinese (Taiwan)**; English only for code/terms. Do not reply with a bare acknowledgement ("收到"); execute directly when given a task/script.

---

## 0. TL;DR state machine

```
02:30 Asia/Taipei (launchd)
 └─ run_daily.sh
     ├─ git pull (branch test-publish)
     ├─ harvest.py  → state/harvest/<DATE>.md (+ .json, lists/)
     ├─ claude -p <docs/scheduled-prompt.txt>   # headless, bypassPermissions
     │    ├─ read harvest md + layer-2 list files
     │    ├─ inventory.py show --date <DATE>
     │    ├─ WebSearch layer 3 (4 fixed query families)
     │    ├─ score → per-category selection (caps, inventory fill)
     │    ├─ verify selected only (primary-source date gate → cross-check → params → og:image)
     │    ├─ write state/<DATE>-igaming-report.md → reports/<DATE>.html
     │    ├─ write state/pending_telegram.txt (+ _url.txt)
     │    ├─ write state/inventory-picks-<DATE>.json → inventory.py update
     │    └─ single commit "daily: <DATE> report" → push test-publish
     ├─ acceptance check (report mtime > start AND new commit)
     └─ publish_test_to_main.sh → main: reports/<DATE>-test.html + index.html
06:40 Asia/Taipei (GitHub Actions on main, often ~2h late)
 └─ telegram-test-0640.yml checks out test-publish → send_telegram.py → Telegram channel
```

---

## 1. Purpose (the user's actual goal)

The user (PM at an iGaming company, Philippines-focused business) reads this daily to:
1. Know **new Slot games** launched in the market (online + land-based cabinets). Exact precision is not required; inspiration is. 3–5 day delay is acceptable. Pre-release reviews are acceptable **only if release is within 7 days**.
2. Track **market dynamics**, especially slot design trends and big-brand moves (online GPs and land-based makers: Aristocrat, Light & Wonder, IGT, Konami, etc.).
3. Track **Philippines**: priority is platform strategy/operations/new products of DigiPlus family (BingoPlus, ArenaPlus, GameZone), PT Gaming, OKBet, Casino Plus, BET88, PlayTime; then new brands making big moves in PH; policy is lowest priority.
4. **Readability**: all five categories should usually have content. A category empty for 1–2 days is fine; it must not stay empty (use inventory).

User works Mon–Fri. Weekend reports may be thinner.

---

## 2. Environment topology

- **Two parallel environments** (parallel period, cutover date not decided):
  - **Old machine** (personal account "natekao", SKILL v4.1, has Claude "Routines"): publishes official `reports/<DATE>.html` to `main`, sends official Telegram + Email.
  - **This environment** (company account nathan.kao@bituslabs.com, a Mac): runs on branch **`test-publish`**, publishes `reports/<DATE>-test.html` to `main` as a "(測試)" card, sends a Telegram prefixed `🧪【測試】公司帳號併行版`.
- Repo: `github.com/igaming-pulse/igaming-daily`. Site: `https://igaming-pulse.github.io/igaming-daily/` (GitHub Pages from `main`).
- Commit author identity: `iGaming Pulse <igaming-pulse@users.noreply.github.com>`.
- **Email**: `notify-email.yml` triggers only on `main` pushes under `reports/**` in the old environment's setup; the company-account line currently does **not** send email.
- Scheduling is **local launchd**, not cloud, because Claude cloud sessions could not push to GitHub (proxy 403). Consequence: the Mac must be awake. `caffeinate -s` only works on AC power; lid-closed on battery → sleep → run freezes mid-way (happened 9/25: resumed 9 h later on wake). No `pmset repeat wake` is currently set despite older docs saying 02:25.
- Firecrawl: HTTP API, key in the launchd plist env (`FIRECRAWL_API_KEY`). Plan = **1,000 credits/month**, resets on the 14th (docs said 1,125 — wrong). Rate limit **20 req/min** → sleep ≥3.5 s between calls. Account email unknown (not exposed by API).
- GitHub API calls (workflow_dispatch) were done with the macOS keychain git credential (`git credential fill`); `gh` CLI is not installed.

---

## 3. Time window rules

- Window = **24 h ending at actual execution time** (normally 02:30 Taipei → window = D-1 02:30 … D 02:30). Never anchor to a fixed start; never widen.
- Late/catch-up runs: window = actual run time − 24 h, and must be stated in the report.
- Backfills/reruns of past dates: `harvest.py --date D --anchor 02:30`.
- Articles published **after** the window end are excluded (the old machine violated this by running late and including 06:00/09:00 articles).

### 3.1 Primary-source date rule (v6.2, hard)
Every item needs **one primary source** whose **publish date includes a year** and falls **in window** (for inventory-filled items: within freshness period).
- Date sources in order: `article:published_time` / `og:published_time` / JSON-LD `datePublished` → URL date (`/2026/09/23/`) → printed byline date. `dateModified` does not count.
- Event dates in body text ("launches on September 22") are NOT publish dates. Origin incident: DigiPlus Brazil "GamePlus" 2025 news was accepted as 2026 because the body had no year.
- Corroborating sources may be older (background), but if **all** sources are out of window → it is old news → reject.
- Red flags that require year verification: yearless dates; future tense about a past time ("will relaunch early 2026" in a Sep-2026 report); resurfacing of a story already reported as "announced".
- Report shows a single date = primary source publish date (no ranges like `09-22/23`). Per-source dates go to an internal section at the end of the state md (not rendered).

---

## 4. Collection: three layers

Sources master = Excel `sources/igaming-daily-report-sources-v2.xlsx` (233 rows, 10 categories) → `sync_sources.py` → `sources/sources.md`. Columns: 編號/分類/名稱/網址/備註/**抓取方式**/**頻率**/**抓取端點**/**觸發關鍵字**/**展期**. In sources.md the trigger regex `|` is written as `¦` (markdown table safety); harvest.py converts it back.

| 抓取方式 / 頻率 | Handled by | Count (approx) |
|---|---|---|
| WP-API / RSS, 每日 | harvest.py layer 1 (curl, free) | ~93 unique endpoints |
| Firecrawl, 每日 | harvest.py layer 2 | 6: EEGaming Recent Slot Releases, BigWinBoard new-slots, SlotsLaunch, iGamingToday, SBC News, Inside Asian Gaming |
| Firecrawl, 輪掃 | harvest.py layer 2 via rotate_sources.py | 3/day from ~71 news-type sites without feeds (~24-day cycle) |
| Firecrawl, 每週／事件 | three triggers (§4.4) | regulators incl. PAGCOR, associations without feeds |
| Firecrawl, 行事曆 | calendar trigger (§4.4) | 21 exhibitions (incl. SBC Summit, iGB Live added 9/27) |
| (forums, podcasts) | not fetched | — |
| 不抓 / 停用 | never | 2 |

### 4.1 Layer 1 (harvest.py)
- WP REST: `<site>/wp-json/wp/v2/posts?after=<ISO>&per_page=100&_fields=date_gmt,link,title,excerpt` → exact UTC times. Preferred when available (supports time filtering, pagination).
- RSS/Atom: parse `pubDate/published/updated/dc:date`. Only the latest ~10–20 items; cannot filter by time.
- Yogonet RSS endpoint: `https://www.yogonet.com/international/rss.xml` (dates are -0300).
- BigWinBoard `/new-slots/` HTML parsed: `title — provider — release date` (date-only; "(TBC)" = unconfirmed; release date ≠ article date).
- Filters: general PH media (GMA News, Rappler, SunStar, BusinessWorld) require gaming keywords; NOISE regex drops lottery draws (Italian/German), sports odds/predictions, press reviews.
- Keeps: in-window items; out-of-window items within 7 days (Slot) / 3 days (others) flagged as "窗外近期" = inventory candidates.
- Category guess by keyword (cat4 PH terms first, then cat1 slot/release/launch terms, cat2, cat5, default cat3). Guess only; Claude reclassifies. Known miss pattern: "BGaming releases Bonanza Billion…" had no "slot" word → fixed by treating `releases` / `launches <Capital>` as cat1 hints; Claude must also scan cat3/cat5 for launches.
- Output md lists per category, caps 10 in-window lines per source (Brazil ban day had 30+ from one source), appends **source health** (OK/failed, in-window counts).
- Saturday extras: fetch the latest EEGaming **Weekend Reels** article (found via EEGaming category page link) into lists/, and list BigWinBoard releases of the past 7 days.

### 4.2 Layer 2 (Firecrawl)
- List pages: `formats:["markdown"], onlyMainContent:false` (v6.1 lesson: `summary` on list pages returns a site description, not the item list → "scanned but found nothing").
- Article pages: `formats:["summary"], onlyMainContent:true`; og:image and publish time come in `data.metadata` in the same call. Never use JSON extraction (5 credits).

### 4.3 Layer 3 (Claude WebSearch, ~30–40/day, cap 60)
Fixed query families, with dates of the week:
1. PH platforms: DigiPlus, BingoPlus, ArenaPlus, GameZone, PT Gaming, OKBet, Casino Plus, BET88, PlayTime + new game/promo/launch/partnership.
2. New brands entering PH: "Philippines launch", "enters Philippine market", "PAGCOR license", PH partnerships.
3. Land-based cabinets: Aristocrat, Light & Wonder, IGT, Konami, Everi, AGS, Zitro, Novomatic + new cabinet/debut.
4. Slot gap-fill & design trends: "new slot release <date>"; weekly search for mechanic/trend round-ups.
Plus one search each for special-watch GPs: Acewin, Omiplay, YellowBat, ATG.
**Do not** use "brand group + RTP max win" queries — tested: returns evergreen ranking pages only.

### 4.4 Three triggers for non-routine sources (v6.4.2)
Rationale: the old wording "平常不抓，遇到題材才查" had no entry point and in practice meant permanent exclusion.
| Trigger | Targets | Condition | Limit |
|---|---|---|---|
| Event | regulators (incl. PAGCOR) + feedless associations with a 觸發關鍵字 regex | an **in-window news TITLE** matches the keyword → Firecrawl the institution's page as primary/corroboration. Priority: PAGCOR → DICJ/Korea → others | **each keyword ≤1 per ISO week (Mon–Sun)**, ≤3 per day; log `state/triggers.json` |
| Calendar | exhibitions with 展期 `YYYY-MM-DD~YYYY-MM-DD` (multiple editions `;`) | report date within **[start − 14 days, end]** (user chose to continue through closing day) | ≤2 per day, nearest start first |
| Fixed | regulators + feedless associations | **every Monday** (Monday report covers Sunday = the thinnest weekday report), 3 sources rotated by ISO week number | 3/week |
Tuning history: first version matched titles+excerpts in list order → low-value Spanish/Italian mentions consumed the 3 slots before PAGCOR; fixed with title-only + PH/Asia priority.
Exhibition dates must be refreshed yearly (researched 2026-09-27; unknowns left blank: AGE Asia next edition, G2E Asia @ Philippines, SiGMA World 2027 Rome). `harvest.py --plan` prints today's layer-2 targets without calling Firecrawl.

### 4.5 Fetch tools comparison
| | curl | Firecrawl | WebSearch | WebFetch |
|---|---|---|---|---|
| What | raw file from the Mac | cloud headless browser, returns cleaned markdown/summary + metadata | search engine by keyword | Claude built-in fetch + summarization |
| Cost | free | 1 credit/call (1,000/mo) | free (≤60/day policy) | free |
| Speed | fast (~90 sources in ~10 s) | slow (20/min) | seconds | seconds |
| JS-rendered pages | empty shell | yes | n/a | often empty |
| Bot protection | often 403 | usually passes | unaffected | often blocked |
| Publish time | exact via RSS/WP API | usually in metadata | vague, often wrong | infer from text |
| Risk | blocked / parser breaks on redesign | quota / rate limit | old news, evergreen pages | summary may omit details |
| Used for | layer 1 (RSS ~30, WP API ~60, BigWinBoard HTML) | layer 2 lists, triggers, selected articles | layer 3 topics | fallback during verification |
Decision order: RSS/WP API or fetchable HTML → curl; awkward parsing → WebFetch; blocked/JS → Firecrawl; topics outside the source list → WebSearch. RSS and WP API are data formats fetched *with* curl, not separate tools.

### 4.6 "Is today really thin?"
Only harvest's in-window count + source health decide it. ≥3 major sources failing → report "抓取異常", never "真實淡季". History: the model repeatedly wrote "true low season, not a scraping error" when it was a parsing failure (9/23 v1, 9/24, 9/26). Treat that sentence as a red flag.

---

## 5. Categories

| cat | Name | Content | Daily target (cap) | Format |
|---|---|---|---|---|
| cat1 | 🎰 Game Provider 新遊戲 | online slot launches; pre-release within 7 days; land-based slot cabinets | weekday ≤5, weekend ≤2 | 3-part: summary + "對 PM 的意義", 衍生調整, 參數 list |
| cat2 | 🕹️ 非 Slot 新內容 | crash/mines/plinko → live → poker → local card games → other; EEZE fixed 1/day unless no news 3 days or same topic within 3 days | 2–3 (≤5) | 3-part, 5 or 3 param fields |
| cat3 | 🤝 主流 GP／平台動態 | concrete big-brand actions (partnership, M&A, lawsuits, ops); online and land-based | 3–5 (≤7) | 動態: body + 類型/對象/影響 |
| cat4 | 🇵🇭 菲律賓 | priority: platform strategy/ops/new products > new-brand big moves > GP listings > policy; PAGCOR/official counted separately | 2–4 (commercial ≤6) | 動態 |
| cat5 | 📊 市場數據 & 趨勢 | slot design trends first, then market data, trade-show impact | 1–3 (≤5) | market format |

Total target 15–18, hard cap 22 (Firecrawl budget: ~9 list pages + ≤22 article fetches ≤ 35/day). Below 10 items → Telegram warning line `❗今日收錄偏少（共 N 則）`.
Sports: low priority; only betting platforms' casino/slot operations or mega-event spillover. No odds/results.

### 5.1 cat1 parameter template
遊戲類型 (實體老虎機 / 線上電子老虎機 / 實體+電子 / 其他) · 盤面 · 消除/賠付 · 最高倍率 · RTP · 波動 · 目標市場 · 關鍵特色. "未公布" only after checking SlotCatalog + provider site + media page, and say so in `查證：`. Cross-check rule: never delete or downgrade existing data ("只增不減").

---

## 6. Scoring

`score = B + E + R + T` (then dedupe/caps).

- **B brand**: 6 = special list of 21 (Acewin, Omiplay, YellowBat, ATG; EEZE; Yggdrasil, Jili, TaDa Gaming; DigiPlus, BingoPlus, ArenaPlus, GameZone, PeryaGame, Casino Plus, PlayTime, BET88, OKBet, PT Gaming; Stake, Betfury; PAGCOR). 4 = PG Soft, Pragmatic Play, Nolimit City, Play'n GO, Red Tiger, Aristocrat, IGT, Light & Wonder. 3 = second-tier known (CP Game, Peter & Sons, NetEnt, Hacksaw, FA CHAI, Evolution, Playtech, Betsoft, Spinomenal, Relax, Push, BGaming, Wazdan, Quickspin, "not limited to"). 1 = other named. 0 = unnamed.
- **E event**: 6 new game launch / land-based cabinet debut / major integration; 5.5 pre-release preview; 5 market data, GGR, breakthroughs, trending mechanics; 2 trade show (±2 weeks of the show); 1 regulation, M&A, earnings; 0.5 awards, hires, pure marketing, sponsorship.
- **R region (market affected, not HQ)**: 6 PH; 5 Taiwan, SEA; 4 LatAm, Brazil, Mexico, South Africa, global; 3 India, US, Europe, Canada; 2 Macau, Japan, Korea, China; 1 other.
- **T**: in window 0–12 h +2; 12–24 h +1; date-only 0.
- Hard caps (override score): same GP ≤2/day; PH commercial ≤6 (official separate); any other single country ≤3; total ≤22. Same event covered by many outlets → merge into one item.
- Ties: score → B → R → newer.

---

## 7. Selection algorithm

### 7.1 Dedupe (3-day rule)
Items in `inventory.py show` → "近 3 天已出現" are excluded (a game's review, launch, and promo = same game). After >3 days, may reappear only with a material update (preview → launch, big brand, new data); prefix `🔁`.
Known consequence: a genuinely new development of a story shown ≤3 days ago is dropped (e.g., MGM/People Inc 9/26 twist). No exception rule exists yet.

### 7.2 cat1 (hard rule)
```
cap = 5 if report weekday in Mon..Fri else 2
cands = in-window slot items (after dedupe), excluding previews with release_date > DATE+7 (→ inventory "待上線")
picked = all cands with B>=3 (respect GP<=2; if > cap take highest B, rest → inventory)
fill picked from remaining cands by score up to cap
if len(in-window new items) <= 3:
    fill from inventory (B desc, first_seen asc, params complete) up to cap; if inventory short, show what exists
else:  # >= 4
    no inventory fill
overflow beyond cap → inventory stock
```
Weekday/weekend refers to the **report date**. Each report covers the previous day's supply.
Supply evidence (EEGaming Weekend Reels, 12 weeks, 177 press releases): Mon 14%, Tue 21.5%, Wed 9%, **Thu 46%**, Fri 9%, Sat 0, Sun 0; Thursday was the max in 12/12 weeks. Big brands (B≥3, n=39): Mon 46% (Spinomenal, Pragmatic, PG Soft, BGaming). So: Friday report is the richest; Sunday and Monday reports have ~0 fresh launches. Caveat: EEGaming only covers GPs that issue press releases (Hacksaw/Nolimit/ELK underrepresented → BigWinBoard compensates).

### 7.3 Saturday checkpoint
Weekend Reels (EEGaming weekly column, published Friday European daytime = Friday night Taipei) lands in the **Saturday 02:30** window. Compare its list + BigWinBoard's week list against history and inventory:
- already shown or stocked → skip
- missed → prefix `📋 本週補遺（M/D 發布）`, counts toward Saturday's cap of 2 (big brands first); rest → inventory for Mon–Wed.
- Report: WR total, already covered, back-filled, stocked.

### 7.4 cat2–cat5
Pick by score to targets. If a category has been empty for 2 consecutive days (`inventory.py show` → 連續空白天數 ≥2), fill 1–2 from inventory on day 3. Empty 1–2 days is acceptable.

### 7.5 Verification (selected items only)
1. Primary-source date gate (harvest's exact times can be trusted directly). Fail → drop and promote next.
2. ≥1 independent corroboration (≥2 for big/high-impact). Single source allowed with conservative wording, but that source must itself qualify as primary.
3. Params from provider site / SlotCatalog / media page.
4. One Firecrawl per item (content + og:image). og:image must be landscape ~16:9; no list thumbnails.
Source trust notes: prefer official press/provider/regulator > industry media > aggregators. **iGamingToday** = affiliate-marketing review site (domain 2017, anonymous team) that often re-publishes BigWinBoard reviews days/weeks later → secondary only, never sole source. **BigWinBoard** = Stockholm, founded 2017 by ex-streamer Daniel Hansson Sokcic, ~6 staff, player-oriented reviews with specs; distinguish review date vs release date; "(TBC)" pages may be placeholders. **EEGaming** = HIPTHER OÜ (Estonia) B2B news since 2015; best aggregation of GP press releases; "Recent Slot Releases" category + Friday "Weekend Reels".

---

## 8. Inventory (`state/inventory.json`, `scripts/inventory.py`)

Structure: `slots[]`, `others[]`, `history[]`. Keys = normalized `title|gp` (lowercase alnum + CJK).

| | Slot (cat1) | cat2–cat5 |
|---|---|---|
| In | overflow beyond daily cap; Saturday back-fill overflow; previews >7 days out ("待上線") | **each category must stock exactly 1 item/day**: highest-scoring unused qualifying item (skip only if none, and say so) |
| Out | when day's new ≤3, fill to cap | category empty 2 days → day 3 fill 1–2 |
| Freshness | 7 days from first_seen; previews until release_date + 3 | 3 days |
| Labels | `📦 近期新作（M/D 首見）` | `📦（M/D）` |

Commands:
- `inventory.py show --date D` → prunes expired, prints today's cap/rule, available stock (excluding last-3-day keys), 待上線 list, recent history, empty streaks.
- `inventory.py update --date D --file state/inventory-picks-D.json` with `{"shown":[{cat,title,gp}], "stock":[{cat,title,gp,b,first_seen,release_date?,sources:[{name,url,published}]}]}`.
Inventory-filled items must still have a primary source within freshness.
Observed pitfall: the model sometimes stocks items it itself judged invalid (placeholders). Clean such items.
Expected dynamics: weekly supply ~15–25 < capacity 29 (5×5 + 2×2) → inventory drains; a big backlog only occurs from one-off seeding.

---

## 9. Output specs

- Markdown: `state/<DATE>-igaming-report.md`; internal sections at end (date log, rejection log) are **not rendered**.
- HTML: `reports/<DATE>.html`; five colored sections, header date + badges, stats grid (omit empty categories), cards with `.verify` line (🔎), sources + date, favicon (`../icon-*.png`), footer `iGaming 日報自動化 v6.4（三層收集＋庫存）`, stats line `本日日報查詢約 N1 個網站，其中提取 N2 個資料來源並進行交叉比對`.
- Numbering per category from 01; PH official items numbered `官方`.
- Quality notes (why thin, rejections, anomalies) go **only** in Telegram, never in HTML/Email.
- Telegram `state/pending_telegram.txt`: line 1 `🎰 iGaming 市場日報 <DATE>（週X）`, line 2 per-category counts (these two lines are parsed by the email workflow — never change format), then per-category titles, then `📝 品質備註` with 1–3 numbered notes. Plain text, ≤3500 chars. `pending_telegram_url.txt` = report URL.
- Commit everything in **one** commit: report, index, pending files, inventory.json, inventory-picks, harvest md (harvest json and lists are gitignored).

---

## 10. Publishing & notifications

- `run_daily.sh` acceptance: report file mtime ≥ start AND HEAD changed. Warns if runtime < 300 s (likely stopped to ask a question). Detects "usage limit" messages.
- `publish_test_to_main.sh`: copies to `reports/<DATE>-test.html`, adds "（測試）" to title/H1, checks out main, runs root `build_index.py`, commits only those 2 files (main has no .gitignore), pushes, returns to test-publish.
- `build_index.py` (main root, used by BOTH machines when rebuilding the homepage) recognizes `<DATE>.html`, `-test`, `-vN` (1 digit = "第N版"; ≥2 digits = rules version, e.g. `-v64` → "v6.4 規則"), `-special`.
  - Card label is derived from the card's background class (one mapping, `MACHINE_TAG`), so text and color cannot diverge: `src-old` light-orange = old machine (natekao) `<DATE>.html` → `YYYY-MM-DD 週X · iGaming 市場日報（15' v）`; white card / green edge = company machine (nathan.kao) `-test` → `…（13' v）`, `-vN` → `…（13' v・第N版／vX.Y 規則）`; `src-special` light-blue = `-special` → `週X 特別版本內容`. Applies to ALL cards (no date cutoff). History: the mapping was reversed once and a 9/28 cutoff briefly hid the labels; both fixed 9/27. The user's final mapping: **old machine = 15' v, company = 13' v**.
  - Legend above the list: `13' v` (white/green) = company account, `15' v` (orange) = old machine, 特別版本內容 (blue).
  - Pinned card: `📘 運作說明 OutputLogic · 生成邏輯 YYYY/MM/DD 📌 置頂`, date = last git commit date of `OutputLogic/index.html`.
  - Pagination: 20 reports per page (client-side JS sets `hidden`), pinned card always visible. CSS must include `a.card[hidden]{display:none}` because `a.card{display:flex}` overrides the UA `[hidden]` rule (this bug made pagination look broken). Verify visually (element height), not just the `hidden` property.
  - Note: `main` has its own root-level `build_index.py`; `test-publish` has `scripts/build_index.py`. Homepage changes must be made on `main`'s copy.
- Telegram workflow (`telegram-test-0640.yml` on main, cron 22:40 UTC) checks out test-publish; env `MSG_PREFIX`, `REPORT_URL_SUFFIX` (default `-test`); manual dispatch inputs: `dry_run`, `url_suffix`, `msg_prefix`, `report_date`, `pending_path`. Guard: if `reports/<date>.html` missing or pending line-1 date ≠ date → sends "⚠️ 日報未產出".
- Manual resend: dispatch with `dry_run=false` and appropriate inputs after Pages returns 200 for the target URL.

---

## 11. Headless-run contract (docs/scheduled-prompt.txt)

Never ask questions; choose the most reasonable interpretation and document assumptions. Pre-decided: overwrite today's report if it exists (never use today's file for dedupe); stay on test-publish; push current branch; no Email/Telegram action (Actions handle it); window overlap is normal; dedupe only per the written rules (don't widen). Budgets: Firecrawl ≤35, WebSearch ≤60, no parallel sub-agents, cross-check ≤3 fetches/item. Done = report written AND committed+pushed (`daily: YYYY-MM-DD report`).

For backfills/special runs, append an override block: fixed DATE/window, "harvest already done", distinct output names (e.g. `-v64`, `-special`), forbid touching official files/inventory as needed, no commit/push.

---

## 12. Version history & rationale (why the rules look like this)

- v5.x: repo-portable rules; launchd; Actions for Telegram/Email; Firecrawl cut to protect quota; rotation 8/day.
- v6.0 (9/22): 3-stage collection (discover → score → verify selected); B+E+R+T scoring; caps; "core 8 list pages". Problem: core sites were industry news, not slot channels; CasinoBeats dead since 9/4, Gambling Insider pivoted to sports.
- v6.1 (9/23): list pages must use markdown (summary returned no items).
- v6.2 (9/24): primary-source date rule after DigiPlus 2025 news leaked in.
- v6.4 (9/27): harvest.py (feeds, exact times), layer-2 slot DB sites, inventory, PH redefinition, xlsx columns. Evidence: 9/23–9/26 our env caught 1 of 12 big-brand launches; 9/27 published 1 item when 4–7 qualified; iGB list parsing failed repeatedly.
- v6.4.2 (9/27): three triggers for regulators/associations/exhibitions; xlsx 觸發關鍵字 + 展期 columns; SBC Summit and iGB Live added; OutputLogic page rewritten.
- v6.4.1 (9/27): weekday 5 / weekend 2; fill only when ≤3; previews >7 days excluded; Saturday Weekend Reels checkpoint; iGamingToday secondary; cat2–5 must stock 1/day.
- Old machine v4.1 comparison: search-first (WebSearch + "brand + RTP max win reels" queries hitting slot DBs), rotation 30/day, 從寬 date acceptance, cat1 fixed 5. Produced more slots but included out-of-window items and unreleased previews (e.g., 9/27: 7 of 13 outside window; slot entries were reviews of games releasing Oct–Dec). Neither environment is a gold standard.

---

## 13. Open issues / next decisions

1. Exception for "new development of a story shown ≤3 days ago" (MGM case) — undecided.
2. Items judged placeholders (BigWinBoard TBC pages) still entered inventory — consider auto-reject rule.
3. Email for the company line not wired; cutover plan (delete `telegram-test-0640.yml`, use `telegram-0630.yml`, run on main) pending.
4. Mac sleep risk; consider pmset wake or cloud scheduling (Routines not available on the company account's UI).
5. Firecrawl budget: ~25–30/day steady state; heavy backfills consume quickly.
6. harvest md can be large on high-volume days (~100 KB); acceptable but watch context.
7. PH platform promos often exist only on Facebook/IG/app; not reliably scrapable.

---

## 13.5 Public docs page (OutputLogic)
`https://igaming-pulse.github.io/igaming-daily/OutputLogic/` is generated by `scripts/build_outputlogic.py` (on test-publish): architecture text, 5 mermaid flowcharts, tools table, triggers table, categories, scoring, and the full source table (with 抓取方式/頻率/展期) read from the xlsx. After changing rules or sources: run it, then copy `OutputLogic/index.html` and `OutputLogic.md` to `main`. Mermaid gotcha: every node label must close with `"]`; verify in a browser that each `pre.mermaid` renders an SVG without "Syntax error".

## 14. Operating commands (reference)

```bash
python3 scripts/sync_sources.py                       # xlsx → sources.md
python3 scripts/harvest.py                            # today, window = now-24h
python3 scripts/harvest.py --date 2026-09-26 --anchor 02:30 [--no-firecrawl] [--plan]
python3 scripts/build_outputlogic.py                  # regenerate OutputLogic page
python3 scripts/rotate_sources.py [--date D]
python3 scripts/inventory.py show --date D
python3 scripts/inventory.py update --date D --file state/inventory-picks-D.json
bash scripts/run_daily.sh                             # full manual run
curl -s https://api.firecrawl.dev/v1/team/credit-usage -H "Authorization: Bearer $FIRECRAWL_API_KEY"
```
