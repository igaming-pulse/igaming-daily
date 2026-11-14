#!/usr/bin/env python3
"""
v6.5 回歸測試（2026-09-28）：改 scripts/ 底下任何程式前後都跑一次。

  python3 -m unittest discover -s tests -v

測試資料：
  tests/fixtures/reports/*.md                    過去 11 份日報原稿（2026-09-20～09-28，含多種舊寫法）
  tests/fixtures/expected_reports.json           每份的日期、各區則數、文末統計（解析結果快照）
  tests/fixtures/igamingtoday-2026-09-28.md      iGamingToday 列表頁（Huff N´Puff 漏收那天）
  tests/fixtures/slotslaunch-calendar-2026-09-28.html  SlotsLaunch 上線日曆
新增一份日報當測試資料：把 .md 複製進 reports/，再重跑快照（見 RUNBOOK「回歸測試」）。
"""
import glob
import json
import os
import re
import sys
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import finalize_report as F  # noqa: E402
import harvest as H  # noqa: E402
import inventory as INV  # noqa: E402
import report_lib as R  # noqa: E402


def theme_compatible(s):
    """與 main 分支 report_theme.py 的 compatible() 同一條件（網站樣式開關靠它判斷能不能套）。"""
    return all(k in s for k in ("<header>", 'class="date"')) and re.search(r'class="card c[1-5]"', s)


class TestReports(unittest.TestCase):
    def setUp(self):
        self.expected = json.load(open(os.path.join(FIX, "expected_reports.json"), encoding="utf-8"))
        self.files = sorted(glob.glob(os.path.join(FIX, "reports", "*.md")))

    def test_fixture_count(self):
        self.assertEqual(len(self.files), len(self.expected))

    def test_parse_matches_snapshot(self):
        for f in self.files:
            with self.subTest(f=os.path.basename(f)):
                with open(f, encoding="utf-8") as fh:
                    r = R.parse_md(fh.read())
                exp = self.expected[os.path.basename(f)]
                self.assertEqual(r["date"], exp["date"])
                self.assertEqual({s["cat"]: len(s["items"]) for s in r["sections"] if s["items"]}, exp["counts"])
                self.assertEqual(r["stats"], exp["stats"])

    def test_every_item_has_source_and_date(self):
        for f in self.files:
            r = R.parse_md(open(f, encoding="utf-8").read())
            for s in r["sections"]:
                for it in s["items"]:
                    with self.subTest(f=os.path.basename(f), item=it["title"][:30]):
                        self.assertTrue(it["sources"], "沒解析到來源連結")
                        self.assertRegex(it["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_render_is_theme_compatible(self):
        for f in self.files:
            r = R.parse_md(open(f, encoding="utf-8").read())
            if not any(s["items"] for s in r["sections"]):
                continue
            with self.subTest(f=os.path.basename(f)):
                out = R.render_html(r)
                self.assertTrue(theme_compatible(out))
                self.assertIn('class="stats-line"', out)
                self.assertNotIn("<p>---</p>", out)
                self.assertEqual(out.count('class="stats-line"'), 1)
                n = sum(len(s["items"]) for s in r["sections"])
                self.assertEqual(len(re.findall(r'class="card c[1-5]"', out)), n)

    def test_internal_section_not_rendered(self):
        r = R.parse_md(open(os.path.join(FIX, "reports", "2026-09-28-igaming-report.md"), encoding="utf-8").read())
        self.assertIn("來源日期紀錄", r["internal"])
        self.assertNotIn("來源日期紀錄", R.render_html(r))


class TestFuzzy(unittest.TestCase):
    SAME = [("Huff N' Puff Mansion", "Light & Wonder", "Huff N´Puff Mansion", "L&W"),
            ("Big Bass Vegas 1000", "Pragmatic Play", "Big Bass Vegas 1000 Slot", "Pragmatic"),
            ("The Traitors™: Fortune", "Games Global", "The Traitors: Fortune", ""),
            ("Lucky Mischief", "PG Soft", "Lucky Mischief", "PG"),
            ("Bao Zhu Zhao Fu Grand", "Light & Wonder", "Bao Zhu Zhao Fu Grand", "SG")]
    DIFF = [("Money Train 4", "Relax", "Money Train 5", "Relax Gaming"),
            ("Thor's Rage", "Red Tiger", "Thor's Rage 2", "Red Tiger"),
            ("Sugar Rush", "Pragmatic", "Sugar Rush", "Hacksaw"),
            ("Fortune Tiger", "PG Soft", "Fortune Ox", "PG Soft")]

    def test_same(self):
        for a in self.SAME:
            with self.subTest(a=a):
                self.assertTrue(R.same_item(*a))

    def test_diff(self):
        for a in self.DIFF:
            with self.subTest(a=a):
                self.assertFalse(R.same_item(*a))


class TestDateRules(unittest.TestCase):
    def run_check(self, cat, d, label="", day="2026-09-29"):
        qa = F.QA()
        F.check_date({"date": d, "label": label}, cat, date.fromisoformat(day), "t", qa)
        return qa

    def test_same_day_ok(self):
        self.assertFalse(self.run_check("cat3", "2026-09-28").errors)

    def test_old_news_blocked(self):
        self.assertTrue(self.run_check("cat3", "2026-09-25").errors)

    def test_inventory_fresh(self):
        self.assertFalse(self.run_check("cat1", "2026-09-23", "📦 近期新作（9/23 首見）").errors)
        self.assertTrue(self.run_check("cat1", "2026-09-20", "📦 近期新作（9/20 首見）").errors)
        self.assertTrue(self.run_check("cat3", "2026-09-25", "📦（9/25）").errors)

    def test_future_blocked(self):
        self.assertTrue(self.run_check("cat1", "2026-10-01").errors)


class TestHarvestParsers(unittest.TestCase):
    def test_igamingtoday(self):
        r = H.parse_igamingtoday(open(os.path.join(FIX, "igamingtoday-2026-09-28.md"), encoding="utf-8").read())
        titles = [x["title"] for x in r]
        self.assertGreaterEqual(len(r), 10)
        self.assertTrue(any("Huff N´Puff" in t for t in titles), "漏掉 Huff N´Puff（9/28 的漏收案例）")
        huff = next(x for x in r if "Huff N´Puff" in x["title"])
        self.assertEqual(huff["dt"].date().isoformat(), "2026-09-27")

    def test_slotslaunch(self):
        body = open(os.path.join(FIX, "slotslaunch-calendar-2026-09-28.html"), encoding="utf-8").read()
        r, err = H.fetch_slotslaunch(body)
        self.assertIsNone(err)
        self.assertGreaterEqual(len(r), 40)
        byname = {x["title"]: x for x in r}
        self.assertIn("Gates of Olympus 2500 — Pragmatic Play", byname)
        self.assertEqual(byname["Gates of Olympus 2500 — Pragmatic Play"]["dt"].date().isoformat(), "2026-09-28")
        self.assertIn("3 Lucky Monkeys — BGaming", byname)
        self.assertEqual(len({x["url"] for x in r}), len(r), "同一款重複")


class TestSitemap(unittest.TestCase):
    def test_playngo_sitemap(self):
        from datetime import datetime
        body = open(os.path.join(FIX, "playngo-sitemap-2026-10-11.xml"), encoding="utf-8").read()
        orig = H.sh
        H.sh = lambda url, timeout=20: body
        try:
            r, err = H.fetch_sitemap({"name": "Play'n GO", "endpoint": "x"}, datetime(2026, 10, 1, tzinfo=H.TPE))
        finally:
            H.sh = orig
        self.assertIsNone(err)
        games = {x["title"]: x for x in r if x["force_cat"] == "cat1"}
        self.assertIn("Redtail Robber Cash Vault Heist — Play'n GO", games)
        self.assertEqual(games["Redtail Robber Cash Vault Heist — Play'n GO"]["dt"].date().isoformat(), "2026-10-08")
        self.assertFalse(any(x["dt"].year == 9999 for x in r))


class TestPageMeta(unittest.TestCase):
    def test_parse(self):
        import page_meta as P
        body = ('<html><head><meta property="og:title" content="New Slot &amp; Co"/>'
                '<meta property="article:published_time" content="2026-10-10T08:00:00+00:00"/>'
                '<meta content="https://x.com/a.jpg" property="og:image"/></head>'
                '<body><article>' + "<p>" + "內文段落" * 30 + "</p>" * 1 + '</article></body></html>')
        self.assertEqual(P.meta(body, "og:title"), "New Slot & Co")
        self.assertEqual(P.meta(body, "og:image"), "https://x.com/a.jpg")
        self.assertEqual(P.published(body), ("2026-10-10T08:00:00+00:00", "metadata"))
        self.assertTrue(len(P.main_text(body, 3000)) > 40)

    def test_jsonld_date(self):
        import page_meta as P
        body = '<script type="application/ld+json">{"dateModified":"2026-10-11","datePublished":"2026-10-09T01:00:00Z"}</script>'
        self.assertEqual(P.published(body)[0], "2026-10-09T01:00:00Z")


class TestTiers(unittest.TestCase):
    def tier(self, remaining, end="2026-10-14", today="2026-09-28"):
        return H.pick_tier({"remaining": remaining, "plan": 1000, "period_end": end}, date.fromisoformat(today))[0][0]

    def test_levels(self):
        self.assertIn("充裕", self.tier(599))           # (599-20)/16 = 36
        self.assertIn("標準", self.tier(400))           # 23
        self.assertIn("節約", self.tier(290))           # 16
        self.assertIn("保命", self.tier(250))           # 14
        self.assertIn("保命", self.tier(99, today="2026-10-01"))   # 低於 100 一律保命（離重置還遠）

    def test_sprint(self):
        # v6.6.12 週期末衝刺：離重置 ≤2 天，剩餘點數在重置前用完（保留 10），不受 100 點保命限制
        t, info = H.pick_tier({"remaining": 172, "period_end": "2026-10-14"}, date(2026, 10, 13))
        self.assertIn("衝刺", t[0]); self.assertEqual(info["budget"], 81)
        t, info = H.pick_tier({"remaining": 92, "period_end": "2026-10-14"}, date(2026, 10, 14))
        self.assertIn("衝刺", t[0]); self.assertEqual(info["budget"], 82)
        self.assertIn("保命", self.tier(25, today="2026-10-13"))   # 幾乎用完就不衝

    def test_no_credit_info(self):
        self.assertIn("標準", H.pick_tier(None, date(2026, 9, 28))[0][0])


class TestInventory(unittest.TestCase):
    def test_placeholder(self):
        tbc = {"title": "Nigel of Ra", "first_seen": "2026-09-26",
               "sources": [{"name": "BigWinBoard（TBC，頁面 metadata 顯示 2026-09-16 舊日期）", "url": "x"}]}
        self.assertTrue(INV.is_placeholder(tbc))
        self.assertFalse(INV.is_placeholder({**tbc, "release_date": "2026-10-02"}))
        ok = {"title": "Aquamasters", "first_seen": "2026-09-23", "sources": [{"name": "BigWinBoard", "url": "x"}]}
        self.assertFalse(INV.is_placeholder(ok))


class TestSlotTiers(unittest.TestCase):
    """v6.7 🎰 區微創新分級：核心機制／微創新兩欄、三級排序、第三級一行格式。"""
    MD = """# 🎰 iGaming 市場日報 2026-11-12（週四）

🎰 Slot 3 ・ 🕹️ 非 Slot 0 ・ 🤝 主流 0 ・ 🇵🇭 菲律賓 0 ・ 📊 市場數據 0

## 🎰 Game Provider 新遊戲

### 01 Gems Plus – JILI

內文。對 PM 的意義：測試。

衍生調整：Fortune Gems 續作

參數：
- 廠牌：JILI
- 核心機制：Fortune Gems 3
- 微創新：倍數輪加入可累積的倍數，整輪不重置
- 遊戲類型：線上電子老虎機

來源：[A](https://example.com/a/1) · 日期：2026-11-12
圖片：無

### 02 Odd One – Studio X

內文。對 PM 的意義：測試。

衍生調整：全新

參數：
- 廠牌：Studio X
- 核心機制：-
- 微創新：盤面中央固定一格收集進度，滿格觸發重轉
- 遊戲類型：線上電子老虎機

來源：[B](https://example.com/b/2) · 日期：2026-11-12
圖片：無

#### 換皮／資料不足（一行帶過）
- Xmas Gold – Play'n GO｜Wrappin' Gold 系｜只換聖誕主題｜[SlotsLaunch](https://example.com/c/3) · 日期：2026-11-12

---

本日日報查詢約 10 個網站，其中提取 3 個資料來源並進行交叉比對
"""

    def test_parse_and_tier(self):
        rep = R.parse_md(self.MD)
        sec = rep["sections"][0]
        self.assertEqual([it["tier"] for it in sec["items"]], [1, 2])
        self.assertEqual(sec["count"], 3)
        b = sec["brief"][0]
        self.assertEqual((b["title"], b["mech"], b["reason"], b["date"]),
                         ("Xmas Gold – Play'n GO", "Wrappin' Gold 系", "只換聖誕主題", "2026-11-12"))
        self.assertEqual(len(R.all_items(sec)), 3)
        html = R.render_html(rep)
        self.assertIn('class="tier t1">N+1<', html)
        self.assertIn("換皮／資料不足", html)

    def test_rules(self):
        self.assertEqual(R.slot_tier({"spec": [["核心機制", "Super Ace II"], ["微創新", "無（換皮）"]]}), 3)
        self.assertEqual(R.slot_tier({"spec": [["核心機制", "未確認"], ["微創新", "未確認"]]}), 3)
        self.assertIsNone(R.slot_tier({"spec": [["盤面", "5x3"]]}))
        self.assertIn("Fortune Gems", F.prototypes())
        # 第二級排在第一級前面 → 錯誤
        rep = R.parse_md(self.MD)
        sec = rep["sections"][0]
        sec["items"].reverse()
        qa = F.QA()
        F.check_tiers(sec, date(2026, 11, 12), qa)
        self.assertTrue(any("第一級" in e for e in qa.errors))
        # 換皮用完整卡片 → 錯誤
        qa = F.QA()
        F.check_tier_fields({"spec": [["核心機制", "Super Ace"], ["微創新", "無（換皮）"]]}, "w", qa)
        self.assertTrue(qa.errors)

    def test_compact_card(self):
        md = self.MD.replace(
            "- Xmas Gold – Play'n GO｜Wrappin' Gold 系｜只換聖誕主題｜[SlotsLaunch](https://example.com/c/3) · 日期：2026-11-12",
            "##### 🔁（11/12 正式上線）Xmas Gold – Play'n GO\n核心機制：-\n判定：Wrappin' Gold 聖誕換皮\n"
            "參數：盤面 5×3｜最高倍率 1,525x｜RTP 96.2%\n摘要：沿用三罐收集，只換聖誕主題。\n"
            "來源：[SlotsLaunch](https://example.com/c/3) · 日期：2026-11-12\n圖片：https://example.com/x.jpg")
        rep = R.parse_md(md)
        b = rep["sections"][0]["brief"][0]
        self.assertEqual((b["title"], b["label"][:1], b["reason"], b["date"], b["image"]),
                         ("Xmas Gold – Play'n GO", "🔁", "Wrappin' Gold 聖誕換皮", "2026-11-12", "https://example.com/x.jpg"))
        self.assertEqual(b["params"][1], ["最高倍率", "1,525x"])
        html = R.render_html(rep)
        self.assertIn('class="mini"', html)
        self.assertIn("沿用三罐收集", html)
        qa = F.QA()
        F.check_tiers(rep["sections"][0], date(2026, 11, 12), qa)
        self.assertFalse(qa.errors)


class TestAsiaProviders(unittest.TestCase):
    """v6.7.3 亞洲廠商官網新作：每家各一份官網樣本，網站改版時這裡會先壞。"""
    D = os.path.join(ROOT, "tests", "fixtures", "asia")

    def rd(self, fn):
        return open(os.path.join(self.D, fn), encoding="utf-8").read()

    def setUp(self):
        import asia_providers as A
        self.A = A

    def test_pgsoft(self):
        games = self.A.parse_pg_list(self.rd("pgsoft-banner.json"))
        self.assertIn(("206", "Eureka Legends"), games)
        self.assertEqual(self.A.parse_pg_ct(self.rd("pgsoft-game-206.html"), 206), "2026-11-10")
        pages = {"https://api.pgsoft.com/Game/GetGamesBannerList/Language/1/live/true": self.rd("pgsoft-banner.json"),
                 "https://www.pgsoft.com/en/games/206/": self.rd("pgsoft-game-206.html")}
        out, err = self.A.fetch_pgsoft({}, lambda u: pages.get(u, ""))
        self.assertIsNone(err)
        it = out[0]
        self.assertEqual((it["title"], it["force_cat"], it["date_only"]), ("Eureka Legends — PG Soft", "cat1", True))
        self.assertIn("上線日 2026-11-10", it["excerpt"])

    def test_yellowbat(self):
        out = self.A.parse_yb(self.rd("yellowbat-games.json"))
        self.assertEqual(out[0]["title"], "Cupids Treasure — Yellow Bat")
        self.assertEqual(out[0]["dt"].strftime("%Y-%m-%d"), "2026-10-14")
        self.assertIn("Buzzin' Party — Yellow Bat", [i["title"] for i in out])

    def test_5g(self):
        out = self.A.parse_5g(self.rd("5g-game-launch.html"))
        names = [i["title"].split(" — ")[0] for i in out]
        self.assertEqual(names[:3], ["SUPER GEMS 5000", "Zeus 2000", "FIESTA 1000"])
        self.assertIn("SUGAR BANG 1000", names)              # 「Online Casino Game by 5G GAMES」要去掉
        self.assertEqual(out[0]["dt"].strftime("%Y-%m-%d"), "2026-11-11")

    def test_jili_first_seen(self):
        from datetime import datetime
        lst = self.rd("jili-games.html")
        games = self.A.parse_jili_list(lst)
        self.assertGreater(len(games), 100)
        self.assertEqual(self.A.parse_jili_month(self.rd("jili-detail-794.html")), "2026-06")
        cache = {}
        d1 = datetime(2026, 11, 13, tzinfo=self.A.TPE)
        out, err = self.A.fetch_jili(cache, d1, lambda u: lst)
        self.assertEqual(out, [])                              # 第一次跑：全部當基準，不算新作
        # 隔天官網多一款新 ID → 抓詳情頁，以首見日當日期
        new = '<div id="game999"><p class="subtitle">Super Ace Test</p></div>' + lst
        pages = {"https://jiligames.com/games": new,
                 "https://jiligames.com/PlusIntro/999?showGame=false": "Publish Time 2026.11"}
        out, _ = self.A.fetch_jili(cache, datetime(2026, 11, 14, tzinfo=self.A.TPE), lambda u: pages.get(u, ""))
        self.assertEqual([i["title"] for i in out], ["Super Ace Test — JILI"])
        self.assertIn("首見 2026-11-14", out[0]["excerpt"])
        self.assertNotIn("上線日", out[0]["excerpt"])        # 首見日不是上線日，不進上線日曆
        # 舊作重新上架（官網月份超過 3 個月）→ 不算
        old = '<div id="game998"><p class="subtitle">Old Game</p></div>' + new
        pages = {"https://jiligames.com/games": old, "https://jiligames.com/PlusIntro/998?showGame=false": "Publish Time 2025.03"}
        out, _ = self.A.fetch_jili(cache, datetime(2026, 11, 15, tzinfo=self.A.TPE), lambda u: pages.get(u, ""))
        self.assertNotIn("Old Game — JILI", [i["title"] for i in out])

    def test_omniplay(self):
        games = self.A.parse_op_list(self.rd("omniplay-games.html"))
        self.assertEqual(games.get("90"), "SUPER NEKO")
        self.assertEqual(self.A.parse_op_date(self.rd("omniplay-detail-90.html")), "2026-10-15")

    def test_fachai(self):
        out = self.A.parse_fachai(self.rd("fachai-game-news.md"))
        got = {i["title"]: i["dt"].strftime("%Y-%m-%d") for i in out}
        self.assertEqual(got.get("Wukong Moreways — FA CHAI"), "2026-09-17")
        self.assertEqual(got.get("Queen Of Inca 2 — FA CHAI"), "2026-08-12")
        self.assertTrue(all(i["url"].startswith("https://fachaigaming.com/en/news/game/") for i in out))

    def test_brand_lists(self):
        import build_slot_db as DB
        self.assertEqual(DB.brand_b("OMNIPLAY（尊博）"), 6)
        self.assertEqual(DB.brand_b("5G Games"), 4)
        self.assertTrue(H.BIG_GP.search("OMNIPLAY unveils") and H.BIG_GP.search("Yellow Bat") and H.BIG_GP.search("5G Games"))


if __name__ == "__main__":
    unittest.main()
