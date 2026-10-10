# iGaming Daily Report — 資訊來源清單（共 233 個來源）

> 核心關注：Game Provider 產品動向、玩法設計、營運調整；盤口平台動態；市場數據與趨勢。
> ⚠️ 本檔由 `sources/igaming-daily-report-sources-v2.xlsx` 自動產生。
> **勿手動編輯本檔** —— 要改來源請改 xlsx，然後跑 `python3 scripts/sync_sources.py`。
> 抓取時依當日題材跨分類取材；「已停用」分類不要抓。
> v6.4：「抓取方式」WP-API／RSS 由 `scripts/harvest.py` 每天自動收集（不花 Firecrawl）；
>       「Firecrawl／每日」是第二層固定抓；「Firecrawl／輪掃」由 `rotate_sources.py` 每天輪 3 個；
>       「每週／事件」＝事件觸發（當天新聞提到觸發關鍵字，每個關鍵字每週最多一次）＋每週一固定輪 3 個；
>       「行事曆」＝展會，開展前 14 天到閉展日每天抓（每天最多 2 個）。

---

## Provider 官網（27）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| Pragmatic Play | https://pragmaticplay.com/en/news/ | WP-API | 每日 | https://pragmaticplay.com/wp-json/wp/v2/posts |  |  | Provider 官網 |
| PG Soft | https://pgsoft.com/en/news/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Jili | https://jiligames.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Play'n GO | https://www.playngo.com/ | Sitemap | 每日 | https://www.playngo.com/sitemap.xml |  |  | Provider 官網；v6.5.2 官網改 Wix、RSS 消失 → 改抓 sitemap（/games/ 的日期＝上線日，/post/ 為新聞） |
| NetEnt | https://www.netent.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Red Tiger Gaming | https://redtiger.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Spribe | https://spribe.co/ | Firecrawl | 輪掃 |  |  |  | Provider 官網（Crash 代表廠商） |
| POP Ok (Popok Gaming) | https://www.popokgaming.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Big Pot Gaming | https://www.bigpotgaming.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Hacksaw Gaming | https://hacksawgaming.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Nolimit City | https://nolimitcity.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Thunderkick | https://www.thunderkick.com/ | WP-API | 每日 | https://www.thunderkick.com/wp-json/wp/v2/posts |  |  | Provider 官網 |
| Big Time Gaming (BTG) | https://www.bigtimegaming.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Yggdrasil Gaming | https://www.yggdrasilgaming.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網；⭐優先展示品牌 |
| Betsoft Gaming | https://www.betsoft.com/ | RSS | 每日 | https://betsoft.com/feed/ |  |  | Provider 官網 |
| Fantasma Games | https://fantasmagames.com/ | RSS | 每日 | https://fantasmagames.com/feed/ |  |  | Provider 官網 |
| ELK Studios | https://elkstudios.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Print Studios | https://www.printstudios.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Relax Gaming | https://www.relaxgaming.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| 4ThePlayer | https://4theplayer.com/ | WP-API | 每日 | https://4theplayer.com/wp-json/wp/v2/posts |  |  | Provider 官網 |
| AvatarUX | https://avatarux.com/ | WP-API | 每日 | https://avatarux.com/wp-json/wp/v2/posts |  |  | Provider 官網 |
| Kalamba Games | https://kalambagames.com/ | Firecrawl | 輪掃 | https://kalambagames.com/ |  |  | Provider 官網；v6.5.2 網站加了機器人驗證（curl 被擋）→ 改 Firecrawl 輪掃 |
| Peter & Sons | https://peterandsonsgames.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| CP Game | https://cpgames.com/ | Firecrawl | 輪掃 |  |  |  | Provider 官網 |
| Acewin | https://www.acewin168.com/ | Firecrawl | 輪掃 |  |  |  | ★優先追蹤｜IGS鈊象電子旗下 GP；可視為 Jili 低配版、多款與 Jili 互通，B 端價格有優勢。上新遊戲於 DigiPlus 系(BingoPlus/ArenaPlus/GameZone)或 CasinoPlus 等菲現金網、或特別線上/線下活動與平台功能更新→提高露出權重 |
| Omiplay | https://omiplay.com/ | Firecrawl | 輪掃 |  |  |  | ★優先追蹤｜台灣尊博集團 GP；Super Gem 對標 Fortune Gem 成功、獲 BingoPlus/CasinoPlus 內部認可、菲律賓有成績。上新遊戲於 DigiPlus 系/CasinoPlus 或特別活動/平台更新→提高露出權重 |
| YellowBat | https://www.yellowbat.com/games/ | WP-API | 每日 | https://www.yellowbat.com/wp-json/wp/v2/posts |  |  | ★優先追蹤｜菲律賓平台 PlayTime 深度策略夥伴。上新遊戲於 DigiPlus 系/CasinoPlus/PlayTime 或特別活動/平台更新→提高露出權重 |

---

## 產品分析／評測（13）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| Clash of Slots | https://clashofslots.com | WP-API | 每日 | https://clashofslots.com/wp-json/wp/v2/posts |  |  | bonus hit rate、variance、max multiplier 統計 |
| SlotCatalog — New Games | https://slotcatalog.com/en/slots/new | Firecrawl | 輪掃 |  |  |  | 全站新遊戲上線清單 |
| SlotCatalog — Jili | https://slotcatalog.com/en/soft/Jili | Firecrawl | 輪掃 |  |  |  | Jili 新遊戲、RTP、volatility 數據 |
| SlotCatalog — PG Soft | https://slotcatalog.com/en/soft/PG-Soft | Firecrawl | 輪掃 |  |  |  | PG Soft 新遊戲、機制數據 |
| SlotCatalog — Pragmatic Play | https://slotcatalog.com/en/soft/Pragmatic-Play | Firecrawl | 輪掃 |  |  |  | PP 新遊戲、機制數據，含待發布排程 |
| Casino Guru | https://casino.guru | Firecrawl | 輪掃 |  |  |  | 遊戲機制解析、Provider 評測、玩家投訴資料庫 |
| AskGamblers | https://www.askgamblers.com | Firecrawl | 輪掃 |  |  |  | Slot variance 分析、Provider 評論 |
| iGamingToday | https://www.igamingtoday.com | Firecrawl | 每日 | https://www.igamingtoday.com/ |  |  | Provider 新聞角度的評測與分析 |
| Gamingsoft Blog | https://www.gamingsoft.com/blog/ | WP-API | 每日 | https://www.gamingsoft.com/blog/wp-json/wp/v2/posts |  |  | B2B 視角 Provider 評測，關注營運整合 |
| EZ Slot Design | https://ezslotdesign.com/ | RSS | 每日 | https://ezslotdesign.com/rss/ |  |  | Slot 遊戲設計分析，設計師視角拆解玩法機制 |
| P-WORLD | https://www.p-world.co.jp/ | Firecrawl | 輪掃 |  |  |  | 日本遊技機資料庫；子頁 introduce_calendar.cgi 為★新台上市日期／規格／導入店數，日本機種情報最關鍵單一來源 |
| BigWinBoard | https://www.bigwinboard.com/new-slots/ | 程式解析 | 每日 | https://www.bigwinboard.com/new-slots/ |  |  | Slot 資料庫站（v6.4 新增）；新作依上線日排序，大廠幾乎都有，含 RTP／最高倍率 |
| SlotsLaunch | https://slotslaunch.com/ | 程式解析 | 每日 | https://slotslaunch.com/calendar |  |  | Slot 資料庫站（v6.4 新增）；v6.5 改抓上線日曆（每款有上線日，免費） |

---

## 產業媒體（102）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| AGB（Asia Gaming Brief） | https://agbrief.com | RSS | 每日 | https://agbrief.com/feed/ |  |  | 東南亞 iGaming 專業媒體，Jili 報導最完整 |
| iGaming Business | https://igamingbusiness.com/news/ | WP-API | 每日 | https://igamingbusiness.com/wp-json/wp/v2/posts |  |  | Provider 合作、盤口動向、市場數據 |
| CasinoBeats | https://casinobeats.com | WP-API | 每日 | https://casinobeats.com/wp-json/wp/v2/posts |  |  | Provider 新遊戲、合作消息 |
| SBC News | https://sbcnews.co.uk | RSS | 每日 | https://sbcnews.co.uk/feed/ |  |  | 盤口動態、Provider 合作；v6.5 改用 RSS（10 則約 3 天，免費） |
| Gambling Insider | https://gamblinginsider.com/news/ | WP-API | 每日 | https://gamblinginsider.com/wp-json/wp/v2/posts |  |  | 盤口市場數據、M&A、財務動態 |
| Yogonet International | https://www.yogonet.com/international/ | RSS | 每日 | https://www.yogonet.com/international/rss.xml |  |  | 全球市場動態、M&A（每日主力來源之一） |
| EGR Global | https://egr.global/news/ | RSS | 每日 | https://www.egr.global/feed/ |  |  | 盤口排名、Provider 表現 |
| Business of iGaming | https://www.businessofigaming.com/provider-power-ranking/ | WP-API | 每日 | https://www.businessofigaming.com/wp-json/wp/v2/posts |  |  | Provider 市場佔比 power ranking |
| iGaming Expert | https://igamingexpert.com | RSS | 每日 | https://igamingexpert.com/feed/ |  |  | Provider 動態新聞 |
| iGaming.news — Slots | https://igaming.news/category/slots/ | Firecrawl | 輪掃 |  |  |  | Slot 分類快訊 |
| Yogonet — Pragmatic Play 專頁 | https://www.yogonet.com/international/topics/pragmatic-play/ | Firecrawl | 輪掃 |  |  |  | 按 Provider 分類的新聞彙整 |
| CDC Gaming | https://cdcgaming.com/ | WP-API | 每日 | https://cdcgaming.com/wp-json/wp/v2/posts |  |  | 美國博彩媒體，含 Provider 與市場報導 |
| NEXT.io | https://next.io/news/ | Firecrawl | 輪掃 |  |  |  | 業內分析，含 Provider 產品設計深度文章 |
| Stake Blog | https://stake.com/blog | Firecrawl | 輪掃 |  |  |  | 現金網官方公告，需瀏覽器模式抓取 |
| iGB – Casino Games | https://igamingbusiness.com/casino-games/ | WP-API | 每日 | https://igamingbusiness.com/wp-json/wp/v2/posts |  |  | Slot／Provider 產品線報導；iGaming Business 子版 |
| iGB – Publications | https://igamingbusiness.com/publications/ | WP-API | 每日 | https://igamingbusiness.com/wp-json/wp/v2/posts |  |  | iGaming Business 深度專刊庫 |
| SBC Americas | https://sbcamericas.com/ | RSS | 每日 | https://sbcamericas.com/feed/ |  |  | SBC News 北美／LatAm 版 |
| EGR Intel | https://www.egr.global/intel/ | RSS | 每日 | https://www.egr.global/intel/feed/ |  |  | EGR Global 深度分析／高階訪談 |
| Gaming Intelligence | https://www.gamingintelligence.com/ | WP-API | 每日 | https://www.gamingintelligence.com/wp-json/wp/v2/posts |  |  | 高階產業情報媒體 |
| Global Gaming Insider | https://globalgaminginsider.com/ | Firecrawl | 輪掃 |  |  |  | B2B／供應商動態 |
| InterGame Online | https://www.intergameonline.com/ | Firecrawl | 輪掃 |  |  |  | Online＋Land-based 綜合報導 |
| InterGame – iGaming Products | https://www.intergameonline.com/igaming/products | Firecrawl | 輪掃 |  |  |  | 線上 Slot 新品發表（與 cat1 高度對應） |
| InterGame – Land-based Products | https://www.intergameonline.com/land-based-gaming/products | Firecrawl | 輪掃 |  |  |  | 實體機台／Cabinet 新品發表 |
| G3 Newswire | https://g3newswire.com/ | WP-API | 每日 | https://g3newswire.com/wp-json/wp/v2/posts |  |  | 全球供應商／機台新聞，含 Aristocrat、L&W、IGT 等新品；子頁 g3newswire.com/magazines/ 為深度雜誌 |
| GGB Magazine | https://ggbmagazine.com/ | Firecrawl | 輪掃 |  |  |  | 北美實體 Slot／Casino Floor；子頁 /publications/ 與 /publications/ggb-magazine/ 為專刊庫 |
| Focus Gaming News | https://focusgn.com/ | RSS | 每日 | https://focusgn.com/feed |  |  | Provider 新遊戲更新速度快；另有地區版 Africa／Asia Pacific／Brasil／Latinoamérica（見下列各行） |
| Gaming International Online | https://gaminginternational.online/ | WP-API | 每日 | https://gaminginternational.online/wp-json/wp/v2/posts |  |  | Slot、game development 專題 |
| Casino International | https://casinointernational-online.com/ | WP-API | 每日 | https://casinointernational-online.com/wp-json/wp/v2/posts |  |  | 實體 Slot／Supplier 報導 |
| Casino Life Magazine | https://www.casinolifemagazine.com/ | RSS | 每日 | https://www.casinolifemagazine.com/rss.xml |  |  | Casino／Supplier 產業雜誌 |
| Gaming & Leisure | https://mygamingandleisure.com/ | WP-API | 每日 | https://mygamingandleisure.com/wp-json/wp/v2/posts |  |  | Casino Technology 報導 |
| Indian Gaming | https://www.indiangaming.com/ | WP-API | 每日 | https://www.indiangaming.com/wp-json/wp/v2/posts |  |  | 北美 Tribal Casino；子頁 /magazine/ 為雜誌版 |
| iGaming Future | https://igamingfuture.com/ | RSS | 每日 | https://igamingfuture.com/feed/ |  |  | Technology／Product 報導；子頁 /category/casino/ 為 Casino／Slot 專區（優先級較高） |
| iGaming Enquirer | https://igamingenquirer.com/ | WP-API | 每日 | https://igamingenquirer.com/wp-json/wp/v2/posts |  |  | B2B／訪談；子頁 /news/ 為 Supplier／Product 新聞 |
| Times of Casino | https://www.timesofcasino.com/ | RSS | 每日 | https://www.timesofcasino.com/feed/ |  |  | Slot Launch 報導 |
| Casino Guru News | https://casino.guru/news | Firecrawl | 輪掃 |  |  |  | Casino Guru 新聞版（與已收錄的 Casino Guru 評測庫互補） |
| Casino Guru Interviews | https://casino.guru/news/in-depth/interviews | Firecrawl | 輪掃 |  |  |  | Provider 高階主管長訪，格式獨特 |
| Casino Reports | https://www.casinoreports.com/ | RSS | 每日 | https://www.casinoreports.com/rss.xml |  |  | 北美 iGaming 報導；子頁 /news/ 為新聞版 |
| Casino Reports Canada | https://www.casinoreports.ca/category/casino-news/ | WP-API | 每日 | https://www.casinoreports.ca/wp-json/wp/v2/posts |  |  | 加拿大 Online Casino 專版 |
| European Gaming | https://europeangaming.eu/portal/ | RSS | 每日 | https://europeangaming.eu/portal/feed/ |  |  | 歐洲 B2B 產業媒體 |
| SiGMA News | https://sigma.world/news/ | Firecrawl | 輪掃 |  |  |  | SiGMA 新聞版（既有清單僅收錄展會頁）；另有繁中／俄語版 |
| Yogonet Latinoamérica | https://www.yogonet.com/latinoamerica/ | Firecrawl | 輪掃 |  |  |  | Yogonet 拉美版 |
| Yogonet Brasil | https://www.yogonet.com/brasil/ | Firecrawl | 輪掃 |  |  |  | Yogonet 巴西版（PT-BR） |
| SoloAzar | https://www.soloazar.com/ | RSS | 每日 | https://soloazar.com/es/feed |  |  | 西語／英語拉美博彩媒體 |
| Zona de Azar | https://zonadeazar.com/ | WP-API | 每日 | https://zonadeazar.com/wp-json/wp/v2/posts |  |  | LatAm Provider、Game launch 報導 |
| InfoPlay | https://www.infoplay.info/ | Firecrawl | 輪掃 |  |  |  | 西語博彩媒體 |
| AZARplus | https://www.azarplus.com/ | WP-API | 每日 | https://www.azarplus.com/wp-json/wp/v2/posts |  |  | 西語博彩媒體 |
| Sector del Juego | https://sectordeljuego.com/ | WP-API | 每日 | https://sectordeljuego.com/wp-json/wp/v2/posts |  |  | 西語博彩產業媒體 |
| El Recreativo | https://www.elrecreativo.com/ | Firecrawl | 輪掃 |  |  |  | 西語 Land-based 報導 |
| Revista Casino Perú | https://www.revistacasinoperu.com/ | WP-API | 每日 | https://www.revistacasinoperu.com/wp-json/wp/v2/posts |  |  | 秘魯／拉美博彩雜誌 |
| Revista Apuesta Colombia | https://apuestacolombia.com.co/ | WP-API | 每日 | https://apuestacolombia.com.co/wp-json/wp/v2/posts |  |  | 哥倫比亞博彩雜誌 |
| SBC Noticias | https://sbcnoticias.com/ | RSS | 每日 | https://sbcnoticias.com/feed/ |  |  | SBC News 西語版；子頁 /br/ 為巴西葡語版 |
| SBC Notícias Brasil | https://sbcnoticias.com/br/ | RSS | 每日 | https://sbcnoticias.com/feed/ |  |  | SBC News 巴西葡語版 |
| iGaming Brazil | https://igamingbrazil.com/ | RSS | 每日 | https://igamingbrazil.com/feed/ |  |  | 巴西 iGaming 專業媒體 |
| Games Magazine Brasil | https://gamesbras.com/ | Firecrawl | 輪掃 |  |  |  | 巴西遊戲產業雜誌 |
| GiocoNews | https://www.gioconews.it/ | WP-API | 每日 | https://www.gioconews.it/wp-json/wp/v2/posts |  |  | 義大利博彩媒體 |
| AGIMEG | https://www.agimeg.it/ | WP-API | 每日 | https://www.agimeg.it/wp-json/wp/v2/posts |  |  | 義大利博彩媒體 |
| AgiproNews | https://www.agipronews.it/ | RSS | 每日 | https://www.agipronews.it/rss |  |  | 義大利 Slot、Provider 排名；子頁 /slot-e-vlt/ 為 Slot／VLT 專區 |
| PressGiochi | https://www.pressgiochi.it/ | WP-API | 每日 | https://www.pressgiochi.it/wp-json/wp/v2/posts |  |  | 義大利博彩媒體 |
| Online Gambling Quarterly | https://www.ogqnews.com/ | WP-API | 每日 | https://www.ogqnews.com/wp-json/wp/v2/posts |  |  | 英語歐洲研究型季刊 |
| AutomatenMarkt | https://www.automatenmarkt.de/ | RSS | 每日 | https://www.automatenmarkt.de/rss |  |  | 德國實體 Gaming 媒體 |
| AutomatenMarkt – Produkte | https://www.automatenmarkt.de/produkte | RSS | 每日 | https://www.automatenmarkt.de/rss |  |  | ★德國新機／Field Test 專區，最具追蹤價值 |
| Games & Business | https://www.gamesundbusiness.de/ | WP-API | 每日 | https://www.gamesundbusiness.de/wp-json/wp/v2/posts |  |  | 德國 B2B 媒體 |
| ISA-GUIDE | https://www.isa-guide.de/ | WP-API | 每日 | https://www.isa-guide.de/wp-json/wp/v2/posts |  |  | 德語 Casino 媒體 |
| Journal des Casinos | https://www.journaldescasinos.com/ | Firecrawl | 輪掃 |  |  |  | 法國 Casino B2B 媒體 |
| LesCasinos.org | https://www.lescasinos.org/ | RSS | 每日 | http://www.lescasinos.org/rss/flux.xml |  |  | 法國 Casino 媒體 |
| CasinoNieuws.nl | https://www.casinonieuws.nl/ | Firecrawl | 輪掃 |  |  |  | 荷蘭博彩媒體 |
| Gaming in Holland | https://gaminginholland.com/ | Firecrawl | 輪掃 |  |  |  | 荷蘭／英語博彩媒體 |
| GBC Time | https://gbc-time.com/ | Firecrawl | 輪掃 |  |  |  | 英／俄／烏語博彩媒體 |
| Casino Inside Romania | https://casinoinside.ro/ | Firecrawl | 輪掃 | https://casinoinside.ro/ |  |  | 羅馬尼亞博彩媒體；v6.5.2 網站加了機器人驗證（curl 被擋）→ 改 Firecrawl 輪掃 |
| Casino Life & Business Romania | https://www.casino-life.ro/ | Firecrawl | 輪掃 |  |  |  | 羅馬尼亞／中東歐博彩媒體 |
| Interplay Poland | https://interplay.pl/ | WP-API | 每日 | https://interplay.pl/wp-json/wp/v2/posts |  |  | 波蘭博彩媒體 |
| GreenBelt | https://web-greenbelt.jp/ | WP-API | 每日 | https://web-greenbelt.jp/wp-json/wp/v2/posts |  |  | 日本 Pachislot 媒體；子頁 /category/machine/ 為新台專區（優先級最高） |
| Amusement Japan | https://amusement-japan.co.jp/ | Firecrawl | 輪掃 |  |  |  | 日本業界月刊 |
| 遊技日本 | https://yugi-nippon.com/ | Firecrawl | 輪掃 |  |  |  | Pachinko／Slot 綜合媒體；子頁 /pachinko-pachislot-kentei/ 為新機審查／型號資訊 |
| PiDEA X | https://www.pidea.jp/ | Firecrawl | 輪掃 |  |  |  | 日本產業媒體 |
| 遊技通信 | https://www.yugitsushin.jp/ | WP-API | 每日 | https://www.yugitsushin.jp/wp-json/wp/v2/posts |  |  | 日本 B2B 媒體 |
| パチンコビレッジ | https://www.pachinkovillage.com/ | Firecrawl | 輪掃 |  |  |  | 日本機種／玩法媒體 |
| 情報島 | https://johojima.com/ | Firecrawl | 輪掃 |  |  |  | 日本 Hall／新機資訊 |
| PlayGraph | https://www.play-graph.com/ | Firecrawl | 輪掃 |  |  |  | 日本遊技專門誌 |
| Pachinko Media Portal | https://www.pmp-paa.com/ | Firecrawl | 輪掃 |  |  |  | 日本業界情報入口網 |
| GGRAsia | https://www.ggrasia.com/ | WP-API | 每日 | https://www.ggrasia.com/wp-json/wp/v2/posts |  |  | 澳門／亞洲 Casino floor 報導 |
| Inside Asian Gaming | https://www.asgam.com/ | RSS | 每日 | https://asgam.com/feed/ |  |  | 亞洲供應商、機台、展會報導；v6.5 改用 RSS（10 則約 3 天，免費） |
| AGB Macau | https://agbrief.com/category/news/macau/ | RSS | 每日 | https://agbrief.com/feed/ |  |  | AGB 澳門專版 |
| AGB Philippines | https://agbrief.com/category/news/philippines/ | RSS | 每日 | https://agbrief.com/feed/ |  |  | ★AGB 菲律賓專版，直接對應本報告 🇵🇭 分類 |
| AGB Vietnam | https://agbrief.com/category/news/vietnam/ | RSS | 每日 | https://agbrief.com/feed/ |  |  | AGB 越南專版 |
| Macau Business | https://www.macaubusiness.com/ | Firecrawl | 輪掃 |  |  |  | 澳門商業／博彩媒體（EN／PT） |
| Macau Daily Times | https://macaudailytimes.com.mo/ | Firecrawl | 輪掃 |  |  |  | 澳門日報英文版 |
| iGaming AFRIKA | https://igamingafrika.com/ | WP-API | 每日 | https://igamingafrika.com/wp-json/wp/v2/posts |  |  | 非洲 B2B 媒體 |
| AGE Insight | https://insight.ageafrique.org/ | WP-API | 每日 | https://insight.ageafrique.org/wp-json/wp/v2/posts |  |  | 非洲市場分析子站 |
| Gaming for Africa | http://www.gfamagazine.com/ | Firecrawl | 輪掃 |  |  |  | 非洲 B2B 雜誌 |
| Find More Africa | https://findmoreafrica.com/ | WP-API | 每日 | https://findmoreafrica.com/wp-json/wp/v2/posts |  |  | 非洲博彩媒體；子頁含東非專版 |
| Focus Gaming News Africa | https://focusgn.com/category/africa | RSS | 每日 | https://focusgn.com/feed |  |  | Focus Gaming News 非洲版 |
| Focus Asia Pacific iGaming | https://focusgn.com/asia-pacific/category/igaming-news | RSS | 每日 | https://focusgn.com/feed |  |  | ★Focus Gaming News 亞太版，對應本報告亞洲焦點 |
| Focus Gaming News Brasil | https://focusgn.com/brasil/ | RSS | 每日 | https://focusgn.com/feed |  |  | Focus Gaming News 巴西版 |
| Focus Gaming News Latinoamérica | https://focusgn.com/latinoamerica/ | RSS | 每日 | https://focusgn.com/feed |  |  | Focus Gaming News 拉美西語版 |
| SlotBeats | https://slotbeats.com/ | WP-API | 每日 | https://slotbeats.com/wp-json/wp/v2/posts |  |  | iGaming/Slot 新聞媒體，新老虎機上線與供應商動態報導快、覆蓋廣；交叉查證 Slot 新遊戲的重點來源之一 |
| GMA News | https://www.gmanetwork.com/news/ | RSS | 每日 | https://www.gmanetwork.com/rss |  |  | 菲律賓在地媒體（v6.4 新增）；全站 RSS，需用博弈關鍵字過濾 |
| Rappler | https://www.rappler.com/ | WP-API | 每日 | https://www.rappler.com/wp-json/wp/v2/posts |  |  | 菲律賓在地媒體（v6.4 新增）；WP API，需用博弈關鍵字過濾 |
| SunStar | https://www.sunstar.com.ph/ | RSS | 每日 | https://www.sunstar.com.ph/feed/ |  |  | 菲律賓在地媒體（v6.4 新增）；需用博弈關鍵字過濾 |
| BusinessWorld | https://www.bworldonline.com/ | RSS | 每日 | https://bworldonline.com/feed/ |  |  | 菲律賓財經媒體（v6.4 新增）；DigiPlus／Bloomberry 等上市公司動態 |
| DigiPlus | https://digiplus.com.ph/news/ | RSS | 每日 | https://digiplus.com.ph/feed/ |  |  | ★DigiPlus 官網新聞（v6.4 新增）；BingoPlus／ArenaPlus／GameZone 主來源 |
| EEGaming（Recent Slot Releases） | https://eegaming.org/category/recent-slot-releases | RSS | 每日 | https://eegaming.org/feed |  |  | Slot 新作通稿集中地（v6.4 新增）；每週五另有 Weekend Reels 整理；v6.5 改用全站 RSS（精確發布時間、免費） |

---

## 產業協會／技術認證機構（23）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| AGEM Index | https://www.agem.org/agem-index/ | WP-API | 每日 | https://www.agem.org/wp-json/wp/v2/posts |  |  | 美國博彩設備商協會（AGEM）產業指數 |
| AGEM News | https://www.agem.org/news/ | WP-API | 每日 | https://www.agem.org/wp-json/wp/v2/posts |  |  | AGEM 新聞版 |
| GLI Standards | https://gaminglabs.com/gli-standards/ | RSS | 每日 | https://gaminglabs.com/feed/ |  |  | Gaming Laboratories International 技術標準；子頁 /igaming/igaming-technical-standards/ 與中文版為 iGaming 專屬技術標準 |
| International Gaming Standards Association | https://igsa.org/ | WP-API | 每日 | https://igsa.org/wp-json/wp/v2/posts |  |  | 博彩通訊協定國際標準組織 |
| BMM Testlabs | https://bmm.com/ | Firecrawl | 每週／事件 |  | BMM Testlabs |  | 第三方遊戲測試／認證機構 |
| American Gaming Association Research | https://www.americangaming.org/research/ | RSS | 每日 | https://www.americangaming.org/feed/ |  |  | 美國博彩協會（AGA）研究部門 |
| AGA State of the States | https://www.americangaming.org/resources/state-of-the-states/ | RSS | 每日 | https://www.americangaming.org/feed/ |  |  | AGA 年度旗艦市場報告 |
| Jdigital | https://www.jdigital.es/ | WP-API | 每日 | https://www.jdigital.es/wp-json/wp/v2/posts |  |  | 西班牙數位博彩產業協會 |
| ANESAR | https://www.anesar.com/ | WP-API | 每日 | https://www.anesar.com/wp-json/wp/v2/posts |  |  | 西班牙遊藝廳／自動機協會 |
| CEJUEGO | https://cejuego.com/ | RSS | 每日 | https://cejuego.com/feed/ |  |  | 西班牙博彩業聯合會 |
| Club de Convergentes | https://clubdeconvergentes.es/ | WP-API | 每日 | https://clubdeconvergentes.es/wp-json/wp/v2/posts |  |  | 西班牙機台供應鏈俱樂部 |
| JAMMA | https://www.jamma.it/ | WP-API | 每日 | https://www.jamma.it/wp-json/wp/v2/posts |  |  | 義大利娛樂機台協會；子頁 /apparecchi-intrattenimento 為設備分類頁 |
| Sistema Gioco Italia | https://sistemagiocoitalia.it/ | Firecrawl | 每週／事件 |  | Sistema Gioco Italia |  | 義大利博彩產業協會 |
| Deutsche Automatenwirtschaft | https://www.automatenwirtschaft.de/ | WP-API | 每日 | https://www.automatenwirtschaft.de/wp-json/wp/v2/posts |  |  | 德國機台產業協會 |
| VDAI | https://www.vdai.de/ | Firecrawl | 每週／事件 |  | \bVDAI\b |  | 德國機台製造商協會 |
| Casinos de France | https://casinos.fr/ | WP-API | 每日 | https://casinos.fr/wp-json/wp/v2/posts |  |  | 法國賭場協會 |
| 日本電動式遊技機工業協同組合 | https://www.nichidenkyo.or.jp/ | RSS | 每日 | https://www.nichidenkyo.or.jp/feed/ |  |  | 日本 Pachislot 廠商協同組合 |
| 日本遊技機工業組合 | https://nikkoso.jp/ | RSS | 每日 | https://nikkoso.jp/feed/ |  |  | 日本遊技機製造商工業組合 |
| Korea Casino Association | https://www.koreacasino.or.kr/ | Firecrawl | 每週／事件 |  | Korea Casino Association |  | 韓國賭場協會 |
| Gaming Technologies Association | https://www.gamingta.com/ | WP-API | 每日 | https://www.gamingta.com/wp-json/wp/v2/posts |  |  | 澳洲機台製造商協會 |
| Australasian Gaming Council | https://austgamingcouncil.org.au/ | Firecrawl | 每週／事件 |  | Australasian Gaming Council |  | 澳洲博彩產業研究協會 |
| AIEJA | https://aieja.org.mx/ | Firecrawl | 每週／事件 |  | AIEJA |  | 墨西哥博彩產業協會 |
| CIBELAE | https://cibelae.net/ | WP-API | 每日 | https://cibelae.net/wp-json/wp/v2/posts |  |  | 拉丁美洲暨伊比利半島博彩監理機關聯盟（監理機關組成的跨國協會） |

---

## 市場數據／分析公司（18）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| Eilers & Krejcik Gaming（新網域） | https://ekgamingllc.com/ | Firecrawl | 輪掃 |  |  |  | ★EKG 官方新網域（原 ekg.com 已停站，見既有清單「已停用」項）；子頁 /reports 為報告庫、/services/game-performance-analytics 為單款 Slot／Cabinet 真實績效服務 |
| Eilers-Fantini Game Performance Reports（各區域月報） | https://ekgamingllc.com/reports | Firecrawl | 輪掃 |  |  |  | 涵蓋 EMEA／LatAm／歐洲線上／美國線上／加拿大線上等區域月度 Slot／Cabinet 排名報告，逐月更新，請至 reports 頁查最新版而非收錄單一 PDF 連結 |
| UNLV Gaming Research & Review Journal | https://oasis.library.unlv.edu/grrj/ | Firecrawl | 輪掃 |  |  |  | 美國內華達大學拉斯維加斯分校博彩學術期刊，Slot 玩家與機率研究 |
| UNLV Gaming Research Infographics | https://oasis.library.unlv.edu/gaming_infographics/ | RSS | 每日 | https://oasis.library.unlv.edu/recent.rss |  |  | UNLV Gaming Statistics 圖表化摘要 |
| H2 Gambling Capital | https://h2gc.com/ | Firecrawl | 輪掃 |  |  |  | 全球博彩市場數據庫，付費情報服務 |
| Vixio | https://www.vixio.com/ | Firecrawl | 輪掃 |  |  |  | Market Intelligence／法規情報服務 |
| Regulus Partners | https://reguluspartners.com/ | Firecrawl | 輪掃 |  |  |  | 博彩產業策略顧問／情報 |
| Spectrum Gaming Group | https://spectrumgaming.com/ | Firecrawl | 輪掃 |  |  |  | Casino 產業顧問公司 |
| nQube Data Science | https://www.nqubedatascience.com/ | Firecrawl | 輪掃 |  |  |  | Slot Floor Analytics，實體機台效能分析 |
| Tangam Systems | https://www.tangamsystems.com/ | Firecrawl | 輪掃 |  |  |  | Casino Floor Analytics |
| Gaming Analytics | https://gaminganalytics.ai/ | Firecrawl | 輪掃 |  |  |  | AI／Slot Operations 分析服務 |
| Blask | https://blask.com/ | WP-API | 每日 | https://blask.com/wp-json/wp/v2/posts |  |  | Online Market Data 分析平台 |
| SOFTSWISS iGaming Trends | https://www.softswiss.com/igaming-trends/ | WP-API | 每日 | https://www.softswiss.com/wp-json/wp/v2/posts |  |  | SOFTSWISS 年度趨勢報告微站 |
| Gambling Research Australia | https://www.dss.gov.au/gambling/gambling-research/gambling-research-australia | Firecrawl | 輪掃 |  |  |  | 澳洲政府資助博彩學術研究計畫 |
| Australian Gambling Research Centre | https://aifs.gov.au/research/areas/gambling | Firecrawl | 輪掃 |  |  |  | 澳洲家庭研究院博彩研究中心 |
| BNLData | https://bnldata.com.br/ | WP-API | 每日 | https://bnldata.com.br/wp-json/wp/v2/posts |  |  | 巴西／拉美 Slot 市場數據；子頁 /category/slot/ 為 Slot 專區 |
| SLEC Africa Insights | https://www.slecafrica.com/insights | Firecrawl | 輪掃 |  |  |  | 非洲市場情報與分析 |
| Gambling Research – Skill-based Gaming Machines（PDF） | https://www.gamblingresearch.org.au/sites/default/files/2023-09/skill-based_gambling_in_australia_report_0.pdf | Firecrawl | 輪掃 |  |  |  | 澳洲 Skill-based EGM 專題研究報告（單一 PDF，非持續更新頁面） |

---

## 監理機關／官方數據（16）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| DGOJ Estudios e Informes | https://www.ordenacionjuego.es/participantes-juego/informacion-estudios | Firecrawl | 每週／事件 |  | DGOJ¦Ordenación del Juego |  | 西班牙官方博彩監理機關（DGOJ）研究與統計 |
| ADM Giochi | https://www.adm.gov.it/portale/giochi | Firecrawl | 每週／事件 |  | Agenzia delle Dogane¦\bADM\b |  | 義大利官方博彩監理機關（海關暨壟斷署） |
| ANJ Études et données | https://anj.fr/ | RSS | 每日 | https://anj.fr/rss.xml |  |  | 法國官方博彩監理機關（Autorité Nationale des Jeux） |
| Kansspelautoriteit | https://kansspelautoriteit.nl/ | RSS | 每日 | https://kansspelautoriteit.nl/feed/rss/nieuws |  |  | 荷蘭官方博彩監理機關 |
| Belgian Gaming Commission | https://www.gamingcommission.be/ | Firecrawl | 每週／事件 |  | Belgian Gaming Commission¦Kansspelcommissie |  | 比利時官方博彩監理機關 |
| Swiss Federal Gaming Board ESBK | https://www.esbk.admin.ch/ | Firecrawl | 每週／事件 |  | ESBK¦Swiss Federal Gaming Board |  | 瑞士聯邦博彩監理機關 |
| Macau DICJ | https://www.dicj.gov.mo/ | Firecrawl | 每週／事件 |  | DICJ¦Gaming Inspection and Coordination |  | 澳門官方博彩監察協調局 |
| PAGCOR Press Releases | https://www.pagcor.ph/press-releases/index.php | Firecrawl | 每週／事件 |  | PAGCOR |  | ★菲律賓官方監理機關新聞稿，直接對應本報告 🇵🇭 分類 |
| PAGCOR Annual Reports | https://www.pagcor.ph/transparency/annual-reports.php | Firecrawl | 每週／事件 |  |  |  | PAGCOR 年度報告，官方統計數據 |
| Coljuegos Sala de Prensa | https://www.coljuegos.gov.co/publicaciones/300016/sala-de-prensa/ | Firecrawl | 每週／事件 |  | Coljuegos |  | 哥倫比亞官方博彩監理機關新聞室 |
| MINCETUR Perú | https://www.gob.pe/mincetur | Firecrawl | 每週／事件 |  | MINCETUR |  | 秘魯外貿旅遊部（主管賭場）官方頁 |
| NSW Gaming Research Reports | https://www.nsw.gov.au/business-and-economy/liquor-and-gaming/resources/research-and-evaluation-reports | Firecrawl | 每週／事件 |  | NSW gaming research |  | 紐南威爾斯州政府博彩研究報告 |
| Liquor & Gaming NSW | https://www.liquorandgaming.nsw.gov.au/ | Firecrawl | 每週／事件 |  | Liquor (&¦and) Gaming NSW |  | 紐南威爾斯州官方博彩監理機關 |
| VGCCC | https://www.vgccc.vic.gov.au/ | Firecrawl | 每週／事件 |  | VGCCC¦Victorian Gambling and Casino Control |  | 維多利亞州官方博彩監理機關 |
| Queensland OLGR | https://www.business.qld.gov.au/industries/hospitality-tourism-sport/liquor-gaming | Firecrawl | 每週／事件 |  | \bOLGR\b¦Office of Liquor and Gaming |  | 昆士蘭州官方博彩監理機關 |
| New Zealand DIA Gambling | https://www.dia.govt.nz/Gambling | Firecrawl | 每週／事件 |  | Department of Internal Affairs¦New Zealand DIA |  | 紐西蘭官方博彩監理機關 |

---

## 展會（21）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| ICE Barcelona | https://www.icegaming.com | Firecrawl | 行事曆 |  |  | 2027-01-18~2027-01-20 | 每年 1 月，全球最大 iGaming 展，有 content hub |
| SiGMA | https://sigma.world | Firecrawl | 行事曆 |  |  | 2026-11-02~2026-11-05;2027-05-03~2027-05-05 | 多地區（Malta、Manila、Rome 等） |
| G2E Las Vegas | https://www.globalgamingexpo.com/ | Firecrawl | 行事曆 |  |  | 2026-09-28~2026-10-01;2027-09-27~2027-09-30 | 每年秋季，北美最大實體機台與 iGaming 展（官方網域 globalgamingexpo.com） |
| ASEAN Gaming Summit | https://aseangaming.com | Firecrawl | 行事曆 |  |  | 2027-03-15~2027-03-17 | 東南亞；2026 停辦，2027 回歸 Manila |
| Asia Gaming Awards | https://asiagamingawards.com | Firecrawl | 行事曆 |  |  | 2027-03-15~2027-03-17 | 追蹤亞洲 Provider 得獎動態 |
| ezslotdesign — Gaming Expos | https://ezslotdesign.com/gaming-expo/ | Firecrawl | 行事曆 | https://ezslotdesign.com/rss/ |  |  | 展會資訊彙整，含 slot 設計視角 |
| Asia Gaming Expo (AGE) | https://asiagaming-expo.com | Firecrawl | 行事曆 |  |  |  | 亞洲 Gaming 實體展會 |
| ICE Casino & Games | https://www.icegaming.com/about-ice/sectors/casino | Firecrawl | 行事曆 |  |  | 2027-01-18~2027-01-20 | ICE 展會 Casino／Slot 產業別頁面 |
| ICE Exhibitor Products | https://www.icegaming.com/exhibitor-product-listings/api-casino-games-integration | Firecrawl | 行事曆 |  |  | 2027-01-18~2027-01-20 | ICE 展商新品發表庫 |
| G2E Asia | https://www.g2easia.com/ | Firecrawl | 行事曆 |  |  | 2027-05-18~2027-05-20 | 亞洲實體 Casino／Slot 展會；子頁 en-gb/media/press-release.html 為新聞稿 |
| SiGMA Asia | https://sigma.world/summits/asia/ | Firecrawl | 行事曆 |  |  | 2027-05-31~2027-06-03 | SiGMA 亞洲分區峰會（含菲律賓 Manila）；另有繁中版 |
| GAT Expo | https://gatexpo.net/ | Firecrawl | 行事曆 | https://gatexpo.net/wp-json/wp/v2/posts |  | 2026-10-15~2026-10-15;2026-11-18~2026-11-18;2027-03-30~2027-04-01;2027-06-02~2027-06-03;2027-07-01~2027-07-02;2027-10-21~2027-10-21 | 西語／英語拉美展會 |
| Peru Gaming Show | https://www.perugamingshow.com/ | Firecrawl | 行事曆 | https://www.perugamingshow.com/wp-json/wp/v2/posts |  | 2027-06-16~2027-06-17 | 秘魯博彩展會 |
| SAGSE | https://sagse.lat/ | Firecrawl | 行事曆 |  |  | 2027-03-17~2027-03-18;2027-08-04~2027-08-06 | 拉美大型博彩展會 |
| Australasian Gaming Expo | https://austgamingexpo.com/ | Firecrawl | 行事曆 | https://austgamingexpo.com/wp-json/wp/v2/posts |  | 2027-08-10~2027-08-12 | 澳洲實體機台展會 |
| iGaming AFRIKA Summit | https://events.igasummit.com/ | Firecrawl | 行事曆 |  |  | 2027-05-04~2027-05-06 | 非洲博彩峰會 |
| Africa Gaming Expo | https://www.ageafrique.org/ | Firecrawl | 行事曆 | https://www.ageafrique.org/wp-json/wp/v2/posts |  | 2027-03-16~2027-03-19 | 非洲實體展會；子頁 /media/ 為報告／簡報下載庫 |
| SiGMA Africa | https://sigma.world/summits/africa/ | Firecrawl | 行事曆 |  |  | 2027-02-15~2027-02-17 | SiGMA 非洲分區峰會 |
| SiGMA South America | https://sigma.world/summits/south-america/ | Firecrawl | 行事曆 |  |  | 2027-04-05~2027-04-08 | SiGMA 南美分區峰會 |
| SBC Summit | https://sbcevents.com/sbc-summit/ | Firecrawl | 行事曆 |  |  | 2026-09-29~2026-10-01;2027-09-21~2027-09-23 | 里斯本，歐洲最大 iGaming／博彩 B2B 展之一（v6.4.2 新增） |
| iGB Live | https://www.igblive.com/ | Firecrawl | 行事曆 |  |  | 2027-07-07~2027-07-08 | 倫敦，iGaming Business 主辦（v6.4.2 新增） |

---

## 論壇／社群（6）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| r/slots | https://www.reddit.com/r/slots | Firecrawl | 每週／事件 |  |  |  | 玩家討論 slot 遊戲體驗、Provider 產品反應 |
| r/onlinegambling | https://www.reddit.com/r/onlinegambling | Firecrawl | 每週／事件 |  |  |  | 廣泛討論 Provider 與盤口體驗 |
| AskGamblers Forum | https://forum.askgamblers.com | Firecrawl | 每週／事件 |  |  |  | 玩家＋業內討論，含 Provider 投訴與產品反應 |
| Mr. Gamble 論壇 — Provider 板 | https://forum.mr-gamble.com/forum/4302-game-providers-exclusive-promos-news-discussions/ | Firecrawl | 每週／事件 |  |  |  | 專屬 Game Provider 討論板，含促銷與新聞 |
| About Slots 論壇 | https://forum.aboutslots.com/ | Firecrawl | 每週／事件 |  |  |  | Slot 玩家論壇 |
| Casinomeister 論壇 | https://www.casinomeister.com/forums/ | Firecrawl | 每週／事件 |  |  |  | 老牌業界論壇，玩家＋業內人士混合 |

---

## Podcast／影音（5）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| Clash of Slots YouTube | https://www.youtube.com/c/ClashofSlots | Firecrawl | 每週／事件 |  |  |  | 大量 slot 試玩，觀察 bonus 觸發與遊戲行為 |
| iGaming Business YouTube | https://www.youtube.com/user/iGamingBusiness1 | Firecrawl | 每週／事件 |  |  |  | B2B 產業訪談、Provider 趨勢分析 |
| iGB Podcast | https://igamingbusiness.com/podcasts/ | WP-API | 每日 | https://igamingbusiness.com/wp-json/wp/v2/posts |  |  | 市場分析，含 Provider 動態 |
| NEXT.io Podcast | https://podcasts.apple.com/gb/podcast/next-io-podcast/id1515442333 | Firecrawl | 每週／事件 |  |  |  | 業內領袖訪談，聚焦 iGaming 產業策略 |
| iGaming Pulse | https://podcasts.apple.com/us/podcast/igaming-pulse-trends-news-analysis/id1771798553 | Firecrawl | 每週／事件 |  |  |  | 產業趨勢與新聞分析 |

---

## 已停用（2）

| 名稱 | URL | 抓取方式 | 頻率 | 抓取端點 | 觸發關鍵字 | 展期 | 備註 |
|------|-----|------|------|------|------|------|------|
| CalvinAyre | （網站已停止營運） | 不抓 | 停用 |  |  |  | 網站已停止營運（2026-06-15 確認），不再抓取 |
| Eilers & Krejcik Gaming (EKG)｜舊網域 | https://ekg.com/news/ | 不抓 | 停用 |  |  |  | 舊網域已出售停站（2026-06-15 確認）；★本次比對發現公司已搬遷新網域 ekgamingllc.com，新網域資料已收錄於「市場數據／分析公司」分類，建議日後改用新網域 |
